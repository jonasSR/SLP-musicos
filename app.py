import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import urllib.parse
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from firebase_admin import auth as firebase_auth
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from werkzeug.utils import secure_filename
import json
from firebase_admin import credentials, initialize_app
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timedelta


# ======================================================
# 🔧 CONFIGURAÇÃO INICIAL
# ======================================================
base_path = os.path.dirname(os.path.abspath(__file__))

# Tenta pegar as credenciais do Firebase da variável de ambiente
cred_json = os.environ.get("FIREBASE_CREDENTIALS")

if cred_json:
    # Se existir, usa a variável de ambiente
    cred_dict = json.loads(cred_json)
    cred = credentials.Certificate(cred_dict)
else:
    # Se não existir, usa o arquivo local
    cred = credentials.Certificate(os.path.join(base_path, "serviceAccountKey.json"))

# Inicializa o Firebase apenas UMA vez
if not firebase_admin._apps:
    initialize_app(cred)

db = firestore.client()


app = Flask(__name__)
# 3. ATIVA O CORS (Logo aqui no começo!)
CORS(app)

# 🔐 Sessão
app.secret_key = "FLUXO_DYNAMO_SLP_2024_KEY"
app.config['SESSION_PERMANENT'] = False

# AGORA você configura o que depende do 'app'
UPLOAD_FOLDER = os.path.join('static', 'img')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ======================================================
# 🔐 DECORATOR DE PROTEÇÃO (SEM MUDAR LÓGICA)
# ======================================================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated
from config import ESTILOS


@app.context_processor
def inject_estilos():
    return dict(estilos=ESTILOS)


@app.context_processor
def inject_firebase():
    return {
        "firebase_config": {
            "apiKey": os.getenv("FIREBASE_API_KEY"),
            "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
            "projectId": os.getenv("FIREBASE_PROJECT_ID"),
            "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
            "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
            "appId": os.getenv("FIREBASE_APP_ID")
        }
    }
# ======================================================
# 🌎 ROTAS PÚBLICAS
# ======================================================
@app.route('/')
def index():
    musicos_ref = db.collection('artistas')
    musicos = []
    
    # 1. Busca feedbacks aprovados para saber quem é relevante
    feedbacks_ref = db.collection('feedbacks').where('status', '==', 'aprovado').stream()
    contagem_feedbacks = {}

    for f in feedbacks_ref:
        f_dados = f.to_dict()
        aid = f_dados.get('artista_id')
        if aid:
            contagem_feedbacks[aid] = contagem_feedbacks.get(aid, 0) + 1

    # 2. Processa os músicos
    for doc in musicos_ref.stream():
        dados = doc.to_dict()
        dados['id'] = doc.id
        dados['qtd_fb'] = contagem_feedbacks.get(doc.id, 0)
        musicos.append(dados)

    # 3. DESTAQUES (Mantido conforme sua solicitação)
    destaques = [m for m in musicos if m.get('qtd_fb', 0) > 0]
    destaques = sorted(destaques, key=lambda x: x['qtd_fb'], reverse=True)[:3]

    # --- NOVAS ATUALIZAÇÕES PARA ARTISTAS LOCAIS ---
    
    # 4. Captura a cidade selecionada no filtro
    cidade_selecionada = request.args.get('cidade')
    
    # 5. Gera lista de cidades únicas para o componente de filtro (Dropdown)
    # Filtra apenas músicos que têm o campo 'cidade' preenchido
    # m.get('cidade') busca o valor dentro de cada documento no banco
    cidades_disponiveis = sorted(list(set([
        str(m.get('cidade')).strip() 
        for m in musicos 
        if m.get('cidade')
    ])))
    
    # 6. Filtra os artistas para a seção local
    if cidade_selecionada:
        artistas_locais = [m for m in musicos if str(m.get('cidade')).strip().lower() == cidade_selecionada.strip().lower()]
    else:
        # Se nenhuma cidade for selecionada, mostramos os 4 músicos mais recentes (ou os primeiros da lista)
        artistas_locais = musicos[:4]

    return render_template(
        'index.html', 
        musicos=musicos, 
        destaques=destaques,
        artistas_locais=artistas_locais,
        cidades_disponiveis=cidades_disponiveis,
        cidade_nome=cidade_selecionada
    )


