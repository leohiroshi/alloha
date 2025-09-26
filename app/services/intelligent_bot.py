"""
Integração Principal do Sistema de Inteligência Imobiliária
Coordena IA, extração de dados e resposta inteligente com análise de imagens
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp
import os
import tempfile
import base64
import json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from rag_pipeline import call_gpt, retrieve, build_prompt

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

    if firebase_cred_path:
        cred = credentials.Certificate(firebase_cred_path)
        firebase_admin.initialize_app(cred)
db = firestore.client()

# RAG endpoint (HTTP fallback, se necessário)
RAG_ENDPOINT = os.getenv("RAG_ENDPOINT", "http://localhost:8000/query")

class IntelligentRealEstateBot:
    """Bot inteligente especializado em imóveis"""

    def __init__(self):
        self.bot_config = {
            'company_name': 'Allega Imóveis',
            'response_style': 'friendly_professional',
            'enable_property_search': True,
            'enable_market_insights': True,
            'enable_image_analysis': True,
            'max_properties_per_response': 3
        }
        logger.info("Bot de Inteligência Imobiliária iniciado")

    async def get_conversation_history(self, user_phone, limit=10) -> List[Dict[str, str]]:
        """
        Busca as últimas mensagens do usuário e do bot no Firestore para manter o contexto da conversa.
        """
        messages_ref = db.collection("messages")
        query = messages_ref.where("user_phone", "==", user_phone).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit)
        docs = query.stream()
        history = []
        for d in docs:
            rec = d.to_dict()
            role = "user" if rec.get("direction") == "received" else "assistant"
            history.append({"role": role, "content": rec.get("message", "")})
        return list(reversed(history))

    async def process_message(self, message: str, user_phone: str) -> str:
        """
        Processa mensagem do usuário, usando RAG + GPT para buscas de imóvel e GPT para conversas gerais.
        """
        try:
            logger.info(f"📨 Mensagem de {user_phone}: {message[:100]}")
            history = await self.get_conversation_history(user_phone, limit=10)

            # Detecta busca de imóvel
            if self._is_property_search(message) and self.bot_config.get("enable_property_search", True):
                property_response = await self.process_property_search(message)
                # salva resposta no Firestore
                db.collection("messages").add({
                    "user_phone": user_phone,
                    "message": property_response,
                    "direction": "sent",
                    "timestamp": datetime.utcnow(),
                    "metadata": {}
                })
                return property_response

            # Para conversas gerais, usa GPT (via call_gpt)
            prompt = self._build_prompt(message, user_phone)
            full_history = [{"role": h["role"], "content": h["content"]} for h in history] + [{"role":"user","content":message}]
            prompt_with_history = prompt + "\n\nHISTORY:\n" + "\n".join([f"{h['role']}: {h['content']}" for h in full_history])

            model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
            resp = await asyncio.to_thread(call_gpt, prompt_with_history, model)
            db.collection("messages").add({
                "user_phone": user_phone,
                "message": resp,
                "direction": "sent",
                "timestamp": datetime.utcnow(),
                "metadata": {}
            })
            return resp
        except Exception as e:
            logger.exception(f"Erro ao processar mensagem: {e}")
            return "Desculpe, ocorreu um erro. Tente novamente mais tarde."

    async def process_image_message(self, image_data: bytes, caption: str, user_phone: str) -> str:
        try:
            logger.info(f"📸 Imagem recebida de {user_phone} - Tamanho: {len(image_data)} bytes")
            image_b64 = base64.b64encode(image_data).decode("utf-8")
            prompt = self._build_image_prompt(caption, user_phone)
            response = await self._call_sofia_vision(prompt, image_b64)
            logger.info(f"✅ Análise de imagem concluída para {user_phone}")
            return response
        except Exception as e:
            logger.exception(f"❌ Erro ao processar imagem: {str(e)}")
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
        system = (
            "Você é Sofia, assistente virtual da Allega Imóveis.\n"
            "Responda de forma concisa, inclua URL e imagem quando disponíveis e ofereça próximos passos.\n"
        )
        return system + f"\nUsuário ({user_phone}): {message}\n"

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

    async def _call_sofia_with_history(self, history: List[Dict[str, str]]) -> str:
        """
        Constrói prompt a partir do histórico e chama o GPT (call_gpt) de forma segura.
        """
        try:
            prompt = ""
            for msg in history:
                role = "Usuário" if msg["role"] == "user" else "Sofia"
                prompt += f"{role}: {msg['content']}\n"
            prompt += "Sofia:"

            model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
            response_text = await asyncio.to_thread(call_gpt, prompt, model)
            return response_text.strip() if response_text else (
                "😅 Tive dificuldade técnica para responder no momento. Por favor, tente novamente em instantes."
            )
        except Exception as e:
            logger.exception(f"Erro ao chamar Sofia: {str(e)}")
            return "😅 Tive dificuldade técnica para responder no momento. Por favor, tente novamente em instantes."

    async def process_property_search(self, user_query: str) -> str:
        """
        Busca imóveis usando RAG local (retrieve + build_prompt + call_gpt).
        Fallback: se retrieve/local falhar, tenta chamar RAG_ENDPOINT HTTP.
        """
        try:
            # 1) recuperar localmente
            retrieved = retrieve(user_query, top_k=5, filters={})
            prompt = build_prompt(user_query, retrieved)
            model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
            answer = await asyncio.to_thread(call_gpt, prompt, model)

            # construir candidates para exibição
            candidates = []
            for r in retrieved:
                m = r.get("meta", {})
                candidates.append({
                    "id": r.get("id"),
                    "preview": (r.get("text","")[:120]),
                    "url": m.get("url"),
                    "image": m.get("main_image") or m.get("image"),
                    "neighborhood": m.get("neighborhood"),
                    "price": m.get("price")
                })

            if not answer:
                answer = "Desculpe, não encontrei imóveis com essas características."

            if candidates:
                answer += "\n\nImóveis encontrados:\n"
                for c in candidates[: self.bot_config.get("max_properties_per_response", 3)]:
                    answer += f"🏠 {c.get('preview','Imóvel')}\n"
                    if c.get("url"):
                        answer += f"🔗 {c['url']}\n"
                    if c.get("image"):
                        answer += f"🖼️ {c['image']}\n"
                    answer += "\n"
            return answer
        except Exception as e:
            logger.exception(f"Erro RAG local: {e}")

            # fallback para RAG HTTP endpoint se disponível
            try:
                payload = {"question": user_query, "filters": {}}
                async with aiohttp.ClientSession() as session:
                    async with session.post(RAG_ENDPOINT, json=payload, timeout=30) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            answer = data.get("answer", "Desculpe, não encontrei imóveis com essas características.")
                            candidates = data.get("candidates", [])
                            if candidates:
                                answer += "\n\nImóveis encontrados:\n"
                                for c in candidates[: self.bot_config.get("max_properties_per_response", 3)]:
                                    answer += f"🏠 {c.get('preview','Imóvel')[:120]}\n"
                                    if c.get("url"):
                                        answer += f"🔗 {c['url']}\n"
                                    if c.get("image"):
                                        answer += f"🖼️ {c['image']}\n"
                                    answer += "\n"
                            return answer
                        else:
                            logger.error(f"RAG endpoint returned {resp.status}")
            except Exception as e2:
                logger.exception(f"Fallback RAG HTTP failed: {e2}")

            return "Erro técnico buscando imóveis. Tente novamente mais tarde."

    def _is_property_search(self, message: str) -> bool:
        # heurística simples; pode ser substituída por NLU
        keywords = ["procuro", "buscar", "apartamento", "quarto", "aluguel", "venda", "quartos", "vaga", "área", "bairro"]
        text = message.lower()
        return any(k in text for k in keywords)

    async def _call_sofia_vision(self, prompt: str, image_base64: str, model_name: Optional[str] = None) -> str:
        """Envio de prompt + imagem (base64) para o GPT via call_gpt (executa em thread)."""
        try:
            model = model_name or os.getenv("OPENAI_MODEL", "gpt-5-mini")
            full_prompt = prompt + "\n\n---BEGIN_IMAGE_BASE64---\n" + image_base64 + "\n---END_IMAGE_BASE64---\n\n"
            full_prompt += "Resuma em até 300 caracteres e destaque campos relevantes."
            resp = await asyncio.to_thread(call_gpt, full_prompt, model)
            return resp or "📸 Não consegui analisar a imagem agora."
        except Exception as e:
            logger.exception(f"Erro visão Sofia (OpenAI): {e}")
            return "📸 Não foi possível analisar a imagem agora. Tente novamente mais tarde."

# Instância global do bot
intelligent_bot = IntelligentRealEstateBot()