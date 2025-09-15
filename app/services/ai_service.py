import aiohttp
import logging
import os
import re
import base64
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.text_model = "llama3-8b-8192"  # Modelo de texto do Groq
        self.vision_model = "llama-3.2-11b-vision-preview"  # Modelo de visão do Groq
        self.conversation_context = {}
        self._property_intelligence = None

        self.property_knowledge = {
            "tipos": ["apartamento", "casa", "kitnet", "studio", "cobertura", "terreno", "comercial"],
            "regioes": ["centro", "zona sul", "zona norte", "zona oeste", "zona leste", "bigorrilho", "batel", "cabral", "champagnat", "água verde", "portão", "santa felicidade"],
            "faixas_preco": {
                "baixo": "até R$ 200.000",
                "medio": "R$ 200.000 - R$ 500.000", 
                "alto": "R$ 500.000 - R$ 1.000.000",
                "premium": "acima de R$ 1.000.000"
            },
            "caracteristicas": ["quartos", "banheiros", "vagas", "area", "piscina", "churrasqueira"]
        }

    @property
    def property_intelligence(self):
        if self._property_intelligence is None:
            try:
                from .property_intelligence import property_intelligence
                self._property_intelligence = property_intelligence
            except ImportError:
                self._property_intelligence = None
        return self._property_intelligence

    async def generate_response(self, message: str, user_phone: str, image_bytes: bytes = None) -> str:
        try:
            intent = await self._analyze_intent(message)
            context = await self._get_conversation_context_from_db(user_phone)
            self._update_conversation_context(user_phone, message, intent)
            
            if image_bytes:
                return await self._handle_image_analysis(message, image_bytes)
            else:
                return await self._generate_contextual_response(message, intent, context)
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return "Desculpe, houve um problema. Tente novamente em alguns instantes."

    async def _get_conversation_context_from_db(self, user_phone: str) -> Dict:
        try:
            from app.services.database_service import DatabaseService
            db_service = DatabaseService()
            history = await db_service.get_conversation_history(user_phone, limit=5)
            conversation_context = {
                "messages": history,
                "user_phone": user_phone,
                "message_count": len(history),
                "recent_topics": []
            }
            for msg in history:
                if msg.get("type") == "received":
                    if any(word in msg.get("message", "").lower() for word in ["casa", "apartamento", "imóvel", "propriedade"]):
                        conversation_context["recent_topics"].append("imoveis")
                    elif any(word in msg.get("message", "").lower() for word in ["preço", "valor", "custo", "quanto"]):
                        conversation_context["recent_topics"].append("precos")
                    elif any(word in msg.get("message", "").lower() for word in ["visita", "agendar", "ver", "mostrar"]):
                        conversation_context["recent_topics"].append("agendamento")
            return conversation_context
        except Exception as e:
            logger.error(f"Error getting conversation context from DB: {str(e)}")
            return self._get_conversation_context(user_phone)

    async def _analyze_intent(self, message: str) -> Dict:
        message_lower = message.lower()
        intent = {
            "type": "unknown",
            "confidence": 0.0,
            "entities": {}
        }
        
        if any(word in message_lower for word in ["oi", "olá", "hello", "hi", "bom dia", "boa tarde", "boa noite"]):
            intent["type"] = "greeting"
            intent["confidence"] = 0.9
        elif any(word in message_lower for word in ["apartamento", "casa", "imóvel", "comprar", "alugar"]):
            intent["type"] = "property_search"
            intent["confidence"] = 0.8
            
            for tipo in self.property_knowledge["tipos"]:
                if tipo in message_lower:
                    intent["entities"]["property_type"] = tipo
            
            for regiao in self.property_knowledge["regioes"]:
                if regiao in message_lower:
                    intent["entities"]["location"] = regiao
            
            numbers = re.findall(r'\d+', message)
            if numbers:
                intent["entities"]["numbers"] = numbers
                
        elif any(word in message_lower for word in ["preço", "valor", "quanto", "custo"]):
            intent["type"] = "price_inquiry"
            intent["confidence"] = 0.8
        elif any(word in message_lower for word in ["visita", "agendar", "ver", "conhecer"]):
            intent["type"] = "schedule_visit"
            intent["confidence"] = 0.8
        elif any(word in message_lower for word in ["documentos", "financiamento", "fies", "itbi"]):
            intent["type"] = "information"
            intent["confidence"] = 0.7
            
        return intent

    def _get_conversation_context(self, user_phone: str) -> Dict:
        if user_phone not in self.conversation_context:
            self.conversation_context[user_phone] = {
                "messages": [],
                "preferences": {},
                "last_intent": None,
                "created_at": datetime.now()
            }
        return self.conversation_context[user_phone]

    def _update_conversation_context(self, user_phone: str, message: str, intent: Dict):
        context = self._get_conversation_context(user_phone)
        context["messages"].append({
            "message": message,
            "intent": intent,
            "timestamp": datetime.now()
        })
        context["last_intent"] = intent["type"]
        if len(context["messages"]) > 10:
            context["messages"] = context["messages"][-10:]

    async def _generate_contextual_response(self, message: str, intent: Dict, context: Dict) -> str:
        intent_type = intent["type"]
        
        if intent_type == "greeting":
            return await self._handle_greeting(context)
        elif intent_type == "property_search":
            return await self._handle_property_search(message, intent, context)
        elif intent_type == "price_inquiry":
            return await self._handle_price_inquiry(message, intent, context)
        elif intent_type == "schedule_visit":
            return await self._handle_schedule_visit(message, intent, context)
        elif intent_type == "information":
            return await self._handle_information_request(message, intent, context)
        else:
            return await self._handle_general_inquiry(message, context)

    async def _handle_greeting(self, context: Dict) -> str:
        if len(context["messages"]) == 1:
            return """🏠 Olá! Bem-vindo à Allega Imóveis! 

Sou a Sofia, sua assistente especializada em imóveis. Posso ajudar você a:
• Encontrar apartamentos e casas
• Informações sobre preços
• Agendar visitas
• Dicas de financiamento

O que você procura hoje?"""
        else:
            return "Olá novamente! Como posso ajudá-lo hoje? 😊"

    async def _handle_property_search(self, message: str, intent: Dict, context: Dict) -> str:
        try:

            if self.property_intelligence:
                user_id = context.get('user_phone', 'unknown')
                response = await self.property_intelligence.process_property_inquiry(message, user_id)
                return response
            else:
                entities = intent.get("entities", {})
                system_prompt = """Você é a Sofia! A assistente virtual da Allega Imóveis.
Responda de forma amigável e profissional sobre busca de imóveis para venda e locação.
Seja específico e útil. Limite a resposta a 300 caracteres.

Informações da Allega Imóveis:
- Site: https://www.allegaimoveis.com
- Vendas: (41) 99214-6670
- Locação: (41) 99223-0874
- Especialistas em imóveis residenciais e comerciais
- Atendimento personalizado e consultoria completa"""
                
                context_info = ""
                if entities:
                    context_info = f"Cliente interessado em: {entities}"
                
                user_prompt = f"""Cliente busca imóvel: {message}
Contexto: {context_info}

Responda oferecendo ajuda e pedindo mais detalhes específicos."""
                
                response = await self._call_groq(system_prompt, user_prompt)
                if response:
                    return response
                else:
                    return self._get_property_search_fallback(message, entities)
        except Exception as e:
            logger.error(f"Erro em _handle_property_search: {str(e)}")
            return "🏠 Entendi que você procura um imóvel! Pode me contar mais detalhes como tipo (casa/apartamento), quantos quartos, região preferida e faixa de preço? Assim posso ajudar melhor!"

    def _get_property_search_fallback(self, message: str, entities: Dict) -> str:
        response = "🔍 Ótimo! Vamos encontrar o imóvel ideal para você.\n\n"
        if "property_type" in entities:
            response += f"Você está interessado em {entities['property_type']}. "
        if "location" in entities:
            response += f"Na região {entities['location']}. "
        response += "\nPode me contar mais sobre suas preferências? (quartos, orçamento, etc.)"
        return response

    async def _handle_price_inquiry(self, message: str, intent: Dict, context: Dict) -> str:
        system_prompt = """Você é a Sofia, especialista em preços de imóveis da Allega Imóveis.
Forneça informações realistas sobre faixas de preço em Curitiba e região metropolitana.
Seja específico e útil. Máximo 300 caracteres."""
        
        response = await self._call_groq(system_prompt, f"Cliente pergunta sobre preços: {message}")
        if response:
            return response
            
        return """💰 Os preços variam conforme localização e características:

• Apartamentos: R$ 150k - R$ 800k+
• Casas: R$ 200k - R$ 1.5M+
• Kitnets: R$ 80k - R$ 200k

Que tipo de imóvel te interessa? Posso dar valores mais específicos!"""

    async def _handle_schedule_visit(self, message: str, intent: Dict, context: Dict) -> str:
        return """📅 Perfeito! Vamos agendar sua visita.

Para agilizar o processo, preciso de:
• Seu nome completo
• Imóvel de interesse
• Dias/horários de preferência

Um corretor entrará em contato em até 2h para confirmar!

📞 Contatos diretos:
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874

Qual imóvel gostaria de visitar?"""

    async def _handle_information_request(self, message: str, intent: Dict, context: Dict) -> str:
        system_prompt = """Você é a Sofia, consultora imobiliária da Allega Imóveis especialista em documentação e financiamento.
Forneça informações práticas e úteis sobre o mercado imobiliário. Máximo 300 caracteres."""
        
        response = await self._call_groq(system_prompt, f"Cliente pergunta: {message}")
        if response:
            return response
            
        return """📋 Posso ajudar com informações sobre:

• Documentação necessária
• Financiamento e FGTS
• ITBI e custos extras
• Processo de compra/venda

📞 Contatos:
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874

Sobre o que você gostaria de saber?"""

    async def _handle_general_inquiry(self, message: str, context: Dict) -> str:
        system_prompt = """Você é a Sofia, assistente da Allega Imóveis.
Responda de forma amigável e direcione para serviços imobiliários.
Máximo 250 caracteres."""
        
        response = await self._call_groq(system_prompt, f"Cliente pergunta: {message}")
        if response:
            return response
            
        return f"""🤖 Entendi: \"{message}\"

Como Sofia da Allega Imóveis, posso ajudar com:
• Busca de apartamentos/casas
• Informações de preços
• Agendamento de visitas
• Documentação

📞 Contatos:
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874

Como posso ajudá-lo hoje?"""

    async def _handle_image_analysis(self, message: str, image_bytes: bytes) -> str:
        try:
            if not self.groq_api_key:
                return "😅 Sistema de análise de imagens temporariamente indisponível."
            
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            enhanced_prompt = (
                f"Analise esta imagem de imóvel. Mensagem do usuário: {message}\n\n"
                "Como Sofia da Allega Imóveis, identifique:\n"
                "- Tipo de imóvel (casa, apartamento, terreno)\n"
                "- Características visíveis (quartos, banheiros, garagem)\n"
                "- Estado de conservação\n"
                "- Localização aproximada se possível\n"
                "- Diferenciais e pontos de destaque\n"
                "- Valor estimado se conseguir identificar\n\n"
                "Seja específico e profissional na análise."
            )
            
            payload = {
                "model": self.vision_model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": enhanced_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }],
                "max_tokens": 1000,
                "temperature": 0.3
            }
            
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions", 
                    json=payload, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        llm_response = result["choices"][0]["message"]["content"]
                        
                       
                        response = f"🏠 *Análise do Imóvel Concluída*\n\n{llm_response}\n\n"
                        
                    
                        response += "💡 *Análise concluída pela Sofia da Allega Imóveis!*\n"
                        response += "📞 *Quer mais informações?*\n"
                        response += "🏠 Vendas: (41) 99214-6670\n"
                        response += "🏡 Locação: (41) 99223-0874"
                        
                        return response
                    else:
                        error_data = await resp.json() if resp.content_type == 'application/json' else {}
                        logger.error(f"Groq Vision API error: {resp.status} - {error_data}")
                        return self._get_image_analysis_fallback()
                        
        except Exception as e:
            logger.error(f"Erro ao analisar imagem com Groq Vision: {e}")
            return self._get_image_analysis_fallback()

    def _get_image_analysis_fallback(self) -> str:
        return """📸 Recebi sua imagem!

😅 Tive dificuldade técnica para analisá-la no momento.

🏠 *Mas posso ajudar de outras formas:*
• Descreva o imóvel que procura
• Informe sua localização preferida
• Conte sobre seu orçamento

📞 *Ou entre em contato direto:*
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874"""

    async def _call_groq(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Chama API do Groq para geração de texto"""
        if not self.groq_api_key:
            return None
        
        try:
            payload = {
                "model": self.text_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.3
            }
            
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.groq.com/openai/v1/chat/completions", 
                    json=payload, 
                    headers=headers, 
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"].strip()
                        return content[:400] if len(content) > 400 else content
                    else:
                        error_data = await response.json() if response.content_type == 'application/json' else {}
                        logger.error(f"Groq API error: {response.status} - {error_data}")
                        return None
        except Exception as e:
            logger.error(f"Error calling Groq API: {str(e)}")
            return None

    def is_available(self) -> bool:
        return bool(self.groq_api_key)

    async def get_property_suggestions(self, criteria: str, user_phone: str) -> str:
        try:
            context = self._get_conversation_context(user_phone)
            system_prompt = """Você é a Sofia, especialista em imóveis da Allega Imóveis.
Sugira imóveis específicos baseado nos critérios do cliente.
Inclua tipos, preços estimados e localizações em Curitiba.
Seja específico e útil. Máximo 400 caracteres."""
            
            user_prompt = f"""Critérios do cliente: {criteria}

Histórico da conversa: {context.get('messages', [])}

Sugira opções de imóveis adequadas."""
            
            response = await self._call_groq(system_prompt, user_prompt)
            if response:
                return response
                
            return """🏠 Baseado no que você procura, temos ótimas opções!

Vou conectar você com um de nossos corretores especializados que tem acesso ao nosso portfólio completo.

📞 Contatos:
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874

Quer agendar uma conversa?"""
        except Exception as e:
            logger.error(f"Error getting property suggestions: {str(e)}")
            return "Erro ao buscar sugestões. Tente novamente."

    def get_conversation_stats(self, user_phone: str) -> Dict:
        context = self._get_conversation_context(user_phone)
        intent_counts = {}
        for msg in context["messages"]:
            intent_type = msg["intent"]["type"]
            intent_counts[intent_type] = intent_counts.get(intent_type, 0) + 1
        return {
            "total_messages": len(context["messages"]),
            "intent_distribution": intent_counts,
            "last_intent": context.get("last_intent"),
            "conversation_started": context.get("created_at")
        }

    def clear_conversation_cache(self, user_phone: str = None):
        if user_phone:
            if user_phone in self.conversation_context:
                del self.conversation_context[user_phone]
                logger.info(f"🗑️ Cache de conversa limpo para {user_phone}")
        else:
            self.conversation_context.clear()
            logger.info("🗑️ Todo o cache de conversas foi limpo")

            
ai_service = AIService()