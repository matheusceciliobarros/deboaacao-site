export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ error: 'Método não permitido' });
    }
    
    try {
        console.log(process.env.key)
        const resposta = await fetch('https://projeto-deboacao.onrender.com', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${process.env.key}`
            },
            body: JSON.stringify(req.body)
        });
        const data = await resposta.json();
        res.status(200).json(data);
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Erro interno' });
    }
}
