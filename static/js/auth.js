console.log("🔥 auth.js carregado");

// 🔥 IMPORTS FIREBASE (CDN)
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import {
    getAuth,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js";

import {
    getFirestore,
    doc,
    setDoc,
    serverTimestamp
} from "https://www.gstatic.com/firebasejs/10.7.1/firebase-firestore.js";

// 🔥 CONFIG FIREBASE (APP WEB JÁ CRIADO)
const firebaseConfig = {
    apiKey: "AIzaSyByff364YvPXLeo6k1ccquKTX4Jv-CeOhA",
    authDomain: "slp-musicos-turismo.firebaseapp.com",
    projectId: "slp-musicos-turismo",
    storageBucket: "slp-musicos-turismo.firebasestorage.app",
    messagingSenderId: "289743101948",
    appId: "1:289743101948:web:c11cb6910506e84d405c79"
};

// 🚀 INICIALIZA
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

// 🎯 ELEMENTOS HTML
const form = document.getElementById("auth-form");
const btnSignup = document.getElementById("btn-signup");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");

// 🔐 LOGIN
form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = emailInput.value;
    const password = passwordInput.value;

    try {
        await signInWithEmailAndPassword(auth, email, password);
        await iniciarSessao(email);
        window.location.href = "/dashboard";
    } catch (error) {
        console.error(error);
        alert(traduzirErroFirebase(error));
    }
});

// 🆕 CADASTRO
btnSignup.addEventListener("click", async () => {
    const email = emailInput.value;
    const password = passwordInput.value;

    try {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);

        console.log("🔥 Salvando usuário no Firestore...");

        await setDoc(doc(db, "usuarios", userCredential.user.uid), {
            email: email,
            tipo: "musico",
            data_cadastro: serverTimestamp()
        });

        console.log("✅ Usuário salvo com sucesso");

        await iniciarSessao(email);
        window.location.href = "/dashboard";

    } catch (error) {
        console.error(error);
        alert(traduzirErroFirebase(error));
    }
});

// 🔁 CRIA SESSÃO NO FLASK
async function iniciarSessao(email) {
    await fetch("/set_session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email })
    });
}

// 🌎 TRADUÇÃO DOS ERROS FIREBASE (PT-BR)
function traduzirErroFirebase(error) {
    switch (error.code) {
        case "auth/email-already-in-use":
            return "Este e-mail já está cadastrado. Faça login.";
        case "auth/invalid-email":
            return "E-mail inválido.";
        case "auth/weak-password":
            return "A senha deve ter no mínimo 6 caracteres.";
        case "auth/user-not-found":
            return "Usuário não encontrado.";
        case "auth/wrong-password":
            return "Senha incorreta.";
        case "auth/invalid-credential":
            return "Credenciais inválidas. Verifique e tente novamente.";
        case "auth/network-request-failed":
            return "Erro de conexão. Verifique sua internet.";
        default:
            return "Erro inesperado. Tente novamente.";
    }
}

// Localize o botão usando a classe correta do novo HTML
const togglePasswordBtn = document.querySelector(".log-toggle-eye");

if (togglePasswordBtn) {
    togglePasswordBtn.addEventListener("click", () => {
        // Verifica se o tipo atual é password
        const isHidden = passwordInput.type === "password";

        // Alterna entre text (visível) e password (escondido)
        passwordInput.type = isHidden ? "text" : "password";
        
        // Opcional: muda o ícone para dar feedback visual
        togglePasswordBtn.textContent = isHidden ? "🙈" : "👁";
    });
}