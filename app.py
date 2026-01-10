import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import urllib.parse

import firebase_admin
from firebase_admin import credentials, firestore
from werkzeug.utils import secure_filename

import json
from firebase_admin import credentials, initialize_app

# ======================================================
# 🔧 CONFIGURAÇÃO INICIAL
# ======================================================

base_path = os.path.dirname(os.path.abspath(__file__))

#cred = credentials.Certificate("serviceAccountKey.json")
#firebase_admin.initialize_app(cred)

cred_json = os.environ.get("FIREBASE_CREDENTIALS")
if not cred_json:
    raise Exception("Variável FIREBASE_CREDENTIALS não encontrada!")

cred_dict = json.loads(cred_json)
cred = credentials.Certificate(cred_dict)
initialize_app(cred)

db = firestore.client()

app = Flask(__name__)

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


# ======================================================
# 🌎 ROTAS PÚBLICAS
# ======================================================

@app.route('/')
def index():
    """Página inicial com todos os artistas do fluxo"""
    musicos_ref = db.collection('artistas')
    musicos = []

    for doc in musicos_ref.stream():
        dados = doc.to_dict()
        dados['id'] = doc.id
        musicos.append(dados)

    return render_template('index.html', musicos=musicos)


@app.route('/musico/<musico_id>')
def perfil_musico(musico_id):
    """Página detalhada de cada artista"""
    doc_ref = db.collection('artistas').document(musico_id)
    musico = doc_ref.get()

    if not musico.exists:
        return "Músico não encontrado", 404

    dados = musico.to_dict()
    agenda_ref = doc_ref.collection('agenda').stream()
    agenda = [show.to_dict() for show in agenda_ref]

    return render_template(
        'perfil.html',
        musico=dados,
        agenda=agenda,
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
    """
    Cria sessão após login no Firebase (front-end)
    e garante que o usuário esteja salvo no banco (Firestore Admin)
    """
    data = request.get_json()

    if not data or 'email' not in data:
        return jsonify({"status": "error"}), 400

    email = data.get('email')

    # cria sessão
    session['user_email'] = email
    print(f"Sessão iniciada para: {email}")

    # garante usuário no banco (BACKEND É A FONTE DA VERDADE)
    usuarios_ref = db.collection('usuarios')
    existente = usuarios_ref.where('email', '==', email).limit(1).stream()

    if not any(existente):
        usuarios_ref.add({
            'email': email,
            'tipo': 'musico',
            'criado_em': firestore.SERVER_TIMESTAMP
        })
        print(f"Usuário salvo no banco: {email}")
    else:
        print(f"Usuário já existia no banco: {email}")

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
    agenda = [] # <--- Adicione esta lista
    artista_dados = None 

    for doc in artista_query:
        artista_id = doc.id
        artista_dados = doc.to_dict()
        artista_dados['id'] = artista_id
        
        # BUSCAR PEDIDOS
        pedidos_ref = db.collection('pedidos_reserva').where('musico_id', '==', artista_id).stream()
        for p in pedidos_ref:
            p_dados = p.to_dict()
            p_dados['id'] = p.id
            pedidos.append(p_dados)

        # BUSCAR AGENDA (IMPORTANTE PARA NÃO DAR ERRO NO HTML)
        agenda_ref = db.collection('artistas').document(artista_id).collection('agenda').order_by('data_completa').stream()
        for s in agenda_ref:
            s_dados = s.to_dict()
            s_dados['id'] = s.id
            agenda.append(s_dados)

    pedidos.sort(key=lambda x: x.get('criado_em') if x.get('criado_em') else 0, reverse=True)

    return render_template(
        'dashboard.html', 
        pedidos=pedidos, 
        musico=artista_dados,
        agenda=agenda  # <--- Certifique-se de enviar a agenda aqui
    )

# NOVA ROTA: Para marcar como lida via JavaScript quando você clicar
@app.route('/marcar_lido/<pedido_id>', methods=['POST'])
@login_required
def marcar_lido(pedido_id):
    db.collection('pedidos_reserva').document(pedido_id).update({'lido': True})
    return jsonify({"status": "success"})


@app.route('/api_cadastrar_musico', methods=['POST'])
@login_required
def cadastrar_musico():
    nome = request.form.get('nome')
    estilo = request.form.get('estilo')
    bio = request.form.get('bio')
    foto_url = request.form.get('foto_url')
    file = request.files.get('foto_arquivo')

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

    # Se não existir artista ainda
    if not artista_doc:
        artista_data = {}

    # 🧠 Foto atual (fallback)
    final_path = artista_data.get('foto')

    # 🔗 Caso usuário tenha informado um link
    if foto_url:
        final_path = foto_url

    # 📤 Caso usuário tenha feito upload
    if file and file.filename != '' and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filename = f"upload_{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        final_path = f"/static/img/{filename}"

    dados = {
        'nome': nome,
        'estilo': estilo,
        'bio': bio,
        'dono_email': email,
        'timestamp': firestore.SERVER_TIMESTAMP
    }

    # 🚨 Só adiciona "foto" se ela existir
    if final_path:
        dados['foto'] = final_path

    if artista_doc:
        db.collection('artistas').document(artista_doc.id).update(dados)
    else:
        db.collection('artistas').add(dados)

    return redirect(url_for('dashboard'))


# ======================================================
# 🎵 CONTRATAR BANDA
# ======================================================
@app.route('/reservar', methods=['POST'])
def reservar():
    # Coleta os dados do formulário
    musico_id = request.form.get('musico_id')
    data_evento = request.form.get('data_evento')
    tipo_evento = request.form.get('tipo')
    
    try:
        # 1. BUSCA O E-MAIL DA BANDA NO BANCO DE DADOS
        # Acessamos o documento da banda pelo ID enviado pelo formulário
        musico_ref = db.collection('artistas').document(musico_id).get()
        
        if not musico_ref.exists:
            return jsonify({"status": "error", "message": "Banda não encontrada"}), 404
            
        dados_musico = musico_ref.to_dict()
        email_da_banda = dados_musico.get('dono_email') # O e-mail que a banda usou no cadastro

        # 2. SALVA O PEDIDO NO BANCO (Isso vai ativar o ícone de mensagem)
        db.collection('pedidos_reserva').add({
            'musico_id': musico_id,
            'data_evento': data_evento,
            'tipo_evento': tipo_evento,
            'status': 'novo', # Status inicial para a banda ver no painel
            'cliente_email': session.get('user_email', 'Visitante'),
            'lido': False, # Para sabermos se a banda já viu a mensagem
            'criado_em': firestore.SERVER_TIMESTAMP
        })

        # Nota: A parte de enviar o e-mail real precisaria daquelas configurações SMTP.
        # Por enquanto, o sistema já sabe QUAL é o e-mail da banda (email_da_banda).

        return jsonify({
            "status": "success", 
            "message": f"Pedido enviado para {email_da_banda}!",
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
# 🚀 START
# ======================================================

if __name__ == '__main__':
    app.run(debug=True)