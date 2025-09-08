import aiohttp
import logging
import json
from typing import Optional

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.base_url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    async def send_message(self, to: str, message: str) -> bool:
        """Enviar mensagem de texto via WhatsApp"""
        try:
            url = f"{self.base_url}/messages"
            
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
                    if response.status == 200:
                        logger.info(f"Message sent successfully to {to}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to send message: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return False
    
    async def send_template_message(self, to: str, template_name: str, language_code: str = "pt_BR") -> bool:
        """Enviar mensagem template via WhatsApp"""
        try:
            url = f"{self.base_url}/messages"
            
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
                    if response.status == 200:
                        logger.info(f"Template message sent successfully to {to}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to send template: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error sending WhatsApp template: {str(e)}")
            return False
    
    def is_configured(self) -> bool:
        """Verificar se o serviço está configurado"""
        return bool(self.access_token and self.phone_number_id)
