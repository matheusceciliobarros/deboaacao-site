export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Método não permitido' });
    }
    
    try {
        res.setHeader('Cache-Control', 'no-store');
        console.log("KEY:", process.env.key ? "Definida" : "Não definida");
        console.log("Enviando requisição para:", 'https://projeto-deboacao.onrender.com/chat');
        console.log("Body da requisição:", JSON.stringify(req.body));
        
        const resposta = await fetch('https://projeto-deboacao.onrender.com/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${process.env.key}`
            },
            body: JSON.stringify(req.body)
        });
        
        console.log("Status da resposta:", resposta.status);
        console.log("Headers da resposta:", Object.fromEntries(resposta.headers.entries()));
        
        const contentType = resposta.headers.get("content-type") || '';

        if (!resposta.ok) {
            if (contentType.includes('application/json')) {
                const data = await resposta.json();
                console.error("Erro da API (JSON):", data);
                return res.status(resposta.status).json(data);
            } else {
                const texto = await resposta.text();
                console.error("Erro da API (texto):", texto);
                return res.status(resposta.status).json({ error: 'upstream_text', message: texto });
            }
        }
        
        if (!contentType.includes("application/json")) {
            const texto = await resposta.text();
            console.error("Resposta não é JSON:", texto);
            return res.status(502).json({ error: 'upstream_non_json', message: 'Resposta inválida do servidor.' });
        }
        
        const data = await resposta.json();
        console.log("Dados recebidos:", data);
        return res.status(200).json(data);

    } catch (error) {
        console.error("Erro no handler:", error);
        return res.status(500).json({ 
            error: 'proxy_internal_error', 
            message: 'Erro interno no proxy.',
            detalhes: error.message
        });
    }
}
