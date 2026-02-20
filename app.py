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
from flask import jsonify
import re
from markupsafe import Markup
from num2words import num2words
import uuid



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


@app.route('/')
def index():
    musicos_ref = db.collection('artistas')
    musicos = []
    
    # 1. Busca feedbacks (Removido filtro 'aprovado' para bater com a lógica do perfil que você usa)
    # Se você quer que a média seja igual, o critério de busca tem que ser o mesmo
    feedbacks_ref = db.collection('feedbacks').stream()
    
    # Dicionário para guardar soma e quantidade por artista
    stats_feedback = {} 

    for f in feedbacks_ref:
        f_dados = f.to_dict()
        aid = f_dados.get('artista_id')
        status = f_dados.get('status', 'pendente')
        nota = f_dados.get('estrelas')

        # Mesma regra do perfil: ignora apenas se for 'excluido'
        if aid and status != 'excluido' and nota is not None:
            if aid not in stats_feedback:
                stats_feedback[aid] = {'soma': 0, 'qtd': 0}
            
            stats_feedback[aid]['soma'] += int(nota)
            stats_feedback[aid]['qtd'] += 1

    # 2. Processa os músicos
    for doc in musicos_ref.stream():
        dados = doc.to_dict()
        aid = doc.id
        dados['id'] = aid
        
        # Pega os dados calculados acima
        artista_stats = stats_feedback.get(aid, {'soma': 0, 'qtd': 0})
        dados['total_cliques'] = dados.get('cliques', 0)
        
        qtd = artista_stats['qtd']
        soma = artista_stats['soma']
        
        # CÁLCULO DA MÉDIA (Exatamente como no perfil)
        media = round(soma / qtd, 1) if qtd > 0 else 0.0
        
        # INJETA NO DICIONÁRIO (Para o HTML ler musico.media_estrelas)
        dados['qtd_fb'] = qtd
        dados['media_estrelas'] = media
        
        musicos.append(dados)

    # 3. DESTAQUES (Agora ordenados pela MÉDIA e depois pela QUANTIDADE)
    destaques = [m for m in musicos if m.get('qtd_fb', 0) > 0]
    destaques = sorted(destaques, key=lambda x: (x['media_estrelas'], x['qtd_fb']), reverse=True)[:3]

    # --- O resto do código (cidades/filtros) permanece igual ---
    cidade_selecionada = request.args.get('cidade')
    cidades_disponiveis = sorted(list(set([str(m.get('cidade')).strip() for m in musicos if m.get('cidade')])))

    if cidade_selecionada:
        artistas_locais = [m for m in musicos if str(m.get('cidade')).strip().lower() == cidade_selecionada.strip().lower()]
    else:
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
    # 1. Tenta buscar pelo ID (documento direto)
    doc_ref = db.collection('artistas').document(musico_id)
    musico = doc_ref.get()

    if musico.exists:
        dados = musico.to_dict()
        # Aqui garantimos que a URL final seja SEMPRE minúscula
        nome_url = dados.get('nome', '').lower().strip().replace(' ', '-')
        if nome_url:
            return redirect(url_for('perfil_musico', musico_id=nome_url))
    
    # 2. SE NÃO EXISTE PELO ID: Busca pelo nome (slug) na URL
    # AQUI ESTAVA O ERRO: Precisamos do .lower() para bater com o banco minúsculo
    nome_busca = musico_id.replace('-', ' ').lower().strip()
    
    # Agora a busca ignora se você digitou maiúsculo na URL
    query = db.collection('artistas').where('nome', '==', nome_busca).limit(1).get()
    
    if not query:
        return "Músico não encontrado", 404
        
    musico = query[0]
    doc_ref = musico.reference 
    musico_id_real = musico.id 
    dados = musico.to_dict()

    doc_ref.update({'cliques': firestore.Increment(1)})

    # --- AQUI É ONDE O NOME FICA BONITO PARA A TELA ---
    # O banco continua minúsculo, mas o HTML recebe "Nicolas"
    if 'nome' in dados and dados['nome']:
        dados['nome'] = dados['nome'].title()
    
    # ... Resto do código (Agenda e Feedbacks) continua igual ...
    agenda_ref = doc_ref.collection('agenda').stream()
    agenda = [show.to_dict() for show in agenda_ref]

    feedbacks_ref = db.collection('feedbacks').where('artista_id', '==', musico_id_real).stream()
    
    feedbacks_para_exibir = []
    total_estrelas, qtd_fas = 0, 0
    
    for f in feedbacks_ref:
        f_dados = f.to_dict()
        status = f_dados.get('status', 'pendente')
        if status != 'excluido':
            if 'estrelas' in f_dados:
                qtd_fas += 1
                total_estrelas += int(f_dados.get('estrelas', 0))
                feedbacks_para_exibir.append(f_dados)
            elif status == 'aprovado':
                feedbacks_para_exibir.append(f_dados)

    media_estrelas = round(total_estrelas / qtd_fas, 1) if qtd_fas > 0 else 0.0
    dados['media_estrelas'] = media_estrelas
    foto_para_meta = dados.get('foto', '') 

    return render_template(
        'perfil.html', 
        musico=dados, 
        agenda=agenda, 
        feedbacks=feedbacks_para_exibir, 
        qtd_fas=qtd_fas, 
        media_estrelas=media_estrelas, 
        id=musico_id_real, 
        foto_meta=foto_para_meta
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


@app.route('/login_session')
def login_session():
    email = request.args.get('email')
    if email:
        # Define as variáveis que o seu Dashboard espera encontrar
        session['user_email'] = email
        session['logado'] = True 
        print(f"✅ Sessão Flask iniciada para: {email}")
        return jsonify({"status": "success"}), 200
    
    return jsonify({"status": "error", "message": "Email faltando"}), 400


# ======================================================
# 🔐 AUTENTICAÇÃOdef login_page():
# ======================================================
@app.route('/login')
def login_page():
    veio_da_venda = request.args.get('pago') == 'true'
    email_logado = session.get('user_email')
    email_encontrado = ""

    if veio_da_venda and email_logado:
        return redirect(url_for('dashboard', sucesso_pagamento='true'))

    if veio_da_venda:
        session['mostrar_boas_vindas'] = True
        
        try:
            # Busca simples apenas pelo status (não exige índice extra)
            # Pegamos os últimos 5 para garantir que o seu esteja ali
            usuarios_pagos = db.collection('usuarios')\
                .where('status_financeiro', '==', 'pago')\
                .limit(5).stream()
            
            # Ordenamos manualmente no Python para evitar o erro 500
            lista_usuarios = []
            for u in usuarios_pagos:
                d = u.to_dict()
                if 'data_pagamento' in d:
                    lista_usuarios.append(d)
            
            if lista_usuarios:
                # Pega o que tem a data mais recente
                lista_usuarios.sort(key=lambda x: x['data_pagamento'], reverse=True)
                email_encontrado = lista_usuarios[0].get('email', "")
                
        except Exception as e:
            print(f"Erro na busca de segurança: {e}")

    mostrar_modal = session.pop('mostrar_boas_vindas', False)

    # Garante que o config não quebre se faltar variável de ambiente
    config = {
        "apiKey": os.getenv("FIREBASE_API_KEY", ""),
        "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN", ""),
        "projectId": os.getenv("FIREBASE_PROJECT_ID", ""),
        "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET", ""),
        "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID", ""),
        "appId": os.getenv("FIREBASE_APP_ID", "")
    }

    return render_template(
        'login.html',
        firebase_config=config,
        confirmacao_venda=mostrar_modal,
        email_preenchido=email_encontrado
    )


