import aiohttp
import logging
import os
import re
import base64
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
from app.services.rag_pipeline import call_gpt, retrieve, build_prompt

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        # RAG endpoint (se usado) — padronizado para integração GPT/OpenAI
        self.rag_endpoint = os.getenv("RAG_ENDPOINT", "http://localhost:8000/query")
        self.conversation_context = {}
        self._property_intelligence = None
        # knowledge tetap disponível
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

    async def generate_response(self, message: str, user_phone: str, image_bytes: bytes = None) -> str:
        """
        Gera resposta usando o GPT (OpenAI, por exemplo GPT-5 mini).
        Para buscas de imóvel, usa RAG via retrieve/build_prompt/call_gpt.
        Para perguntas gerais, chama call_gpt diretamente com prompt.
        """
        # detecção simples de busca de imóvel
        if any(k in message.lower() for k in ["apartamento", "casa", "procuro", "quartos", "aluguel", "venda"]):
            # Retrieval + RAG
            retrieved = retrieve(message, top_k=5, filters={})
            prompt = build_prompt(message, retrieved)
            model = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:sofia:CKv6isOD")
            return await asyncio.to_thread(call_gpt, prompt, model)

        prompt = f"Você é Sofia, assistente da Allega Imóveis.\nUsuário: {message}\nResponda de forma concisa."
        model = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:sofia:CKv6isOD")
        return await asyncio.to_thread(call_gpt, prompt, model)

    async def generate_text(self, prompt: str) -> str:
        # wrapper async para chamar o GPT (bloqueante) em thread
        model = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:sofia:CKv6isOD")
        return await asyncio.to_thread(call_gpt, prompt, model)

    @property
    def property_intelligence(self):
        if self._property_intelligence is None:
            try:
                from .property_intelligence import property_intelligence
                self._property_intelligence = property_intelligence
            except ImportError:
                self._property_intelligence = None
        return self._property_intelligence

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
                
                prompt = f"{system_prompt}\n{user_prompt}"
                response = await self.generate_text(prompt)
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
        prompt = f"{system_prompt}\nCliente pergunta sobre preços: {message}"
        response = await self.generate_text(prompt)
        if response:
            return response
        return (
            "💰 Os preços variam conforme localização e características:\n\n"
            "• Apartamentos: R$ 150k - R$ 800k+\n"
            "• Casas: R$ 200k - R$ 1.5M+\n"
            "• Kitnets: R$ 80k - R$ 200k\n\n"
            "Que tipo de imóvel te interessa? Posso dar valores mais específicos!"
        )

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
        prompt = f"{system_prompt}\nCliente pergunta: {message}"
        response = await self.generate_text(prompt)
        if response:
            return response
        return (
            "📋 Posso ajudar com informações sobre:\n\n"
            "• Documentação necessária\n"
            "• Financiamento e FGTS\n"
            "• ITBI e custos extras\n"
            "• Processo de compra/venda\n\n"
            "📞 Contatos:\n"
            "🏠 Vendas: (41) 99214-6670\n"
            "🏡 Locação: (41) 99223-0874\n\n"
            "Sobre o que você gostaria de saber?"
        )

    async def _handle_general_inquiry(self, message: str, context: Dict) -> str:
        system_prompt = """Você é a Sofia, assistente da Allega Imóveis.
Responda de forma amigável e direcione para serviços imobiliários.
Máximo 250 caracteres."""
        prompt = f"{system_prompt}\nCliente pergunta: {message}"
        response = await self.generate_text(prompt)
        if response:
            return response
        return (
            f"🤖 Entendi: \"{message}\"\n\n"
            "Como Sofia da Allega Imóveis, posso ajudar com:\n"
            "• Busca de apartamentos/casas\n"
            "• Informações de preços\n"
            "• Agendamento de visitas\n"
            "• Documentação\n\n"
            "📞 Contatos:\n"
            "🏠 Vendas: (41) 99214-6670\n"
            "🏡 Locação: (41) 99223-0874\n\n"
            "Como posso ajudá-lo hoje?"
        )

    async def _handle_image_analysis(self, message: str, image_bytes: bytes) -> str:
        try:
            # converter imagem para base64 (atenção ao tamanho)
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            # adicionar marcadores para facilitar parsing no LLM
            prompt = (
                f"Analise esta imagem de imóvel. Mensagem do usuário: {message}\n\n"
                "Como Sofia da Allega Imóveis, identifique:\n"
                "- Tipo de imóvel (casa, apartamento, terreno)\n"
                "- Características visíveis (quartos, banheiros, garagem)\n"
                "- Estado de conservação\n"
                "- Localização aproximada se possível\n"
                "- Diferenciais e pontos de destaque\n"
                "- Valor estimado se conseguir identificar\n\n"
                "Seja específico e profissional na análise.\n\n"
                "---BEGIN_IMAGE_BASE64---\n"
                f"{image_b64}\n"
                "---END_IMAGE_BASE64---\n\n"
                "Resuma em até 300 caracteres."
            )

            model_name = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:sofia:CKv6isOD")
            # call_gpt é bloqueante — executar em thread
            llm_response = await asyncio.to_thread(call_gpt, prompt, model_name)

            if llm_response:
                content = llm_response.strip()
                return (
                    f"🏠 *Análise do Imóvel Concluída*\n\n{content}\n\n"
                    "💡 *Análise concluída pela Sofia da Allega Imóveis!*\n"
                    "📞 *Quer mais informações?*\n"
                    "🏠 Vendas: (41) 99214-6670\n"
                    "🏡 Locação: (41) 99223-0874"
                )
            else:
                return self._get_image_analysis_fallback()
        except Exception as e:
            logger.error(f"Erro ao analisar imagem com OpenAI: {e}")
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


    def is_available(self) -> bool:
        return True 

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