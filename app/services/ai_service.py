import aiohttp
import logging
import os
import json
from typing import Optional

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.api_key = os.getenv("ABACUS_API_KEY", "")
        self.base_url = "https://api.abacus.ai"
        self.provider = os.getenv("AI_PROVIDER", "abacus")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate_response(self, message: str, user_phone: str) -> str:
        """Gerar resposta usando Abacus AI"""
        try:
            if not self.api_key:
                return "Desculpe, o serviço de AI não está configurado no momento."
            
            # Prompt personalizado para imobiliária
            system_prompt = """
            Você é um assistente especializado em imóveis da Alloha, uma imobiliária inovadora.
            
            Suas responsabilidades:
            - Ajudar clientes a encontrar imóveis (casas, apartamentos, terrenos)
            - Fornecer informações sobre compra, venda e aluguel
            - Dar dicas sobre financiamento e documentação
            - Agendar visitas e reuniões
            - Ser sempre educado, profissional e prestativo
            
            Responda de forma clara, objetiva e amigável.
            Limite suas respostas a 200 caracteres para WhatsApp.
            """
            
            user_prompt = f"Cliente pergunta: {message}"
            
            # Usar API do Abacus para gerar resposta
            response = await self._call_abacus_api(system_prompt, user_prompt)
            
            if response:
                return response
            else:
                return "Olá! Sou o assistente da Alloha. Como posso ajudá-lo com imóveis hoje?"
                
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return "Desculpe, houve um problema. Tente novamente em alguns instantes."
    
    async def _call_abacus_api(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Chamar API do Abacus AI"""
        try:
            # Configuração específica para Abacus AI
            payload = {
                "model": "gpt-3.5-turbo",  # Ou o modelo disponível no Abacus
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 150,
                "temperature": 0.7
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions", 
                    headers=self.headers, 
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["choices"][0]["message"]["content"].strip()
                    else:
                        error_text = await response.text()
                        logger.error(f"Abacus API error: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error calling Abacus API: {str(e)}")
            return None
    
    def is_available(self) -> bool:
        """Verificar se o serviço de AI está disponível"""
        return bool(self.api_key)
    
    async def get_property_suggestions(self, criteria: str) -> str:
        """Sugerir imóveis baseado em critérios"""
        try:
            prompt = f"""
            Baseado nos critérios: {criteria}
            
            Sugira algumas opções de imóveis que podem interessar ao cliente.
            Inclua tipos de imóveis, faixas de preço e bairros recomendados.
            Mantenha a resposta concisa para WhatsApp.
            """
            
            response = await self._call_abacus_api(
                "Você é um especialista em imóveis que sugere propriedades.",
                prompt
            )
            
            return response or "Vou verificar as melhores opções para você. Um corretor entrará em contato em breve!"
            
        except Exception as e:
            logger.error(f"Error getting property suggestions: {str(e)}")
            return "Erro ao buscar sugestões. Tente novamente."
