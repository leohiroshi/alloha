"""
Integração Principal do Sistema de Inteligência Imobiliária
Coordena IA, extração de dados e resposta inteligente com análise de imagens usando Gemini
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp
import base64
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json
import tempfile
import re
import google.generativeai as genai

load_dotenv()

logger = logging.getLogger("IntelligentRealEstateBot")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Inicialize o Firebase apenas uma vez
if not firebase_admin._apps:
    firebase_credentials_json = os.getenv("FIREBASE_CREDENTIALS")
    if firebase_credentials_json and firebase_credentials_json.strip().startswith("{"):
        # Cria arquivo temporário com o conteúdo do JSON
        temp_cred_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        temp_cred_file.write(firebase_credentials_json.encode())
        temp_cred_file.close()
        firebase_cred_path = temp_cred_file.name
    else:
        # Se já for um caminho, usa direto
        firebase_cred_path = firebase_credentials_json

    cred = credentials.Certificate(firebase_cred_path)
    firebase_admin.initialize_app(cred)
db = firestore.client()

class IntelligentRealEstateBot:
    """Bot inteligente especializado em imóveis usando Gemini"""

    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel("gemini-2.5-pro")
        self.bot_config = {
            'company_name': 'Allega Imóveis',
            'response_style': 'friendly_professional',
            'enable_property_search': True,
            'enable_market_insights': True,
            'enable_image_analysis': True,
            'max_properties_per_response': 3
        }
        logger.info("Bot de Inteligência Imobiliária com Gemini iniciado")

    async def get_conversation_history(self, user_phone, limit=10):
        """
        Busca as últimas mensagens do usuário e do bot no Firestore para manter o contexto da conversa.
        """
        messages_ref = db.collection("messages")
        query = (
            messages_ref
            .where("user_phone", "==", user_phone)
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        docs = query.stream()
        history = []
        for doc in reversed(list(docs)):  # do mais antigo para o mais recente
            data = doc.to_dict()
            role = "user" if data.get("direction") == "received" else "assistant"
            history.append({"role": role, "content": data.get("message", "")})
        return history

    async def process_message(self, message: str, user_phone: str) -> str:
        """
        Processa mensagem do usuário, mantendo o contexto da conversa salvo no Firebase.
        """
        try:
            logger.info(f"📨 Mensagem de {user_phone}: {message[:50]}...")

            # Busca o histórico recente da conversa
            history = await self.get_conversation_history(user_phone, limit=10)
            history.append({"role": "user", "content": message})

            # --- NOVO: verifica se é busca de imóvel ---
            if self._is_property_search(message):
                property_response = await self.process_property_search(message)
                # Se encontrou imóveis, retorna a resposta e salva no Firestore
                if property_response and "não encontrei" not in property_response.lower():
                    db.collection("messages").add({
                        "user_phone": user_phone,
                        "message": property_response,
                        "direction": "sent",
                        "timestamp": datetime.utcnow(),
                        "metadata": {}
                    })
                    logger.info(f"✅ Resposta de imóveis enviada para {user_phone}")
                    return property_response
            # --- FIM NOVO ---

            # Prompt inicial só se for o início da conversa
            if len(history) == 1:
                system_prompt = self._build_prompt("", user_phone)
                history = [{"role": "system", "content": system_prompt}] + history

            response = await self._call_gemini_with_history(history)

            # Salva a resposta do bot no Firestore
            db.collection("messages").add({
                "user_phone": user_phone,
                "message": response,
                "direction": "sent",
                "timestamp": datetime.utcnow(),
                "metadata": {}
            })

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
        """Processa imagem enviada pelo usuário usando Gemini Vision"""
        try:
            logger.info(f"📸 Imagem recebida de {user_phone} - Tamanho: {len(image_data)} bytes")
            
            # Converter imagem para base64
            image_b64 = base64.b64encode(image_data).decode("utf-8")
            
            # Criar prompt para análise de imagem
            prompt = self._build_image_prompt(caption, user_phone)
            
            response = await self._call_gemini_vision(prompt, image_b64)
            
            logger.info(f"✅ Análise de imagem concluída para {user_phone}")
            return response
            
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

    def _build_prompt(self, message: str, user_phone: str) -> str:
        """Constrói o prompt para o Gemini"""
        return (
            "Você é Sofia, assistente virtual da Allega Imóveis, especializada em imóveis de Curitiba e região metropolitana. "
            "Seu papel é responder clientes via WhatsApp de forma cordial, profissional e objetiva, sempre se apresentando como Sofia. "
            "Responda apenas com informações do banco de dados da Allega Imóveis (https://www.allegaimoveis.com). "
            "Se não souber a resposta, ofereça contato com um corretor. "
            "Sempre que falar de um imóvel, envie o link correspondente do site. "
            "Nunca diga que é uma IA, sempre diga que é Sofia. "
            "Use linguagem clara, humana e formal, adequada ao setor imobiliário. "
            "Limite suas respostas a até 200 caracteres, sendo objetiva. "
            "Exemplo: 'Olá, sou Sofia, a assistente virtual da Allega Imóveis! Temos casas no Bigorrilho. Gostaria de agendar uma visita?'\n\n"
            f"Usuário ({user_phone}) enviou: \"{message}\"\n\n"
            "Responda como Sofia, seguindo todas as regras acima."
        )

    def _build_image_prompt(self, caption: str, user_phone: str) -> str:
        """Constrói prompt específico para análise de imagens"""
        return (
            f"Você é a Sofia, assistente virtual da Allega Imóveis. Analise esta imagem de imóvel enviada pelo cliente.\n\n"
            f"INSTRUÇÕES PARA ANÁLISE:\n"
            f"1. Descreva detalhadamente o que você vê na imagem\n"
            f"2. Identifique características do imóvel (tipo, quartos, área, localização se visível)\n"
            f"3. Se for um print de anúncio, extraia todas as informações disponíveis\n"
            f"4. Verifique se temos imóveis similares em nossa base\n"
            f"5. Seja cordial e ofereça ajuda adicional\n\n"
            f"Mensagem do usuário: {caption}\n\n"
            f"Responda como Sofia da Allega Imóveis, sendo profissional e prestativa."
        )

    async def _call_gemini_with_history(self, history: list) -> str:
        """
        Chama o Gemini usando o histórico da conversa.
        """
        try:
            # Constrói o prompt concatenando as mensagens do histórico
            prompt = ""
            for msg in history:
                role = "Usuário" if msg["role"] == "user" else "Sofia"
                prompt += f"{role}: {msg['content']}\n"
            prompt += "Sofia:"

            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Erro ao chamar Gemini: {str(e)}")
            return (
                "😅 Tive dificuldade técnica para responder no momento.\n"
                "Por favor, tente novamente em instantes ou fale com um corretor."
            )

    async def _call_gemini_vision(self, prompt: str, image_b64: str) -> str:
        """
        Chama o Gemini para análise de imagem.
        """
        try:
            image_bytes = base64.b64decode(image_b64)
            response = await asyncio.to_thread(
                self.model.generate_content,
                [prompt, genai.types.content.ImageData(data=image_bytes, mime_type="image/jpeg")]
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Erro ao chamar Gemini Vision: {str(e)}")
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
        Busca imóveis no Firebase Firestore apenas no bairro ou região mencionada pelo usuário.
        """
        try:
            # Extrai o bairro/região após "no", "na", "em", "para", etc.
            match = re.search(r"(?:no|na|em|para|do|da|de)\s+([a-zA-ZÀ-ÿ\s\-]+)", user_query, re.IGNORECASE)
            bairro = match.group(1).strip().title() if match else None

            if not bairro:
                return (
                    "Por favor, informe o bairro ou região desejada para que eu possa buscar imóveis disponíveis."
                )

            properties_ref = db.collection("properties")
            query = properties_ref.where("neighborhood", "==", bairro).limit(5)
            results = [doc.to_dict() for doc in query.stream()]

            if not results:
                return (
                    f"😕 Não encontrei imóveis disponíveis para '{bairro}' agora.\n"
                    "Posso conectar você com um corretor para uma busca personalizada?"
                )

            response = f"🏠 *Imóveis encontrados no bairro {bairro}:*\n\n"
            for prop in results:
                response += (
                    f"• *{prop.get('title', 'Imóvel')}* - {prop.get('price', 'Preço sob consulta')}\n"
                    f"  [Ver detalhes]({prop.get('url', 'https://www.allegaimoveis.com')})\n\n"
                )
            response += "Gostaria de agendar uma visita ou saber mais sobre algum deles?"

            return response
        except Exception as e:
            logger.error(f"Erro ao buscar imóveis no Firebase: {str(e)}")
            return (
                "😅 Tive um problema técnico ao buscar imóveis agora.\n"
                "Por favor, tente novamente em instantes ou fale com um corretor."
            )

    def _is_property_search(self, message: str) -> bool:
        """Verifica se a mensagem é uma busca por imóveis"""
        keywords = [
            "casa", "apartamento", "imóvel", "quartos", "bairro", "comprar", 
            "alugar", "locação", "venda", "preço", "valor", "m²", "garagem",
            "sala", "cozinha", "banheiro", "área", "terreno", "condomínio",
            "studio", "kitnet", "cobertura", "sobrado", "comercial"
        ]
        return any(kw in message.lower() for kw in keywords)



# Instância global do bot
intelligent_bot = IntelligentRealEstateBot()