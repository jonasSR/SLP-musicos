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
    // ##########################################
    // 1. FILTRO DE GÊNERO (Com suporte a busca)
    // ##########################################
    const genreContainer = document.getElementById('genreFilterContainer');
    const genreInput = document.getElementById('genre-search'); // Referência ao input
    const genreOptions = document.querySelector('#genreFilterContainer .music-options-list');

    if (genreContainer && genreOptions) {
        // Abre/Fecha a lista
        genreContainer.addEventListener('click', function (e) {
            e.stopPropagation();
            if (cityContainer) cityContainer.classList.remove('is-active');
            this.classList.toggle('is-active');
        });

        // Lógica de DIGITAÇÃO no Gênero
        genreInput.addEventListener('input', function() {
            const filter = this.value.toLowerCase();
            const items = genreOptions.querySelectorAll('.music-opt-item');
            items.forEach(item => {
                const text = item.innerText.toLowerCase();
                item.style.display = text.includes(filter) ? 'block' : 'none';
            });
        });

        genreOptions.addEventListener('click', function (e) {
            const option = e.target.closest('.music-opt-item');
            if (!option) return;
            e.stopPropagation();
            const filtro = option.dataset.filter;
            
            // Atualiza o valor do input e remove a lista
            genreInput.value = option.innerText.toUpperCase();
            genreOptions.querySelectorAll('.music-opt-item').forEach(opt => opt.classList.remove('active'));
            option.classList.add('active');

            // Filtra os cards na tela
            document.querySelectorAll('.modern-card').forEach(card => {
                const estilo = card.dataset.estilo;
                card.style.display = (filtro === 'all' || estilo === filtro) ? 'block' : 'none';
            });
            genreContainer.classList.remove('is-active');
        });
    }

    // ##########################################
    // 2. FILTRO DE CIDADE (Com suporte a busca)
    // ##########################################
    const cityContainer = document.getElementById('cityFilterContainer');
    const cityInput = document.getElementById('city-search'); // Referência ao input
    const cityOptions = document.querySelector('#cityFilterContainer .music-options-list');

    if (cityContainer && cityOptions) {
        // Abre/Fecha a lista
        cityContainer.addEventListener('click', function (e) {
            e.stopPropagation();
            if (genreContainer) genreContainer.classList.remove('is-active');
            this.classList.toggle('is-active');
        });

        // Lógica de DIGITAÇÃO na Cidade
        cityInput.addEventListener('input', function() {
            const filter = this.value.toLowerCase();
            const items = cityOptions.querySelectorAll('.music-opt-item');
            items.forEach(item => {
                const text = item.innerText.toLowerCase();
                item.style.display = text.includes(filter) ? 'block' : 'none';
            });
        });

        cityOptions.addEventListener('click', function (e) {
            const option = e.target.closest('.music-opt-item');
            if (!option) return;
            e.stopPropagation();
            
            const form = document.getElementById('cityForm');
            const hiddenInput = document.getElementById('hiddenCityInput');
            
            hiddenInput.value = option.dataset.filter === 'all' ? '' : option.innerText;
            form.submit(); 
        });
    }

    // Fechar ao clicar fora
    window.addEventListener('click', function () {
        if (genreContainer) genreContainer.classList.remove('is-active');
        if (cityContainer) cityContainer.classList.remove('is-active');
    });
});

// ##########################################
// 3. VINCULANDO OS BOTÕES À SUA LÓGICA
// ##########################################
document.querySelectorAll('.category-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const filtro = this.dataset.filter; // Pega o valor exatamente como o seu dropdown

        // 1. Marca o botão como ativo e limpa os outros
        document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');

        // 2. REPLICAÇÃO EXATA DA SUA LÓGICA (Linhas 37-41 do seu código original)
        document.querySelectorAll('.modern-card').forEach(card => {
            const estilo = card.dataset.estilo; //
            card.style.display = (filtro === 'all' || estilo === filtro) ? 'block' : 'none';
        });

        // 3. Atualiza o texto do seu input de gênero para não dar conflito visual
        if (genreInput) {
            genreInput.value = (filtro === 'all') ? "" : this.innerText.trim().toUpperCase();
        }
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


const observerOptions = {
    threshold: 0.1
};


const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, observerOptions);


document.querySelectorAll('.modern-card').forEach(card => {
    observer.observe(card);
});


document.addEventListener('DOMContentLoaded', function() {
    var swiper = new Swiper(".highlightsSwiper", {
        slidesPerView: "auto",      // Mostra quantos couberem
        spaceBetween: 20,           // Espaço entre os cards
        loop: true,                 // Faz o carrossel ser infinito
        grabCursor: true,           // Mostra a mãozinha ao passar o mouse
        autoplay: {
            delay: 2000,            // 2 segundos (2000ms)
            disableOnInteraction: false, // Continua rodando mesmo se o usuário clicar
        },
        speed: 800,                 // Velocidade da transição (suavidade)
    });
});


const menuTrigger = document.getElementById('mobile-menu-trigger');
    const navActions = document.getElementById('nav-links');

    menuTrigger.addEventListener('click', () => {
        // Abre e fecha o menu lateral
        navActions.classList.toggle('nav-active');
        // Transforma o ícone em X
        menuTrigger.classList.toggle('toggle');
    });

    // Fecha o menu se clicar em qualquer link lá dentro
    document.querySelectorAll('.nav-actions a').forEach(link => {
        link.addEventListener('click', () => {
            navActions.classList.remove('nav-active');
            menuTrigger.classList.remove('toggle');
        });
    });