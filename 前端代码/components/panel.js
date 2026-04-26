import eventBus from '../core/eventBus.js';

export const initPanel = () => {
    const panel = document.getElementById('info-panel');
    
    eventBus.on('node-clicked', (data) => {
        panel.classList.remove('hidden');
        document.getElementById('p-name').innerText = data.name;
        document.getElementById('p-dynasty').innerText = data.dynasty;
        document.getElementById('p-style').innerText = data.style;
        document.getElementById('p-desc').innerText = data.description;
        document.getElementById('p-img').src = data.image_url;
    });

    document.getElementById('close-panel').onclick = () => {
        panel.classList.add('hidden');
    };
};