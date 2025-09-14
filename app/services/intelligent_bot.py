"""
Integração Principal do Sistema de Inteligência Imobiliária
Coordena IA, extração de dados e resposta inteligente com análise de imagens
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp
import base64
from llama_index import GPTVectorStoreIndex


logger = logging.getLogger("IntelligentRealEstateBot")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class IntelligentRealEstateBot:
    """Bot inteligente especializado em imóveis usando LLaMA 3.1"""

    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3.1"):
        self.ollama_url = ollama_url
        self.model = model
        self.bot_config = {
            'company_name': 'Allega Imóveis',
            'response_style': 'friendly_professional',
            'enable_property_search': True,
            'enable_market_insights': True,
            'enable_image_analysis': True,
            'max_properties_per_response': 3
        }
        logger.info("Bot de Inteligência Imobiliária com LLaMA 3.1 iniciado")

    async def process_message(self, message: str, user_phone: str) -> str:
        """Processa mensagem do usuário com LLaMA 3.1"""
        try:
            logger.info(f"📨 Mensagem de {user_phone}: {message[:50]}...")
            prompt = self._build_prompt(message, user_phone)
            response = await self._call_llama(prompt)
            logger.info(f"✅ Resposta enviada para {user_phone}")
            return response
        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem: {str(e)}")
            return (
                "😅 Ops! Tive um probleminha técnico, mas já estou me recuperando!\n\n"
                "Enquanto isso, você pode entrar em contato diretamente:\n"
                "📞 Vendas: (41) 99214-6670\n"
                "📞 Locação: (41) 99223-0874\n\n"
                "Nossos especialistas estão prontos para ajudar! 😊"
            )

    async def process_image_message(self, image_data: bytes, caption: str, user_phone: str) -> str:
        """Processa imagem enviada pelo usuário usando LLaMA 3.1"""
        try:
            logger.info(f"Imagem recebida de {user_phone} - Tamanho: {len(image_data)} bytes")
            image_b64 = base64.b64encode(image_data).decode("utf-8")
            prompt = f"Analise esta imagem de imóvel. Mensagem do usuário: {caption}"
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
                    logger.info(f"Resposta da análise de imagem: status={resp.status}, body={text[:200]}")
                    if resp.status == 200:
                        result = await resp.json()
                        llm_response = result.get("message", {}).get("content", "")
                        return f"🏠 *Análise do Imóvel Concluída*\n\n{llm_response}\n\n💡 *Análise concluída!*"
                    else:
                        return (
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
        except Exception as e:
            logger.error(f"❌ Erro ao processar imagem: {str(e)}")
            return (
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

    async def process_property_search(self, user_query: str) -> str:
        """
        Busca imóveis usando o índice inteligente.
        """
        index = self.property_index
        if not index:
            return "😅 O índice de imóveis não está disponível no momento. Tente novamente mais tarde."

        try:
            response = index.query(user_query)
            return str(response)
        except Exception as e:
            logger.error(f"Erro ao consultar o índice: {str(e)}")
            return "😅 Não consegui buscar imóveis agora. Tente novamente em instantes."

    def _build_prompt(self, message: str, user_phone: str) -> str:
        """Constrói o prompt para o LLaMA 3.1"""
        return (
            f"Você é o assistente virtual da Allega Imóveis.\n"
            f"Usuário ({user_phone}) enviou: \"{message}\"\n"
            "Responda de forma amigável, profissional e objetiva. "
            "Se possível, ofereça ajuda para busca de imóveis, informações de preços, agendamento de visitas ou esclarecimento de dúvidas sobre documentação. "
            "Inclua contatos e informações relevantes da empresa ao final da resposta."
        )

    async def _call_llama(self, prompt: str) -> str:
        """Chama o modelo LLaMA 3.1 via Ollama"""
        payload = {
            "model": self.model,
            "messages": [{
                "role": "user",
                "content": prompt
            }]
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.ollama_url}/api/chat", json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    text = await resp.text()
                    logger.info(f"Resposta LLaMA: status={resp.status}, body={text[:200]}")
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get("message", {}).get("content", "")
                    else:
                        return (
                            "😅 Tive dificuldade técnica para responder no momento.\n\n"
                            "📞 Vendas: (41) 99214-6670\n"
                            "🏡 Locação: (41) 99223-0874"
                        )
        except Exception as e:
            logger.error(f"Erro ao chamar LLaMA 3.1: {str(e)}")
            return (
                "😅 Tive dificuldade técnica para responder no momento.\n\n"
                "📞 Vendas: (41) 99214-6670\n"
                "🏡 Locação: (41) 99223-0874"
            )

    def _is_property_search(self, message: str) -> bool:
        """
        Detecta se a mensagem é uma busca de imóvel.
        """
        keywords = ["casa", "apartamento", "imóvel", "quartos", "bairro", "comprar", "alugar", "locação"]
        return any(kw in message.lower() for kw in keywords)

    @property
    def property_index(self) -> Optional[GPTVectorStoreIndex]:
        """
        Retorna o índice de busca inteligente dos imóveis, se existir.
        """
        try:
            index = GPTVectorStoreIndex.load_from_disk("property_index.json")
            return index
        except Exception as e:
            logger.error(f"Erro ao carregar o índice de imóveis: {str(e)}")
            return None

# Instância global do bot
intelligent_bot = IntelligentRealEstateBot()
