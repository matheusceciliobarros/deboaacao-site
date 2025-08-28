import os
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app, origins=["https://deboaacao.vercel.app"])

api_key = os.getenv("API_KEY")
access_key = os.getenv("key")

@app.route('/chat', methods=['POST'])
def chat():
    origin = request.headers.get('Origin')
    origens_permitidas = [
        "https://deboaacao.vercel.app",
        "https://deboaacao.vercel.app/",
        None
    ]

    if origin not in origens_permitidas:
        app.logger.warning(f"Origin não permitida: {origin}")
        abort(403)
    
    token = request.headers.get('Authorization')
    if token != f"Bearer {access_key}":
        app.logger.warning("Tentativa de acesso não autorizado.")
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    mensagens = data.get("history")

    if not isinstance(mensagens, list) or len(mensagens) == 0:
        return jsonify({'reply': 'Erro: histórico de mensagens ausente ou inválido.'}), 400
    for msg in mensagens:
        if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
            return jsonify({'reply': 'Erro: formato de mensagem inválido.'}), 400

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-oss-20b:free",
                "messages": mensagens
            }
        )
        response.raise_for_status()
        raw_reply = response.json()['choices'][0]['message']['content']

        if "assistantfinal" in raw_reply:
            reply = raw_reply.split("assistantfinal", 1)[1].strip()
        else:
            reply = raw_reply.strip()

        return jsonify({'reply': reply})
    except Exception as e:
        app.logger.error(f"Erro ao chamar OpenRouter: {str(e)}")
        return jsonify({'reply': f'Erro: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)


