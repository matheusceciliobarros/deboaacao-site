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
                "model": "openai/gpt-oss-20b:free",
                "messages": mensagens_com_instrucoes,
                "temperature": 0.7,
                "max_tokens": 500,
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "final_answer",
                            "description": "Retorna exclusivamente a resposta final pronta para o usuário, sem raciocínio interno.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "text": {"type": "string", "description": "Resposta final para o usuário."}
                                },
                                "required": ["text"]
                            }
                        }
                    }
                ],
                "tool_choice": {"type": "function", "function": {"name": "final_answer"}}
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
            
        # Prioridade 1: tentar extrair via tool_call
        msg = response_data['choices'][0].get('message', {})
        tool_calls = msg.get('tool_calls') or []
        cleaned_reply = None
        if tool_calls:
            for call in tool_calls:
                function_call = (call or {}).get('function') or {}
                if function_call.get('name') == 'final_answer':
                    import json
                    try:
                        args_raw = function_call.get('arguments')
                        if isinstance(args_raw, str):
                            args = json.loads(args_raw)
                        elif isinstance(args_raw, dict):
                            args = args_raw
                        else:
                            args = {}
                        text = (args.get('text') or '').strip()
                        if text:
                            cleaned_reply = text
                            break
                    except Exception as e:
                        app.logger.warning(f"Falha ao parsear arguments do tool_call: {e}")

        # Prioridade 2: extrair SOMENTE o conteúdo dentro de <final>...</final>
        if cleaned_reply is None:
            reply = msg.get('content') or ''
            import re
            match = re.search(r"<final>([\s\S]*?)</final>", reply, re.IGNORECASE)
            if match:
                cleaned_reply = match.group(1).strip()
        if not cleaned_reply:
            app.logger.warning("Resposta sem tool_call 'final_answer' e sem tags <final>; retornando erro controlado.")
            return jsonify({'reply': 'Desculpe, não consegui gerar a resposta agora. Tente novamente.'}), 502

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