@app.route('/musico/<musico_id>')
def perfil_musico(musico_id):
    """Página detalhada de cada artista"""
    doc_ref = db.collection('artistas').document(musico_id)
    
    # Incrementa cliques
    doc_ref.update({'cliques': firestore.Increment(1)})

    musico = doc_ref.get()
    if not musico.exists:
        return "Músico não encontrado", 404

    dados = musico.to_dict()
    
    # Buscar Agenda
    agenda_ref = doc_ref.collection('agenda').stream()
    agenda = [show.to_dict() for show in agenda_ref]

    # --- NOVO: BUSCAR FEEDBACKS APROVADOS ---
    feedbacks_ref = db.collection('feedbacks')\
        .where('artista_id', '==', musico_id)\
        .where('status', '==', 'aprovado')\
        .stream()
    
    feedbacks_aprovados = []
    total_estrelas = 0
    
    for f in feedbacks_ref:
        f_dados = f.to_dict()
        feedbacks_aprovados.append(f_dados)
        total_estrelas += f_dados.get('estrelas', 5)

    # Cálculo de estatísticas para o perfil
    qtd_fas = len(feedbacks_aprovados)
    media_estrelas = round(total_estrelas / qtd_fas, 1) if qtd_fas > 0 else 0

    return render_template(
        'perfil.html',
        musico=dados,
        agenda=agenda,
        feedbacks=feedbacks_aprovados, # Lista para o Mural
        qtd_fas=qtd_fas,               # Contador de fãs
        media_estrelas=media_estrelas, # Média de estrelas
        id=musico_id
    )


# ======================================================
# 🔐 AUTENTICAÇÃOdef login_page():
# ======================================================
@app.route('/login')
def login_page():
    veio_da_venda = request.args.get('pago') == 'true'

    if veio_da_venda:
        session['mostrar_boas_vindas'] = True

    mostrar_modal = session.pop('mostrar_boas_vindas', False)

    config = {
        "apiKey": os.getenv("FIREBASE_API_KEY"),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
        "projectId": os.getenv("FIREBASE_PROJECT_ID"),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
        "appId": os.getenv("FIREBASE_APP_ID")
    }

    return render_template(
        'login.html',
        firebase_config=config,
        confirmacao_venda=mostrar_modal
    )


@app.route('/set_session', methods=['POST'])
def set_session():
    data = request.get_json()
    email = data.get('email')
    session['user_email'] = email
    
    # Verifica na hora se é estabelecimento
    doc_estab = db.collection('estabelecimentos').document(email).get()
    if doc_estab.exists:
        session['user_tipo'] = 'estabelecimento'
    else:
        session['user_tipo'] = 'musico'
        
    return jsonify({"status": "success"}), 200


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ======================================================
# 🔒 ÁREA PRIVADA
# ======================================================
@app.route('/check_user_type')
def check_user_type():
    email = request.args.get('email')
    
    # 1. Checa se o cadastro está TOTALMENTE COMPLETO
    # Verifica em Estabelecimentos
    if db.collection('estabelecimentos').document(email).get().exists:
        return jsonify({"status": "completo", "redirect": "/dashboard-estabelecimento"})
    
    # Verifica em Artistas
    artista = db.collection('artistas').where('dono_email', '==', email).limit(1).get()
    if len(list(artista)) > 0:
        return jsonify({"status": "completo", "redirect": "/dashboard"})

    # 2. Se não está completo, checa se ele já ESCOLHEU um tipo na modal antes
    # Buscamos na coleção genérica de 'usuarios' criada no Auth
    user_query = db.collection('usuarios').where('email', '==', email).limit(1).get()
    user_docs = list(user_query)
    
    if len(user_docs) > 0:
        dados = user_docs[0].to_dict()
        tipo = dados.get('tipo')
        
        if tipo in ['musico', 'estabelecimento']:
            return jsonify({"status": "pendente", "tipo": tipo})

    # 3. Se chegou aqui, ele nunca escolheu nada (abrir modal)
    return jsonify({"status": "novo"})


