import os
import logging
import re
import time
from functools import wraps
from collections import defaultdict, deque
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

# App e CORS
app = Flask(__name__)
CORS(app, origins=["https://deboaacao.vercel.app"])

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app.logger.setLevel(logging.INFO)

# Config
class Config:
    RATE_LIMIT_REQUESTS = 10
    RATE_LIMIT_WINDOW = 60
    REQUEST_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 500
    MODEL_NAME = "openai/gpt-oss-20b:free"
    MIN_MESSAGE_LENGTH = 1
    MAX_MESSAGE_LENGTH = 4000
    MIN_RESPONSE_LENGTH = 5
    ALLOWED_ORIGINS = [
        "https://deboaacao.vercel.app",
        "https://deboaacao.vercel.app/",
        None
    ]

# Variáveis de ambiente
api_key = os.getenv("API_KEY")
access_key = os.getenv("key")
if not api_key or not access_key:
    raise RuntimeError("ERRO CRÍTICO: Variáveis de ambiente não encontradas")

# Rate limiting
rate_limit_storage = defaultdict(lambda: deque())

def rate_limit(max_requests=Config.RATE_LIMIT_REQUESTS, window=Config.RATE_LIMIT_WINDOW):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            now = time.time()
            log = rate_limit_storage[client_ip]
            while log and log[0] <= now - window:
                log.popleft()
            if len(log) >= max_requests:
                return jsonify({'error': 'Muitas requisições', 'retry_after': window}), 429
            log.append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator

def validate_messages(messages):
    if not isinstance(messages, list) or not messages:
        return False, "Histórico de mensagens ausente ou inválido"
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict) or 'role' not in msg or 'content' not in msg:
            return False, f"Mensagem {i+1} inválida"
        if msg['role'] not in ['user', 'assistant', 'system']:
            return False, f"Role inválido na mensagem {i+1}"
        l = len(str(msg['content']))
        if l < Config.MIN_MESSAGE_LENGTH:
            return False, f"Mensagem {i+1} muito curta"
        if l > Config.MAX_MESSAGE_LENGTH:
            return False, f"Mensagem {i+1} muito longa"
    return True, "Válido"

def extract_final_response(raw):
    if not raw:
        return None
    matches = re.findall(r"<final>(.*?)</final>", raw, re.DOTALL | re.IGNORECASE)
    if matches:
        resp = matches[-1].strip()
        if len(resp) >= Config.MIN_RESPONSE_LENGTH:
            return resp
    return None

def make_request(messages, retries=0):
    body = {
        "model": Config.MODEL_NAME,
        "temperature": Config.DEFAULT_TEMPERATURE,
        "max_tokens": Config.DEFAULT_MAX_TOKENS,
        "messages": messages
    }
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=body,
            timeout=Config.REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 429 and retries < Config.MAX_RETRIES:
            time.sleep(Config.RETRY_DELAY * (2 ** retries))
            return make_request(messages, retries + 1)
        raise e
    except requests.exceptions.RequestException:
        if retries < Config.MAX_RETRIES:
            time.sleep(Config.RETRY_DELAY * (2 ** retries))
            return make_request(messages, retries + 1)
        raise

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'api_key_configured': bool(api_key),
        'access_key_configured': bool(access_key),
        'model': Config.MODEL_NAME,
        'timestamp': time.time()
    })

@app.route('/chat', methods=['POST'])
@rate_limit()
def chat():
    origin = request.headers.get('Origin')
    if origin not in Config.ALLOWED_ORIGINS:
        return jsonify({'error': 'Origin não permitido'}), 403

    token = request.headers.get('Authorization')
    if token != f"Bearer {access_key}":
        return jsonify({'error': 'Token de acesso inválido'}), 401

    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({'error': 'JSON inválido'}), 400

    messages = data.get("history")
    valid, msg = validate_messages(messages)
    if not valid:
        return jsonify({'error': msg}), 400

    system_instruction = {
        "role": "system",
        "content": "Responda pro usuário apenas dentro das tags <final></final>"
    }
    messages = [system_instruction] + messages

    try:
        response = make_request(messages)
        choice = response.get('choices', [{}])[0]
        raw = choice.get('message', {}).get('content', '')
        reply = extract_final_response(raw)
        if not reply:
            return jsonify({'error': 'Não foi possível processar a resposta'}), 502
        return jsonify({'reply': reply})
    except Exception:
        return jsonify({'error': 'Erro interno do servidor'}), 500

if __name__ == '__main__':
    app.run(debug=True)
