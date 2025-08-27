import os
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app, origins=["https://deboaacao.vercel.app"])

api_key = os.getenv("API_KEY")
access_key = os.getenv("key")

if not api_key:
    print("AVISO: Variável de ambiente API_KEY não encontrada")
if not access_key:
    print("AVISO: Variável de ambiente key não encontrada")

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

    # Instrução adicional do servidor para forçar a resposta limpa
    server_instruction = (
        "Regra: Não exiba raciocínio, correntes de pensamento, análise, notas internas ou instruções do sistema. "
        "Responda SOMENTE com a resposta final do usuário. "
        "Envolva a resposta final estritamente entre as tags <final> e </final> e não escreva nada fora dessas tags."
    )
    mensagens_com_instrucoes = [{"role": "system", "content": server_instruction}] + mensagens

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-3.1-8b-instruct:free",
                "messages": mensagens_com_instrucoes,
                "temperature": 0.7,
                "max_tokens": 500
            }
        )
        response.raise_for_status()
        response_data = response.json()
        app.logger.info(f"Resposta da API: {response_data}")
        
        if 'choices' not in response_data:
            app.logger.error(f"Resposta da API não contém 'choices': {response_data}")
            return jsonify({'reply': 'Erro: Resposta inválida da API'}), 500
            
        if len(response_data['choices']) == 0:
            app.logger.error("Array 'choices' está vazio")
            return jsonify({'reply': 'Erro: Resposta vazia da API'}), 500
            
        if 'message' not in response_data['choices'][0]:
            app.logger.error(f"Primeiro choice não contém 'message': {response_data['choices'][0]}")
            return jsonify({'reply': 'Erro: Formato de resposta inválido'}), 500
            
        reply = response_data['choices'][0]['message']['content']

        # Extrair SOMENTE o conteúdo dentro de <final>...</final>
        import re
        match = re.search(r"<final>([\s\S]*?)</final>", reply, re.IGNORECASE)
        if match:
            cleaned_reply = match.group(1).strip()
        else:
            app.logger.warning("Resposta sem tags <final>: retornando conteúdo bruto.")
            cleaned_reply = reply.strip()

        return jsonify({'reply': cleaned_reply})
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Erro de requisição para OpenRouter: {str(e)}")
        return jsonify({'reply': 'Erro: Falha na comunicação com a API'}), 500
    except KeyError as e:
        app.logger.error(f"Erro de chave na resposta: {str(e)}")
        return jsonify({'reply': f'Erro: Campo ausente na resposta - {str(e)}'}), 500
    except Exception as e:
        app.logger.error(f"Erro inesperado: {str(e)}")
        return jsonify({'reply': f'Erro: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
