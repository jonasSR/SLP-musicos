console.log("🔥 auth.js carregado");

// 🔥 IMPORTS FIREBASE (CDN)
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import {
    getAuth,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    updatePassword,
    GoogleAuthProvider,
    signInWithPopup,
    deleteUser // <--- ADICIONE ESTA LINHA AQUI
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";

import {
    getFirestore,
    doc,
    setDoc,
    serverTimestamp
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";

// 🔥 CONFIG FIREBASE
const firebaseConfig = {
    apiKey: "AIzaSyByff364YvPXLeo6k1ccquKTX4Jv-CeOhA",
    authDomain: "slp-musicos-turismo.firebaseapp.com",
    projectId: "slp-musicos-turismo",
    storageBucket: "slp-musicos-turismo.firebasestorage.app",
    messagingSenderId: "289743101948",
    appId: "1:289743101948:web:c11cb6910506e84d405c79"
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

// 🎯 ELEMENTOS HTML
const formLogin = document.getElementById("auth-form");
const btnSignup = document.getElementById("btn-signup");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");

// --- FUNÇÕES AUXILIARES ---
function traduzirErroFirebase(error) {
    console.log("Código do erro:", error.code); // Útil para debug

    switch (error.code) {
        // Erro unificado (v10+) para E-mail não encontrado OU Senha incorreta
        case "auth/invalid-credential":
            return "E-mail não encontrado ou senha incorreta. Verifique seus dados e tente novamente.";
        
        // Caso o Firebase retorne separadamente (depende da config do console)
        case "auth/user-not-found":
            return "Este e-mail não está cadastrado em nossa plataforma.";
        case "auth/wrong-password":
            return "Senha incorreta. Caso tenha esquecido, use a recuperação de senha.";
        
        // Erros de Formato e Cadastro
        case "auth/invalid-email":
            return "O formato do e-mail digitado é inválido.";
        case "auth/email-already-in-use":
            return "Este e-mail já está em uso por outra conta.";
        case "auth/weak-password":
            return "A senha deve conter pelo menos 6 caracteres.";
            
        // Erros de Bloqueio e Rede
        case "auth/too-many-requests":
            return "Muitas tentativas malsucedidas. Sua conta foi bloqueada temporariamente. Tente mais tarde.";
        case "auth/user-disabled":
            return "Esta conta de usuário foi desativada por um administrador.";
        case "auth/network-request-failed":
            return "Falha na conexão. Verifique se você está conectado à internet.";
            
        default:
            return "Ocorreu um erro inesperado. Por favor, tente novamente.";
    }
}

// Abre a modal de alerta (Erro ou Instrução)
function exibirPopup(titulo, mensagem) {
    const modal = document.getElementById('modal-auth');
    const modalTitle = document.getElementById('modal-title');
    const modalText = document.getElementById('modal-text');
    
    if (modal && modalTitle && modalText) {
        modalTitle.innerText = titulo;
        modalText.innerText = mensagem;
        modal.style.display = "flex";
    }
}

// Fecha a modal de alerta
const fecharModal = () => {
    const modal = document.getElementById('modal-auth');
    if (modal) modal.style.display = "none";
};

// Vincula o fechamento aos botões da modal-auth
const btnCloseX = document.getElementById('btn-close-x');
const btnModalConfirm = document.getElementById('btn-modal-confirm');
if (btnCloseX) btnCloseX.onclick = fecharModal;
if (btnModalConfirm) btnModalConfirm.onclick = fecharModal;

window.onclick = (event) => {
    const modal = document.getElementById('modal-auth');
    if (event.target == modal) fecharModal();
};

async function iniciarSessao(email) {
    await fetch("/set_session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email })
    });
}


// 🔐 LOGIN ATUALIZADO
if (formLogin) {
    formLogin.addEventListener("submit", async (e) => {
        e.preventDefault();

        // 1. Captura e limpa os inputs
        const email = emailInput.value.trim();
        const password = passwordInput.value;

        // 2. Validação simples antes de enviar ao servidor
        if (!email || !password) {
            exibirPopup("Campos Vazios", "Por favor, informe seu e-mail e senha para acessar.");
            return;
        }

        try {
            // 3. Tentativa de autenticação
            await signInWithEmailAndPassword(auth, email, password);
            
            // 4. Inicia sessão no Python (Flask)
            await iniciarSessao(email);
            
            // 5. Direciona para o Dashboard correto (Músico ou Estabelecimento)
            acaoPosLogin(); 

        } catch (error) {
            // 6. Tratamento de erro detalhado
            console.error("Erro na autenticação:", error);
            exibirPopup("Erro no Login", traduzirErroFirebase(error));
        }
    });
}

// 🆕 CADASTRO (UNIFICADO)
// 1. Variáveis temporárias (não salvam no banco ainda)
let dadosTemporarios = { email: "", senha: "" };

// 2. O BOTÃO "CRIAR CONTA" (O primeiro que o usuário vê)
if (btnSignup) {
    btnSignup.addEventListener("click", (e) => {
        const email = emailInput.value.trim();
        const password = passwordInput.value;

        if (!email || !password) {
            exibirPopup("Atenção", "Preencha os campos antes de continuar.");
            return; 
        }

        // APENAS GUARDA OS DADOS E ABRE A MODAL
        dadosTemporarios.email = email;
        dadosTemporarios.senha = password;

        const modalEscolha = document.getElementById('modal-escolha-perfil');
        if (modalEscolha) {
            modalEscolha.style.display = "flex";
        }
    });
}

// 3. OS BOTÕES DENTRO DA MODAL (Aqui é onde a mágica acontece)
document.addEventListener("DOMContentLoaded", () => {
    const btnMusico = document.getElementById('btn-escolha-musico');
    const btnEmpresa = document.getElementById('btn-escolha-empresa');

    // Esta função é a única que realmente toca no Banco de Dados
    async function executarCadastroFinal(tipoPerfil) {
        try {
            // SÓ AGORA criamos o login no Firebase Auth
            const userCredential = await createUserWithEmailAndPassword(
                auth, 
                dadosTemporarios.email, 
                dadosTemporarios.senha
            );

            // SÓ AGORA salvamos no Firestore
            await setDoc(doc(db, "usuarios", userCredential.user.uid), {
                email: dadosTemporarios.email,
                tipo: tipoPerfil,
                data_cadastro: serverTimestamp()
            });

            // Cria a sessão no Python e redireciona
            await iniciarSessao(dadosTemporarios.email);
            
            if (tipoPerfil === 'estabelecimento') {
                window.location.href = "/cadastro-estabelecimento";
            } else {
                window.location.href = "/dashboard";
            }

        } catch (error) {
            exibirPopup("Erro", traduzirErroFirebase(error));
        }
    }

    if (btnMusico) btnMusico.onclick = () => executarCadastroFinal('musico');
    if (btnEmpresa) btnEmpresa.onclick = () => executarCadastroFinal('estabelecimento');
});

// 🌐 GOOGLE
const provider = new GoogleAuthProvider();
provider.setCustomParameters({ prompt: 'select_account' });

window.loginComGoogle = async function() {
    try {
        const result = await signInWithPopup(auth, provider);
        const idToken = await result.user.getIdToken();
        const response = await fetch('/login_google', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ idToken: idToken })
        });
        const data = await response.json();
        if (data.status === 'success') {
            acaoPosLogin();
        } else {
            alert("Erro ao sincronizar: " + data.message);
        }
    } catch (error) {
        if (error.code !== 'auth/cancelled-popup-request' && error.code !== 'auth/popup-closed-by-user') {
            exibirPopup("Erro Google", traduzirErroFirebase(error));
        }
    }
}