@app.route('/dashboard')
@login_required
def dashboard():
    email_logado = session.get('user_email')
    
    # 🔍 1. BUSCA DADOS DA CONTA DO USUÁRIO
    # 🔍 1. BUSCA DADOS DA CONTA DO USUÁRIO (FORMA CORRETA)
    user_query = db.collection('usuarios').where('email', '==', email_logado).limit(1).stream()
    user_docs = list(user_query)

    if not user_docs:
        session.clear()
        flash("Sua conta não foi encontrada ou foi desativada.", "danger")
        return redirect(url_for('login'))

    dados_usuario = user_docs[0].to_dict()
    tipo_usuario = dados_usuario.get('tipo')
    pagou = dados_usuario.get('acesso_pago', False)


    # 🔍 2. BUSCA DADOS DO PERFIL DO ARTISTA (Necessário para a lógica de bloqueio)
    artista_query = db.collection('artistas').where('dono_email', '==', email_logado).limit(1).stream()
    artista_docs = list(artista_query)
    artista_dados = None

    # Variável que controla a exibição da modal no HTML
    bloqueado = False

    # 🛑 REGRA 1: Se ainda não escolheu o tipo (Músico/Estabelecimento)
    if not tipo_usuario:
        return render_template('dashboard.html', pedidos=[], musico=None, agenda=[], feedbacks=[], notificacoes_fas=0, total_cliques=0, media_estrelas=0, bloqueado=False)

    # 🛑 REGRA 2: LÓGICA DE ACESSO E PAGAMENTO (PÁGINA DE VENDAS + INTERNO)
    if tipo_usuario == 'musico':

        # ✅ PAGOU → acesso normal
        if pagou:
            bloqueado = False

        # ❌ NÃO PAGOU → SEMPRE bloqueia a tela
        else:
            bloqueado = True



    # 🟢 SE FOR ESTABELECIMENTO
    if tipo_usuario == 'estabelecimento':
        doc_estab = db.collection('estabelecimentos').document(email_logado).get()
        if not doc_estab.exists:
            return redirect(url_for('abrir_pagina_estabelecimento'))
        return redirect(url_for('dashboard_estabelecimento'))

    # 🟢 PROCESSAMENTO DE DADOS DO ARTISTA (Para o Dashboard)
    pedidos, agenda, feedbacks = [], [], []
    total_cliques, notificacoes_fas, total_estrelas = 0, 0, 0

    if artista_docs:
        doc = artista_docs[0]
        artista_id = doc.id
        artista_dados = doc.to_dict()
        artista_dados['id'] = artista_id
        
        total_cliques = artista_dados.get('cliques', 0)

        # Carregar Pedidos de Reserva
        pedidos_ref = db.collection('pedidos_reserva').where('musico_id', '==', artista_id).stream()
        for p in pedidos_ref:
            p_dados = p.to_dict()
            p_dados['id'] = p.id
            pedidos.append(p_dados)
        pedidos.sort(key=lambda x: x.get('criado_em') if x.get('criado_em') else 0, reverse=True)

        # Carregar Agenda
        agenda_ref = db.collection('artistas').document(artista_id).collection('agenda').order_by('data_completa').stream()
        for s in agenda_ref:
            s_dados = s.to_dict()
            s_dados['id'] = s.id
            agenda.append(s_dados)

        # Carregar Feedbacks
        feedbacks_ref = db.collection('feedbacks').where('artista_email', '==', email_logado).stream()
        for f in feedbacks_ref:
            f_dados = f.to_dict()
            f_dados['id'] = f.id
            feedbacks.append(f_dados)
            total_estrelas += int(f_dados.get('estrelas', 0))
            if f_dados.get('status') == 'pendente':
                notificacoes_fas += 1

    qtd_feedbacks = len(feedbacks)
    media_estrelas = round(total_estrelas / qtd_feedbacks, 1) if qtd_feedbacks > 0 else 0.0

    data_ativacao = None
    data_vencimento = None
    dias_restantes = None

    if dados_usuario.get('data_pagamento'):
        from datetime import datetime, timedelta
        
        # Converte o timestamp do Firestore para objeto datetime do Python
        dt_pagamento = dados_usuario['data_pagamento']
        data_ativacao = dt_pagamento.strftime('%d/%m/%Y')
        
        # Calcula vencimento (30 dias depois)
        dt_vencimento = dt_pagamento + timedelta(days=30)
        data_vencimento = dt_vencimento.strftime('%d/%m/%Y')

        # Calcula a diferença de dias para o alerta de cor
        hoje = datetime.now()
        # Garante que dt_vencimento não tenha timezone se 'hoje' não tiver, ou vice-versa
        diff = dt_vencimento.replace(tzinfo=None) - hoje.replace(tzinfo=None)
        dias_restantes = diff.days

    return render_template(
        'dashboard.html',
        pedidos=pedidos,
        musico=artista_dados,
        agenda=agenda,
        feedbacks=feedbacks,
        notificacoes_fas=notificacoes_fas,
        total_cliques=total_cliques,
        media_estrelas=media_estrelas,
        bloqueado=bloqueado,
        data_ativacao=data_ativacao,
        data_vencimento=data_vencimento,
        dias_restantes=dias_restantes,
        pagou=pagou
    )

