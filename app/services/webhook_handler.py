# handler para orquestrar mark_read -> typing -> AI -> send_message
import asyncio
import logging
import inspect
from typing import Callable, Awaitable, Dict, Any

logger = logging.getLogger(__name__)

async def handle_webhook_message(webhook_data: Dict[str, Any], whatsapp_service, ai_func: Callable[[str], Awaitable[str]]):
    """
    webhook_data: payload recebido da Meta
    whatsapp_service: instância de WhatsAppService
    ai_func: função/coroutine que recebe texto e retorna string de resposta
    """
    try:
        entry = webhook_data["entry"][0]
        message_data = entry["changes"][0]["value"]["messages"][0]
        user_wa_id = message_data["from"]
        message_id = message_data.get("id")
        message_text = message_data.get("text", {}).get("body", "")

        # dispara mark read + typing em paralelo (não aguarda AI)
        tasks = []
        if message_id:
            tasks.append(whatsapp_service.mark_message_as_read(message_id))
        # attempt typing indicator (may return False if API doesn't support it)
        if hasattr(whatsapp_service, "send_typing_indicator"):
            tasks.append(whatsapp_service.send_typing_indicator(user_wa_id))
        # fire-and-forget but await to ensure API called quickly
        await asyncio.gather(*tasks, return_exceptions=True)

        # obter resposta da IA — detecta assinatura (1 ou 2 params) e chama apropriadamente
        sig = inspect.signature(ai_func)
        param_count = len(sig.parameters)
        ai_response = None

        if param_count == 1:
            if asyncio.iscoroutinefunction(ai_func):
                ai_response = await ai_func(message_text)
            else:
                ai_response = await asyncio.to_thread(ai_func, message_text)
        elif param_count == 2:
            # chama com (message, user_phone)
            if asyncio.iscoroutinefunction(ai_func):
                ai_response = await ai_func(message_text, user_wa_id)
            else:
                ai_response = await asyncio.to_thread(ai_func, message_text, user_wa_id)
        else:
            # fallback: tente chamar com message_text e logue
            logger.warning("ai_func has unexpected signature (%d params). Calling with only message_text.", param_count)
            if asyncio.iscoroutinefunction(ai_func):
                ai_response = await ai_func(message_text)
            else:
                ai_response = await asyncio.to_thread(ai_func, message_text)

        # opcional: atraso natural para simular digitação
        await asyncio.sleep(2.5)

        # enviar resposta final
        sent_ok = await whatsapp_service.send_message(user_wa_id, ai_response or "")
        if not sent_ok:
            logger.error("Failed to send AI response to %s", user_wa_id)

    except (KeyError, IndexError) as e:
        logger.warning("Webhook payload inválido ou sem texto: %s", e)
    except Exception as e:
        logger.exception("Erro processando webhook: %s", e)

# exemplo de uso (no endpoint de webhook chame):
# await handle_webhook_message(payload, whatsapp_service_instance, your_ai_function)