// 👁️ MOSTRAR / ESCONDER SENHA
const togglePasswordBtn = document.querySelector(".log-toggle-eye");
if (togglePasswordBtn && passwordInput) {
    togglePasswordBtn.addEventListener("click", () => {
        const oculto = passwordInput.type === "password";
        passwordInput.type = oculto ? "text" : "password";
        togglePasswordBtn.textContent = oculto ? "🙈" : "👁";
    });
}


// 🔐 TROCAR SENHA (SOBRESCREVE A ANTIGA NO FIREBASE)
document.addEventListener("DOMContentLoaded", () => {
    const formSenha = document.getElementById("form-trocar-senha");
    if (!formSenha) return;

    formSenha.addEventListener("submit", async (e) => {
        e.preventDefault();

        const novaSenha = document.getElementById("nova-senha").value;
        const confirmaSenha = document.getElementById("confirma-senha").value;

        if (novaSenha !== confirmaSenha) {
            alert("As senhas não coincidem");
            return;
        }

        try {
            await updatePassword(auth.currentUser, novaSenha);

            alert("Senha alterada com sucesso!");

            await auth.signOut();
            window.location.href = "/login";

        } catch (error) {
            console.error(error);
            alert("Erro ao trocar senha. Faça login novamente.");
        }
    });
});

// Variável para controle local
let perfilPendente = { tipo: "", email: "" };

