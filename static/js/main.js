// main.js
document.addEventListener('DOMContentLoaded', () => {
    // Exemplo de interatividade básica
    const heroButton = document.querySelector('.btn-primary-action');
    heroButton.addEventListener('click', () => {
        // Scroll suave para a seção de artistas
        document.querySelector('.featured-artists').scrollIntoView({
            behavior: 'smooth'
        });
    });

    // Animação dos cards ao aparecer na tela (opcional, requer Intersection Observer)
    const artistCards = document.querySelectorAll('.artist-card');
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            } else {
                entry.target.classList.remove('visible'); // Remove ao sair da tela para reanimar ao voltar
            }
        });
    }, { threshold: 0.1 }); // Começa a animar quando 10% do card está visível

    artistCards.forEach(card => {
        observer.observe(card);
    });

    // Adicione um CSS para essa classe 'visible' para ver o efeito:
    // .artist-card { opacity: 0; transform: translateY(20px); transition: all 0.6s ease-out; }
    // .artist-card.visible { opacity: 1; transform: translateY(0); }
});

document.addEventListener('DOMContentLoaded', function () {
    const container = document.getElementById('genreFilterContainer');
    const selectedText = document.getElementById('genre-label');
    const optionsList = document.querySelector('.music-options-list');

    if (!container || !optionsList) return;

    // Abrir / fechar menu
    container.addEventListener('click', function (e) {
        e.stopPropagation();
        this.classList.toggle('is-active');
    });

    // Seleção de opções (Usando delegação de eventos)
    optionsList.addEventListener('click', function (e) {
        const option = e.target.closest('.music-opt-item');
        if (!option) return;

        e.stopPropagation();

        // 1. Atualiza o texto do botão
        const filtro = option.dataset.filter;
        selectedText.innerText = option.innerText.toUpperCase();

        // 2. Gerencia classe ativa visualmente
        document.querySelectorAll('.music-opt-item').forEach(opt => opt.classList.remove('active'));
        option.classList.add('active');

        // 3. Lógica de Filtro dos Cards
        document.querySelectorAll('.modern-card').forEach(card => {
            const estilo = card.dataset.estilo;
            // Se for 'all' mostra todos, senão compara com o dataset do card
            card.style.display = (filtro === 'all' || estilo === filtro) ? 'block' : 'none';
        });

        // 4. Fecha o menu
        container.classList.remove('is-active');
    });

    // Fechar ao clicar fora de qualquer lugar da janela
    window.addEventListener('click', function () {
        container.classList.remove('is-active');
    });
});
document.addEventListener("DOMContentLoaded", function() {
    const cards = document.querySelectorAll(".modern-card");

    const appearanceOptions = {
        threshold: 0.2, // O efeito começa quando 20% do card aparece na tela
        rootMargin: "0px 0px -50px 0px" // Dispara um pouco antes de chegar na visão total
    };

    const appearanceObserver = new IntersectionObserver(function(entries, appearanceObserver) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("visible");
                // Uma vez que apareceu, não precisamos mais observar esse card
                appearanceObserver.unobserve(entry.target);
            }
        });
    }, appearanceOptions);

    cards.forEach(card => {
        appearanceObserver.observe(card);
    });
});