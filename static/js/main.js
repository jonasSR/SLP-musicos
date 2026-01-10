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