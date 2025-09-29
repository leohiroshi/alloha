"""
Integração Principal do Sistema de Inteligência Imobiliária
Coordena IA, extração de dados e resposta inteligente com análise de imagens
"""

import asyncio
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp
import tempfile
import base64
import json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from app.services.rag_pipeline import rag
from app.services.property_intelligence import property_intelligence

from app.services.whatsapp_service import WhatsAppService  # assume exists in workspace
from app.services.firebase_service import firebase_service

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
        # Whatsapp service será instanciado sob demanda
        self.whatsapp_service = None
        # flags controláveis via env para evitar 400s da Cloud API
        self.whatsapp_supports_typing = False
        self.whatsapp_supports_presence = False
        logger.info("Bot de Inteligência Imobiliária iniciado")

    async def get_conversation_history(self, user_phone, limit=10) -> List[Dict[str, str]]:
        """Delega ao FirebaseService para obter histórico de conversa (async)."""
        try:
            return await firebase_service.get_conversation_history(user_phone, limit)
        except Exception as e:
            logger.debug(f"Falha ao obter histórico via FirebaseService: {e}")
            return []

    async def process_message(self, message: str, user_phone: str) -> str:
        """
        Processa mensagem do usuário.
        Não cria placeholder "digitando..." no Firestore. Em vez disso:
         - salva a mensagem recebida;
         - inicia um background task que periodicamente envia typing indicator via WhatsApp;
         - gera a resposta em background e envia a mensagem final.
        """
        try:
            logger.info(f"📨 Mensagem de {user_phone}: {message[:100]}")

            # 1) Salva mensagem recebida (received)
            await asyncio.to_thread(db.collection("messages").add, {
                "user_phone": user_phone,
                "message": message,
                "direction": "received",
                "timestamp": datetime.utcnow(),
                "metadata": {}
            })
            logger.info(f"Mensagem salva no Firestore para {user_phone}.")

            if self.whatsapp_service is None:
                token = os.getenv("WHATSAPP_ACCESS_TOKEN")
                phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
                if token and phone_id:
                    self.whatsapp_service = WhatsAppService(token, phone_id)
                else:
                    logger.error("WhatsAppService não configurado corretamente.")
                    return "Erro interno: serviço indisponível."

            # 4) Recupera histórico rápido (menor limite para agilizar)
            history = await self.get_conversation_history(user_phone, limit=6)

            # 5) Se for busca por imóvel, dispare tarefa específica de busca+envio.
            #    Assim garantimos que process_property_search seja chamado.
            if self._is_property_search(message):
                logger.info("Mensagem identificada como busca de imóvel — iniciando fluxo de property_search em background.")
                asyncio.create_task(self._process_property_search_and_send(message, user_phone, history))
            else:
                # Dispara geração/atualização em background (fluxo genérico)
                asyncio.create_task(self._generate_and_send_response(
                    message, user_phone, history
                ))

             # 6) Retorna rápido para caller — sem placeholder criado no Firestore
            return ""
        except Exception as e:
            logger.exception(f"Erro ao processar mensagem (inicial): {e}")
            return "Desculpe, ocorreu um erro. Tente novamente mais tarde."

    async def _generate_and_send_response(self, message: str, user_phone: str, history: List[Dict[str, str]]):
        """Gera a resposta, pára o typing loop e envia a mensagem final (sem placeholder)."""
        try:
            logger.info(f"Iniciando geração de resposta para {user_phone}...")
            # Normalizar histórico: aceitar formatos {role, content} ou {direction, message} ou firestore doc shape
            def _normalize_history(raw_history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
                normalized = []
                for h in raw_history or []:
                    try:
                        if isinstance(h, dict):
                            if "role" in h and "content" in h:
                                normalized.append({"role": h["role"], "content": h["content"]})
                                continue
                            # Firestore saved message shape
                            if "direction" in h and "message" in h:
                                role = "user" if h.get("direction") == "received" else "assistant"
                                normalized.append({"role": role, "content": h.get("message", "")})
                                continue
                            # Alternative firestore doc shape used in firebase_service: keys id, message, direction
                            if "message" in h and "direction" in h:
                                role = "user" if h.get("direction") == "received" else "assistant"
                                normalized.append({"role": role, "content": h.get("message", "")})
                                continue
                            # If payload is nested (ex: webhook message)
                            if "text" in h and isinstance(h["text"], dict) and "body" in h["text"]:
                                normalized.append({"role": "user", "content": h["text"]["body"]})
                                continue
                        # Fallback: stringify
                        normalized.append({"role": "user", "content": str(h)})
                    except Exception:
                        # ignore malformed entries
                        continue
                return normalized

            logger.info(f"Gerando resposta para {user_phone}...")
            prompt = self._build_prompt(message, user_phone)
            normalized_history = _normalize_history(history)
            short_history = normalized_history + [{"role": "user", "content": message}]
            prompt_with_history = prompt + "\n\nHISTORY:\n" + "\n".join([f"{h['role']}: {h['content']}" for h in short_history])

            model = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:sofia:CKv6isOD")
            response_text = await asyncio.to_thread(rag.call_gpt, prompt_with_history, model)

            if not response_text:
                response_text = "Desculpe, não consegui gerar uma resposta no momento."

            # Persistir a mensagem final como "sent" no Firestore
            try:
                await asyncio.to_thread(db.collection("messages").add, {
                    "user_phone": user_phone,
                    "message": response_text,
                    "direction": "sent",
                    "timestamp": datetime.utcnow(),
                    "metadata": {"ai": True}
                })
            except Exception:
                logger.exception("Falha ao persistir mensagem enviada no Firestore.")

            # Envia a mensagem final via WhatsApp (se configurado)
            if getattr(self, "whatsapp_service", None):
                try:
                    ok = await self.whatsapp_service.send_message(user_phone, response_text)
                    if not ok:
                        logger.warning("Envio via WhatsAppService não confirmou sucesso; verifique logs.")
                except Exception:
                    logger.exception("Erro ao enviar mensagem via WhatsAppService.")
            else:
                logger.debug("WhatsAppService não está configurado; mensagem persistida apenas no Firestore.")

        except Exception as e:
            logger.exception(f"Erro ao gerar/enviar resposta: {e}")
            try:
                await asyncio.to_thread(db.collection("messages").add, {
                    "user_phone": user_phone,
                    "message": "Desculpe, ocorreu um erro ao gerar a resposta.",
                    "direction": "sent",
                    "timestamp": datetime.utcnow(),
                    "metadata": {"ai": True, "error": True}
                })
            except Exception:
                logger.debug("Falha ao persistir mensagem de erro.")

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

            model = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:sofia:CKv6isOD")
            response_text = await asyncio.to_thread(rag.call_gpt, prompt, model)
            return response_text.strip() if response_text else (
                "😅 Tive dificuldade técnica para responder no momento. Por favor, tente novamente em instantes."
            )
        except Exception as e:
            logger.exception(f"Erro ao chamar Sofia: {str(e)}")
            return "😅 Tive dificuldade técnica para responder no momento. Por favor, tente novamente em instantes."

    async def _extract_profile_with_gpt(self, message: str, user_phone: str, history: List[Dict[str,str]]) -> dict:
        """Chama LLM para extrair um JSON com campos de perfil/requisitos do usuário."""
        try:
            system = (
                "Você é um assistente que extrai informações estruturadas de mensagens de clientes. "
                "Retorne apenas um JSON válido com campos opcionais: name, email, phone, transaction_type, "
                "budget_min, budget_max, preferred_neighborhoods (lista), bedrooms (int), contact_time (string)."
            )
            example = {
                "name": "Maria Silva",
                "email": "maria@example.com",
                "phone": user_phone,
                "transaction_type": "locacao",
                "budget_min": None,
                "budget_max": 2000,
                "preferred_neighborhoods": ["Água Verde"],
                "bedrooms": 2,
                "contact_time": "tarde"
            }
            prompt = (
                f"{system}\n\nCONTEXT HISTORY:\n"
                + "\n".join([f"{h['role']}: {h['content']}" for h in history])
                + f"\n\nMESSAGE:\n{message}\n\nReturn JSON example:\n{json.dumps(example, ensure_ascii=False)}\n\nJSON:"
            )
            model = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:sofia:CKv6isOD")
            resp = await asyncio.to_thread(rag.call_gpt, prompt, model)
            if not resp:
                return {}
            # tentar extrair JSON bruto do texto
            start = resp.find("{")
            end = resp.rfind("}") + 1
            json_text = resp[start:end] if start != -1 and end != -1 else resp
            data = json.loads(json_text)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.debug(f"Falha extrair perfil: {e}")
            return {}

    async def _upsert_user_profile(self, user_phone: str, profile: dict):
        """Atualiza/insere documento do usuário com os dados extraídos."""
        try:
            if not profile:
                return
            doc_ref = db.collection("users").document(user_phone)
            # normalize basic keys
            to_save = {}
            for k in ["name", "email", "phone", "transaction_type", "budget_min", "budget_max", "preferred_neighborhoods", "bedrooms", "contact_time"]:
                if k in profile and profile[k] not in (None, "", []):
                    to_save[k] = profile[k]
            to_save["last_seen"] = datetime.utcnow()
            doc_ref.set(to_save, merge=True)
            logger.info(f"Perfil atualizado para {user_phone}: {list(to_save.keys())}")
        except Exception as e:
            logger.debug(f"Erro upsert user profile: {e}")

    async def _save_property_search(self, user_phone: str, query: str, criteria: dict):
        """Salva histórico de buscas do usuário em property_searches."""
        try:
            coll = db.collection("property_searches")
            doc = {
                "user_phone": user_phone,
                "query": query,
                "criteria": criteria or {},
                "timestamp": datetime.utcnow()
            }
            coll.add(doc)
            logger.info(f"Property search saved for {user_phone}")
        except Exception as e:
            logger.debug(f"Erro salvar property_search: {e}")

    async def process_property_search(self, user_query: str) -> str:
        """
        Busca imóveis usando RAG local (retrieve + prompt grounding + call_gpt).
        Garante que somente strings normalizadas são incluídas no prompt (evita repr() de objetos).
        """
        try:
            # 1) recuperar localmente (await!)
            retrieved = await rag.retrieve(user_query, top_k=8, filters={})
            hits = retrieved or []
            logger.info("RAG retrieved %d documents for query: %s", len(hits), user_query)

            # 2) Normalizar retrieved para texto + metadados (garante que build_prompt receba conteúdo útil)
            normalized_hits = []
            for idx, r in enumerate(hits):
                meta = {}
                text = ""
                rid = None
                # dicionário retornado pelo indexer
                if isinstance(r, dict):
                    meta = r.get("meta") or r.get("metadata") or r.get("meta_data") or {}
                    # garantir pegar campos de texto conhecidos
                    text = (r.get("text") or r.get("content") or r.get("snippet") or "").strip()
                    rid = r.get("id") or r.get("doc_id") or meta.get("id")
                else:
                    # objetos com atributos (fallback)
                    try:
                        meta = getattr(r, "meta", {}) or getattr(r, "metadata", {}) or {}
                        text = (getattr(r, "text", None) or getattr(r, "content", None) or "")
                        rid = getattr(r, "id", None)
                    except Exception:
                        text = str(r)

                normalized_hits.append({
                    "id": rid or f"unknown_{idx}",
                    "text": (text or "")[:1200],
                    "meta": meta
                })

            # 3) construir prompt explícito incluindo top results para grounding (evita usar raw retrieved)
            top_n = self.bot_config.get("max_properties_per_response", 3)
            prompt_parts = [
                "Você é Sofia, assistente virtual da Allega Imóveis em Curitiba. Use os documentos abaixo para responder objetivamente.",
                f"Consulta do usuário: {user_query}",
                "Documentos relevantes (use esses dados para listar imóveis e incluir URLs/imagens quando existirem):"
            ]
            for i, h in enumerate(normalized_hits[:top_n]):
                m = h.get("meta", {}) or {}
                prompt_parts.append(
                    f"DOCUMENT {i+1} - id:{h.get('id')} | snippet: {h.get('text')[:300]} | neighborhood: {m.get('neighborhood') or m.get('bairro') or 'n/a'} | price: {m.get('price') or m.get('valor') or 'n/a'} | url: {m.get('url') or ''} | image: {m.get('main_image') or m.get('image') or ''}"
                )
            prompt_parts.append(
                "Instruções: 1) Resuma e proponha até 3 opções mostrando título/snippet, bairro, preço (se disponível) e link quando houver. 2) Seja objetivo, cordial e proponha próximos passos (visita/contato). 3) Se não houver resultados relevantes, diga claramente que não encontrou."
            )
            prompt = "\n\n".join(prompt_parts)
            logger.debug("RAG prompt (truncated): %s", (prompt or "")[:3000])

            # 4) chamar LLM (síncrono via thread) passando apenas a string do prompt
            model = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:sofia:CKv6isOD")
            answer = await asyncio.to_thread(rag.call_gpt, prompt, model)

            # 5) montar lista de candidates para resposta e CTA (use normalized_hits)
            candidates = []
            for h in normalized_hits:
                m = h.get("meta") or {}
                candidates.append({
                    "id": h.get("id"),
                    "preview": (h.get("text") or "")[:140],
                    "url": m.get("url"),
                    "image": m.get("main_image") or m.get("image"),
                    "neighborhood": m.get("neighborhood") or m.get("bairro"),
                    "price": m.get("price") or m.get("valor")
                })

            if not answer:
                answer = "Desculpe, não encontrei imóveis com essas características."

            if candidates:
                answer += "\n\nImóveis encontrados:\n"
                for c in candidates[:top_n]:
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
            model = model_name or os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:sofia:CKv6isOD")
            full_prompt = prompt + "\n\n---BEGIN_IMAGE_BASE64---\n" + image_base64 + "\n---END_IMAGE_BASE64---\n\n"
            full_prompt += "Resuma em até 300 caracteres e destaque campos relevantes."
            resp = await asyncio.to_thread(rag.call_gpt, full_prompt, model)
            return resp or "📸 Não consegui analisar a imagem agora."
        except Exception as e:
            logger.exception(f"Erro visão Sofia (OpenAI): {e}")
            return "📸 Não foi possível analisar a imagem agora. Tente novamente mais tarde."

    async def _save_attachment(self, owner_phone: str, storage_url: str, content_type: str, size: int, message_id: str = None, meta: dict = None):
        """Salvar metadados de attachments no Firestore (executa em thread)."""
        try:
            doc = {
                "attachment_id": storage_url.split("/")[-1],
                "owner_phone": owner_phone,
                "storage_url": storage_url,
                "content_type": content_type,
                "size": size,
                "message_id": message_id,
                "meta": meta or {},
                "uploaded_at": datetime.utcnow()
            }
            await asyncio.to_thread(db.collection("attachments").document(doc["attachment_id"]).set, doc)
            logger.info(f"Attachment salvo: {doc['attachment_id']}")
        except Exception as e:
            logger.debug(f"Erro salvar attachment: {e}")

    async def _save_audit(self, action: str, actor: str = "system", details: dict | None = None):
        """Registra auditoria de ações críticas."""
        try:
            doc = {
                "action": action,
                "actor": actor,
                "timestamp": datetime.utcnow(),
                "details": details or {}
            }
            await asyncio.to_thread(db.collection("audits").add, doc)
            logger.info(f"Audit registrado: {action}")
        except Exception as e:
            logger.debug(f"Erro salvar audit: {e}")

    async def _save_embedding_meta(self, doc_id: str, vector_id: str, model: str, meta: dict | None = None):
        """Salva metadados de embeddings (vetores são guardados no vector DB)."""
        try:
            doc = {
                "doc_id": doc_id,
                "vector_id": vector_id,
                "model": model,
                "meta": meta or {},
                "created_at": datetime.utcnow()
            }
            await asyncio.to_thread(db.collection("embeddings").document(vector_id).set, doc)
            logger.info(f"Embedding meta salvo: {vector_id}")
        except Exception as e:
            logger.debug(f"Erro salvar embedding meta: {e}")

    async def _process_property_search_and_send(self, user_query: str, user_phone: str, history: List[Dict[str, str]]):
        """Wrapper: executa process_property_search e envia resultado+persiste via WhatsApp."""
        try:
            logger.info("Iniciando fluxo de property_search para %s: %s", user_phone, user_query[:120])
            answer = await self.process_property_search(user_query)
            if not answer:
                answer = "Desculpe, não encontrei imóveis com essas características no momento."
            # Persistir mensagem enviada
            try:
                await asyncio.to_thread(db.collection("messages").add, {
                    "user_phone": user_phone,
                    "message": answer,
                    "direction": "sent",
                    "timestamp": datetime.utcnow(),
                    "metadata": {"ai": True, "flow": "property_search"}
                })
            except Exception:
                logger.exception("Falha ao persistir mensagem de property_search no Firestore.")
            # Enviar via WhatsApp se disponível
            if getattr(self, "whatsapp_service", None):
                try:
                    ok = await self.whatsapp_service.send_message(user_phone, answer)
                    if not ok:
                        logger.warning("Envio de property_search via WhatsAppService não confirmou sucesso; verifique logs.")
                except Exception:
                    logger.exception("Erro ao enviar property_search via WhatsAppService.")
            else:
                logger.debug("WhatsAppService não configurado; property_search apenas persistido no Firestore.")
        except Exception as e:
            logger.exception("Erro no fluxo property_search: %s", e)


# Instância global do bot
intelligent_bot = IntelligentRealEstateBot()