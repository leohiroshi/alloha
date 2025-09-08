from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from app.services.whatsapp_service import WhatsAppService
from app.services.ai_service import AIService
from app.services.database_service import DatabaseService

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar instância do FastAPI
app = FastAPI(
    title="Alloha WhatsApp Bot",
    description="AI-powered real estate WhatsApp bot",
    version="1.0.0"
)

# CORS para desenvolvimento
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variáveis de ambiente
VERIFY_TOKEN = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "alloha_secret")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

# Inicializar serviços
whatsapp_service = WhatsAppService(ACCESS_TOKEN, PHONE_NUMBER_ID)
ai_service = AIService()
db_service = DatabaseService()

@app.get("/")
async def root():
    return {
        "message": "Alloha WhatsApp Bot is running!",
        "service": "alloha-bot",
        "version": "1.0.0",
        "endpoints": ["/webhook", "/health", "/docs"],
        "status": "active"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "service": "alloha-bot",
        "verify_token_configured": bool(VERIFY_TOKEN),
        "access_token_configured": bool(ACCESS_TOKEN),
        "phone_number_configured": bool(PHONE_NUMBER_ID),
        "database_connected": await db_service.check_connection(),
        "ai_service_available": ai_service.is_available()
    }

@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    """Verificação do webhook do WhatsApp"""
    params = request.query_params
    
    logger.info(f"Webhook verification request: {dict(params)}")
    
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    logger.info(f"Mode: {mode}, Token: {token}, Challenge: {challenge}")
    logger.info(f"Expected token: {VERIFY_TOKEN}")
    
    if not mode or not token or not challenge:
        logger.error("Missing required parameters")
        raise HTTPException(status_code=400, detail="Missing required parameters")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info(f"Webhook verified successfully with challenge: {challenge}")
        return challenge
    else:
        logger.error(f"Verification failed. Mode: {mode}, Token received: {token}, Expected: {VERIFY_TOKEN}")
        raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handler para mensagens do WhatsApp"""
    try:
        body = await request.json()
        logger.info(f"Received webhook payload: {body}")
        
        # Processar mensagens recebidas
        if "messages" in body.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}):
            await process_whatsapp_message(body)
        
        return {"status": "success"}
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_whatsapp_message(webhook_data):
    """Processar mensagem recebida do WhatsApp"""
    try:
        entry = webhook_data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        
        if "messages" not in value:
            return
        
        message = value["messages"][0]
        from_number = message["from"]
        message_text = message.get("text", {}).get("body", "")
        
        logger.info(f"Message from {from_number}: {message_text}")
        
        # Salvar mensagem no banco
        await db_service.save_message(from_number, message_text, "received")
        
        # Gerar resposta com AI
        ai_response = await ai_service.generate_response(message_text, from_number)
        
        # Enviar resposta via WhatsApp
        await whatsapp_service.send_message(from_number, ai_response)
        
        # Salvar resposta no banco
        await db_service.save_message(from_number, ai_response, "sent")
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
