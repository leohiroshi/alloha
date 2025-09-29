import aiohttp
import logging
import json
import base64
from typing import Optional, Dict, Any
import asyncio

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
        # endpoint único para envio/atualização de mensagens
        self.messages_url = f"{self.base_url}/messages"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def send_message(self, to: str, message: str) -> bool:
        """Enviar mensagem de texto via WhatsApp"""
        # não tentar enviar mensagens vazias
        if not message or not message.strip():
            logger.warning("send_message called with empty message; aborting send.")
            return False

        try:
            url = self.messages_url
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {
                    "body": message
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, json=payload) as response:
                    resp_text = await response.text()
                    if 200 <= response.status < 300:
                        logger.info(f"Message sent successfully to %s (status=%s)", to, response.status)
                        return True
                    logger.error("Failed to send message: %s - %s", response.status, resp_text[:1000])
                    return False
                         
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return False
    
    async def download_media(self, media_id: str) -> Optional[bytes]:
        """Download de mídia (imagem) do WhatsApp"""
        try:
            # Primeiro, obter URL da mídia
            media_url_endpoint = f"https://graph.facebook.com/v18.0/{media_id}"
            
            async with aiohttp.ClientSession() as session:
                # Obter URL da mídia
                async with session.get(media_url_endpoint, headers={"Authorization": f"Bearer {self.access_token}"}) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get media URL: {response.status}")
                        return None
                    
                    media_data = await response.json()
                    media_url = media_data.get("url")
                    
                    if not media_url:
                        logger.error("No media URL found")
                        return None
                
                # Download da mídia
                async with session.get(media_url, headers={"Authorization": f"Bearer {self.access_token}"}) as response:
                    if response.status == 200:
                        media_content = await response.read()
                        logger.info(f"Media downloaded successfully: {len(media_content)} bytes")
                        return media_content
                    else:
                        logger.error(f"Failed to download media: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error downloading media: {str(e)}")
            return None
    
    def extract_media_info(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extrai informações de mídia do webhook"""
        try:
            entry = webhook_data.get("entry", [])[0]
            changes = entry.get("changes", [])[0]
            value = changes.get("value", {})
            
            if "messages" not in value:
                return None
            
            message = value["messages"][0]
            
            # Verificar se é imagem
            if message.get("type") == "image":
                image_info = message.get("image", {})
                return {
                    "media_id": image_info.get("id"),
                    "mime_type": image_info.get("mime_type", "image/jpeg"),
                    "caption": image_info.get("caption", ""),
                    "message_type": "image"
                }
            
            # Verificar se é documento (pode ser imagem)
            elif message.get("type") == "document":
                doc_info = message.get("document", {})
                mime_type = doc_info.get("mime_type", "")
                
                if mime_type.startswith("image/"):
                    return {
                        "media_id": doc_info.get("id"),
                        "mime_type": mime_type,
                        "caption": doc_info.get("caption", ""),
                        "filename": doc_info.get("filename", ""),
                        "message_type": "document_image"
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting media info: {str(e)}")
            return None
    
    async def send_template_message(self, to: str, template_name: str, language_code: str = "pt_BR") -> bool:
        """Enviar mensagem template via WhatsApp"""
        try:
            url = self.messages_url
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": language_code
                    }
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, json=payload) as response:
                    resp_text = await response.text()
                    if 200 <= response.status < 300:
                        logger.info("Template message sent successfully to %s (status=%s)", to, response.status)
                        return True
                    logger.error("Failed to send template: %s - %s", response.status, resp_text[:1000])
                    return False
                         
        except Exception as e:
            logger.error(f"Error sending WhatsApp template: {str(e)}")
            return False
    
    async def mark_message_as_read(self, message_id: str) -> bool:
        """Marcar uma mensagem como lida (status read)."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
            "typing_indicator": {
                "type": "text"
            }
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.messages_url, headers=self.headers, json=payload, timeout=10) as response:
                    resp_text = await response.text()
                    if 200 <= response.status < 300:
                        logger.info("Message %s marked as read.", message_id)
                        return True
                    logger.error("Failed to mark as read: %s - %s", response.status, resp_text[:1000])
                    return False
        except Exception as e:
            logger.exception("Error marking message as read: %s", e)
            return False

    async def send_interactive_cta_url(
        self,
        to: str,
        image_url: Optional[str],
        body_text: str,
        button_text: str,
        url: str,
        footer_text: Optional[str] = None
    ) -> bool:
        """
        Envia uma Interactive Call-to-Action URL Button Message (tipo cta_url).
        Exemplo de uso: await whatsapp_service.send_interactive_cta_url(from_number, image_url, body, "Ver imóvel", link)
        """
        try:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "cta_url",
                    "body": {"text": body_text},
                    "action": {
                        "name": "cta_url",
                        "parameters": {
                            "display_text": button_text,
                            "url": url
                        }
                    }
                }
            }

            # optional header image
            if image_url:
                payload["interactive"]["header"] = {
                    "type": "image",
                    "image": {"link": image_url}
                }

            # optional footer
            if footer_text:
                payload["interactive"]["footer"] = {"text": footer_text}

            async with aiohttp.ClientSession() as session:
                async with session.post(self.messages_url, headers=self.headers, json=payload) as response:
                    resp_text = await response.text()
                    if 200 <= response.status < 300:
                        logger.info("Interactive CTA sent successfully to %s (status=%s)", to, response.status)
                        return True
                    logger.error("Failed to send interactive CTA: %s - %s", response.status, resp_text[:1000])
                    return False

        except Exception as e:
            logger.exception("Error sending interactive CTA: %s", e)
            return False

    def is_configured(self) -> bool:
        """Verificar se o serviço está configurado"""
        return bool(self.access_token and self.phone_number_id)
