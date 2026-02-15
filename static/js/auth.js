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
    deleteUser
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";

import {
    getFirestore,
    doc,
    setDoc,
    serverTimestamp
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";

// 🔐 BUSCA AS CONFIGURAÇÕES INJETADAS PELO FLASK NO HTML
// Não coloque as chaves aqui! Elas vêm do window.firebaseConfig
const firebaseConfig = window.firebaseConfig;

// 🛡️ VERIFICAÇÃO DE SEGURANÇA
// Se as chaves não existirem (erro de carregamento), o código avisa em vez de travar
if (!firebaseConfig || !firebaseConfig.apiKey) {
    console.error("❌ Erro: As chaves do Firebase não foram encontradas. Verifique o arquivo .env e o app.py.");
}

// 🔥 INICIALIZAÇÃO
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










// 🌐 GOOGLE
const provider = new GoogleAuthProvider();
provider.setCustomParameters({ prompt: 'select_account' });
// 🌐 FLUXO EXCLUSIVO GOOGLE
window.loginComGoogle = async function() {
    try {
        const result = await signInWithPopup(auth, provider);
        const idToken = await result.user.getIdToken();
        const emailGoogle = result.user.email; // Captura direta do provedor

        // 1. Avisa o Python que o cara logou pelo Google
        const response = await fetch('/login_google', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ idToken: idToken })
        });
        
        const data = await response.json();

        if (data.status === 'success') {
            // 2. Chama a verificação exclusiva para o Google
            // Passamos o email direto para não depender de campos da tela
            fluxoVerificacaoExclusivoGoogle(emailGoogle);
        } else {
            alert("Erro no servidor: " + data.message);
        }
    } catch (error) {
        if (error.code !== 'auth/cancelled-popup-request' && error.code !== 'auth/popup-closed-by-user') {
            exibirPopup("Erro Google", "Falha na autenticação");
        }
    }
}

// 🛡️ FUNÇÃO DE APOIO SÓ PARA O GOOGLE (Não mexe no login normal)
async function fluxoVerificacaoExclusivoGoogle(email) {
    try {
        const response = await fetch(`/check_user_type?email=${email}`);
        const statusData = await response.json();

        // Guardamos o email na variável global que sua modal já usa
        dadosTemporarios.email = email;

        if (statusData.status === 'completo') {
            // Se já tem perfil pronto, vai embora pro dash dele
            window.location.href = statusData.redirect;
        } 
        else if (statusData.status === 'pendente') {
            // Se escolheu tipo mas não terminou o cadastro
            const tipoTexto = statusData.tipo === 'musico' ? 'MÚSICO / BANDA' : 'ESTABELECIMENTO';
            document.getElementById('tipo-pendente').innerText = tipoTexto;
            document.getElementById('modal-retomar-cadastro').style.display = "flex";
        } 
        else {
            // STATUS NOVO: É aqui que a modal de escolha abre para o usuário do Google
            document.getElementById('modal-escolha-perfil').style.display = "flex";
        }
    } catch (e) {
        console.error("Erro no fluxo Google:", e);
        window.location.href = "/dashboard";
    }
}




// 🆕 CADASTRO (UNIFICADO)
let dadosTemporarios = { email: "", senha: "" };

if (btnSignup) {
    // Mudamos para ASYNC para poder esperar a resposta do Firebase antes de abrir a modal
    btnSignup.addEventListener("click", async (e) => {
        const email = emailInput.value.trim();
        const password = passwordInput.value;

        if (!email || !password) {
            exibirPopup("Atenção", "Preencha os campos antes de continuar.");
            return; 
        }

        try {
            // 🔥 TRAVA AQUI: Tenta criar a conta ANTES de abrir a modal
            // Se o e-mail já existir, o Firebase vai dar erro e pular direto para o 'catch'
            await createUserWithEmailAndPassword(auth, email, password);

            // Se chegou aqui, a conta é NOVA e foi criada. Agora guardamos e abrimos a modal.
            dadosTemporarios.email = email;
            dadosTemporarios.senha = password;

            const modalEscolha = document.getElementById('modal-escolha-perfil');
            if (modalEscolha) {
                modalEscolha.style.display = "flex";
            }
        } catch (error) {
            console.error("Erro na verificação inicial:", error.code);
            
            // Se o e-mail já existe, ele barra aqui e a modal nem chega a abrir
            if (error.code === 'auth/email-already-in-use') {
                exibirPopup("Erro", "Este e-mail já está cadastrado.");
            } else {
                exibirPopup("Erro", "Erro ao validar cadastro: " + error.message);
            }
        }
    });
}