@app.route('/dashboard')
@login_required
def dashboard():
    email_logado = session.get('user_email')
    # 🔍 BUSCA AS PROPOSTAS
    propostas_ref = db.collection('propostas').where('dono_email', '==', email_logado).stream()
    
    # Converte para lista de dicionários
    historico = [p.to_dict() for p in propostas_ref]
    
    # Ordena para a mais recente aparecer em cima
    historico.sort(key=lambda x: x.get('timestamp') if x.get('timestamp') else 0, reverse=True)
    
    # 🟢 NOVO: Detecta se o usuário está voltando do checkout (via nosso redirecionamento do login)
    veio_do_checkout_interno = request.args.get('sucesso_pagamento') == 'true'
    
    # 🔍 1. BUSCA DADOS DA CONTA DO USUÁRIO
    user_query = db.collection('usuarios').where('email', '==', email_logado).limit(1).stream()
    user_docs = list(user_query)

    if not user_docs:
        session.clear()
        flash("Sua conta não foi encontrada ou foi desativada.", "danger")
        return redirect(url_for('login'))

    dados_usuario = user_docs[0].to_dict()
    tipo_usuario = dados_usuario.get('tipo')
    pagou = dados_usuario.get('acesso_pago', False)

    # 🔍 2. BUSCA DADOS DO PERFIL DO ARTISTA
    artista_query = db.collection('artistas').where('dono_email', '==', email_logado).limit(1).stream()
    artista_docs = list(artista_query)
    artista_dados = None

    bloqueado = False

    # 🛑 REGRA 1: Se ainda não escolheu o tipo
    if not tipo_usuario:
        return render_template('dashboard.html', pedidos=[], musico=None, agenda=[], feedbacks=[], notificacoes_fas=0, total_cliques=0, media_estrelas=0, bloqueado=False)
    
    """# 🛑 REGRA 2: LÓGICA DE ACESSO PARA MÚSICO
    if tipo_usuario == 'musico':
        # Só libera se acesso_pago for True OU se acabou de voltar com o token de sucesso
        if pagou == True or veio_do_checkout_interno == True:
            bloqueado = False
        else:
            return redirect(url_for('checkout')) # Força a ida para o pagamento"""
    
    # 🛑 REGRA 2: LÓGICA DE ACESSO PARA MÚSICO (CORRIGIDA)
    if tipo_usuario == 'musico':
        # Se pagou OU se acabou de voltar do checkout, liberado.
        if pagou == True or veio_do_checkout_interno == True:
            bloqueado = False
        else:
            # EM VEZ DE REDIRECT, apenas marcamos como bloqueado para o HTML mostrar a barra
            bloqueado = True
            
    # 🟢 SE FOR ESTABELECIMENTO
    if tipo_usuario == 'estabelecimento':
        doc_estab = db.collection('estabelecimentos').document(email_logado).get()
        if not doc_estab.exists:
            return redirect(url_for('abrir_pagina_estabelecimento'))
        return redirect(url_for('dashboard_estabelecimento'))

    # 🟢 PROCESSAMENTO DE DADOS DO ARTISTA
    pedidos, agenda, feedbacks = [], [], []
    total_cliques, notificacoes_fas, total_estrelas = 0, 0, 0

    if artista_docs:
        doc = artista_docs[0]
        artista_id = doc.id
        artista_dados = doc.to_dict()
        artista_dados['id'] = artista_id
        total_cliques = artista_dados.get('cliques', 0)

        # Pedidos
        pedidos_ref = db.collection('pedidos_reserva').where('musico_id', '==', artista_id).stream()
        for p in pedidos_ref:
            p_dados = p.to_dict()
            p_dados['id'] = p.id
            pedidos.append(p_dados)
        pedidos.sort(key=lambda x: x.get('criado_em') if x.get('criado_em') else 0, reverse=True)

        # Agenda
        agenda_ref = db.collection('artistas').document(artista_id).collection('agenda').order_by('data_completa').stream()
        for s in agenda_ref:
            s_dados = s.to_dict()
            s_dados['id'] = s.id
            agenda.append(s_dados)

        # Feedbacks
        feedbacks_ref = db.collection('feedbacks').where('artista_email', '==', email_logado).stream()
        # No processamento de feedbacks (DENTRO da condição if artista_docs):
    total_estrelas = 0
    qtd_validas = 0 # Contador específico para quem tem estrelas
    
    for f in feedbacks_ref:
        f_dados = f.to_dict()
        status = f_dados.get('status', 'pendente')
        
        # REGRA UNIFICADA: Só ignora se for excluído
        if status != 'excluido':
            feedbacks.append(f_dados)
            if 'estrelas' in f_dados:
                total_estrelas += int(f_dados.get('estrelas', 0))
                qtd_validas += 1
            if status == 'pendente':
                notificacoes_fas += 1

    # CÁLCULO DA MÉDIA
    media_estrelas = round(total_estrelas / qtd_validas, 1) if qtd_validas > 0 else 0.0

    # A LINHA QUE MANDA PARA O HTML:
    if artista_dados:
        artista_dados['media_estrelas'] = media_estrelas

    # Lógica de datas (Ativação e Vencimento)
    data_ativacao, data_vencimento, dias_restantes = None, None, None
    if dados_usuario.get('data_pagamento'):
        from datetime import datetime, timedelta
        dt_pagamento = dados_usuario['data_pagamento']
        data_ativacao = dt_pagamento.strftime('%d/%m/%Y')
        dt_vencimento = dt_pagamento + timedelta(days=30)
        data_vencimento = dt_vencimento.strftime('%d/%m/%Y')
        hoje = datetime.now()
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
        exibir_boas_vindas_interno=veio_do_checkout_interno, # Ativa a modal no HTML
        data_ativacao=data_ativacao,
        data_vencimento=data_vencimento,
        dias_restantes=dias_restantes,
        pagou=pagou,
        historico_propostas=historico,
        total_propostas=len(historico)
    )


