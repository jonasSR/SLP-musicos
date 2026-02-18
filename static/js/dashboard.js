function showMobileTab(evt, tabName) {
    if (window.innerWidth > 768) return;

    // 1. Atualizado para remover também a tab-fas
    document.body.classList.remove('tab-perfil', 'tab-agenda', 'tab-mensagens', 'tab-fas');
    
    // 2. Adiciona a nova (funciona automaticamente para 'fas')
    document.body.classList.add('tab-' + tabName);

    // 3. Gerencia botões
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    evt.currentTarget.classList.add('active');

    window.scrollTo({ top: 0, behavior: 'smooth' });
}


// Inicializa a aba perfil no mobile
document.addEventListener("DOMContentLoaded", function() {
    if (window.innerWidth <= 768) {
        document.body.classList.add('tab-perfil');
    }
});


// --- ELEMENTOS DE PREVIEW ---
const inputName = document.getElementById('input-name');
const inputFile = document.getElementById('input-file');
const selectStyle = document.getElementById('select-style');
const inputCidade = document.getElementById('input-cidade');
const inputEstado = document.getElementById('input-estado');

const previewName = document.getElementById('preview-name');
const previewTag = document.getElementById('preview-tag');
const previewImg = document.getElementById('preview-img');
const previewCidade = document.getElementById('preview-cidade');
const previewEstado = document.getElementById('preview-estado');

// --- NOVOS ELEMENTOS PARA O HEADER (ACRÉSCIMO) ---
const headerName = document.getElementById('header-user-name');
const userEmailPrefix = "{{ session.get('user_email').split('@')[0]|upper }}";

// Fallback de imagem caso não exista uma foto salva
const imagemDoBanco = "{{ musico.foto or 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000' }}";


// Função para atualizar a prévia do card em tempo real
function atualizarCard() {
    // Mantendo seu original
    if (previewName && inputName) previewName.innerText = inputName.value.trim() || "Nome do Artista";
    if (previewTag && selectStyle) previewTag.innerText = selectStyle.value || "Estilo";
    if (previewCidade && inputCidade) previewCidade.innerText = inputCidade.value.trim() || "Cidade";
    if (previewEstado && inputEstado) previewEstado.innerText = inputEstado.value.trim().toUpperCase() || "UF";

    // Lógica de upload de imagem local
    if (inputFile && inputFile.files && inputFile.files[0]) {
        const reader = new FileReader();
        reader.onload = (e) => {
            if (previewImg) previewImg.style.backgroundImage = `url('${e.target.result}')`;
        };
        reader.readAsDataURL(inputFile.files[0]);
    }

    // --- NOVO: Atualiza o nome lá no topo (Painel) enquanto digita ---
    if (headerName && inputName) {
        headerName.innerText = inputName.value.trim().toUpperCase() || "LOGADO";
    }
}