document.addEventListener("DOMContentLoaded", () => {
    const btnMusico = document.getElementById('btn-escolha-musico');
    const btnEmpresa = document.getElementById('btn-escolha-empresa');

    async function executarCadastroFinal(tipoPerfil) {
        try {
            // 1. O usuário JÁ FOI CRIADO no clique do btnSignup.
            // Aqui apenas salvamos as preferências no Firestore.

            // 2. Salva os dados no Firestore
            await setDoc(doc(db, "usuarios", dadosTemporarios.email), {
                email: dadosTemporarios.email,
                tipo: tipoPerfil,
                acesso_pago: false,
                criado_via: 'sistema', // Adicionado conforme solicitado
                data_cadastro: serverTimestamp()
            }, { merge: true });

            console.log("Dados salvos. Iniciando sessão no servidor...");

            // 3. Cria a sessão no Flask
            await iniciarSessao(dadosTemporarios.email); 

            // 4. REDIRECIONAMENTO
            if (tipoPerfil === 'musico') {
                window.location.href = "/checkout";
            } else {
                window.location.href = "/dashboard";
            }

        } catch (error) {
            console.error("Erro detalhado no salvamento:", error);
            // Se der erro aqui, fechamos a modal para o usuário ver o erro
            const modalEscolha = document.getElementById('modal-escolha-perfil');
            if (modalEscolha) modalEscolha.style.display = "none";
            
            const msg = error.message || "Erro ao processar perfil";
            exibirPopup("Erro", msg);
        }
    }

    if (btnMusico) {
        btnMusico.onclick = () => executarCadastroFinal('musico');
    }

    if (btnEmpresa) {
        btnEmpresa.onclick = () => executarCadastroFinal('estabelecimento');
    }

    window.executarCadastroFinal = executarCadastroFinal;
});


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


// 🎯 AÇÃO: NÃO (APENAS SAIR E SALVAR PROGRESSO)
document.getElementById('btn-retomar-nao').onclick = async () => {
    // 1. Fecha a modal
    document.getElementById('modal-retomar-cadastro').style.display = "none";

    // 2. Avisa que os dados estão salvos
    exibirPopup("Até breve!", "Seu progresso foi salvo. Você pode continuar quando quiser, basta fazer login novamente.");

    try {
        // 3. Desloga do Firebase
        await auth.signOut();

        // 4. Limpa a sessão no Flask
        await fetch('/logout'); 

        // 5. Manda para a home
        setTimeout(() => { window.location.href = "/"; }, 2500);

    } catch (error) {
        console.error("Erro ao sair:", error);
        window.location.href = "/";
    }
};

document.addEventListener("DOMContentLoaded", () => {
    const btnFinalizar = document.getElementById('btn-finalizar-venda');

    if (btnFinalizar) {
        btnFinalizar.addEventListener('click', async () => {
            const emailInput = document.getElementById('email_final');
            const passwordInput = document.getElementById('senha_final');

            const email = emailInput.value.trim();
            const password = passwordInput.value;

            // 🛑 FILTRO CONTRA O ERRO DO STRIPE
            if (email.includes("{CHECKOUT_SESSION") || !email.includes("@")) {
                alert("O e-mail não foi carregado corretamente. Por favor, digite o e-mail manualmente.");
                return;
            }

            // Validação de senha
            if (!password || password.length < 7) {
                alert("Por favor, digite uma senha com pelo menos 7 caracteres.");
                return;
            }

            try {
                console.log("Tentando criar conta para:", email);

                // 1. Cria a conta no Firebase Auth
                await createUserWithEmailAndPassword(auth, email, password);

                // 2. Sincroniza a sessão com o Flask
                // Usamos encodeURIComponent para evitar erros com caracteres especiais no e-mail
                const response = await fetch(`/login_session?email=${encodeURIComponent(email)}`);
                
                if (!response.ok) {
                    throw new Error("O servidor não reconheceu a rota de sessão (Erro 404). Verifique se a rota /login_session existe no Python.");
                }

                console.log("Sessão criada! Redirecionando para o Dashboard...");

                // 3. Redirecionamento Direto
                // Pequeno delay para garantir que o Flask gravou o cookie de sessão
                setTimeout(() => {
                    window.location.href = "/dashboard?sucesso_pagamento=true";
                }, 500);

            } catch (error) {
                console.error("Erro ao finalizar cadastro:", error);
                
                if (error.code === 'auth/email-already-in-use') {
                    alert("Este e-mail já possui conta. Tente fazer login normalmente.");
                } else {
                    alert("Erro técnico: " + error.message);
                }
            }
        });
    }
});