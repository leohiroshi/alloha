# Sistema Inteligente de Imóveis - Allega Imóveis

from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict
from app.services.whatsapp_service import WhatsAppService
from app.services.intelligent_bot import intelligent_bot
from app.services.property_intelligence import property_intelligence
from app.services.property_scraper import monitor_scraper
from app.services.rag_pipeline import rag
from app.services.dataset_living_loop import dataset_living_loop
from app.services.dual_stack_intelligence import dual_stack_intelligence
from app.services.urgency_score_system import urgency_score_system
from app.services.autonomous_followup import autonomous_followup
from app.services.voice_ptt_system import voice_ptt_system
from app.services.live_pricing_system import live_pricing_system
from app.services.white_label_system import white_label_system
from app.services.supabase_client import supabase_client
from app.services.webhook_idempotency import webhook_idempotency
import asyncio

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

@app.on_event("startup")
async def startup_event():
    """Eventos de inicialização da aplicação"""
    logger.info("🚀 Iniciando SISTEMA DUAL-STACK + DIFERENCIAIS...")
    
    # Iniciar loops de background
    try:
        # Dataset living loop
        asyncio.create_task(dataset_living_loop.start_continuous_loop())
        logger.info("✅ Dataset living loop iniciado")
        
        # Sistema de preços ao vivo (sync a cada 30min)
        asyncio.create_task(live_pricing_system.start_live_sync_loop())
        logger.info("✅ Live pricing system iniciado")
        
        # Limpeza de cache de voz a cada hora
        async def cleanup_voice_cache():
            while True:
                await asyncio.sleep(3600)  # 1 hora
                await voice_ptt_system.cleanup_old_cache()
        
        asyncio.create_task(cleanup_voice_cache())
        
        # Inicializar Google Calendar (v1 desativado por padrão)
        if os.getenv('ENABLE_GOOGLE_CALENDAR', 'false').lower() in ('1','true','yes','on'):
            calendar_initialized = await autonomous_followup.initialize_calendar_service()
            if calendar_initialized:
                logger.info("✅ Google Calendar inicializado para agendamentos autônomos")
            else:
                logger.warning("⚠️ Google Calendar não configurado ou indisponível - fallback ativo")
        else:
            logger.info("ℹ️ Google Calendar desativado (ENABLE_GOOGLE_CALENDAR=false) - usando fallback de agendamento")
        
        # Monitor de scraping sempre ativo
        asyncio.create_task(monitor_scraper())
        logger.info("✅ Property monitor iniciado")

        # Iniciar idempotency cleanup task de forma segura
        webhook_idempotency.start()

    except Exception as e:
        logger.error(f"❌ Erro na inicialização: {e}")
    
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
            "Supabase integration",
            "Real estate data scraping",
            "Image analysis with GPT-5 mini",
            "Property availability verification"
        ],
        "endpoints": ["/webhook", "/health", "/docs", "/update-properties"],
        "status": "active"
    }

@app.get("/health")
async def health():
    """Check system health status"""
    try:
        
        # Verificar dados de propriedades
        property_data_loaded = bool(property_intelligence.property_cache)
        
        return {
            "status": "healthy", 
            "service": "allega-intelligent-bot",
            "version": "2.1.0",
            "verify_token_configured": bool(VERIFY_TOKEN),
            "access_token_configured": bool(ACCESS_TOKEN),
            "phone_number_configured": bool(PHONE_NUMBER_ID),
            "property_data_loaded": property_data_loaded,
            "features": {
                "property_search": True,
                "market_insights": True,
                "conversation_memory": True,
                "supabase_integration": True,
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
    """Handler idempotente para mensagens do WhatsApp"""
    try:
        body = await request.json()
        
        # Importar serviço de idempotência
        from app.services.webhook_idempotency import webhook_idempotency
        
        # 1) RESPONDER 200 IMEDIATAMENTE (como requerido pela Meta)
        response_data = {"status": "success"}
        
        # 2) Verificar duplicação
        if await webhook_idempotency.is_duplicate(body):
            logger.info("Webhook duplicado ignorado")
            return response_data
        
        # 3) Marcar como processando
        fingerprint = await webhook_idempotency.mark_as_processing(body)
        if not fingerprint:
            logger.info("Webhook já sendo processado por outra thread")
            return response_data
        
        # 4) Processar em background (não bloqueia resposta 200)
        if "messages" in body.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}):
            asyncio.create_task(process_whatsapp_message_safe(body, fingerprint))
        else:
            await webhook_idempotency.mark_as_completed(fingerprint, {"skipped": "no_messages"})
        
        return response_data
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        # Ainda responde 200 para não quebrar com a Meta
        return {"status": "error", "message": str(e)}

