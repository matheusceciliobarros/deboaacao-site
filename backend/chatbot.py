import os
import logging
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app, origins=["https://deboaacao.vercel.app"])

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

    server_instruction = (
        "IMPORTANTE: Atue de forma EFICIENTE e OTIMIZADA. Responder o usuário EXCLUSIVAMENTE dentro das tags <final> e </final>. "
        "NÃO escreva NADA antes, depois ou fora dessas tags."
        "Formato OBRIGATÓRIO: <final>sua resposta aqui</final> "
        "Exemplo CORRETO: <final>Olá! Como posso ajudar você?</final> "   
    )
    mensagens_com_instrucoes = [{"role": "system", "content": server_instruction}] + mensagens

    # Analisar se a pergunta precisa de pesquisa na internet
    def precisa_pesquisa(mensagem_usuario):
        """Determina se a pergunta do usuário precisa de pesquisa na internet"""
        palavras_pesquisa = [
    # Termos genéricos de pesquisa
    'pesquise', 'procure por', 'busque por', 'encontre para mim', 'dá pra verificar',
    'você consegue achar', 'descubra', 'me diga onde', 'veja se', 'veja onde', 'confira',

    # Palavras relacionadas a informações recentes ou atualizadas
    'recente', 'atual', 'atualizado', 'último', 'última', 'novo', 'nova', 'novos', 'novas',
    'governo atual', 'mudanças', 'edição atual', 'versão mais recente', 'dados atuais',

    # Termos de eventos, oportunidades e programas
    'programas sociais 2025', 'novos programas', 'nova ong', 'novas iniciativas',
    'inscrições abertas', 'vagas disponíveis', 'cadastro aberto', 'edital aberto', 'chamada pública',

    # Solicitações específicas de tempo ou localização
    'quando será', 'qual o horário', 'que dia vai ser', 'onde acontece', 'local do evento',
    'onde está disponível', 'onde comprar', 'preço atual de', 'valor hoje',

    # Citações a fontes externas (indicando possível pesquisa)
    'segundo o site', 'no google', 'no reclame aqui', 'no linkedin', 'no site oficial', 'no youtube'
]

        
        mensagem_lower = mensagem_usuario.lower()
        return any(palavra in mensagem_lower for palavra in palavras_pesquisa)
    
    # Verificar se precisa de pesquisa
    ultima_mensagem = mensagens[-1]['content'] if mensagens else ""
    usar_pesquisa = precisa_pesquisa(ultima_mensagem)
    
    app.logger.info(f"Última mensagem: {ultima_mensagem}")
    app.logger.info(f"Precisa de pesquisa: {usar_pesquisa}")
    
    if usar_pesquisa:
        # Usar modelo com pesquisa para perguntas que precisam de informações atualizadas
        # ATENÇÃO: z-ai também é modelo de raciocínio, precisa de tratamento especial
        model_config = {
            "model": "z-ai/glm-4.5-air:free",
            "temperature": 0.5,  # Reduzir criatividade para ser mais direto
            "max_tokens": 300    # Reduzir tokens para evitar raciocínio longo
        }
        request_body = {
            **model_config,
            "messages": mensagens_com_instrucoes,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "Pesquisar informações atualizadas na internet"
                    }
                }
            ]
        }
        app.logger.info("Usando modelo z-ai COM PESQUISA (também é modelo de raciocínio)")
    else:
        # Usar modelo otimizado para conversas normais
        model_config = {
            "model": "openai/gpt-oss-20b:free",
            "temperature": 0.7,
            "max_tokens": 500
        }
        request_body = {
            **model_config,
            "messages": mensagens_com_instrucoes
        }
        app.logger.info("Usando modelo gpt-oss para conversa normal")

    try:
        app.logger.info(f"Fazendo requisição para OpenRouter com {len(mensagens_com_instrucoes)} mensagens")
        app.logger.info(f"Modelo: {model_config['model']}")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=request_body,
            timeout=30
        )
        
        app.logger.info(f"Status da resposta OpenRouter: {response.status_code}")
        app.logger.info(f"Headers da resposta: {dict(response.headers)}")
        
        response.raise_for_status()
        response_data = response.json()
        app.logger.info(f"Resposta da API: {response_data}")
        
        # Processar resposta
        if 'choices' not in response_data:
            app.logger.error(f"Resposta da API não contém 'choices': {response_data}")
            return jsonify({'reply': 'Resposta inválida do provedor de IA.'}), 500
            
        if len(response_data['choices']) == 0:
            app.logger.error("Array 'choices' está vazio")
            return jsonify({'reply': 'Resposta vazia do provedor de IA.'}), 500
            
        if 'message' not in response_data['choices'][0]:
            app.logger.error(f"Primeiro choice não contém 'message': {response_data['choices'][0]}")
            return jsonify({'reply': 'Formato de resposta inválido do provedor.'}), 500
            
        msg = response_data['choices'][0].get('message', {})
        reply = msg.get('content') or ''
        
        app.logger.info(f"Resposta bruta da IA: {reply}")
        
        # Extrair SOMENTE o conteúdo dentro de <final>...</final>
        import re
        matches = re.findall(r"<final>(.*?)</final>", reply, re.DOTALL | re.IGNORECASE)
        if matches:
            cleaned_reply = matches[-1].strip()
            app.logger.info(f"Resposta limpa extraída (última tag): {cleaned_reply}")
        else:
            app.logger.warning(f"Tags <final> não encontradas na resposta: {reply}")
            # Para o modelo z-ai, tentar extrair apenas a resposta final
            if usar_pesquisa:
                # Tentar encontrar padrões de resposta final do z-ai
                # O modelo z-ai às vezes termina com a resposta direta sem tags
                lines = [line.strip() for line in reply.strip().split('\n') if line.strip()]
                if lines:
                    # Pegar as últimas linhas que não sejam raciocínio
                    resposta_lines = []
                    for line in reversed(lines):
                        if not any(palavra in line.lower() for palavra in ['reasoning', 'analysis', 'devo', 'preciso', 'vou']):
                            resposta_lines.insert(0, line)
                        else:
                            break
                    cleaned_reply = ' '.join(resposta_lines) if resposta_lines else lines[-1]
                else:
                    cleaned_reply = "Desculpe, não consegui processar sua mensagem."
            else:
                lines = reply.strip().split('\n')
                cleaned_reply = lines[-1].strip() if lines else "Desculpe, não consegui processar sua mensagem."

        # Se ainda não há resposta válida, retornar erro
        if not cleaned_reply or len(cleaned_reply.strip()) == 0:
            app.logger.warning("Resposta vazia após processamento.")
            return jsonify({'reply': 'Não consegui gerar a resposta agora. Tente novamente.'}), 500

        return jsonify({'reply': cleaned_reply})
        
    except requests.exceptions.HTTPError as e:
        app.logger.error(f"HTTPError com modelo {model_config['model']}: {e}")
        
        # Se der erro 404 (modelo não suporta tools), tentar sem ferramentas
        if e.response and e.response.status_code == 404 and usar_pesquisa:
            app.logger.info("Modelo z-ai não suporta tools, tentando sem pesquisa...")
            try:
                fallback_body = {
                    "model": "openai/gpt-oss-20b:free",
                    "messages": mensagens_com_instrucoes,
                    "temperature": 0.7,
                    "max_tokens": 500
                }
                
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=fallback_body,
                    timeout=30
                )
                response.raise_for_status()
                response_data = response.json()
                app.logger.info("Sucesso com modelo gpt-oss (fallback)")
                
                # Processar resposta do fallback
                if 'choices' not in response_data or len(response_data['choices']) == 0:
                    return jsonify({'reply': 'Resposta vazia do provedor de IA.'}), 500
                
                msg = response_data['choices'][0].get('message', {})
                reply = msg.get('content') or ''
                
                # Para gpt-oss, usar o sistema de tags
                import re
                matches = re.findall(r"<final>(.*?)</final>", reply, re.DOTALL | re.IGNORECASE)
                if matches:
                    cleaned_reply = matches[-1].strip()
                else:
                    lines = reply.strip().split('\n')
                    cleaned_reply = lines[-1].strip() if lines else "Desculpe, não consegui processar sua mensagem."
                
                if not cleaned_reply:
                    return jsonify({'reply': 'Não consegui gerar a resposta agora. Tente novamente.'}), 500
                
                return jsonify({'reply': cleaned_reply})
                
            except Exception as fallback_error:
                app.logger.error(f"Fallback também falhou: {fallback_error}")
                return jsonify({'reply': 'Erro interno do servidor.'}), 500
        else:
            # Para outros tipos de erro HTTP
            status = e.response.status_code if e.response else 500
            if status == 429:
                return jsonify({'reply': 'Estamos com alta demanda no momento. Tente novamente em instantes.'}), 429
            elif status in (401, 403):
                return jsonify({'reply': 'Erro de autenticação com o provedor de IA.'}), 500
            else:
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
