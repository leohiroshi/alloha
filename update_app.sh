#!/bin/bash

# Script para atualizar aplicação FastAPI no container
echo "🚀 Iniciando atualização da aplicação Alloha..."

# Instalar dependências adicionais
pip install httpx

# Criar nova aplicação main.py
cat > /app/main.py << 'PYTHON_APP'
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
import os
import logging
import httpx
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Alloha WhatsApp Bot",
    description="AI-powered real estate WhatsApp bot",
    version="1.0.0"
)

# Variáveis de ambiente
VERIFY_TOKEN = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "alloha_secret")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

@app.get("/")
async def root():
    return {
        "message": "🏠 Alloha WhatsApp Bot funcionando!",
        "service": "alloha-bot",
        "version": "1.0.0",
        "status": "✅ Operacional",
        "endpoints": ["/webhook", "/health", "/docs", "/test"]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "service": "alloha-bot",
        "verify_token_configured": bool(VERIFY_TOKEN),
        "access_token_configured": bool(ACCESS_TOKEN),
        "phone_number_configured": bool(PHONE_NUMBER_ID)
    }

@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    """Verificação do webhook do WhatsApp"""
    params = request.query_params
    logger.info(f"🔍 Verificação webhook: {dict(params)}")
    
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    logger.info(f"Mode: {mode}, Token: {token}, Challenge: {challenge}")
    logger.info(f"Token esperado: {VERIFY_TOKEN}")
    
    if not mode or not token or not challenge:
        logger.error("❌ Parâmetros ausentes")
        raise HTTPException(status_code=400, detail="Missing parameters")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info(f"✅ Webhook verificado! Challenge: {challenge}")
        return challenge
    else:
        logger.error(f"❌ Falha verificação. Esperado: {VERIFY_TOKEN}, Recebido: {token}")
        raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handler mensagens WhatsApp"""
    try:
        body = await request.json()
        logger.info(f"📩 Webhook recebido: {body}")
        
        # Processar mensagem se existir
        if "entry" in body:
            for entry in body["entry"]:
                if "changes" in entry:
                    for change in entry["changes"]:
                        if "value" in change and "messages" in change["value"]:
                            await process_message(change["value"])
        
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"❌ Erro webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_message(value):
    """Processar mensagem"""
    try:
        messages = value.get("messages", [])
        if not messages:
            return
        
        message = messages[0]
        from_number = message["from"]
        text = message.get("text", {}).get("body", "")
        
        logger.info(f"📱 Mensagem de {from_number}: {text}")
        
        # Resposta básica
        response = f"🏠 Olá! Recebi sua mensagem: '{text}'. Sou o assistente da Alloha!"
        await send_message(from_number, response)
        
    except Exception as e:
        logger.error(f"❌ Erro processando: {str(e)}")

async def send_message(to: str, text: str):
    """Enviar mensagem WhatsApp"""
    try:
        if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
            logger.warning("⚠️ WhatsApp não configurado")
            return
        
        url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                logger.info(f"✅ Mensagem enviada para {to}")
            else:
                logger.error(f"❌ Erro envio: {resp.status_code}")
                
    except Exception as e:
        logger.error(f"❌ Erro envio: {str(e)}")

@app.get("/test")
async def test():
    return {
        "status": "✅ OK",
        "verify_token": VERIFY_TOKEN,
        "webhook_url": "https://alloha.app/webhook",
        "test_url": f"https://alloha.app/webhook?hub.mode=subscribe&hub.verify_token={VERIFY_TOKEN}&hub.challenge=test123"
    }
PYTHON_APP

echo "✅ Aplicação atualizada!"
echo "🔄 Reiniciando servidor..."

# Reiniciar aplicação
exec python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
