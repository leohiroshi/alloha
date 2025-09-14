"""
Chatbot Inteligente para Análise de Imóveis
Integra o PropertyImageAnalyzer com interface de chat
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
from llama_index import GPTVectorStoreIndex

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PropertyImageAnalyzer:
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3.2-vision", index_path: str = "property_index.json"):
        self.ollama_url = ollama_url
        self.model = model
        self.index_path = index_path

    async def analyze_property_image(self, image_bytes: bytes, prompt: str = "Analyze this property image") -> dict:
        try:
            logger.info(f"Analisando imagem ({len(image_bytes)} bytes) com LLaMA 3.2 Vision")
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            payload = {
                "model": self.model,
                "messages": [{
                    "role": "user",
                    "content": prompt,
                    "images": [image_b64]
                }]
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.ollama_url}/api/chat", json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    text = await resp.text()
                    logger.info(f"Resposta recebida: status={resp.status}, body={text[:200]}")
                    if resp.status == 200:
                        result = await resp.json()
                        # Tenta extrair características do imóvel da resposta da IA
                        llm_content = result.get("message", {}).get("content", "")
                        extracted_query = self._extract_query_from_llm(llm_content)
                        index_response = None
                        if extracted_query:
                            index_response = self.query_property_index(extracted_query)
                        return {
                            "success": True,
                            "response": result,
                            "index_query": extracted_query,
                            "index_response": str(index_response) if index_response else None
                        }
                    else:
                        return {"success": False, "error": f"Status {resp.status}: {text}"}
        except Exception as e:
            logger.error(f"Erro ao analisar imagem com LLaMA 3.2 Vision: {e}")
            return {"success": False, "error": str(e)}

    def _extract_query_from_llm(self, llm_content: str) -> str:
        """
        Extrai uma consulta textual do conteúdo gerado pela IA Vision.
        Exemplo: busca por 'casa 3 quartos Bigorrilho'
        """
        # Simples heurística: pega a primeira frase que contém tipo, quartos e bairro
        import re
        match = re.search(r'(casa|apartamento|imóvel)[^\n]*?(\d+)\s*quartos?[^\n]*?(bigorrilho|batel|centro|cabral|champagnat)', llm_content, re.IGNORECASE)
        if match:
            return match.group(0)
        # Fallback: retorna a primeira frase
        return llm_content.split('.')[0] if llm_content else ""

    def query_property_index(self, query: str):
        """
        Consulta o índice inteligente de imóveis usando LlamaIndex.
        """
        try:
            index = GPTVectorStoreIndex.load_from_disk(self.index_path)
            response = index.query(query)
            return response
        except Exception as e:
            logger.error(f"Erro ao consultar o índice de imóveis: {str(e)}")
            return None

    def format_analysis_response(self, analysis_result: Dict, user_message: str) -> str:
        if not analysis_result.get("success", True):
            error_msg = analysis_result.get("error", "Erro desconhecido")
            return f"😅 *Tive dificuldade para analisar esta imagem.*\n\nErro: {error_msg}\n\n📞 *Fale direto com nossos especialistas:*\n🏠 Vendas: (41) 99214-6670\n🏡 Locação: (41) 99223-0874"

        response = "🏠 *Análise do Imóvel Concluída*\n\n"
        llm_response = analysis_result.get("response", {}).get("message", {}).get("content", "")
        response += f"{llm_response}\n\n"
        if analysis_result.get("index_response"):
            response += f"🔎 *Imóveis similares encontrados:*\n{analysis_result['index_response']}\n\n"
        response += "💡 *Análise concluída!*\n"
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
            'greeting': "🏠 *Olá! Sou o assistente da Allega Imóveis!*\n\nEnvie uma foto de imóvel para análise ou digite 'ajuda' para ver comandos.\n\n📞 Vendas: (41) 99214-6670\n🏡 Locação: (41) 99223-0874",
            'help': "🤖 *Como usar o assistente:*\n\n• Envie uma foto do imóvel\n• Eu analiso automaticamente\n• Receba informações detalhadas\n\n📞 Vendas: (41) 99214-6670\n🏡 Locação: (41) 99223-0874",
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
        return "🤖 *Não entendi bem sua mensagem.*\n\nEnvie uma foto de um imóvel ou digite 'ajuda' para ver todos os comandos.\n\n📞 Vendas: (41) 99214-6670\n🏡 Locação: (41) 99223-0874"

    def _get_error_response(self) -> str:
        return "😅 *Ops! Algo deu errado.*\n\nTente novamente ou entre em contato diretamente:\n\n📞 Vendas: (41) 99214-6670\n🏡 Locação: (41) 99223-0874"

    def _get_analysis_error_response(self) -> str:
        return "🔧 *Sistema de análise temporariamente indisponível*\n\n📞 Vendas: (41) 99214-6670\n🏡 Locação: (41) 99223-0874"

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