async def process_whatsapp_message_safe(webhook_data, fingerprint: str):
    """Wrapper seguro que marca conclusão/falha"""
    try:
        from app.services.webhook_idempotency import webhook_idempotency
        
        await process_whatsapp_message(webhook_data)
        await webhook_idempotency.mark_as_completed(fingerprint)
        
    except Exception as e:
        from app.services.webhook_idempotency import webhook_idempotency
        logger.error(f"Erro no processamento seguro: {e}")
        await webhook_idempotency.mark_as_failed(fingerprint, str(e))

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
        message_id = message.get("id")
        message_type = message.get("type", "text")
        
        logger.info(f"📨 Message from {from_number} - Type: {message_type}")
        
        # Marcar como lida (check azul) — não é obrigatório, apenas tenta e loga falhas
        if message_id and getattr(whatsapp_service, "is_configured", None):
            try:
                await whatsapp_service.mark_message_as_read(message_id)
                logger.info("Marked incoming message as read: %s", message_id)
            except Exception as e:
                logger.debug("Failed to mark message as read: %s", e)
        
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
        
        # Análise de imagem usando Sofia Vision
        try:
            response = await intelligent_bot.process_image_message(
                image_data=image_data,
                caption=caption,
                user_phone=from_number
            )
            
            logger.info(f"✅ Image analysis completed for {from_number}")
            
        except Exception as analyzer_error:
            logger.error(f"Image analysis error: {str(analyzer_error)}")
            
            # Fallback para resposta de erro
            response = (
                "📸 Recebi sua imagem!\n\n"
                "😅 Tive dificuldade técnica para analisá-la no momento.\n\n"
                "🏠 *Mas posso ajudar de outras formas:*\n"
                "• Descreva o imóvel que procura\n"
                "• Informe sua localização preferida\n"
                "• Conte sobre seu orçamento\n\n"
                "📞 *Ou entre em contato direto:*\n"
                "🏠 Vendas: (41) 99214-6670\n"
                "🏡 Locação: (41) 99223-0874"
            )
        
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
        # Obter dados do Supabase
        user_profile = await asyncio.to_thread(supabase_client.get_user_profile, user_phone)
        user_stats = await asyncio.to_thread(supabase_client.get_user_stats, user_phone)
        
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
        
        # Testar análise de imagem com Sofia Vision
        try:
            response = await intelligent_bot.process_image_message(
                image_data=image_data,
                caption=caption or "",
                user_phone=user_phone
            )
            
        except Exception as analyzer_error:
            logger.error(f"Image analysis test error: {str(analyzer_error)}")
            
            # Fallback para erro de teste
            response = f"Erro ao analisar imagem de teste: {str(analyzer_error)}"
        
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
    """Status detalhado do sistema com métricas de performance"""
    try:
        # Importar serviços otimizados
        from app.services.embedding_cache import embedding_cache
        from app.services.webhook_idempotency import webhook_idempotency
        from app.models.conversation_state import conversation_manager
        
        status_info = await intelligent_bot._get_system_status()
        
        return {
            "detailed_status": status_info,
            "components": {
                "whatsapp_service": bool(ACCESS_TOKEN and PHONE_NUMBER_ID),
                "supabase_client": True,
                "property_intelligence": bool(intelligent_bot.property_intelligence),
                "intelligent_bot": True,
                "sofia_vision": True,  # Análise de imagens integrada
                "embedding_cache": True,
                "conversation_manager": True,
                "webhook_idempotency": True
            },
            "performance_metrics": {
                "embedding_cache": embedding_cache.get_stats(),
                "webhook_idempotency": webhook_idempotency.get_stats(),
                "active_conversations": len(conversation_manager.get_active_conversations())
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

@app.get("/dataset/status")
async def get_dataset_status():
    """Status do sistema de dataset living"""
    try:
        from app.services.dataset_living_loop import dataset_living_loop
        
        status = dataset_living_loop.get_status()
        
        # Adicionar estatísticas dos arquivos
        datasets_dir = Path("datasets")
        dataset_files = []
        
        if datasets_dir.exists():
            for file_path in datasets_dir.rglob("*.jsonl"):
                if "train" in file_path.name:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            line_count = sum(1 for _ in f)
                        
                        dataset_files.append({
                            "filename": file_path.name,
                            "path": str(file_path),
                            "examples": line_count,
                            "size_mb": file_path.stat().st_size / (1024 * 1024),
                            "created": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                        })
                    except Exception:
                        pass
        
        return {
            "living_loop": status,
            "available_datasets": sorted(dataset_files, key=lambda x: x["created"], reverse=True),
            "total_datasets": len(dataset_files),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting dataset status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dataset/expand")
async def expand_dataset_now():
    """Força expansão imediata do dataset"""
    try:
        from app.services.dataset_expander import dataset_expander
        
        # Buscar conversas dos últimos 7 dias
        since = datetime.utcnow() - timedelta(days=7)
        examples = await dataset_expander.expand_from_supabase(limit=100)
        
        if not examples:
            return {
                "status": "no_data",
                "message": "Nenhuma conversa encontrada para expansão"
            }
        
        # Aplicar data augmentation
        augmented = await dataset_expander.data_augment_examples(examples, target_multiplier=3)
        
        # Salvar dataset
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        train_path = dataset_expander.save_expanded_dataset(augmented, f"manual_{timestamp}")
        
        return {
            "status": "success",
            "original_examples": len(examples),
            "augmented_examples": len(augmented),
            "train_file": train_path,
            "message": f"Dataset expandido com {len(augmented)} exemplos"
        }
        
    except Exception as e:
        logger.error(f"Error expanding dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================
# ENDPOINTS SISTEMA DUAL-STACK + DIFERENCIAIS  
# ==============================================

@app.post("/api/dual-stack/query")
async def dual_stack_query(request: Request):
    """API para consultas com sistema dual-stack"""
    try:
        data = await request.json()
        
        user_message = data.get("message", "")
        user_phone = data.get("phone", "")
        conversation_history = data.get("history", [])
        
        if not user_message or not user_phone:
            raise HTTPException(status_code=400, detail="Mensagem e telefone são obrigatórios")
        
        # Processar com dual-stack
        result = await dual_stack_intelligence.process_dual_stack_query(
            user_message=user_message,
            user_phone=user_phone,
            conversation_history=conversation_history
        )
        
        # Analisar urgência
        urgency_alert = await urgency_score_system.analyze_urgency(
            message=user_message,
            phone=user_phone,
            conversation_history=conversation_history
        )
        
        # Se urgência alta, tentar agendamento autônomo
        if urgency_alert.urgency_score >= 4:
            client_name = data.get("client_name", "Cliente")
            
            scheduling_result = await autonomous_followup.schedule_autonomous_visit(
                phone=user_phone,
                client_name=client_name,
                urgency_score=urgency_alert.urgency_score,
                property_interests=result.get("properties", [])
            )
            
            result["autonomous_scheduling"] = scheduling_result
        
        result["urgency_analysis"] = {
            "score": urgency_alert.urgency_score,
            "reasons": urgency_alert.urgency_reasons,
            "suggested_actions": urgency_alert.suggested_actions
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Erro na consulta dual-stack: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/fresh-properties")
async def get_fresh_properties(
    query: str = "",
    neighborhood: str = None,
    min_price: float = None,
    max_price: float = None,
    bedrooms: int = None,
    limit: int = 10
):
    """API para buscar apenas propriedades frescas (< 6h)"""
    try:
        filters = {}
        
        if neighborhood:
            filters["neighborhood"] = neighborhood
        if min_price:
            filters["price"] = {"$gte": min_price}
        if max_price:
            if "price" in filters:
                filters["price"]["$lte"] = max_price
            else:
                filters["price"] = {"$lte": max_price}
        if bedrooms:
            filters["bedrooms"] = bedrooms
        
        # Buscar apenas propriedades frescas
        results = await live_pricing_system.get_fresh_properties_only(
            query=query,
            filters=filters,
            limit=limit
        )
        
        return {
            "success": True,
            "count": len(results),
            "properties": results,
            "freshness_hours": live_pricing_system.freshness_hours,
            "last_sync": live_pricing_system.sync_stats.get("last_sync_time")
        }
        
    except Exception as e:
        logger.error(f"Erro na busca de propriedades frescas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/urgency/alerts")
async def get_urgency_alerts(limit: int = 50):
    """API para dashboard de alerts de urgência"""
    try:
        alerts = await urgency_score_system.get_pending_alerts(limit)
        
        return {
            "success": True,
            "count": len(alerts),
            "alerts": alerts,
            "stats": urgency_score_system.get_urgency_stats()
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar alerts de urgência: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/urgency/mark-contacted/{alert_id}")
async def mark_alert_contacted(alert_id: str, broker_name: str = Body(...)):
    """Marca alert de urgência como contatado"""
    try:
        await urgency_score_system.mark_alert_as_contacted(alert_id, broker_name)
        
        return {
            "success": True,
            "message": f"Alert {alert_id} marcado como contatado por {broker_name}"
        }
        
    except Exception as e:
        logger.error(f"Erro ao marcar alert como contatado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/white-label/create")
async def create_white_label_site(
    company_name: str = Body(...),
    company_email: str = Body(...),
    template_id: str = Body("modern"),
    custom_domain: str = Body(None),
    branding: dict = Body(None)
):
    """Cria site white-label instantâneo"""
    try:
        result = await white_label_system.create_white_label_site(
            company_name=company_name,
            company_email=company_email,
            template_id=template_id,
            custom_domain=custom_domain,
            branding=branding
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Erro ao criar site white-label: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats/dashboard")
async def get_dashboard_stats():
    """Estatísticas completas do dashboard"""
    try:
        stats = {
            "dual_stack": dual_stack_intelligence.get_cache_stats(),
            "urgency_system": urgency_score_system.get_urgency_stats(),
            "voice_ptt": voice_ptt_system.get_voice_stats(),
            "live_pricing": await live_pricing_system.get_pricing_stats(),
            "white_label": white_label_system.get_deployment_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dataset/trigger-update")
async def trigger_dataset_update():
    """Dispara atualização manual do dataset living"""
    try:
        # Executar check manual (sem esperar intervalo)
        await dataset_living_loop.check_and_update_dataset()
        
        return {
            "status": "success",
            "message": "Atualização do dataset disparada manualmente",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering dataset update: {str(e)}")
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

@app.post("/query")
async def query_endpoint(payload: dict = Body(...)):
    """
    Recebe JSON com:
    {
        "question": "texto da pergunta",
        "filters": {"neighborhood": "Água Verde"}  # opcional
    }
    """
    question = payload.get("question")
    filters = payload.get("filters", {})

    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    # 1) Recuperar documentos relevantes
    retrieved = rag.retrieve(question, top_k=5, filters=filters)

    # 2) Montar prompt para o OpenAI
    prompt = rag.build_prompt(question, retrieved)

    # 3) Chamar OpenAI via função compat (bloqueante) em thread
    try:
        response = await asyncio.to_thread(rag.call_gpt, prompt)
    except Exception as e:
        logger.error(f"Error calling OpenAI: {str(e)}")
        raise HTTPException(status_code=500, detail="Error generating response")

    # 4) Preparar dados para retorno (incluindo URLs e imagens)
    candidates = []
    for r in retrieved:
        m = r.get("meta", r.get("metadata", {}))
        candidates.append({
            "id": r.get("id"),
            "preview": r.get("text", "")[:200],
            "url": m.get("url"),
            "image": m.get("main_image") or m.get("image"),
            "neighborhood": m.get("neighborhood"),
            "price": m.get("price")
        })

    # 5) Retornar JSON com resposta e candidatos
    return {
        "answer": response,
        "candidates": candidates
    }
