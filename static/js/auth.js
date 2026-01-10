console.log("🔥 auth.js carregado");

// 🔥 IMPORTS FIREBASE (CDN)
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import {
    getAuth,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    updatePassword
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

// 🚀 INICIALIZA FIREBASE
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

// 🎯 ELEMENTOS HTML (LOGIN)
const formLogin = document.getElementById("auth-form");
const btnSignup = document.getElementById("btn-signup");
const emailInput = document.getElementById("email");
const passwordInput = document.getElementById("password");

// 🔐 LOGIN
if (formLogin) {
    formLogin.addEventListener("submit", async (e) => {
        e.preventDefault();

        try {
            await signInWithEmailAndPassword(
                auth,
                emailInput.value,
                passwordInput.value
            );

            await iniciarSessao(emailInput.value);
            window.location.href = "/dashboard";

        } catch (error) {
            console.error(error);
            alert(traduzirErroFirebase(error));
        }
    });
}

// 🆕 CADASTRO
if (btnSignup) {
    btnSignup.addEventListener("click", async () => {
        try {
            const userCredential = await createUserWithEmailAndPassword(
                auth,
                emailInput.value,
                passwordInput.value
            );

            await setDoc(doc(db, "usuarios", userCredential.user.uid), {
                email: emailInput.value,
                tipo: "musico",
                data_cadastro: serverTimestamp()
            });

            await iniciarSessao(emailInput.value);
            window.location.href = "/dashboard";

        } catch (error) {
            console.error(error);
            alert(traduzirErroFirebase(error));
        }
    });
}

// 🔁 CRIA SESSÃO NO FLASK
async function iniciarSessao(email) {
    await fetch("/set_session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email })
    });
}

// 🌎 TRADUÇÃO DE ERROS FIREBASE
function traduzirErroFirebase(error) {
    switch (error.code) {
        case "auth/email-already-in-use":
            return "Este e-mail já está cadastrado.";
        case "auth/invalid-email":
            return "E-mail inválido.";
        case "auth/weak-password":
            return "A senha deve ter no mínimo 6 caracteres.";
        case "auth/user-not-found":
            return "Usuário não encontrado.";
        case "auth/wrong-password":
            return "Senha incorreta.";
        case "auth/invalid-credential":
            return "Credenciais inválidas.";
        default:
            return "Erro inesperado. Tente novamente.";
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
