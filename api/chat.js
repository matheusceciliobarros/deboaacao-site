export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Método não permitido' });
    }
    
    try {
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
        
        const contentType = resposta.headers.get("content-type");

        if (!resposta.ok) {
            const texto = await resposta.text();
            console.error("Erro da API:", texto);
            return res.status(500).json({ error: 'Erro da API externa', detalhes: texto });
        }
        
        if (!contentType || !contentType.includes("application/json")) {
            const texto = await resposta.text();
            return res.status(resposta.status).json({ 
                error: 'Erro da API externa', 
                detalhes: texto,
                status: resposta.status
            });
        }
        
        const data = await resposta.json();
        res.status(200).json(data);

    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Erro interno' });
    }
}