@app.route('/checkout')
@login_required
def checkout():
    email_usuario = session.get('user_email')
    dominio_producao = "https://slp-musicos-1.onrender.com"
    
    # Passamos o email_venda direto via Python, sem depender das chaves do Stripe
    link_stripe = (
        f"https://buy.stripe.com/test_5kQ8wO90m6yWbRl0I5gIo00"
        f"?prefilled_email={email_usuario}"
        f"&success_url={dominio_producao}/login?pago=true&email_venda={email_usuario}"
    )
    return redirect(link_stripe)


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
        # 1. Validação rigorosa do Token do Google
        decoded_token = firebase_auth.verify_id_token(id_token)
        email_google = decoded_token['email']

        if not email_google:
            return jsonify({"status": "error", "message": "Email não verificado pelo Google"}), 401

        # 2. CAMADA DE SEGURANÇA TOTAL: Limpa qualquer rastro de sessões anteriores
        # Isso garante que se outra pessoa usou o PC antes, os dados dela sumiram agora.
        session.clear() 
        
        # 3. Define a nova sessão vinculada EXCLUSIVAMENTE ao ID único do Google
        session['user_email'] = email_google
        session.permanent = True # Faz a sessão expirar se o navegador fechar

        # 4. Busca ou Cria o usuário com base no Email ÚNICO
        user_ref = db.collection('usuarios').document(email_google)
        doc = user_ref.get()
        
        if not doc.exists:
            user_ref.set({
                'email': email_google,
                'nome': decoded_token.get('name'),
                'tipo': None,
                'acesso_pago': False,
                'criado_em': firestore.SERVER_TIMESTAMP
            })
            destino = url_for('dashboard')
        else:
            dados = doc.to_dict()
            # Redirecionamento baseado estritamente nos dados do documento encontrado
            if dados.get('tipo') == 'musico' and not dados.get('acesso_pago'):
                destino = url_for('checkout')
            elif dados.get('tipo') == 'estabelecimento':
                destino = url_for('dashboard_estabelecimento')
            else:
                destino = url_for('dashboard')

        return jsonify({"status": "success", "redirect": destino}), 200

    except Exception as e:
        session.clear() # Se der erro, por segurança limpa tudo
        return jsonify({"status": "error", "message": "Falha crítica de segurança"}), 401


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
        return redirect('/dashboard')