@app.route('/webhook-stripe', methods=['POST'])
def webhook_stripe():
    payload = request.get_data()
    try:
        event = json.loads(payload)
    except Exception as e:
        return jsonify({"status": "error", "message": "Payload inválido"}), 400

    tipo_evento = event['type']
    data_object = event['data']['object']
    email_cliente = data_object.get('customer_details', {}).get('email')

    if not email_cliente:
        return jsonify({"status": "success", "message": "Sem email no evento"}), 200

    # 🔍 BUSCA O DOCUMENTO
    user_query = db.collection('usuarios').where('email', '==', email_cliente).limit(1).stream()
    user_docs = list(user_query)

    # 1. ✅ PAGAMENTO APROVADO
    if tipo_evento == 'checkout.session.completed':
        if user_docs:
            # USUÁRIO JÁ EXISTE: Apenas atualiza
            user_ref = user_docs[0].reference
            user_ref.update({
                'acesso_pago': True,
                'status_financeiro': 'pago',
                'data_pagamento': firestore.SERVER_TIMESTAMP
            })
            print(f"✅ SUCESSO: Cadastro existente de {email_cliente} atualizado para PAGO.")
        else:
            # USUÁRIO NÃO EXISTE (Vindo da página de vendas): Cria o documento prévio
            db.collection('usuarios').document(email_cliente).set({
                'email': email_cliente,
                'acesso_pago': True,
                'status_financeiro': 'pago',
                'tipo': 'musico', # Já pré-define como músico
                'data_pagamento': firestore.SERVER_TIMESTAMP,
                'criado_via': 'pagina_vendas'
            })
            print(f"✨ NOVO: Usuário {email_cliente} pagou na LP e teve documento criado.")

    # 2. ❌ PAGAMENTO FALHOU / EXPIROU
    elif tipo_evento in ['checkout.session.async_payment_failed', 'checkout.session.expired']:
        if user_docs:
            user_ref = user_docs[0].reference
            user_ref.update({
                'acesso_pago': False,
                'status_financeiro': 'falha/expirado'
            })

    return jsonify({"status": "success"}), 200    



# ======================================================
# LOGIN GOOGLE
# ======================================================
@app.route('/login_google', methods=['POST'])
def login_google():
    data = request.get_json()
    id_token = data.get('idToken')
    
    try:
        # Valida o token vindo do front-end
        decoded_token = firebase_auth.verify_id_token(id_token)
        email_logado = decoded_token['email']
        nome = decoded_token.get('name', 'Usuário Google')
        foto = decoded_token.get('picture', '')

        # Inicia a sessão
        session['user_email'] = email_logado
        
        # 🔍 1. BUSCA DADOS DA CONTA DO USUÁRIO
        user_ref = db.collection('usuarios').document(email_logado)
        user_doc = user_ref.get()

        if not user_doc.exists:
            # Cria exatamente como você pediu
            user_ref.set({
                'email': email_logado,
                'nome': nome,
                'foto_google': foto,
                'tipo': None,
                'acesso_pago': False,
                'criado_em': firestore.SERVER_TIMESTAMP
            })
            # Recarrega o doc recém criado para seguir a lógica abaixo
            user_doc = user_ref.get()

        dados_usuario = user_doc.to_dict()
        tipo_usuario = dados_usuario.get('tipo')
        pagou = dados_usuario.get('acesso_pago', False)

        # 🔍 2. BUSCA DADOS DO PERFIL DO ARTISTA
        artista_query = db.collection('artistas').where('dono_email', '==', email_logado).limit(1).stream()
        artista_docs = list(artista_query)
        artista_dados = None
        bloqueado = False

        # 🛑 REGRA 1: Se ainda não escolheu o tipo
        if not tipo_usuario:
            return jsonify({"status": "success", "redirect": "/dashboard"}), 200

        # 🛑 REGRA 2: LÓGICA DE ACESSO E PAGAMENTO
        if tipo_usuario == 'musico':
            if pagou:
                bloqueado = False
            else:
                bloqueado = True

        # 🟢 SE FOR ESTABELECIMENTO
        if tipo_usuario == 'estabelecimento':
            doc_estab = db.collection('estabelecimentos').document(email_logado).get()
            if not doc_estab.exists:
                return jsonify({"status": "success", "redirect": "/abrir_pagina_estabelecimento"}), 200
            return jsonify({"status": "success", "redirect": "/dashboard_estabelecimento"}), 200

        # 🟢 PROCESSAMENTO DE DADOS DO ARTISTA (Lógica completa do Dashboard)
        pedidos, agenda, feedbacks = [], [], []
        total_cliques, notificacoes_fas, total_estrelas = 0, 0, 0

        if artista_docs:
            doc = artista_docs[0]
            artista_id = doc.id
            artista_dados = doc.to_dict()
            artista_dados['id'] = artista_id
            total_cliques = artista_dados.get('cliques', 0)

            pedidos_ref = db.collection('pedidos_reserva').where('musico_id', '==', artista_id).stream()
            for p in pedidos_ref:
                p_dados = p.to_dict()
                p_dados['id'] = p.id
                pedidos.append(p_dados)
            pedidos.sort(key=lambda x: x.get('criado_em') if x.get('criado_em') else 0, reverse=True)

            agenda_ref = db.collection('artistas').document(artista_id).collection('agenda').order_by('data_completa').stream()
            for s in agenda_ref:
                s_dados = s.to_dict()
                s_dados['id'] = s.id
                agenda.append(s_dados)

            feedbacks_ref = db.collection('feedbacks').where('artista_email', '==', email_logado).stream()
            for f in feedbacks_ref:
                f_dados = f.to_dict()
                f_dados['id'] = f.id
                feedbacks.append(f_dados)
                total_estrelas += int(f_dados.get('estrelas', 0))
                if f_dados.get('status') == 'pendente':
                    notificacoes_fas += 1

        qtd_feedbacks = len(feedbacks)
        media_estrelas = round(total_estrelas / qtd_feedbacks, 1) if qtd_feedbacks > 0 else 0.0

        # Retorna o sucesso para o JS redirecionar para o local correto baseado na lógica
        return jsonify({
            "status": "success", 
            "redirect": "/dashboard",
            "bloqueado": bloqueado
        }), 200
        
    except Exception as e:
        print(f"Erro na validação Google: {e}")
        return jsonify({"status": "error", "message": "Token inválido"}), 401


