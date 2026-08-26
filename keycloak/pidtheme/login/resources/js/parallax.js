document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById('kc-parallax-wrap');
    const layers = document.querySelectorAll('.kc-parallax-layer');

    if (!container || layers.length === 0) {
        return;
    }

    const handleMouseMove = (event) => {
        const center_x = window.innerWidth / 2;
        const center_y = window.innerHeight / 2;

        layers.forEach(layer => {
            const depth = parseFloat(layer.getAttribute('data-depth')) || 1;

            const offsetX = event.clientX / window.innerWidth
            const offsetY = event.clientY / window.innerHeight

            const translateX = -offsetX * depth * 20;
            const translateY = -offsetY * depth * 20;

            layer.style.transform = `translate3d(${translateX}px, ${translateY}px, 0)`;
        });
    };

    window.addEventListener('mousemove', handleMouseMove);
});