@app.route('/remover_feedback/<string:id>', methods=['POST'])
def remover_feedback(id):
    try:
        # EM VEZ DE DELETE, FAZEMOS UPDATE
        # Isso mantém o documento vivo para as estrelas contarem no perfil
        feedback_ref = db.collection('feedbacks').document(id)
        feedback_ref.update({
            'status': 'excluido'
        })
        return redirect('/dashboard')
    except Exception as e:
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
    contato = request.form.get('contato')
    
    # --- AJUSTADO: SALVAR SEM ACENTO ("musico") ---
    tipo_input = request.form.get('tipo', '') 
    term_check = tipo_input.lower()
    
    if "músico" in term_check or "musico" in term_check:
        tipo = "musico"  # Força sem acento e sem o "independente"
    elif "dj" in term_check:
        tipo = "dj"
    elif "banda" in term_check:
        tipo = "banda"
    else:
        tipo = tipo_input
    # ----------------------------------------------

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

    """if file and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filename = f"upload_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        final_path = f"/static/img/{filename}"""

        # --- UPLOAD PARA VERCEL BLOB (SUBSTITUINDO O SALVAMENTO LOCAL) ---
    if file and file.filename != '' and allowed_file(file.filename):
        import requests
        import os
        from werkzeug.utils import secure_filename

        filename = secure_filename(file.filename)
        # Lê o conteúdo da imagem
        conteudo = file.read()
        
        # Pega o Token do seu arquivo .env
        token = os.getenv("BLOB_READ_WRITE_TOKEN")
        
        # Faz o upload para a Vercel
        url_vercel = f"https://blob.vercel-storage.com/artistas/{filename}"
        headers = {
            "Authorization": f"Bearer {token}",
            "x-content-type": file.content_type
        }
        
        response = requests.put(url_vercel, data=conteudo, headers=headers)
        
        if response.status_code == 200:
            # SUCESSO: Agora final_path terá o link https://...
            final_path = response.json().get('url')
        else:
            print("Erro no upload:", response.text)

    # Dicionário de dados atualizado
    dados = {
        'nome': nome,
        'contato': contato,
        'tipo': tipo, # Aqui agora entra "musico" (sem acento)
        'cidade': cidade,
        'estado': estado,
        'estilo': estilo,
        'bio': bio,
        'instagram': instagram, 
        'facebook': facebook,   
        'youtube': youtube, 
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
        return jsonify({'status': 'error', 'message': str(e)}), 500


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
        'whatsapp': request.form.get('whatsapp'), # <-- ADICIONADO AQUI
        'foto': foto_final, 
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
    if termo_busca == 'músico':
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
        return f"Erro: Arquivo lista_{tipo_limpo}.html não encontrado", 404
    

# ======================================================
# 🔎 PORTA LATERAL: VISUALIZADOR DE MEMBROS
# ======================================================
@app.route('/admin/membros')
def lista_membros_secreta():
    # Busca todos os artistas cadastrados no Firestore
    artistas_ref = db.collection('artistas').stream()
    lista_artistas = []
    
    for doc in artistas_ref:
        dados = doc.to_dict()
        dados['id'] = doc.id
        lista_artistas.append(dados)
    
    # Renderiza uma página simples só para você gerenciar
    return render_template('admin_membros.html', artistas=lista_artistas)


@app.route('/termos')
def termos():
    return render_template('termos.html')


@app.route('/privacidade')
def privacidade():
    return render_template('privacidade.html')    


@app.route('/gerar_proposta', methods=['POST'])
@login_required
def gerar_proposta():
    email_logado = session.get('user_email')
    artista_docs = list(db.collection('artistas').where('dono_email', '==', email_logado).limit(1).stream())
    
    if not artista_docs:
        return redirect(url_for('dashboard'))
    
    m = artista_docs[0].to_dict()
    
    # --- AJUSTE PARA NÃO DUPLICAR ---
    # 1. Pegamos o ID que o JavaScript enviou (seja o aleatório novo ou o original da edição)
    temp_id = request.form.get('proposta_temp_id')
    
    # 2. Definimos o documento_id baseado nesse temp_id
    documento_id = f"{email_logado}_{temp_id}".replace('.', '_')
    
    # 3. O auth_id DEVE ser o mesmo temp_id para que o link de reimpressão funcione
    # e para que o banco entenda que é o mesmo documento.
    auth_id = temp_id 
    # --------------------------------
    
    agora = datetime.now().strftime('%d/%m/%Y às %H:%M')

    # --- TRATAMENTO DA DATA (Mantido igual) ---
    data_festa_raw = request.form.get('data_festa', '')
    try:
        data_festa = datetime.strptime(data_festa_raw, '%Y-%m-%d').strftime('%d/%m/%Y')
    except:
        data_festa = data_festa_raw

    # --- LÓGICA DO VALOR (Mantido igual) ---
    valor_input = request.form.get('valor_cache', '0')
    try:
        limpo_v = re.sub(r'[^\d,]', '', valor_input).replace(',', '.')
        valor_float = float(limpo_v)
        valor_cache_formatado = "{:,.2f}".format(valor_float).replace(',', 'X').replace('.', ',').replace('X', '.')
        valor_extenso = num2words(valor_float, to='currency', lang='pt_BR').capitalize()
    except:
        valor_cache_formatado = valor_input
        valor_extenso = "Valor não identificado"

    # --- LÓGICA CPF / CNPJ (Mantido igual) ---
    doc_input = request.form.get('documento_artista', '')
    doc_numeros = re.sub(r'\D', '', doc_input)
    if len(doc_numeros) == 11:
        doc_formatado = f"{doc_numeros[:3]}.{doc_numeros[3:6]}.{doc_numeros[6:9]}-{doc_numeros[9:]}"
    elif len(doc_numeros) == 14:
        doc_formatado = f"{doc_numeros[:2]}.{doc_numeros[2:5]}.{doc_numeros[5:8]}/{doc_numeros[8:12]}-{doc_numeros[12:]}"
    else:
        doc_formatado = doc_input

    dados_proposta = {
        'nome_festa': request.form.get('nome_festa'),
        'data_festa': data_festa,
        'hora_festa': request.form.get('hora_festa'),
        'local_festa': request.form.get('local_festa'),
        'valor_cache': valor_cache_formatado,
        'valor_extenso': valor_extenso, 
        'detalhes_show': request.form.get('detalhes_show'),
        'cor_proposta': request.form.get('cor_proposta', '#00f2ff'),
        'documento_artista': doc_formatado,
        'auth_id': auth_id, # Agora o auth_id é o próprio temp_id fixo
        'data_emissao': agora,
        'dono_email': email_logado,
        'timestamp': datetime.now()
    }

    # 💾 SALVAMENTO:
    # Como o documento_id agora é baseado no temp_id que o JS enviou,
    # o Firestore vai encontrar o documento existente e apenas atualizar os campos.
    db.collection('propostas').document(documento_id).set(dados_proposta)

    return render_template('proposta_template.html', m=m, p=dados_proposta)



@app.route('/gerar_proposta_reimpressao/<auth_id>')
@login_required
def gerar_proposta_reimpressao(auth_id):
    from google.cloud.firestore_v1.base_query import FieldFilter
    email_logado = session.get('user_email')
    
    # 1. Busca a proposta salva no banco pelo auth_id
    propostas_ref = db.collection('propostas')\
        .where(filter=FieldFilter('auth_id', '==', auth_id))\
        .where(filter=FieldFilter('dono_email', '==', email_logado))\
        .limit(1).stream()
    
    proposta_doc = next(propostas_ref, None)

    if not proposta_doc:
        return "Proposta não encontrada.", 404

    p = proposta_doc.to_dict()

    # 2. Busca os dados do artista para garantir que o layout use as infos atuais (foto, nome)
    artista_docs = list(db.collection('artistas')\
        .where(filter=FieldFilter('dono_email', '==', email_logado))\
        .limit(1).stream())
    
    if not artista_docs:
        return redirect(url_for('dashboard'))
    
    m = artista_docs[0].to_dict()

    # 3. Renderiza o mesmo template, mas com os dados que vieram do banco
    return render_template('proposta_template.html', m=m, p=p)


@app.template_filter('nl2br')
def nl2br_filter(s):
    if not s:
        return ""
    # Substitui quebras de linha por <br>\n e marca como seguro para o HTML
    result = re.sub(r'\r\n|\r|\n', '<br>\n', s)
    return Markup(result)


if __name__ == '__main__':
    app.run(debug=True)