# 🔔 ROTA: Marcar como lido
@app.route('/marcar_lido/<pedido_id>', methods=['POST'])
@login_required
def marcar_lido(pedido_id):
    db.collection('pedidos_reserva').document(pedido_id).update({'lido': True})
    return jsonify({"status": "success"})


# ======================================================
# APROVAR/DESAPROVAR FEEDBACK-DASHBOARD (CORRIGIDO PARA FIRESTORE)
# ======================================================
@app.route('/aprovar_feedback/<string:id>', methods=['POST'])
def aprovar_feedback(id):
    try:
        # No Firestore, acessamos a coleção e o documento pelo ID (string)
        feedback_ref = db.collection('feedbacks').document(id)
        
        # Altera o campo status para 'aprovado'
        feedback_ref.update({
            'status': 'aprovado'
        })
        
        return redirect('/dashboard')
    except Exception as e:
        print(f"Erro ao aprovar: {e}")
        return redirect('/dashboard')


@app.route('/remover_feedback/<string:id>', methods=['POST'])
def remover_feedback(id):
    try:
        # No Firestore, deletamos o documento diretamente
        db.collection('feedbacks').document(id).delete()
        
        return redirect('/dashboard')
    except Exception as e:
        print(f"Erro ao remover: {e}")
        return redirect('/dashboard')


# ======================================================
# ENVIAR FEEDBACK-PERFIL USUARIO
# ======================================================
@app.route('/api/enviar_feedback', methods=['POST'])
def api_enviar_feedback():
    dados = {
        'artista_id': request.form.get('artista_id'),
        'artista_email': request.form.get('artista_email'),
        'nome_fa': request.form.get('nome_fa'),
        'comentario': request.form.get('comentario'),
        'estrelas': int(request.form.get('estrelas', 5)),
        'status': 'pendente', # Importante: entra como pendente
        'timestamp': firestore.SERVER_TIMESTAMP
    }
    db.collection('feedbacks').add(dados)
    return jsonify({'status': 'success'})


