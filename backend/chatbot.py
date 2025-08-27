import os
import logging
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app, origins=["https://deboaacao.vercel.app"])

# Configurar logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

api_key = os.getenv("API_KEY")
access_key = os.getenv("key")

app.logger.info(f"API_KEY configurada: {'Sim' if api_key else 'Não'}")
app.logger.info(f"Access key configurada: {'Sim' if access_key else 'Não'}")

if not api_key:
    app.logger.error("ERRO CRÍTICO: Variável de ambiente API_KEY não encontrada")
if not access_key:
    app.logger.error("ERRO CRÍTICO: Variável de ambiente key não encontrada")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'api_key_configured': bool(api_key),
        'access_key_configured': bool(access_key)
    })

@app.route('/chat', methods=['POST'])
def chat():
    # Log detalhado para debug
    app.logger.info(f"Recebendo requisição de: {request.headers.get('Origin')}")
    app.logger.info(f"Headers de autorização: {request.headers.get('Authorization')}")
    app.logger.info(f"API_KEY configurada: {'Sim' if api_key else 'Não'}")
    app.logger.info(f"Access key configurada: {'Sim' if access_key else 'Não'}")
    
    origin = request.headers.get('Origin')
    origens_permitidas = [
        "https://deboaacao.vercel.app",
        "https://deboaacao.vercel.app/",
        None
    ]

    if origin not in origens_permitidas:
        app.logger.warning(f"Origin não permitida: {origin}")
        return jsonify({'reply': 'Erro: Origin não permitido'}), 403
    
    token = request.headers.get('Authorization')
    expected_token = f"Bearer {access_key}"
    
    app.logger.info(f"Token recebido: {token}")
    app.logger.info(f"Token esperado: {expected_token}")
    
    if not access_key:
        app.logger.error("Access key não configurada no servidor")
        return jsonify({'reply': 'Erro: Configuração do servidor incompleta'}), 500
        
    if token != expected_token:
        app.logger.warning(f"Token inválido. Recebido: {token}, Esperado: {expected_token}")
        return jsonify({'reply': 'Erro: Token de acesso inválido'}), 401

    data = request.json
    if not data:
        app.logger.error("Dados JSON não recebidos ou inválidos")
        return jsonify({'reply': 'Erro: Dados da requisição inválidos'}), 400
        
    mensagens = data.get("history")

    if not isinstance(mensagens, list) or len(mensagens) == 0:
        app.logger.error(f"Histórico inválido: {mensagens}")
        return jsonify({'reply': 'Erro: histórico de mensagens ausente ou inválido.'}), 400
    for msg in mensagens:
        if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
            app.logger.error(f"Mensagem inválida: {msg}")
            return jsonify({'reply': 'Erro: formato de mensagem inválido.'}), 400

    if not api_key:
        app.logger.error("API_KEY não configurada")
        return jsonify({'reply': 'Erro: API key não configurada no servidor'}), 500

    # Instrução adicional do servidor para forçar a resposta limpa
    server_instruction = (
        "Regra: Não exiba raciocínio, correntes de pensamento, análise, notas internas ou instruções do sistema. "
        "Responda SOMENTE com a resposta final do usuário. "
        "Envolva a resposta final estritamente entre as tags <final> e </final> e não escreva nada fora dessas tags."
    )
    mensagens_com_instrucoes = [{"role": "system", "content": server_instruction}] + mensagens

    try:
        app.logger.info(f"Fazendo requisição para OpenRouter com {len(mensagens_com_instrucoes)} mensagens")
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
            },
            timeout=30
        )
        
        app.logger.info(f"Status da resposta OpenRouter: {response.status_code}")
        app.logger.info(f"Headers da resposta: {dict(response.headers)}")
        
        response.raise_for_status()
        response_data = response.json()
        app.logger.info(f"Resposta da API: {response_data}")
        
        if 'choices' not in response_data:
            app.logger.error(f"Resposta da API não contém 'choices': {response_data}")
            return jsonify({'reply': 'Resposta inválida do provedor de IA.'}), 500
            
        if len(response_data['choices']) == 0:
            app.logger.error("Array 'choices' está vazio")
            return jsonify({'reply': 'Resposta vazia do provedor de IA.'}), 500
            
        if 'message' not in response_data['choices'][0]:
            app.logger.error(f"Primeiro choice não contém 'message': {response_data['choices'][0]}")
            return jsonify({'reply': 'Formato de resposta inválido do provedor.'}), 500
            
        # Prioridade 1: extrair via tool_call (quando suportado)
        msg = response_data['choices'][0].get('message', {})
        tool_calls = msg.get('tool_calls') or []
        cleaned_reply = None
        if tool_calls:
            for call in tool_calls:
                function_call = (call or {}).get('function') or {}
                if function_call.get('name') == 'final_answer':
                    # arguments pode ser string JSON
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

        # Se nada funcionou, não exponha conteúdo bruto potencialmente com raciocínio
        if not cleaned_reply:
            app.logger.warning("Resposta sem tool_call 'final_answer' e sem tags <final>; retornando erro controlado.")
            return jsonify({'reply': 'Não consegui gerar a resposta agora. Tente novamente.'}), 500

        return jsonify({'reply': cleaned_reply})
        
    except requests.exceptions.HTTPError as e:
        app.logger.error(f"HTTPError: {e}")
        if e.response is not None:
            app.logger.error(f"Response content: {e.response.text}")
        status = 502
        try:
            status = e.response.status_code if e.response is not None else 502
        except Exception:
            pass
        # Tratamento por status comum
        if status == 429:
            retry_after = None
            try:
                if e.response is not None:
                    retry_after = e.response.headers.get('Retry-After')
            except Exception:
                retry_after = None
            payload = {'reply': 'Estamos com alta demanda no momento. Tente novamente em instantes.'}
            if retry_after:
                payload['retryAfter'] = retry_after
            app.logger.warning(f"Rate limited pelo provedor. Retry-After: {retry_after}")
            return jsonify(payload), 429
        elif status in (401, 403):
            app.logger.error("Erro de autenticação/autorização com o provedor de IA.")
            return jsonify({'reply': 'Erro de autenticação com o provedor de IA.'}), 500
        elif 500 <= status <= 599:
            app.logger.error(f"Erro 5xx do provedor de IA: {status}")
            return jsonify({'reply': 'Falha no provedor de IA. Tente novamente.'}), 500
        else:
            app.logger.error(f"Erro HTTP ao chamar provedor de IA: {status}")
            return jsonify({'reply': 'Erro ao chamar o provedor de IA.'}), 500
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Erro de requisição para OpenRouter: {str(e)}")
        return jsonify({'reply': 'Não foi possível conectar ao provedor de IA.'}), 500
    except KeyError as e:
        app.logger.error(f"Erro de chave na resposta: {str(e)}")
        return jsonify({'reply': 'Falha ao interpretar a resposta do provedor.'}), 500
    except Exception as e:
        app.logger.error(f"Erro inesperado: {str(e)}")
        return jsonify({'reply': 'Ocorreu um erro interno.'}), 500

if __name__ == '__main__':
    app.run(debug=True)