// Vigia global de sessão
auth.onAuthStateChanged((user) => {
    if (user) {
        verificarStatusCadastro(user.email);
    }
});

async function verificarStatusCadastro(email) {
    try {
        const response = await fetch(`/check_user_type?email=${email}`);
        const data = await response.json();
        window.statusUsuario = data; 
        
        // Atualiza o controle local para as modais saberem o tipo
        perfilPendente.tipo = data.tipo;
        perfilPendente.email = email;
    } catch (e) { console.error(e); }
}

// 🎯 INTERCEPTAR O CLIQUE NO BOTÃO "PAINEL" (Menu Superior)
document.addEventListener('click', function(e) {
    if (e.target.id === 'btn-menu-painel' || e.target.innerText === 'Painel') {
        const status = window.statusUsuario;

        if (status && status.status === 'pendente') {
            e.preventDefault();
            const tipoTexto = status.tipo === 'musico' ? 'MÚSICO / BANDA' : 'ESTABELECIMENTO';
            document.getElementById('tipo-pendente').innerText = tipoTexto;
            document.getElementById('modal-retomar-cadastro').style.display = "flex";
        } 
        else if (status && status.status === 'novo') {
            e.preventDefault();
            document.getElementById('modal-escolha-perfil').style.display = "flex";
        }
    }
});

// 🎯 CÉREBRO DO LOGIN (Página de Login)
window.acaoPosLogin = async function() {
    const user = auth.currentUser;
    const email = (user ? user.email : null) || (document.getElementById('email') ? document.getElementById('email').value : "");

    if (!email) return;

    try {
        const response = await fetch(`/check_user_type?email=${email}`);
        const data = await response.json();

        if (data.status === 'completo') {
            window.location.href = data.redirect;
        } 
        else if (data.status === 'pendente') {
            perfilPendente.tipo = data.tipo;
            perfilPendente.email = email;
            const tipoTexto = data.tipo === 'musico' ? 'MÚSICO / BANDA' : 'ESTABELECIMENTO';
            document.getElementById('tipo-pendente').innerText = tipoTexto;
            document.getElementById('modal-retomar-cadastro').style.display = "flex";
        } 
        else {
            document.getElementById('modal-escolha-perfil').style.display = "flex";
        }
    } catch (error) { console.error(error); }
};

// 🎯 AÇÃO: SIM (CONTINUAR CADASTRO)
document.getElementById('btn-retomar-sim').onclick = () => {
    document.getElementById('modal-retomar-cadastro').style.display = "none";
    
    // 🔥 SEM TRAVA: Músico vai para o Dashboard, Estabelecimento vai para o form de cadastro
    if (perfilPendente.tipo === 'estabelecimento') {
        window.location.href = "/cadastro-estabelecimento";
    } else {
        window.location.href = "/dashboard"; 
    }
};

// 🎯 AÇÃO: NÃO (EXCLUIR TUDO)
document.getElementById('btn-retomar-nao').onclick = async () => {
    const user = auth.currentUser;
    // Pega o e-mail do objeto pendente ou do usuário logado
    const emailExcluir = perfilPendente.email || (user ? user.email : null);
    
    document.getElementById('modal-retomar-cadastro').style.display = "none";

    if (!emailExcluir) {
        exibirPopup("Erro", "Não foi possível identificar o e-mail para exclusão.");
        return;
    }

    try {
        // 1. Chamar o Python para deletar os documentos no Firestore
        const response = await fetch('/api_deletar_dados_usuario', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: emailExcluir })
        });

        if (!response.ok) throw new Error("Erro ao deletar documentos no servidor");

        // 2. Limpar a sessão do Flask
        await fetch('/logout'); 

        // 3. Deletar o usuário do Firebase Authentication
        if (user) {
            await user.delete();
        }

        exibirPopup("Conta Excluída", "Seus dados e sua conta foram apagados com sucesso.");
        
        // Pequeno delay para o usuário ler a mensagem e recarregar a página limpa
        setTimeout(() => { window.location.href = "/"; }, 3000);

    } catch (error) {
        console.error("Erro no processo de exclusão:", error);
        
        // O Firebase Auth exige login recente para deletar conta por segurança
        if (error.code === 'auth/requires-recent-login') {
            exibirPopup("Ação Necessária", "Por segurança, faça login novamente para confirmar a exclusão.");
            auth.signOut();
            setTimeout(() => { window.location.reload(); }, 3500);
        } else {
            exibirPopup("Erro na Exclusão", "Houve um problema. Tente novamente em instantes.");
        }
    }
};



