document.getElementById('chatbot-btn').addEventListener('click', function () {
    document.getElementById('chatbot-btn').style.scale = 0;
    document.getElementById('chatbot').style.scale = 1;
});
document.getElementById('close-chat').addEventListener('click', function () {
    document.getElementById('chatbot').style.scale = 0;
    document.getElementById('chatbot-btn').style.scale = 1;
});

const maps = [
    {
        nome: "Banco de Alimentos",
        link: "https://www.google.com/maps/d/embed?mid=1WberAFnBZwC1B_ThSlMHwalF7lMq5t4&ehbc=2E312F"
    },
    {
        nome: "Pontos de Alimentos",
        link: "https://www.google.com/maps/d/embed?mid=1UJVgedVRrfsIsFI5RnAnOswyRepQ6cY&ehbc=2E312F"
    },
    {
        nome: "Cozinhas Comunitárias",
        link: "https://www.google.com/maps/d/embed?mid=1dkD-4pGtcab0Jd79Zp68SvMJet8BlDQ&ehbc=2E312F"
    },
    {
        nome: "Serviços Gratuitos",
        link: "https://www.google.com/maps/d/embed?mid=1qcf2QypXu1H5Bs0bTsB-OrE79RNQD8Y&ehbc=2E312F"
    },
    {
        nome: "Cursos Gratuitos",
        link: "https://www.google.com/maps/d/embed?mid=1SYSR7QVxmPES7t4fHFC68RIuLtU_FT4&ehbc=2E312F"
    }
];

let currentMapIndex = 0;

const mapFrame = document.getElementById('map-frame');
const prevBtn = document.getElementById('prev-map');
const nextBtn = document.getElementById('next-map');

function loadMap(index) {
    mapFrame.src = maps[index].link;
}

prevBtn.addEventListener('click', () => {
    currentMapIndex = (currentMapIndex - 1 + maps.length) % maps.length;
    loadMap(currentMapIndex);
});

nextBtn.addEventListener('click', () => {
    currentMapIndex = (currentMapIndex + 1) % maps.length;
    loadMap(currentMapIndex);
});

loadMap(currentMapIndex);

// chatbot

const chatForm = document.getElementById('chat-form');
const chatInput = chatForm.querySelector('input');
const chatbox = document.getElementById('chatbox');

const suggestions = [
    "Quem foi Carolina Maria de Jesus?",
    "Fale sobre cozinhas comunitárias"
];

const suggestionsDiv = document.getElementById('suggestions');

suggestions.forEach(suggestion => {
    const btn = document.createElement('button');
    btn.textContent = suggestion;
    btn.type = "button";
    btn.classList.add('suggestion-btn');
    
    btn.addEventListener('click', () => {
        chatInput.value = suggestion;
        chatInput.focus();
    });

    suggestionsDiv.appendChild(btn);
});

const history = [
    { role: "system", content: "Você é uma assistente simpática, direta e informativa de uma ONG que ajuda comunidades carentes. Nunca use estilos na mensagem, como negrito ou emojis." }
];

chatForm.addEventListener('submit', async function(event) {
    event.preventDefault();

    const userMessage = chatInput.value.trim();
    if (!userMessage) return;

    const userDiv = document.createElement('div');
    userDiv.classList.add('message', 'user-message');
    userDiv.textContent = userMessage;
    chatbox.appendChild(userDiv);
    chatbox.scrollTop = chatbox.scrollHeight;

    history.push({ role: "user", content: userMessage });

    const mensagensLimitadas = [history[0], ...history.slice(-20)];

    chatInput.value = '';

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: userMessage,
                history: mensagensLimitadas
            })
        });

        const data = await response.json();
        const botReply = data.reply || "Erro na resposta";

        const botDiv = document.createElement('div');
        botDiv.classList.add('message', 'bot-message');
        botDiv.textContent = botReply;
        chatbox.appendChild(botDiv);
        chatbox.scrollTop = chatbox.scrollHeight;

        history.push({ role: "assistant", content: botReply });

    } catch (err) {
        const botDiv = document.createElement('div');
        botDiv.classList.add('message', 'bot-message');
        botDiv.textContent = "Erro ao conectar com o chatbot.";
        chatbox.appendChild(botDiv);
        chatbox.scrollTop = chatbox.scrollHeight;
    }
});

// Mensagem inicial automática
window.onload = function() {
    const botDiv = document.createElement('div');
    botDiv.classList.add('message', 'bot-message');
    botDiv.textContent = "Olá! Sou a Carolina. Pode me perguntar qualquer coisa, sobre ONGs, cozinhas comunitárias ou minha história!";
    chatbox.appendChild(botDiv);
    chatbox.scrollTop = chatbox.scrollHeight;
};
