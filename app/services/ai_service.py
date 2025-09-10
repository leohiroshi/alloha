import aiohttp
import logging
import os
import json
import re
from typing import Optional, Dict, List
from datetime import datetime

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
        
        # Cache de conversas por usuário
        self.conversation_context = {}
        
        # Importar property_intelligence de forma lazy para evitar importação circular
        self._property_intelligence = None
        
        # Base de conhecimento sobre imóveis
        self.property_knowledge = {
            "tipos": ["apartamento", "casa", "kitnet", "studio", "cobertura", "terreno", "comercial"],
            "regioes": ["centro", "zona sul", "zona norte", "zona oeste", "zona leste"],
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
        """Lazy loading da property intelligence para evitar importação circular"""
        if self._property_intelligence is None:
            try:
                from .property_intelligence import property_intelligence
                self._property_intelligence = property_intelligence
            except ImportError:
                self._property_intelligence = None
        return self._property_intelligence
    
    async def generate_response(self, message: str, user_phone: str) -> str:
        """Gerar resposta inteligente usando Abacus AI com contexto"""
        try:
            if not self.api_key:
                return await self._fallback_response(message)
            
            # Analisar intenção do usuário
            intent = await self._analyze_intent(message)
            
            # Recuperar contexto da conversa do Firebase
            context = await self._get_conversation_context_from_db(user_phone)
            
            # Atualizar contexto em memória
            self._update_conversation_context(user_phone, message, intent)
            
            # Gerar resposta baseada na intenção e contexto
            response = await self._generate_contextual_response(message, intent, context)
            
            return response
                
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}")
            return "Desculpe, houve um problema. Tente novamente em alguns instantes."
    
    async def _get_conversation_context_from_db(self, user_phone: str) -> Dict:
        """Recuperar contexto da conversa do banco de dados"""
        try:
            # Importar aqui para evitar importação circular
            from app.services.database_service import DatabaseService
            
            db_service = DatabaseService()
            
            # Obter histórico de conversas
            history = await db_service.get_conversation_history(user_phone, limit=5)
            
            # Processar histórico para criar contexto
            conversation_context = {
                "messages": history,
                "user_phone": user_phone,
                "message_count": len(history),
                "recent_topics": []
            }
            
            # Extrair tópicos recentes das mensagens
            for msg in history:
                if msg.get("type") == "received":
                    # Analisar mensagem para extrair tópicos
                    if any(word in msg.get("message", "").lower() for word in ["casa", "apartamento", "imóvel", "propriedade"]):
                        conversation_context["recent_topics"].append("imoveis")
                    elif any(word in msg.get("message", "").lower() for word in ["preço", "valor", "custo", "quanto"]):
                        conversation_context["recent_topics"].append("precos")
                    elif any(word in msg.get("message", "").lower() for word in ["visita", "agendar", "ver", "mostrar"]):
                        conversation_context["recent_topics"].append("agendamento")
            
            return conversation_context
            
        except Exception as e:
            logger.error(f"Error getting conversation context from DB: {str(e)}")
            # Fallback para contexto em memória
            return self._get_conversation_context(user_phone)
    
    async def _analyze_intent(self, message: str) -> Dict:
        """Analisar intenção da mensagem"""
        message_lower = message.lower()
        
        intent = {
            "type": "unknown",
            "confidence": 0.0,
            "entities": {}
        }
        
        # Detectar saudações
        if any(word in message_lower for word in ["oi", "olá", "hello", "hi", "bom dia", "boa tarde", "boa noite"]):
            intent["type"] = "greeting"
            intent["confidence"] = 0.9
        
        # Detectar busca por imóveis
        elif any(word in message_lower for word in ["apartamento", "casa", "imóvel", "comprar", "alugar"]):
            intent["type"] = "property_search"
            intent["confidence"] = 0.8
            
            # Extrair entidades
            for tipo in self.property_knowledge["tipos"]:
                if tipo in message_lower:
                    intent["entities"]["property_type"] = tipo
            
            for regiao in self.property_knowledge["regioes"]:
                if regiao in message_lower:
                    intent["entities"]["location"] = regiao
            
            # Extrair números (quartos, preço)
            numbers = re.findall(r'\d+', message)
            if numbers:
                intent["entities"]["numbers"] = numbers
        
        # Detectar consulta de preço
        elif any(word in message_lower for word in ["preço", "valor", "quanto", "custo"]):
            intent["type"] = "price_inquiry"
            intent["confidence"] = 0.8
        
        # Detectar agendamento
        elif any(word in message_lower for word in ["visita", "agendar", "ver", "conhecer"]):
            intent["type"] = "schedule_visit"
            intent["confidence"] = 0.8
        
        # Detectar informações
        elif any(word in message_lower for word in ["documentos", "financiamento", "fies", "itbi"]):
            intent["type"] = "information"
            intent["confidence"] = 0.7
        
        return intent
    
    def _get_conversation_context(self, user_phone: str) -> Dict:
        """Recuperar contexto da conversa"""
        if user_phone not in self.conversation_context:
            self.conversation_context[user_phone] = {
                "messages": [],
                "preferences": {},
                "last_intent": None,
                "created_at": datetime.now()
            }
        return self.conversation_context[user_phone]
    
    def _update_conversation_context(self, user_phone: str, message: str, intent: Dict):
        """Atualizar contexto da conversa"""
        context = self._get_conversation_context(user_phone)
        context["messages"].append({
            "message": message,
            "intent": intent,
            "timestamp": datetime.now()
        })
        context["last_intent"] = intent["type"]
        
        # Manter apenas últimas 10 mensagens
        if len(context["messages"]) > 10:
            context["messages"] = context["messages"][-10:]
    
    async def _generate_contextual_response(self, message: str, intent: Dict, context: Dict) -> str:
        """Gerar resposta baseada no contexto"""
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
        """Responder saudações"""
        if len(context["messages"]) == 1:  # Primeira interação
            return """🏠 Olá! Bem-vindo à Alloha! 

Sou seu assistente especializado em imóveis. Posso ajudar você a:
• Encontrar apartamentos e casas
• Informações sobre preços
• Agendar visitas
• Dicas de financiamento

O que você procura hoje?"""
        else:
            return "Olá novamente! Como posso ajudá-lo hoje? 😊"
    
    async def _handle_property_search(self, message: str, intent: Dict, context: Dict) -> str:
        """Lidar com busca por imóveis usando inteligência imobiliária"""
        try:
            # Verificar se temos property_intelligence disponível
            if self.property_intelligence:
                # Usar o sistema de inteligência imobiliária
                user_id = context.get('user_phone', 'unknown')
                response = await self.property_intelligence.process_property_inquiry(message, user_id)
                return response
            else:
                # Fallback para resposta básica
                entities = intent.get("entities", {})
                
                # Criar prompt contextual para Abacus AI
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
                
                # Tentar usar Abacus AI
                response = await self._call_abacus_ai(system_prompt, user_prompt)
                
                if response:
                    return response
                else:
                    # Resposta de fallback
                    return self._get_property_search_fallback(message, entities)
                    
        except Exception as e:
            logger.error(f"Erro em _handle_property_search: {str(e)}")
            return "🏠 Entendi que você procura um imóvel! Pode me contar mais detalhes como tipo (casa/apartamento), quantos quartos, região preferida e faixa de preço? Assim posso ajudar melhor!"
    
    def _get_property_search_fallback(self, message: str, entities: Dict) -> str:
        """Resposta de fallback para busca de imóveis"""
        response = "🔍 Ótimo! Vamos encontrar o imóvel ideal para você.\n\n"
        
        if "property_type" in entities:
            response += f"Você está interessado em {entities['property_type']}. "
        
        if "location" in entities:
            response += f"Na região {entities['location']}. "
        
        response += "\nPode me contar mais sobre suas preferências? (quartos, orçamento, etc.)"
        
        return response
    
    async def _handle_price_inquiry(self, message: str, intent: Dict, context: Dict) -> str:
        """Lidar com consultas de preço"""
        system_prompt = """Você é um especialista em preços de imóveis da Alloha.
        Forneça informações realistas sobre faixas de preço.
        Seja específico e útil. Máximo 300 caracteres."""
        
        ai_response = await self._call_abacus_api(system_prompt, f"Cliente pergunta sobre preços: {message}")
        
        if ai_response:
            return ai_response
        
        return """💰 Os preços variam conforme localização e características:

• Apartamentos: R$ 150k - R$ 800k+
• Casas: R$ 200k - R$ 1.5M+
• Kitnets: R$ 80k - R$ 200k

Que tipo de imóvel te interessa? Posso dar valores mais específicos!"""
    
    async def _handle_schedule_visit(self, message: str, intent: Dict, context: Dict) -> str:
        """Lidar com agendamento de visitas"""
        return """📅 Perfeito! Vamos agendar sua visita.

Para agilizar o processo, preciso de:
• Seu nome completo
• Imóvel de interesse
• Dias/horários de preferência

Um corretor entrará em contato em até 2h para confirmar!

Qual imóvel gostaria de visitar?"""
    
    async def _handle_information_request(self, message: str, intent: Dict, context: Dict) -> str:
        """Lidar com pedidos de informação"""
        system_prompt = """Você é um consultor imobiliário da Alloha especialista em documentação e financiamento.
        Forneça informações práticas e úteis. Máximo 300 caracteres."""
        
        ai_response = await self._call_abacus_api(system_prompt, f"Cliente pergunta: {message}")
        
        if ai_response:
            return ai_response
        
        return """📋 Posso ajudar com informações sobre:

• Documentação necessária
• Financiamento e FGTS
• ITBI e custos extras
• Processo de compra/venda

Sobre o que você gostaria de saber?"""
    
    async def _handle_general_inquiry(self, message: str, context: Dict) -> str:
        """Lidar com perguntas gerais"""
        system_prompt = """Você é o assistente da Alloha Imóveis.
        Responda de forma amigável e direcione para serviços imobiliários.
        Máximo 250 caracteres."""
        
        ai_response = await self._call_abacus_api(system_prompt, f"Cliente pergunta: {message}")
        
        if ai_response:
            return ai_response
        
        return f"""🤖 Entendi: "{message}"

Como especialista em imóveis, posso ajudar com:
• Busca de apartamentos/casas
• Informações de preços
• Agendamento de visitas
• Documentação

Como posso ajudá-lo hoje?"""
    
    async def _fallback_response(self, message: str) -> str:
        """Resposta quando IA não está disponível"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["oi", "olá", "hello"]):
            return "🏠 Olá! Sou o assistente da Alloha. Como posso ajudá-lo com imóveis?"
        elif any(word in message_lower for word in ["apartamento", "casa"]):
            return "🔍 Ótimo! Que tipo de imóvel você procura? Em qual região?"
        elif any(word in message_lower for word in ["preço", "valor"]):
            return "💰 Posso ajudar com informações de preços. Que tipo de imóvel te interessa?"
        else:
            return "🤖 Olá! Sou especialista em imóveis. Como posso ajudá-lo hoje?"

    async def test_abacus_image_support(self, image_base64: str) -> Dict[str, Any]:
        """Testar se Abacus suporta análise de imagem"""
        if not self.api_key:
            return {"error": "API key não configurada", "supports_vision": False}
        
        try:
            # Teste 1: Formato OpenAI Vision
            payload_vision = {
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Analise esta imagem de imóvel"},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                            }
                        ]
                    }
                ],
                "max_tokens": 150
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload_vision,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    
                    result = {
                        "status": response.status,
                        "supports_vision": response.status == 200,
                        "endpoint_tested": "/chat/completions with vision"
                    }
                    
                    if response.status == 200:
                        data = await response.json()
                        result["success"] = True
                        result["response"] = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        logger.info("✅ Abacus suporta análise de imagem!")
                    else:
                        error_text = await response.text()
                        result["error"] = error_text
                        logger.info(f"❌ Abacus não suporta visão: {response.status}")
                    
                    return result
                    
        except Exception as e:
            logger.error(f"Erro testando Abacus vision: {str(e)}")
            return {
                "error": str(e),
                "supports_vision": False,
                "test_failed": True
            }

    async def analyze_image_with_abacus(self, image_base64: str, prompt: str = "") -> Optional[str]:
        """Analisar imagem usando Abacus AI (se suportado)"""
        if not self.api_key:
            return None
            
        try:
            # Prompt padrão se não fornecido
            if not prompt:
                prompt = """Analise esta imagem de imóvel brasileiro e forneça:
                1. Tipo de imóvel (casa, apartamento, etc.)
                2. Características visíveis
                3. Estado de conservação
                4. Qualidade para marketing imobiliário
                
                Seja específico e útil para corretores."""
            
            # Tentar formato vision
            payload = {
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                    "detail": "low"  # Para economizar tokens
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 300,
                "temperature": 0.1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"]
                        logger.info("✅ Análise de imagem com Abacus realizada!")
                        return content
                    else:
                        error_text = await response.text()
                        logger.warning(f"Abacus vision failed: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"Erro na análise de imagem com Abacus: {str(e)}")
            return None

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
                "max_tokens": 200,
                "temperature": 0.7
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions", 
                    headers=self.headers, 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data["choices"][0]["message"]["content"].strip()
                        # Limitar tamanho para WhatsApp
                        return content[:300] if len(content) > 300 else content
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
    
    async def get_property_suggestions(self, criteria: str, user_phone: str) -> str:
        """Sugerir imóveis baseado em critérios com contexto"""
        try:
            context = self._get_conversation_context(user_phone)
            
            system_prompt = """Você é um especialista em imóveis da Alloha.
            Sugira imóveis específicos baseado nos critérios do cliente.
            Inclua tipos, preços estimados e localizações.
            Seja específico e útil. Máximo 400 caracteres."""
            
            user_prompt = f"""Critérios do cliente: {criteria}
            
            Histórico da conversa: {context.get('messages', [])}
            
            Sugira opções de imóveis adequadas."""
            
            response = await self._call_abacus_api(system_prompt, user_prompt)
            
            if response:
                return response
            
            return """🏠 Baseado no que você procura, temos ótimas opções!

Vou conectar você com um de nossos corretores especializados que tem acesso ao nosso portfólio completo.

Quer agendar uma conversa?"""
            
        except Exception as e:
            logger.error(f"Error getting property suggestions: {str(e)}")
            return "Erro ao buscar sugestões. Tente novamente."
    
    def get_conversation_stats(self, user_phone: str) -> Dict:
        """Obter estatísticas da conversa"""
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
        """Limpa o cache de conversas"""
        if user_phone:
            # Limpar cache de usuário específico
            if user_phone in self.conversation_context:
                del self.conversation_context[user_phone]
                logger.info(f"🗑️ Cache de conversa limpo para {user_phone}")
        else:
            # Limpar todo o cache
            self.conversation_context.clear()
            logger.info("🗑️ Todo o cache de conversas foi limpo")