# ======================================================
# CADASTRAR MÚSICO-DASHBOARD (ATUALIZADO COM TIPO)
# ======================================================
@app.route('/api_cadastrar_musico', methods=['POST'])
@login_required
def cadastrar_musico():
    nome = request.form.get('nome')
    tipo = request.form.get('tipo') 
    estilo = request.form.get('estilo')
    cidade = request.form.get('cidade')
    estado = request.form.get('estado')
    bio = request.form.get('bio')
    foto_url = request.form.get('foto_url')
    file = request.files.get('foto_arquivo')
    
    # --- NOVOS CAMPOS REDES SOCIAIS ---
    instagram = request.form.get('instagram')
    facebook = request.form.get('facebook')
    youtube = request.form.get('youtube')
    # ----------------------------------

    # 1. ACRESCENTADO: Captura o link do formulário
    vibracao_link = request.form.get('vibracao_link')

    email = session['user_email']

    # 🔎 Busca artista existente
    artista_query = (
        db.collection('artistas')
        .where('dono_email', '==', email)
        .limit(1)
        .stream()
    )

    artista_doc = None
    artista_data = None
    for doc in artista_query:
        artista_doc = doc
        artista_data = doc.to_dict()
        break

    if not artista_doc:
        artista_data = {}

    # 🧠 Foto atual (fallback)
    final_path = artista_data.get('foto')

    if foto_url:
        final_path = foto_url

    if file and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filename = f"upload_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        final_path = f"/static/img/{filename}"

    # Dicionário de dados atualizado
    dados = {
        'nome': nome,
        'tipo': tipo,
        'cidade': cidade,
        'estado': estado,
        'estilo': estilo,
        'bio': bio,
        'instagram': instagram, 
        'facebook': facebook,   
        'youtube': youtube, 
        # 2. ACRESCENTADO: Adiciona o link ao dicionário que vai para o Firebase
        'vibracao_link': vibracao_link, 
        'dono_email': email,
        'timestamp': firestore.SERVER_TIMESTAMP
    }

    if final_path:
        dados['foto'] = final_path

    if artista_doc:
        db.collection('artistas').document(artista_doc.id).update(dados)
    else:
        dados['cliques'] = 0 
        db.collection('artistas').add(dados)

    return redirect(url_for('dashboard'))


# ======================================================
# 🎵 CONTRATAR BANDA
# ======================================================
@app.route('/reservar', methods=['POST'])
def reservar():
    # 1. COLETA TODOS OS NOVOS DADOS DO FORMULÁRIO
    musico_id = request.form.get('musico_id')
    nome_solicitante = request.form.get('nome_solicitante')
    email_solicitante = request.form.get('email_solicitante')
    telefone_solicitante = request.form.get('telefone_solicitante')
    data_evento = request.form.get('data_evento')
    local_evento = request.form.get('local_evento')
    tipo_evento = request.form.get('tipo')
    
    try:
        # 2. BUSCA O E-MAIL DA BANDA NO BANCO DE DADOS
        musico_ref = db.collection('artistas').document(musico_id).get()
        
        if not musico_ref.exists:
            return jsonify({"status": "error", "message": "Banda não encontrada"}), 404
            
        dados_musico = musico_ref.to_dict()
        email_da_banda = dados_musico.get('dono_email')

        # 3. SALVA O PEDIDO DETALHADO NO BANCO
        # Adicionamos os campos de contato para você poder intermediar depois
        db.collection('pedidos_reserva').add({
            'musico_id': musico_id,
            'nome_contratante': nome_solicitante,
            'email_contratante': email_solicitante,
            'telefone_contratante': telefone_solicitante,
            'data_evento': data_evento,
            'local_evento': local_evento,
            'tipo_evento': tipo_evento,
            'status': 'novo',
            'lido': False,
            'criado_em': firestore.SERVER_TIMESTAMP,
            # Mantemos quem enviou (caso esteja logado) para auditoria
            'usuario_logado': session.get('user_email', 'Visitante')
        })

        # Retorno de sucesso
        return jsonify({
            "status": "success", 
            "message": f"Pedido enviado com sucesso para a banda!",
            "redirect": url_for('perfil_musico', musico_id=musico_id)
        })

    except Exception as e:
        print(f"Erro ao processar reserva: {e}")
        return jsonify({"status": "error", "message": "Erro interno no servidor"}), 500
    

@app.route('/adicionar_agenda', methods=['POST'])
@login_required
def adicionar_agenda():
    email = session['user_email']
    data_input = request.form.get('data_show')
    horario = request.form.get('horario_show') # NOVO
    nome_festa = request.form.get('nome_festa') # NOVO
    local = request.form.get('local')
    cidade = request.form.get('cidade')

    artista_query = db.collection('artistas').where('dono_email', '==', email).limit(1).stream()
    artista_id = None
    for doc in artista_query:
        artista_id = doc.id

    if artista_id:
        ano, mes, dia = data_input.split('-')
        
        db.collection('artistas').document(artista_id).collection('agenda').add({
            'data_dia': dia,
            'data_mes': mes,
            'data_completa': data_input,
            'horario': horario,      # SALVANDO NO BANCO
            'nome_festa': nome_festa, # SALVANDO NO BANCO
            'local': local,
            'cidade': cidade,
            'criado_em': firestore.SERVER_TIMESTAMP
        })
    
    return redirect(url_for('dashboard'))



