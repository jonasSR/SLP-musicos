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

# ======================================================
# 🌎 ROTAS PÚBLICAS
# ======================================================

@app.route('/')
def index():
    musicos_ref = db.collection('artistas')
    musicos = []

    for doc in musicos_ref.stream():
        dados = doc.to_dict()
        dados['id'] = doc.id
        musicos.append(dados)

    return render_template(
        'index.html',
        musicos=musicos
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
# 🔐 AUTENTICAÇÃO
# ======================================================

@app.route('/login')
def login_page():
    """Tela de acesso para músicos"""
    if 'user_email' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')


@app.route('/set_session', methods=['POST'])
def set_session():
    data = request.get_json()

    if not data or 'email' not in data:
        return jsonify({"status": "error"}), 400

    email = data.get('email')

    # 🔐 CRIA SESSÃO (ESSENCIAL)
    session['user_email'] = email

    user_ref = db.collection('usuarios').document(email)

    if not user_ref.get().exists:
        user_ref.set({
            'email': email,
            'tipo': 'musico',
            'criado_em': firestore.SERVER_TIMESTAMP
        })

    return jsonify({"status": "success"}), 200



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ======================================================
# 🔒 ÁREA PRIVADA
# ======================================================

@app.route('/dashboard')
@login_required
def dashboard():
    email_logado = session.get('user_email')
    
    artista_query = db.collection('artistas').where('dono_email', '==', email_logado).limit(1).stream()
    
    pedidos = []
    agenda = [] 
    feedbacks = [] 
    artista_dados = None 
    total_cliques = 0 
    notificacoes_fas = 0  # <--- INICIALIZA O CONTADOR DE PENDENTES

    for doc in artista_query:
        artista_id = doc.id
        artista_dados = doc.to_dict()
        artista_dados['id'] = artista_id
        
        # --- BUSCAR CLICKS ---
        total_cliques = artista_dados.get('cliques', 0) 
        
        # BUSCAR PEDIDOS
        pedidos_ref = db.collection('pedidos_reserva').where('musico_id', '==', artista_id).stream()
        for p in pedidos_ref:
            p_dados = p.to_dict()
            p_dados['id'] = p.id
            pedidos.append(p_dados)

        # BUSCAR AGENDA
        agenda_ref = db.collection('artistas').document(artista_id).collection('agenda').order_by('data_completa').stream()
        for s in agenda_ref:
            s_dados = s.to_dict()
            s_dados['id'] = s.id
            agenda.append(s_dados)

        # --- BUSCAR FEEDBACKS (MURAL DE FÃS) ---
        feedbacks_ref = db.collection('feedbacks').where('artista_email', '==', email_logado).stream()
        for f in feedbacks_ref:
            f_dados = f.to_dict()
            f_dados['id'] = f.id 
            feedbacks.append(f_dados)
            
            # --- LÓGICA DO CONTADOR ---
            # Se o status for pendente, aumenta o número da notificação
            if f_dados.get('status') == 'pendente':
                notificacoes_fas += 1

    pedidos.sort(key=lambda x: x.get('criado_em') if x.get('criado_em') else 0, reverse=True)

    return render_template(
        'dashboard.html', 
        pedidos=pedidos, 
        musico=artista_dados,
        agenda=agenda,
        feedbacks=feedbacks, 
        notificacoes_fas=notificacoes_fas, # <--- ENVIA O NÚMERO PARA O ÍCONE
        total_cliques=total_cliques 
    )

# NOVA ROTA: Para marcar como lida via JavaScript quando você clicar
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
# CADASTRAR MÚSICO-DASHBOARD
# ======================================================
@app.route('/api_cadastrar_musico', methods=['POST'])
@login_required
def cadastrar_musico():
    nome = request.form.get('nome')
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

    # Dicionário de dados atualizado com as redes sociais
    dados = {
        'nome': nome,
        'cidade': cidade,
        'estado': estado,
        'estilo': estilo,
        'bio': bio,
        'instagram': instagram, # Salva no banco
        'facebook': facebook,   # Salva no banco
        'youtube': youtube,     # Salva no banco
        'dono_email': email,
        'timestamp': firestore.SERVER_TIMESTAMP
    }

    if final_path:
        dados['foto'] = final_path

    if artista_doc:
        db.collection('artistas').document(artista_doc.id).update(dados)
    else:
        dados['cliques'] = 0 # <--- Inicializa com 0 apenas se for um documento novo
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
        email = decoded_token['email']
        nome = decoded_token.get('name', 'Usuário Google')
        foto = decoded_token.get('picture', '')

        # Inicia a sessão
        session['user_email'] = email
        
        # Verifica se o usuário já existe na coleção 'usuarios'
        user_ref = db.collection('usuarios').document(email)
        if not user_ref.get().exists:
            user_ref.set({
                'email': email,
                'nome': nome,
                'foto_google': foto,
                'tipo': 'musico',
                'criado_em': firestore.SERVER_TIMESTAMP
            })
            
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        print(f"Erro na validação Google: {e}")
        return jsonify({"status": "error", "message": "Token inválido"}), 401


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
    
# ======================================================
# 🚀 START
# ======================================================

if __name__ == '__main__':
    app.run(debug=True)