// Listeners para garantir que a função dispare
if (inputName) inputName.addEventListener('input', atualizarCard);
if (selectStyle) selectStyle.addEventListener('change', atualizarCard);
if (inputCidade) inputCidade.addEventListener('input', atualizarCard);
if (inputEstado) inputEstado.addEventListener('input', atualizarCard);
if (inputFile) inputFile.addEventListener('change', atualizarCard);


    // --- LÓGICA DO MENU HAMBÚRGUER ---
    function setupMenu() {
        const mobileMenu = document.getElementById('mobile-menu');
        const navLinks = document.getElementById('nav-links');

        if (mobileMenu && navLinks) {
            // Alternar menu ao clicar
            mobileMenu.addEventListener('click', (e) => {
                e.stopPropagation();
                mobileMenu.classList.toggle('active');
                navLinks.classList.toggle('active');
                document.body.style.overflow = navLinks.classList.contains('active') ? 'hidden' : 'auto';
            });

            // Fechar ao clicar em qualquer link do menu
            document.querySelectorAll('.nav-links a').forEach(link => {
                link.addEventListener('click', () => {
                    mobileMenu.classList.remove('active');
                    navLinks.classList.remove('active');
                    document.body.style.overflow = 'auto';
                });
            });

            // Fechar ao clicar fora do menu
            document.addEventListener('click', (e) => {
                if (!navLinks.contains(e.target) && !mobileMenu.contains(e.target)) {
                    mobileMenu.classList.remove('active');
                    navLinks.classList.remove('active');
                    document.body.style.overflow = 'auto';
                }
            });
        }
    }


    // --- MODAIS E MENSAGENS ---
    function abrirModalSenha() { document.getElementById('modal-senha')?.classList.add('active'); }
    function fecharModalSenha() { document.getElementById('modal-senha')?.classList.remove('active'); }


    function abrirMensagem(id, nome, email, tel, data, local, tipo) {
    // 1. Preenche o Modal (Visual)
    document.getElementById('view-nome').innerText = nome || 'Não informado';
    document.getElementById('view-email').innerText = email || 'Não informado';
    document.getElementById('view-telefone').innerText = tel || 'Não informado';
    document.getElementById('view-data').innerText = data || 'Não informada';
    document.getElementById('view-local').innerText = local || 'Não informado';
    document.getElementById('view-tipo').innerText = tipo || 'Não informado';

    // 2. TRATAMENTO DO NOME (Primeira Letra Maiúscula)
    const rawNome = window.NOME_DO_ARTISTA || "Artista";
    const nomeDoArtista = rawNome.charAt(0).toUpperCase() + rawNome.slice(1).toLowerCase();
    
    // Tratando também o nome do cliente para ficar bonito
    const nomeCliente = (nome || 'cliente').charAt(0).toUpperCase() + (nome || '').slice(1).toLowerCase();

    // 3. TEMPLATE WHATSAPP (Direto e Profissional)
    if (tel) {
        const numeroLimpo = tel.replace(/\D/g, "");
        const msgZap = `Olá, ${nomeCliente}!\n\nAqui é ${nomeDoArtista}. Acabei de receber sua solicitação para o evento do dia ${data} em ${local}.\n\nFiquei muito interessado! Podemos conversar sobre os detalhes e o que você planejou para esse dia?`;
        
        const linkZap = `https://wa.me/55${numeroLimpo}?text=${encodeURIComponent(msgZap)}`;
        document.getElementById('link-telefone-zap').href = linkZap;
        document.getElementById('btn-whats-action').href = linkZap;
    }

    // 4. TEMPLATE E-MAIL TOP (Gmail formatado)
    if (email) {
        const assunto = `PROPOSTA COMERCIAL: Show de ${nomeDoArtista} | Evento ${data}`;
        
        // Template com estrutura de tópicos para facilitar a leitura do cliente
        const corpoEmail = 
            `Olá, ${nomeCliente}.\n\n` +
            `É um prazer entrar em contato! Sou ${nomeDoArtista} e recebi seu interesse através da plataforma Pulsa Music.\n\n` +
            `Verifiquei os detalhes da sua solicitação:\n` +
            `📅 DATA: ${data}\n` +
            `📍 LOCAL: ${local}\n` +
            `🎉 TIPO DE EVENTO: ${tipo}\n\n` +
            `Estou com esta data disponível em minha agenda e adoraria fazer parte deste momento. Gostaria de entender melhor a estrutura do evento para te enviar um orçamento personalizado.\n\n` +
            `Você prefere seguir por aqui ou podemos agilizar os detalhes via WhatsApp?\n\n` +
            `Fico no seu aguardo!\n\n` +
            `Atenciosamente,\n` +
            `${nomeDoArtista}`;

        const linkGmail = `https://mail.google.com/mail/?view=cm&fs=1&to=${email}&su=${encodeURIComponent(assunto)}&body=${encodeURIComponent(corpoEmail)}`;
        
        const btnEmail = document.getElementById('btn-responder');
        if (btnEmail) { 
            btnEmail.href = linkGmail; 
            btnEmail.target = "_blank"; 
        }
    }

    document.getElementById('modal-leitura')?.classList.add('active');
}


    function fecharModal() {
        document.getElementById('modal-leitura')?.classList.remove('active');
        location.reload(); 
    }


    // --- EXCLUSÃO EM MASSA ---
    function updateBulkUI() {
        const checkboxes = document.querySelectorAll('.msg-checkbox:checked');
        const bulkBar = document.getElementById('bulk-actions');
        const countSpan = document.getElementById('selected-count');
        
        if (bulkBar) bulkBar.style.display = checkboxes.length > 0 ? 'block' : 'none';
        if (countSpan) countSpan.innerText = checkboxes.length;
    }


    function toggleSelectAll(master) {
        document.querySelectorAll('.msg-checkbox').forEach(cb => cb.checked = master.checked);
        updateBulkUI();
    }


    function enviarExclusao(listaIds) {
        fetch('/excluir_pedidos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: listaIds })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                location.reload();
            } else {
                alert("Erro: " + data.message);
            }
        });
    }


    function excluirSelecionados() {
        const selecionados = Array.from(document.querySelectorAll('.msg-checkbox:checked')).map(cb => cb.value);
        if (selecionados.length > 0 && confirm(`Excluir ${selecionados.length} mensagens?`)) {
            enviarExclusao(selecionados);
        }
    }


    function excluirMensagemIndividual(id) {
        if (confirm("Apagar esta mensagem?")) enviarExclusao([id]);
    }


    // --- INICIALIZAÇÃO ---
    document.addEventListener('DOMContentLoaded', function() {
        setupMenu();
        atualizarCard();

        // Adicionar eventos de input apenas se existirem
        [inputName, inputFile, selectStyle, inputCidade, inputEstado].forEach(el => {
            el?.addEventListener('input', atualizarCard);
        });

        // Configuração de inputs de data modernos
        document.querySelectorAll('input[type="date"]').forEach(input => {
            input.addEventListener('click', function() {
                try { this.showPicker(); } catch (e) {}
            });
        });

        // Lógica de envio de nova senha
        const formSenha = document.getElementById('form-trocar-senha');
        formSenha?.addEventListener('submit', function(e) {
            e.preventDefault();
            const nova = document.getElementById('nova-senha').value;
            const confirma = document.getElementById('confirma-senha').value;

            if (nova !== confirma) return alert("As senhas não coincidem!");

            fetch('/api_registrar_troca_senha', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nova_senha: nova })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    alert("Senha alterada!");
                    fecharModalSenha();
                }
            });
        });
    });


