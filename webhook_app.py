from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
import os
import logging
import httpx
import asyncio

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
        "message": "🏠 Alloha WhatsApp Bot está funcionando!",
        "service": "alloha-bot",
        "version": "1.0.0",
        "endpoints": ["/webhook", "/health", "/docs", "/test"],
        "status": "active",
        "ai_ready": True
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy", 
        "service": "alloha-bot",
        "verify_token_configured": bool(VERIFY_TOKEN),
        "access_token_configured": bool(ACCESS_TOKEN),
        "phone_number_configured": bool(PHONE_NUMBER_ID),
        "webhook_ready": True
    }

@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request):
    """Verificação do webhook do WhatsApp"""
    params = request.query_params
    
    logger.info(f"🔍 Webhook verification request: {dict(params)}")
    
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    logger.info(f"Mode: {mode}, Token recebido: {token}, Challenge: {challenge}")
    logger.info(f"Token esperado: {VERIFY_TOKEN}")
    
    if not mode or not token or not challenge:
        logger.error("❌ Parâmetros obrigatórios ausentes")
        raise HTTPException(status_code=400, detail="Missing required parameters")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info(f"✅ Webhook verificado com sucesso! Challenge: {challenge}")
        return challenge
    else:
        logger.error(f"❌ Falha na verificação. Esperado: {VERIFY_TOKEN}, Recebido: {token}")
        raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handler para mensagens do WhatsApp"""
    try:
        body = await request.json()
        logger.info(f"📩 Webhook recebido: {body}")
        
        # Verificar se há mensagens
        if "entry" in body and len(body["entry"]) > 0:
            entry = body["entry"][0]
            if "changes" in entry and len(entry["changes"]) > 0:
                change = entry["changes"][0]
                if "value" in change and "messages" in change["value"]:
                    await process_whatsapp_message(change["value"])
        
        return {"status": "success", "processed": True}
    
    except Exception as e:
        logger.error(f"❌ Erro processando webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_whatsapp_message(value):
    """Processar mensagem recebida do WhatsApp"""
    try:
        messages = value.get("messages", [])
        if not messages:
            return
        
        message = messages[0]
        from_number = message["from"]
        message_text = message.get("text", {}).get("body", "")
        
        logger.info(f"📱 Mensagem de {from_number}: {message_text}")
        
        # Gerar resposta inteligente
        response = await generate_ai_response(message_text, from_number)
        
        # Enviar resposta
        success = await send_whatsapp_message(from_number, response)
        
        if success:
            logger.info(f"✅ Resposta enviada para {from_number}")
        else:
            logger.error(f"❌ Falha ao enviar resposta para {from_number}")
        
    except Exception as e:
        logger.error(f"❌ Erro processando mensagem: {str(e)}")

async def generate_ai_response(message: str, user_phone: str) -> str:
    """Gerar resposta usando IA (simulado por enquanto)"""
    try:
        # Por enquanto, resposta inteligente simulada
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["oi", "olá", "hello", "hi"]):
            return f"🏠 Olá! Sou o assistente da Alloha, sua imobiliária digital! Como posso ajudá-lo a encontrar o imóvel dos seus sonhos?"
        
        elif any(word in message_lower for word in ["apartamento", "casa", "imóvel", "comprar", "alugar"]):
            return f"🔍 Ótimo! Estou aqui para ajudá-lo a encontrar o imóvel perfeito. Pode me contar mais sobre suas preferências? (bairro, valor, tamanho)"
        
        elif any(word in message_lower for word in ["preço", "valor", "quanto"]):
            return f"💰 Temos imóveis para todos os orçamentos! Pode me informar sua faixa de preço preferida?"
        
        elif any(word in message_lower for word in ["bairro", "região", "localização"]):
            return f"📍 Localização é muito importante! Temos ótimas opções em várias regiões. Qual área prefere?"
        
        elif any(word in message_lower for word in ["financiamento", "banco", "prestação"]):
            return f"🏦 Ajudamos com financiamento também! Temos parcerias com os melhores bancos. Quer saber mais sobre as opções?"
        
        else:
            return f"🤖 Recebi sua mensagem: '{message}'. Sou especialista em imóveis! Como posso ajudá-lo com compra, venda ou aluguel?"
        
    except Exception as e:
        logger.error(f"❌ Erro gerando resposta AI: {str(e)}")
        return "Desculpe, houve um problema. Tente novamente em alguns instantes."

async def send_whatsapp_message(to: str, message: str) -> bool:
    """Enviar mensagem via WhatsApp"""
    try:
        if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
            logger.warning("⚠️ WhatsApp não configurado completamente")
            return False
        
        url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                logger.info(f"✅ Mensagem enviada com sucesso para {to}")
                return True
            else:
                error_text = response.text
                logger.error(f"❌ Falha ao enviar mensagem: {response.status_code} - {error_text}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Erro enviando mensagem WhatsApp: {str(e)}")
        return False

@app.get("/test")
async def test():
    """Endpoint de teste"""
    return {
        "test": "✅ OK",
        "verify_token": VERIFY_TOKEN,
        "access_token_configured": len(ACCESS_TOKEN) > 0,
        "phone_number_id": PHONE_NUMBER_ID,
        "webhook_url": "https://alloha.app/webhook",
        "verify_url": f"https://alloha.app/webhook?hub.mode=subscribe&hub.verify_token={VERIFY_TOKEN}&hub.challenge=test123"
    }

@app.get("/send-test/{phone}")
async def send_test_message(phone: str):
    """Enviar mensagem de teste"""
    test_message = "🏠 Olá! Esta é uma mensagem de teste do bot da Alloha. Sistema funcionando perfeitamente!"
    success = await send_whatsapp_message(phone, test_message)
    return {"sent": success, "phone": phone, "message": test_message}
