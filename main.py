from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
import os
import logging

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

@app.get("/")
async def root():
    return {"message": "Alloha WhatsApp Bot is running!"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "alloha-bot"}

@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    """Verificação do webhook do WhatsApp"""
    params = request.query_params
    
    # Log da requisição
    logger.info(f"Webhook verification request: {dict(params)}")
    
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    # Verificar parâmetros obrigatórios
    if not mode or not token or not challenge:
        logger.error("Missing required parameters")
        raise HTTPException(status_code=400, detail="Missing required parameters")
    
    # Verificar token
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info(f"Webhook verified successfully with challenge: {challenge}")
        return challenge
    else:
        logger.error(f"Verification failed. Mode: {mode}, Token: {token}")
        raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handler para mensagens do WhatsApp"""
    try:
        body = await request.json()
        logger.info(f"Received webhook: {body}")
        
        # Por enquanto, apenas log das mensagens
        # Aqui implementaremos a lógica de AI posteriormente
        
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