@app.route('/remover_agenda/<show_id>', methods=['POST'])
@login_required
def remover_agenda(show_id):
    email = session['user_email']
    artista_query = db.collection('artistas').where('dono_email', '==', email).limit(1).stream()
    
    for doc in artista_query:
        db.collection('artistas').document(doc.id).collection('agenda').document(show_id).delete()
        
    return redirect(url_for('dashboard'))  

    
# ======================================================
# TROCAR SENHA USUARIO
# ======================================================   
@app.route('/api_registrar_troca_senha', methods=['POST'])
@login_required
def registrar_troca_senha():
    data = request.get_json()
    nova_senha = data.get('nova_senha')
    email = session.get('user_email')

    # 🔎 Busca usuário no Firebase
    user = firebase_auth.get_user_by_email(email)

    # 🔐 Atualiza senha (sobrescreve a antiga)
    firebase_auth.update_user(
        user.uid,
        password=nova_senha
    )

    # 🚨 INVALIDA TODOS OS LOGINS ANTIGOS
    firebase_auth.revoke_refresh_tokens(user.uid)

    return jsonify({
        "status": "success",
        "message": "Senha alterada e sessões antigas invalidadas"
    })

    
@app.route('/api_login_interno', methods=['POST'])
def login_interno():
    data = request.get_json()
    email = data.get('email')
    senha_digitada = data.get('password')

    user_ref = db.collection('usuarios').document(email)
    user_doc = user_ref.get()

    if not user_doc.exists:
        return jsonify({"status": "use_firebase"})

    user_data = user_doc.to_dict()

    if 'password' not in user_data:
        return jsonify({"status": "use_firebase"})

    if check_password_hash(user_data['password'], senha_digitada):
        session['user_email'] = email
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Senha incorreta"}), 401
 

