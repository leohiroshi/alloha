# Integração do PropertyImageAnalyzer com main.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from datetime import datetime
from typing import Dict
from app.services.whatsapp_service import WhatsAppService
from app.services.intelligent_bot import intelligent_bot
from app.services.ai_service import ai_service
from app.services.property_intelligence import property_intelligence
from app.services.firebase_service import firebase_service
from app.services.property_scraper import monitor_scraper

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar instância do FastAPI
app = FastAPI(
    title="Allega Imóveis WhatsApp Bot",
    description="AI-powered real estate WhatsApp bot with intelligent property search and image analysis",
    version="2.1.0"
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
    
@app.get("/")
async def root():
    return {
        "message": "Allega Imóveis WhatsApp Bot is running!",
        "service": "allega-intelligent-bot",
        "version": "2.1.0",
        "features": [
            "Intelligent property search",
            "Market insights", 
            "AI-powered conversations",
            "Firebase integration",
            "Real estate data scraping",
            "Image analysis with LLaMA 3.2 Vision",
            "Property availability verification"
        ],
        "endpoints": ["/webhook", "/health", "/docs", "/update-properties"],
        "status": "active"
    }

@app.get("/health")
async def health():
    """Check system health status"""
    try:
        # Verificar conectividade do Firebase
        firebase_status = "unknown"
        try:
            await firebase_service.check_connection()
            firebase_status = "connected"
        except:
            firebase_status = "disconnected"
        
        # Verificar dados de propriedades
        property_data_loaded = bool(property_intelligence.property_cache)
        
        return {
            "status": "healthy", 
            "service": "allega-intelligent-bot",
            "version": "2.1.0",
            "verify_token_configured": bool(VERIFY_TOKEN),
            "access_token_configured": bool(ACCESS_TOKEN),
            "phone_number_configured": bool(PHONE_NUMBER_ID),
            "firebase_status": firebase_status,
            "property_data_loaded": property_data_loaded,
            "ai_service_available": bool(ai_service.groq_api_key),
            "features": {
                "property_search": True,
                "market_insights": True,
                "conversation_memory": True,
                "firebase_integration": True,
                "image_analysis": True,
                "availability_check": True
            }
        }
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return {
            "status": "degraded",
            "error": str(e),
            "service": "allega-intelligent-bot"
        }

@app.get("/whatsapp/token-status")
async def check_whatsapp_token_status():
    """Verificar o status do token do WhatsApp"""
    try:
        import aiohttp
        
        if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
            return {
                "status": "error",
                "message": "Token ou Phone Number ID não configurados",
                "access_token_configured": bool(ACCESS_TOKEN),
                "phone_number_id_configured": bool(PHONE_NUMBER_ID)
            }
        
        # Testar token fazendo uma requisição para o WhatsApp API
        url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                status_code = response.status
                response_text = await response.text()
                
                if status_code == 200:
                    import json
                    data = json.loads(response_text)
                    return {
                        "status": "valid",
                        "message": "Token do WhatsApp está válido e ativo",
                        "phone_number_info": {
                            "id": data.get("id"),
                            "display_phone_number": data.get("display_phone_number"),
                            "verified_name": data.get("verified_name")
                        },
                        "token_masked": f"{ACCESS_TOKEN[:10]}...{ACCESS_TOKEN[-10:]}"
                    }
                elif status_code == 401:
                    return {
                        "status": "expired",
                        "message": "Token do WhatsApp expirado ou inválido",
                        "error_details": response_text,
                        "action_required": "Renovar token no Facebook Developers"
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Erro ao validar token: {status_code}",
                        "error_details": response_text
                    }
    
    except Exception as e:
        logger.error(f"Error checking WhatsApp token: {str(e)}")
        return {
            "status": "error",
            "message": f"Erro interno ao verificar token: {str(e)}"
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
    """Processar mensagem recebida do WhatsApp com inteligência avançada e suporte a imagens"""
    try:
        entry = webhook_data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        
        if "messages" not in value:
            return
        
        message = value["messages"][0]
        from_number = message["from"]
        message_type = message.get("type", "text")
        
        logger.info(f"📨 Message from {from_number} - Type: {message_type}")
        
        # Verificar se é imagem
        if message_type == "image" or (message_type == "document" and message.get("document", {}).get("mime_type", "").startswith("image/")):
            await process_image_message(message, from_number, webhook_data)
            return
        
        # Processar mensagem de texto
        message_text = message.get("text", {}).get("body", "")
        
        # Processar com sistema inteligente
        ai_response = await intelligent_bot.process_message(message_text, from_number)
        
        logger.info(f"🤖 AI Response: {ai_response[:100]}...")
        
        # Enviar resposta via WhatsApp
        success = await whatsapp_service.send_message(from_number, ai_response)
        
        if success:
            logger.info(f"✅ Message sent successfully to {from_number}")
        else:
            logger.error(f"❌ Failed to send message to {from_number}")
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        
        # Enviar resposta de fallback em caso de erro
        try:
            fallback_msg = (
                "😅 Ops! Tive um probleminha técnico.\n\n"
                "📞 Entre em contato direto:\n"
                "• Vendas: (41) 99214-6670\n"
                "• Locação: (41) 99223-0874"
            )
            await whatsapp_service.send_message(from_number, fallback_msg)
        except:
            pass

async def process_image_message(message: Dict, from_number: str, webhook_data: Dict):
    """Processa mensagens com imagens"""
    try:
        logger.info(f"📸 Processing image from {from_number}")
        
        # Extrair informações da mídia
        media_info = whatsapp_service.extract_media_info(webhook_data)
        
        if not media_info:
            logger.error("Failed to extract media info")
            await send_image_error_response(from_number)
            return
        
        media_id = media_info.get("media_id")
        caption = media_info.get("caption", "")
        
        if not media_id:
            logger.error("No media ID found")
            await send_image_error_response(from_number)
            return
        
        # Download da imagem
        image_data = await whatsapp_service.download_media(media_id)
        
        if not image_data:
            logger.error("Failed to download image")
            await send_image_error_response(from_number)
            return
        
        logger.info(f"📸 Image downloaded: {len(image_data)} bytes")
        
        # NOVA INTEGRAÇÃO: Usar PropertyChatbot para análise de imagens
        try:
            # Usar o chatbot integrado com PropertyImageAnalyzer
            response = await intelligent_bot.process_image_message(
                image_data=image_data,
                caption=caption,
                user_phone=from_number
            )
            
            logger.info(f"✅ PropertyChatbot analysis completed for {from_number}")
            
        except Exception as analyzer_error:
            logger.error(f"PropertyChatbot error: {str(analyzer_error)}")
            
            # Fallback para o sistema original
            if caption and any(word in caption.lower() for word in ['disponível', 'disponivel', 'status', 'verificar']):
                response = await intelligent_bot.check_property_availability_from_image(image_data, from_number)
            else:
                response = await intelligent_bot.process_image_message(image_data, caption, from_number)
        
        # Enviar resposta
        success = await whatsapp_service.send_message(from_number, response)
        
        if success:
            logger.info(f"✅ Image analysis response sent to {from_number}")
        else:
            logger.error(f"❌ Failed to send image response to {from_number}")
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        await send_image_error_response(from_number)

async def send_image_error_response(from_number: str):
    """Envia resposta de erro para problemas com imagem"""
    try:
        error_response = (
            "📸 Recebi sua imagem!\n\n"
            "😅 Tive dificuldade para processá-la no momento.\n\n"
            "🏠 *Posso ajudar de outras formas:*\n"
            "• Descreva o imóvel que procura\n"
            "• Informe sua região preferida\n"
            "• Conte sobre seu orçamento\n\n"
            "📞 *Ou entre em contato direto:*\n"
            "🏠 Vendas: (41) 99214-6670\n"
            "🏡 Locação: (41) 99223-0874"
        )
        
        await whatsapp_service.send_message(from_number, error_response)
        
    except Exception as e:
        logger.error(f"Error sending image error response: {str(e)}")

@app.get("/analytics/{user_phone}")
async def get_user_analytics(user_phone: str):
    """Obter analytics de um usuário específico"""
    try:
        # Obter dados do Firebase
        user_profile = await intelligent_bot.firebase_service.get_user_profile(user_phone)
        user_stats = await intelligent_bot.firebase_service.get_user_stats(user_phone)
        
        return {
            "user_phone": user_phone,
            "profile": user_profile,
            "stats": user_stats,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test-ai")
async def test_ai_response(request: Request):
    """Endpoint para testar respostas da IA"""
    try:
        body = await request.json()
        message = body.get("message", "")
        user_phone = body.get("user_phone", "test_user")
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Testar com sistema inteligente
        response = await intelligent_bot.process_message(message, user_phone)
        
        return {
            "input_message": message,
            "ai_response": response,
            "user_phone": user_phone,
            "system": "intelligent_bot",
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error testing AI: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test-image-analysis")
async def test_image_analysis(request: Request):
    """Endpoint para testar análise de imagens"""
    try:
        body = await request.json()
        image_url = body.get("image_url", "")
        user_phone = body.get("user_phone", "test_user")
        analysis_type = body.get("analysis_type", "complete")  # complete ou availability
        caption = body.get("caption", "") 
        if not image_url:
            raise HTTPException(status_code=400, detail="Image URL is required")
        
        # Download da imagem de teste
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status == 200:
                    image_data = await resp.read()
                else:
                    raise HTTPException(status_code=400, detail="Failed to download image")
        
        # NOVA INTEGRAÇÃO: Testar com PropertyChatbot
        try:
            # Determinar mensagem baseada no tipo de análise
            test_message = "verificar disponibilidade" if analysis_type == "availability" else "analisar imóvel completo"
            
            # Usar PropertyChatbot para análise
            response = await intelligent_bot.process_image_message(
                image_data=image_data,
                caption=caption,
                user_phone=user_phone
            )
            
        except Exception as analyzer_error:
            logger.error(f"PropertyChatbot test error: {str(analyzer_error)}")
            
            # Fallback para sistema original
            if analysis_type == "availability":
                response = await intelligent_bot.check_property_availability_from_image(image_data, user_phone)
            else:
                response = await intelligent_bot.process_image_message(image_data, "", user_phone)
        
        return {
            "image_url": image_url,
            "analysis_type": analysis_type,
            "ai_response": response,
            "user_phone": user_phone,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error testing image analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update-properties")
async def update_property_database():
    """Atualizar base de dados de imóveis"""
    try:
        logger.info("🔄 Iniciando atualização manual da base de imóveis...")
        
        success = await intelligent_bot.update_property_database()
        
        if success:
            return {
                "status": "success",
                "message": "Base de dados de imóveis atualizada com sucesso",
                "timestamp": str(datetime.now())
            }
        else:
            return {
                "status": "error", 
                "message": "Falha na atualização da base de dados",
                "timestamp": str(datetime.now())
            }
            
    except Exception as e:
        logger.error(f"Error updating properties: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/properties/stats")
async def get_property_statistics():
    """Obter estatísticas dos imóveis"""
    try:
        # Carregar dados de propriedades
        await intelligent_bot.property_intelligence.load_property_data()
        
        stats = {}
        if intelligent_bot.property_intelligence.property_cache:
            cache = intelligent_bot.property_intelligence.property_cache
            stats = cache.get('statistics', {})
        
        return {
            "statistics": stats,
            "cache_status": "loaded" if intelligent_bot.property_intelligence.property_cache else "empty",
            "last_update": intelligent_bot.property_intelligence.last_cache_update,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting property stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/status")
async def get_system_status():
    """Status detalhado do sistema"""
    try:
        status_info = await intelligent_bot._get_system_status()
        
        return {
            "detailed_status": status_info,
            "components": {
                "whatsapp_service": bool(ACCESS_TOKEN and PHONE_NUMBER_ID),
                "firebase_service": bool(intelligent_bot.firebase_service),
                "ai_service": bool(intelligent_bot.ai_service.api_key),
                "property_intelligence": bool(intelligent_bot.property_intelligence),
                "intelligent_bot": True,  # PropertyChatbot integrado
                "image_analyzer": True,  # Componente original
            },
            "environment": {
                "verify_token_set": bool(VERIFY_TOKEN),
                "access_token_set": bool(ACCESS_TOKEN),
                "phone_number_set": bool(PHONE_NUMBER_ID)
            },
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-property-scraper")
async def run_property_scraper():
    """
    Executa o monitor do scraper manualmente (uma vez).
    """
    try:
        # Executa uma rodada do monitor (não entra em loop)
        await monitor_scraper(interval_minutes=0.01, max_properties=100)
        return {
            "status": "success",
            "message": "Scraper executado manualmente.",
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        logger.error(f"Erro ao executar o scraper manualmente: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)