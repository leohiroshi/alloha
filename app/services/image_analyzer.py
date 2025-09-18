"""
Chatbot Inteligente para Análise de Imóveis
Integra o PropertyImageAnalyzer com interface de chat usando Gemini Vision
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import os
import aiohttp
import socket
import random
import base64
from dotenv import load_dotenv

import google.generativeai as genai

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PropertyImageAnalyzer:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-2.5-pro-vision")

    async def analyze_property_image(self, image_bytes: bytes, prompt: str = "Analyze this property image") -> dict:
        try:
            logger.info(f"Analisando imagem ({len(image_bytes)} bytes) com Gemini Vision")
            if not self.gemini_api_key:
                return {"success": False, "error": "Gemini API key não configurada"}
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            enhanced_prompt = (
                f"{prompt}\n\n"
                "Analise esta imagem de imóvel e identifique:\n"
                "- Tipo de imóvel (casa, apartamento, terreno)\n"
                "- Características visíveis (quartos, banheiros, garagem)\n"
                "- Estado de conservação\n"
                "- Localização aproximada se possível\n"
                "- Diferenciais e pontos de destaque\n"
                "- Valor estimado se conseguir identificar\n\n"
                "Seja específico e profissional na análise."
            )
            # Gemini Vision API (google.generativeai) suporta imagens:
            response = await asyncio.to_thread(self.model.generate_content, [
                {"text": enhanced_prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}
            ])
            if response and hasattr(response, "text"):
                llm_content = response.text
                extracted_query = self._extract_query_from_llm(llm_content)
                return {
                    "success": True,
                    "response": {
                        "message": {
                            "content": llm_content
                        }
                    }
                }
            else:
                return {"success": False, "error": "Gemini Vision não retornou resposta."}
        except Exception as e:
            logger.error(f"Erro ao analisar imagem com Gemini Vision: {e}")
            return {"success": False, "error": str(e)}

    def _extract_query_from_llm(self, llm_content: str) -> str:
        """
        Extrai uma consulta textual do conteúdo gerado pela IA Vision.
        Exemplo: busca por 'casa 3 quartos Bigorrilho'
        """
        import re
        
        # Busca por padrões mais específicos
        patterns = [
            r'(casa|apartamento|imóvel)[^\n]*?(\d+)\s*quartos?[^\n]*?(bigorrilho|batel|centro|cabral|champagnat|água verde|portão|santa felicidade)',
            r'(casa|apartamento)[^\n]*?(bigorrilho|batel|centro|cabral|champagnat|água verde|portão|santa felicidade)[^\n]*?(\d+)\s*quartos?',
            r'(casa|apartamento|imóvel)[^\n]*?(\d+)\s*quartos?',
            r'(casa|apartamento|imóvel)[^\n]*?(bigorrilho|batel|centro|cabral|champagnat|água verde|portão|santa felicidade)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, llm_content, re.IGNORECASE)
            if match:
                return match.group(0)
        
        # Fallback: extrai palavras-chave relevantes
        keywords = re.findall(r'\b(casa|apartamento|imóvel|\d+\s*quartos?|bigorrilho|batel|centro|cabral|champagnat|água verde|portão|santa felicidade|garagem|suite|banheiro)\b', llm_content, re.IGNORECASE)
        if keywords:
            return ' '.join(keywords[:5])  # Primeiras 5 palavras-chave
        
        # Último fallback: primeira frase
        return llm_content.split('.')[0] if llm_content else ""


    def format_analysis_response(self, analysis_result: Dict, user_message: str) -> str:
        if not analysis_result.get("success", True):
            error_msg = analysis_result.get("error", "Erro desconhecido")
            return (
                f"😅 *Tive dificuldade para analisar esta imagem.*\n\n"
                f"Erro: {error_msg}\n\n"
                f"📞 *Fale direto com nossos especialistas:*\n"
                f"🏠 Vendas: (41) 99214-6670\n"
                f"🏡 Locação: (41) 99223-0874"
            )

        response = "🏠 *Análise do Imóvel Concluída*\n\n"
        llm_response = analysis_result.get("response", {}).get("message", {}).get("content", "")
        response += f"{llm_response}\n\n"
        
        response += "💡 *Análise concluída pela Sofia da Allega Imóveis!*\n"
        response += "📞 *Quer mais informações? Entre em contato:*\n"
        response += "🏠 Vendas: (41) 99214-6670\n"
        response += "🏡 Locação: (41) 99223-0874"
        return response

property_image_analyzer = PropertyImageAnalyzer()

class PropertyChatbot:
    def __init__(self):
        self.analyzer = property_image_analyzer
        self.conversation_history = {}

        self.responses = {
            'greeting': "🏠 *Olá! Sou a Sofia, assistente da Allega Imóveis!*\n\nEnvie uma foto de imóvel para análise ou digite 'ajuda' para ver comandos.\n\n📞 Vendas: (41) 99214-6670\n🏡 Locação: (41) 99223-0874",
            'help': "🤖 *Como usar a Sofia:*\n\n• Envie uma foto do imóvel\n• Eu analiso automaticamente\n• Receba informações detalhadas\n• Encontre imóveis similares\n\n📞 Vendas: (41) 99214-6670\n🏡 Locação: (41) 99223-0874",
            'no_image': "📸 *Preciso de uma imagem para analisar!*\n\nEnvie uma foto do imóvel que você quer analisar.\n\n📞 Vendas: (41) 99214-6670\n🏡 Locação: (41) 99223-0874"
        }

    async def process_message(self, user_id: str, message: str, image_data: bytes = None) -> str:
        try:
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []

            self.conversation_history[user_id].append({
                'timestamp': datetime.now().isoformat(),
                'message': message,
                'has_image': bool(image_data)
            })

            message_lower = message.lower().strip()

            if any(word in message_lower for word in ['oi', 'olá', 'hello', 'início', 'start']):
                return self.responses['greeting']
            elif any(word in message_lower for word in ['ajuda', 'help', 'comandos']):
                return self.responses['help']
            elif image_data:
                return await self._process_image_analysis(user_id, message, image_data)
            elif any(word in message_lower for word in ['analisar', 'análise', 'foto', 'imagem']):
                return self.responses['no_image']
            else:
                return self._default_text_response(message)
        except Exception as e:
            logger.error(f"Erro processando mensagem: {str(e)}")
            return self._get_error_response()

    async def _process_image_analysis(self, user_id: str, message: str, image_data: bytes) -> str:
        try:
            prompt = f"Analyze this property image. User message: {message}"
            analysis_result = await self.analyzer.analyze_property_image(image_data, prompt)
            
            self.conversation_history[user_id].append({
                'timestamp': datetime.now().isoformat(),
                'analysis_result': analysis_result,
            })
            
            return self.analyzer.format_analysis_response(analysis_result, message)
        except Exception as e:
            logger.error(f"Erro na análise de imagem: {str(e)}")
            return self._get_analysis_error_response()

    def _default_text_response(self, message: str) -> str:
        return (
            "🤖 *Não entendi bem sua mensagem.*\n\n"
            "Envie uma foto de um imóvel ou digite 'ajuda' para ver todos os comandos.\n\n"
            "📞 Vendas: (41) 99214-6670\n"
            "🏡 Locação: (41) 99223-0874"
        )

    def _get_error_response(self) -> str:
        return (
            "😅 *Ops! Algo deu errado.*\n\n"
            "Tente novamente ou entre em contato diretamente:\n\n"
            "📞 Vendas: (41) 99214-6670\n"
            "🏡 Locação: (41) 99223-0874"
        )

    def _get_analysis_error_response(self) -> str:
        return (
            "🔧 *Sistema de análise temporariamente indisponível*\n\n"
            "📞 Vendas: (41) 99214-6670\n"
            "🏡 Locação: (41) 99223-0874"
        )

    def get_user_stats(self, user_id: str) -> Dict:
        if user_id not in self.conversation_history:
            return {'messages': 0, 'images_analyzed': 0}
        
        history = self.conversation_history[user_id]
        return {
            'messages': len(history),
            'images_analyzed': sum(1 for msg in history if msg.get('has_image')),
            'last_interaction': history[-1]['timestamp'] if history else None
        }

property_chatbot = PropertyChatbot()