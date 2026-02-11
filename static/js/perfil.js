flatpickr("#data-criativa", {
"locale": "pt", 
dateFormat: "d/m/Y",
disableMobile: "true", 
minDate: "today", 
onReady: function(selectedDates, dateStr, instance) {
    instance.calendarContainer.classList.add("custom-flatpickr");
}, // <--- Faltava essa vírgula e o fechamento da chave
onOpen: function(selectedDates, dateStr, instance) {
    instance.calendarContainer.classList.add("open");
}
});



document.addEventListener('DOMContentLoaded', function() {
const flashContainer = document.getElementById('flash-container');
if (flashContainer) {
    setTimeout(() => {
        flashContainer.style.transition = "opacity 0.8s ease";
        flashContainer.style.opacity = "0";
        setTimeout(() => flashContainer.remove(), 800);
    }, 5000); // 5 segundos
}
});


document.getElementById('form-feedback').addEventListener('submit', async (e) => {
e.preventDefault();
const btn = document.getElementById('btn-enviar-feedback');
const formData = new FormData(e.target);

btn.disabled = true;
btn.innerText = "ENVIANDO...";

try {
    const response = await fetch('/api/enviar_feedback', {
        method: 'POST',
        body: formData
    });
    const res = await response.json();

    if (res.status === 'success') {
        Swal.fire({
            title: 'Valeu pelo carinho!',
            text: 'Seu depoimento foi enviado e aparecerá aqui assim que o artista aprovar.',
            icon: 'success',
            background: '#1a1a1a',
            color: '#fff',
            confirmButtonColor: '#00d2ff'
        });
        e.target.reset();
    }
} catch (error) {
    Swal.fire('Erro', 'Tente novamente mais tarde.', 'error');
} finally {
    btn.disabled = false;
    btn.innerText = "ENVIAR NO MURAL";
}
});


document.querySelector('.profile-form').addEventListener('submit', async (e) => {
e.preventDefault(); // Impede o navegador de abrir a página de JSON puro

const formData = new FormData(e.target);
const submitBtn = e.target.querySelector('button');

// Desativa o botão para evitar cliques duplos
submitBtn.disabled = true;
submitBtn.innerText = "ENVIANDO...";

try {
    const response = await fetch('/reservar', {
        method: 'POST',
        body: formData
    });

    const result = await response.json();

    if (result.status === 'success') {
        Swal.fire({
            title: 'Sucesso!',
            text: result.message,
            icon: 'success',
            background: '#1a1a1a', // Cor escura para combinar com seu tema
            color: '#fff',
            confirmButtonColor: '#6200ea',
            confirmButtonText: 'OK'
        }).then(() => {
            // Redireciona de volta para o perfil do músico
            window.location.href = result.redirect;
        });
    } else {
        Swal.fire({
            title: 'Erro',
            text: result.message,
            icon: 'error',
            background: '#1a1a1a',
            color: '#fff'
        });
        submitBtn.disabled = false;
        submitBtn.innerText = "SOLICITAR ORÇAMENTO";
    }
} catch (error) {
    console.error('Erro:', error);
    Swal.fire('Erro', 'Ocorreu uma falha na conexão.', 'error');
    submitBtn.disabled = false;
    submitBtn.innerText = "SOLICITAR ORÇAMENTO";
}
});


function toggleDropdown() {
document.getElementById('optionsList').classList.toggle('active');
}


function selectOption(texto, valor) {
// Atualiza o texto que o usuário vê
document.getElementById('selected-text').innerText = texto;
document.getElementById('selected-text').style.color = "#00d2ff";

// Salva o valor no input escondido para o Flask receber
document.getElementById('tipo_hidden_input').value = valor;

// Fecha o menu
toggleDropdown();
}

// Fecha o menu se clicar fora dele
window.onclick = function(event) {
if (!event.target.matches('.select-trigger') && !event.target.matches('#selected-text')) {
    const dropdown = document.getElementById('optionsList');
    if (dropdown.classList.contains('active')) {
        dropdown.classList.remove('active');
    }
}
}

// FUNÇÃO PARA TROCAR ABAS NO MOBILE
function showMobileTab(event, tabId) {
// 1. Esconde todos os blocos com a classe tab-content
const contents = document.querySelectorAll('.tab-content');
contents.forEach(c => c.classList.remove('active'));

// 2. Desativa todos os botões de aba
const buttons = document.querySelectorAll('.tab-btn');
buttons.forEach(b => b.classList.remove('active'));

// 3. Mostra o bloco que tem o ID clicado
const target = document.getElementById(tabId);
if(target) {
    target.classList.add('active');
}

// 4. Ativa o botão que foi clicado
event.currentTarget.classList.add('active');

// 5. Scroll para o topo
document.querySelector('.artist-details').scrollTop = 0;
window.scrollTo(0,0);
}