# ======================================================
# EXCLUIR MENSAGENS
# ======================================================
@app.route('/excluir_pedidos', methods=['POST'])
@login_required
def excluir_pedidos():
    try:
        data = request.get_json()
        ids = data.get('ids', [])

        if not ids:
            return jsonify({'status': 'error', 'message': 'Nenhuma mensagem selecionada.'}), 400

        pedidos_ref = db.collection('pedidos_reserva')

        for pedido_id in ids:
            pedidos_ref.document(pedido_id).delete()

        # O JavaScript vai ler este 'success' para mostrar o alert
        return jsonify({'status': 'success', 'message': 'Excluído com sucesso'})

    except Exception as e:
        print(f"Erro ao excluir: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500



@app.route('/api/artistas_vitrine')
def api_artistas_vitrine():
    try:
        # Pega 4 artistas aleatórios ou os últimos
        musicos_ref = db.collection('artistas').limit(4).stream()
        musicos = []

        for doc in musicos_ref:
            dados = doc.to_dict()
            foto = dados.get('foto', '')
            
            # Se a foto for um caminho interno, coloca o domínio completo
            if foto and foto.startswith('/static'):
                foto = f"https://slp-musicos-3.onrender.com{foto}"

            musicos.append({
                'id': doc.id,
                'nome': dados.get('nome'),
                'estilo': dados.get('estilo'),
                'foto': foto
            })

        return jsonify(musicos)
    except Exception as e:
        return jsonify({"error": str(e)}), 500        
    

# 1. ROTA PARA EXIBIR O FORMULÁRIO DE CADASTRO
@app.route('/cadastro-estabelecimento')
@login_required
def abrir_pagina_estabelecimento():
    return render_template('cadastro_estabelecimento.html')


# 2. ROTA QUE PROCESSA O CADASTRO (API)
@app.route('/api_cadastrar_estabelecimento', methods=['POST'])
@login_required
def api_cadastrar_estabelecimento():
    email_dono = session.get('user_email')
    
    # 1. Busca os dados atuais no banco antes de salvar
    doc_ref = db.collection('estabelecimentos').document(email_dono)
    doc_atual = doc_ref.get()
    
    # Define o caminho da foto como o que já está no banco (caso exista)
    foto_final = "/static/img/default_estabelecimento.jpg"
    if doc_atual.exists:
        foto_final = doc_atual.to_dict().get('foto', foto_final)

    # 2. Processa a nova foto APENAS se o usuário enviou uma
    file = request.files.get('foto_estabelecimento')
    if file and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"estabel_{email_dono.replace('@', '_')}_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
        foto_final = f"/static/img/{unique_filename}"

    # 3. Monta os dados (mantendo a foto antiga ou a nova)
    dados = {
        'nome': request.form.get('nome'),
        'cidade': request.form.get('cidade'),
        'estado': request.form.get('estado'),
        'instagram': request.form.get('instagram'),
        'facebook': request.form.get('facebook'),
        'foto': foto_final, # Aqui está a segurança: ela nunca será vazia
        'dono_email': email_dono,
        'tipo': 'estabelecimento',
        'timestamp': firestore.SERVER_TIMESTAMP
    }

    doc_ref.set(dados)
    return redirect(url_for('dashboard_estabelecimento'))


# 3. ROTA DO DASHBOARD EXCLUSIVO DO ESTABELECIMENTO
@app.route('/dashboard-estabelecimento')
@login_required
def dashboard_estabelecimento():
    email_usuario = session.get('user_email')
    
    # Busca o documento diretamente pelo ID (que definimos como o e-mail)
    doc_ref = db.collection('estabelecimentos').document(email_usuario)
    doc = doc_ref.get()
    
    if doc.exists:
        dados_estab = doc.to_dict()
        dados_estab['id'] = doc.id
        return render_template('dashboard_estabelecimento.html', estab=dados_estab)
    else:
        # Se não houver cadastro, redireciona para o formulário
        return redirect(url_for('abrir_pagina_estabelecimento'))


@app.route('/palco')
def lista_palcos():
    # 1. Acessa a coleção 'estabelecimentos' no Firestore
    estab_ref = db.collection('estabelecimentos')
    
    # 2. Pega todos os documentos (estabelecimentos cadastrados)
    docs = estab_ref.stream()
    
    # 3. Converte os documentos em uma lista de dicionários para o HTML
    todos_estabs = []
    for doc in docs:
        dados = doc.to_dict()
        dados['id'] = doc.id  # Garante que o ID (e-mail) esteja disponível
        todos_estabs.append(dados)
    
    # 4. Renderiza o template passando a lista correta
    return render_template('palco.html', todos_estabelecimentos=todos_estabs)


@app.route('/artistas')
def lista_artistas():
    tipo_original = request.args.get('tipo', '') # Recebe "músico independente"
    
    # TRADUÇÃO PARA O BANCO DE DADOS
    # Se receber "músico independente", vira "musico" para buscar no Firebase
    termo_busca = tipo_original.lower()
    if termo_busca == 'músico independente':
        termo_busca = 'musico'

    # 1. Ajuste para o nome do arquivo template
    tipo_limpo = termo_busca.replace(' ', '_')
    
    artistas_ref = db.collection('artistas')
    
    # 2. Agora a busca usa o termo traduzido ("musico")
    docs = artistas_ref.where('tipo', '==', termo_busca).stream()
    
    lista = []
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        lista.append(d)

    try:
        # Retorna lista_musico.html com os dados encontrados
        return render_template(f'lista_{tipo_limpo}.html', musicos=lista, categoria=tipo_original)
    except Exception as e:
        print(f"Erro ao carregar template: {e}")
        return f"Erro: Arquivo lista_{tipo_limpo}.html não encontrado", 404
    
    
@app.route('/api_deletar_dados_usuario', methods=['POST'])
def api_deletar_dados_usuario():
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({"status": "error", "message": "E-mail não fornecido"}), 400

        # 1. Deleta da coleção 'usuarios' (onde você viu na imagem)
        users_ref = db.collection('usuarios').document(email)
        for doc in users_ref:
            doc.reference.delete()

        # 2. Deleta da coleção 'artistas' (caso tenha começado algo)
        artistas_ref = db.collection('artistas').where('dono_email', '==', email).stream()
        for doc in artistas_ref:
            doc.reference.delete()

        # 3. Deleta da coleção 'estabelecimentos' (caso seja o caso)
        db.collection('estabelecimentos').document(email).delete()

        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Erro ao deletar dados do Firestore: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api_deletar_dados_usuario', methods=['POST'])
def api_excluir_conta_definitiva(): # <--- Mudei o nome da função aqui
    try:
        data = request.get_json()
        email = data.get('email')
        # ... resto do seu código de deletar ...
        db.collection('estabelecimentos').document(email).delete()
        
        user_query = db.collection('usuarios').document(email)

        for doc in user_query:
            doc.reference.delete()

        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ======================================================
# 🚀 START
# ======================================================

if __name__ == '__main__':
    app.run(debug=True)