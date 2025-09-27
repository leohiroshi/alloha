import aiohttp
import logging
import json
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
        self.messages_url = f"{self.base_url}/messages"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    async def send_message(self, to: str, message: str) -> bool:
        """Enviar mensagem de texto via WhatsApp Cloud API (garante text.body presente)."""
        if not message:
            logger.warning("send_message called with empty message; aborting send.")
            return False
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": message}
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.messages_url, headers=self.headers, json=payload, timeout=15) as resp:
                    text = await resp.text()
                    if 200 <= resp.status < 300:
                        try:
                            data = await resp.json()
                        except Exception:
                            data = None
                        msg_id = None
                        if isinstance(data, dict):
                            # tentativa de extrair message id retornado pela API
                            msg_id = data.get("messages", [{}])[0].get("id") if data.get("messages") else None
                        logger.info("Message sent to %s status=%s message_id=%s", to, resp.status, msg_id)
                        return True
                    else:
                        logger.error("Failed to send message: %s - %s", resp.status, text[:1000])
                        return False
        except Exception as e:
            logger.exception("Error sending WhatsApp message: %s", e)
            return False

    async def mark_message_as_read(self, message_id: str) -> bool:
        """Marcar uma mensagem como lida (status read)."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.messages_url, headers=self.headers, json=payload, timeout=10) as response:
                    text = await response.text()
                    if 200 <= response.status < 300:
                        logger.info("Message %s marked as read.", message_id)
                        return True
                    else:
                        logger.error("Failed to mark as read: %s - %s", response.status, text[:1000])
                        return False
        except Exception as e:
            logger.exception("Error marking message as read: %s", e)
            return False

    async def send_typing_indicator(self, to: str) -> bool:
        """Tenta enviar 'typing' action; a Cloud API oficial pode não suportar esse tipo."""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "typing",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.messages_url, headers=self.headers, json=payload, timeout=10) as response:
                    text = await response.text()
                    if 200 <= response.status < 300:
                        logger.info("Typing indicator sent to %s.", to)
                        return True
                    else:
                        logger.error("Failed to send typing indicator: %s - %s", response.status, text[:1000])
                        return False
        except Exception as e:
            logger.exception("Error sending typing indicator: %s", e)
            return False

    def is_configured(self) -> bool:
        """Verificar se o serviço está configurado"""
        return bool(self.access_token and self.phone_number_id)