// FUNÇÂO BARRA MENU DESKTOP
function showSection(sectionId) {
    // Lista de IDs das suas seções
    const sections = ['aba-perfil', 'aba-agenda', 'aba-inbox', 'aba-fas'];
    
    sections.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.classList.remove('section-active');
            element.style.display = 'none';
        }
    });

    const target = document.getElementById(sectionId);
    if (target) {
        target.classList.add('section-active');
        // Garantir que o display apareça mesmo se o CSS travar
        target.style.display = 'block'; 
    }
}


// Inicializa a página mostrando o Perfil
document.addEventListener('DOMContentLoaded', () => {
    if (window.innerWidth > 1024) {
        showSection('aba-perfil');
    }
});


function mascaraTelefone(input) {
    let value = input.value;
    
    // Remove tudo que não for número
    value = value.replace(/\D/g, "");
    
    // Formata: (XX) XXXXX-XXXX
    if (value.length > 0) {
        value = "(" + value;
    }
    if (value.length > 3) {
        value = value.slice(0, 3) + ") " + value.slice(3);
    }
    if (value.length > 10) {
        value = value.slice(0, 10) + "-" + value.slice(10);
    }
    
    // Limita a 15 caracteres: (11) 99999-9999
    input.value = value.slice(0, 15);
}


function compartilharPerfil(elemento) {
    const nomeUrl = elemento.getAttribute('data-nome-url');
    const nomeReal = elemento.getAttribute('data-nome-exibicao');
    
    // Certifique-se que essa URL pública é a página que tem as METATAGS configuradas
    const urlPublica = window.location.protocol + "//" + window.location.host + "/musico/" + nomeUrl;

    if (navigator.share) {
        navigator.share({
            title: 'Perfil de ' + nomeReal,
            text: 'Confira o trabalho de ' + nomeReal,
            url: urlPublica // O app de destino lerá a foto através desta URL
        }).catch(err => {
            console.log("Erro ao compartilhar: ", err);
        });
    } else {
        navigator.clipboard.writeText(urlPublica).then(() => {
            alert("Link de " + nomeReal + " copiado!");
        });
    }
}



function toggleSeguranca(event) {
    event.stopPropagation(); 
    var lista = document.getElementById('lista-seguranca');
    var seta = document.getElementById('seta-seguranca');
    
    if (lista.style.display === 'none' || lista.style.display === '') {
        lista.style.display = 'block';
        seta.style.transform = 'rotate(180deg)'; // Seta vira para cima
    } else {
        lista.style.display = 'none';
        seta.style.transform = 'rotate(0deg)'; // Seta volta ao normal
    }
}

document.addEventListener('click', function(e) {
    var container = document.getElementById('container-seguranca');
    var lista = document.getElementById('lista-seguranca');
    var seta = document.getElementById('seta-seguranca');
    
    if (container && !container.contains(e.target)) {
        lista.style.display = 'none';
        seta.style.transform = 'rotate(0deg)';
    }
});


// FUNÇÃO MODAL GERAR PROPOSTA
function openModal(id) {
    document.getElementById(id).style.display = 'flex'; // Use FLEX aqui
    document.body.style.overflow = 'hidden'; // Trava o scroll do fundo
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
    document.body.style.overflow = 'auto'; // Libera o scroll do fundo
}
window.onclick = function(event) {
    if (event.target.className === 'modal-overlay') { event.target.style.display = "none"; }
}


const colorInput = document.getElementById('cor_proposta');
    const previewBox = document.getElementById('preview-box');
    const labelCor = document.getElementById('label-cor');
    const themeInputs = document.querySelectorAll('input[name="estilo_pdf"]');

    function updateColor(color) {
        // Atualiza o input de cor
        colorInput.value = color;
        // Muda a cor da borda da caixinha de visualização
        previewBox.style.borderColor = color;
        labelCor.style.color = color;
        // Atualiza a variável CSS para os botões acenderem com a cor certa
        document.documentElement.style.setProperty('--accent-color', color);
    }

    // Escuta o clique nos botões (VIP, PULSE...)
    themeInputs.forEach(input => {
        input.addEventListener('change', (e) => {
            const selectedColor = e.target.getAttribute('data-color');
            updateColor(selectedColor);
        });
    });

    // Escuta se o usuário mudar a cor manualmente no seletor
    colorInput.addEventListener('input', (e) => {
        updateColor(e.target.value);
    });