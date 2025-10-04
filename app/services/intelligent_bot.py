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

from app.services.rag_pipeline import rag
from app.services.property_intelligence import property_intelligence
from app.services.embedding_cache import embedding_cache
from app.models.conversation_state import conversation_manager, ConversationState
from app.services.webhook_idempotency import webhook_idempotency
from app.services.whatsapp_service import WhatsAppService
from app.services.supabase_client import supabase_client

load_dotenv()

logger = logging.getLogger("IntelligentRealEstateBot")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

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
        # Flag para evitar spam de warnings de funcionalidades ainda não migradas
        self._embedding_meta_warning_emitted = False
        logger.info("Bot de Inteligência Imobiliária iniciado")

    async def get_conversation_history(self, user_phone, limit=10) -> List[Dict[str, str]]:
        """Busca histórico de conversa usando Supabase."""
        try:
            conversation = await asyncio.to_thread(
                supabase_client.get_or_create_conversation,
                user_phone
            )
            
            messages = await asyncio.to_thread(
                supabase_client.get_conversation_messages,
                conversation['id'],
                limit
            )
            
            # Converter para formato esperado
            history = []
            for msg in reversed(messages):  # Ordem cronológica
                history.append({
                    "direction": msg["direction"],
                    "message": msg["content"],
                    "timestamp": msg["created_at"]
                })
            
            return history
        except Exception as e:
            logger.debug(f"Falha ao obter histórico via Supabase: {e}")
            return []

    async def process_message(self, message: str, user_phone: str) -> str:
        """
        Processa mensagem com otimizações de escala:
        - State machine para evitar race conditions
        - Cache de embeddings para reduzir latência
        - Processamento thread-safe
        """
        try:
            logger.info(f"📨 Mensagem de {user_phone}: {message[:100]}")

            # 1) Gerenciar estado da conversa (thread-safe)
            conversation = await conversation_manager.get_or_create_conversation(user_phone)
            current_state = conversation["state"]
            
            # 2) Verificar se já está processando para evitar duplicação
            if current_state == ConversationState.PENDING:
                await conversation_manager.transition_state(
                    user_phone, 
                    ConversationState.PENDING,
                    {"processing": True, "last_message": message}
                )

            # 3) Salva mensagem recebida (received) no Supabase
            conversation = await asyncio.to_thread(
                supabase_client.get_or_create_conversation,
                user_phone
            )
            await asyncio.to_thread(
                supabase_client.save_message,
                conversation['id'],
                'received',
                message,
                'text',
                None,
                {"conversation_state": current_state.value}
            )
            logger.info(f"Mensagem salva no Supabase para {user_phone}.")

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
            if await self._is_property_search(message):
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
                            if "direction" in h and "message" in h:
                                role = "user" if h.get("direction") == "received" else "assistant"
                                normalized.append({"role": role, "content": h.get("message", "")})
                                continue
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

            model = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:alloha-sofia-v1:CMFHyUpi")
            response_text = await asyncio.to_thread(rag.call_gpt, prompt_with_history, model)

            if not response_text:
                response_text = "Desculpe, não consegui gerar uma resposta no momento."

            # Persistir a mensagem final como "sent" no Supabase
            try:
                conversation = await asyncio.to_thread(
                    supabase_client.get_or_create_conversation,
                    user_phone
                )
                await asyncio.to_thread(
                    supabase_client.save_message,
                    conversation['id'],
                    'sent',
                    response_text,
                    'text',
                    None,
                    {"ai": True}
                )
            except Exception:
                logger.exception("Falha ao persistir mensagem enviada no Supabase.")

            # Envia a mensagem final via WhatsApp (se configurado)
            if getattr(self, "whatsapp_service", None):
                try:
                    ok = await self.whatsapp_service.send_message(user_phone, response_text)
                    if not ok:
                        logger.warning("Envio via WhatsAppService não confirmou sucesso; verifique logs.")
                except Exception:
                    logger.exception("Erro ao enviar mensagem via WhatsAppService.")
            else:
                logger.debug("WhatsAppService não está configurado; mensagem persistida apenas no Supabase.")

        except Exception as e:
            logger.exception(f"Erro ao gerar/enviar resposta: {e}")
            try:
                conversation = await asyncio.to_thread(
                    supabase_client.get_or_create_conversation,
                    user_phone
                )
                await asyncio.to_thread(
                    supabase_client.save_message,
                    conversation['id'],
                    'sent',
                    "Desculpe, ocorreu um erro ao gerar a resposta.",
                    'text',
                    None,
                    {"ai": True, "error": True}
                )
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
        user_display = user_phone
        try:
            # Buscar profile agregado (conversa + lead) e extrair nome
            profile = supabase_client.get_user_profile(user_phone)
            if profile and profile.get('conversation'):
                raw_name = profile['conversation'].get('user_name')
                if raw_name:
                    # pegar primeiro nome limpo
                    first = raw_name.strip().split()[0]
                    if 2 <= len(first) <= 25:
                        user_display = first
        except Exception:
            pass
        return system + f"\nUsuário ({user_display}): {message}\n"

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

            model = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:alloha-sofia-v1:CMFHyUpi")
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
            model = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:alloha-sofia-v1:CMFHyUpi")
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
        """
        Atualiza/insere documento do usuário com os dados extraídos.
        TODO: Migrar para Supabase (tabela user_profiles)
        """
        try:
            logger.warning("⚠️ _upsert_user_profile ainda não migrado para Supabase - funcionalidade desabilitada temporariamente")
            return
            # TODO: Implementar usando supabase_client
            # if not profile:
            #     return
            # ...
        except Exception as e:
            logger.debug(f"Erro upsert user profile: {e}")

    async def _save_property_search(self, user_phone: str, query: str, criteria: dict):
        """
        Salva histórico de buscas do usuário em property_searches.
        TODO: Migrar para Supabase (tabela property_searches)
        """
        try:
            logger.warning("⚠️ _save_property_search ainda não migrado para Supabase - funcionalidade desabilitada temporariamente")
            return
            # TODO: Implementar usando supabase_client
            # ...
        except Exception as e:
            logger.debug(f"Erro salvar property_search: {e}")

    async def process_property_search(self, user_query: str, phone_number: Optional[str] = None) -> tuple[str, list]:
        """
        Busca imóveis usando RAG local com resposta mais natural e session cache.
        Retorna: (resposta_texto, lista_de_imoveis_estruturados)
        """
        try:
            # 1) Buscar documentos relevantes (com cache filtering)
            retrieved_docs = await self._retrieve_property_documents(user_query, phone_number=phone_number)
            if not retrieved_docs:
                return self._handle_no_results(), []

            # 2) Processar e estruturar dados
            normalized_hits, structured_properties = self._process_retrieved_documents(retrieved_docs)
            
            # 3) Gerar resposta natural via LLM
            response_text = await self._generate_natural_response(user_query, normalized_hits)
            
            return response_text, structured_properties

        except Exception as e:
            logger.exception(f"Erro na busca de imóveis: {e}")
            return "Desculpe, ocorreu um erro técnico. Tente novamente em alguns instantes.", []


    async def _retrieve_property_documents(self, user_query: str, phone_number: Optional[str] = None) -> list:
        """Busca documentos no RAG local com session cache"""
        # Gerar phone_hash se phone_number fornecido
        phone_hash = None
        if phone_number:
            import hashlib
            phone_hash = hashlib.md5(phone_number.encode()).hexdigest()
        
        retrieved = await rag.retrieve(user_query, top_k=8, filters={}, phone_hash=phone_hash)
        hits = retrieved or []
        logger.info("RAG encontrou %d documentos para: %s", len(hits), user_query[:100])
        return hits


    def _process_retrieved_documents(self, hits: list) -> tuple[list, list]:
        """
        Processa documentos brutos e retorna dados normalizados + estruturados
        """
        normalized_hits = []
        structured_properties = []
        
        for idx, doc in enumerate(hits):
            # Extrair dados do documento
            doc_data = self._extract_document_data(doc, idx)
            normalized_hits.append(doc_data)
            
            # Se tem URL válida, adicionar à lista estruturada
            if self._is_valid_property_url(doc_data["meta"].get("url")):
                structured_property = self._create_structured_property(doc_data, idx)
                structured_properties.append(structured_property)
        
        return normalized_hits, structured_properties


    def _extract_document_data(self, doc, idx: int) -> dict:
        """Extrai dados de um documento individual"""
        meta = {}
        text = ""
        doc_id = None
        
        if isinstance(doc, dict):
            meta = doc.get("meta") or doc.get("metadata") or doc.get("meta_data") or {}
            text = (doc.get("text") or doc.get("content") or doc.get("snippet") or "").strip()
            doc_id = doc.get("id") or doc.get("doc_id") or meta.get("id")
        else:
            try:
                meta = getattr(doc, "meta", {}) or getattr(doc, "metadata", {}) or {}
                text = (getattr(doc, "text", None) or getattr(doc, "content", None) or "")
                doc_id = getattr(doc, "id", None)
            except Exception:
                text = str(doc)
        
        return {
            "id": doc_id or f"doc_{idx}",
            "text": (text or "")[:1200],
            "meta": meta
        }


    def _is_valid_property_url(self, url: str) -> bool:
        """Verifica se a URL é válida"""
        return url and isinstance(url, str) and url.startswith("http")


    def _create_structured_property(self, doc_data: dict, idx: int) -> dict:
        """Cria estrutura de propriedade para CTA"""
        meta = doc_data["meta"]
        text = doc_data["text"]
        
        return {
            "id": doc_data["id"],
            "title": self._extract_title_from_text(text) or f"Imóvel em {meta.get('neighborhood', 'Curitiba')}",
            "description": text[:200],
            "url": meta.get("url"),
            "main_image": meta.get("main_image") or meta.get("image"),
            "neighborhood": meta.get("neighborhood") or meta.get("bairro"),
            "price": meta.get("price") or meta.get("valor"),
            "bedrooms": meta.get("bedrooms") or meta.get("quartos")
        }


    async def _generate_natural_response(self, user_query: str, normalized_hits: list) -> str:
        """Gera resposta natural usando LLM"""
        if not normalized_hits:
            return self._handle_no_results()
        
        # Construir contexto para o LLM
        context = self._build_llm_context(user_query, normalized_hits)
        
        # Chamar LLM
        model = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:alloha-sofia-v1:CMFHyUpi")
        response = await asyncio.to_thread(rag.call_gpt, context, model)
        
        return response or self._handle_no_results()


    def _build_llm_context(self, user_query: str, normalized_hits: list) -> str:
        """Constrói contexto mais natural para o LLM"""
        max_properties = self.bot_config.get("max_properties_per_response", 3)
        
        context_parts = [
            "Você é Sofia, consultora imobiliária da Allega Imóveis em Curitiba.",
            "Responda de forma natural e conversacional, como se estivesse falando pessoalmente com o cliente.",
            f"Pergunta do cliente: {user_query}",
            "",
            "Imóveis disponíveis que podem interessar:"
        ]
        
        # Adicionar informações dos imóveis de forma mais natural
        for i, hit in enumerate(normalized_hits[:max_properties]):
            meta = hit.get("meta", {})
            property_info = self._format_property_info(hit, i + 1)
            context_parts.append(property_info)
        
        context_parts.extend([
            "",
            "Instruções para sua resposta:",
            "- Seja natural e conversacional, não robotizada",
            "- Destaque os pontos mais relevantes para o que o cliente pediu",
            "- Se houver links ou imagens, inclua-os naturalmente na conversa",
            "- Ofereça ajuda adicional (visita, mais opções, contato direto)",
            "- Se não encontrar nada adequado, seja honesta e ofereça alternativas",
            "- Mantenha o tom amigável e profissional da Sofia"
        ])
        
        return "\n".join(context_parts)


    def _format_property_info(self, hit: dict, number: int) -> str:
        """Formata informações de um imóvel para o contexto do LLM"""
        meta = hit.get("meta", {})
        text = hit.get("text", "")
        
        info_parts = [f"Opção {number}:"]
        info_parts.append(f"Descrição: {text[:300]}")
        
        if meta.get("neighborhood") or meta.get("bairro"):
            neighborhood = meta.get("neighborhood") or meta.get("bairro")
            info_parts.append(f"Bairro: {neighborhood}")
        
        if meta.get("price") or meta.get("valor"):
            price = meta.get("price") or meta.get("valor")
            info_parts.append(f"Preço: {price}")
        
        if meta.get("url"):
            info_parts.append(f"Link: {meta.get('url')}")
        
        if meta.get("main_image") or meta.get("image"):
            image = meta.get("main_image") or meta.get("image")
            info_parts.append(f"Imagem: {image}")
        
        return " | ".join(info_parts)


    def _handle_no_results(self) -> str:
        """Resposta quando não encontra imóveis"""
        return (
            "Não encontrei imóveis que atendam exatamente ao que você procura no momento. "
            "Que tal me contar mais detalhes sobre suas preferências? "
            "Posso buscar opções similares ou te ajudar a refinar a busca. "
            "Também posso te passar o contato direto da nossa equipe para uma consulta personalizada."
        )

    def _extract_title_from_text(self, text: str) -> str:
        """Extrai título do texto do imóvel"""
        if not text:
            return ""
        
        # Procura por "Título:" no início
        lines = text.split('\n')
        for line in lines:
            if line.strip().startswith("Título:"):
                return line.replace("Título:", "").strip()
        
        # Fallback: primeira linha não vazia
        for line in lines:
            if line.strip():
                return line.strip()[:50]
        
        return ""

    async def _is_property_search(self, message: str) -> bool:
        """
        Detecta intenção de 'property_search' usando NLU via LLM.
        - Tenta pedir ao LLM para devolver JSON {"intent": "...", "confidence": 0.x}
        - Se falhar, usa heurística simples como fallback.
        """
        try:
            model = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:alloha-sofia-v1:CMFHyUpi")
            prompt = (
                "Analise se o usuário está PROCURANDO/BUSCANDO um imóvel para alugar ou comprar. "
                "Retorne JSON: {\"intent\": \"property_search\" ou \"other\", \"confidence\": 0.0-1.0}\n\n"
                f"Mensagem: \"{message}\"\n\n"
                "Exemplos:\n"
                "- 'Procuro apartamento 2 quartos' → property_search (0.95)\n"
                "- 'Não quero mais apartamento' → other (0.9)\n"
                "- 'Oi, tudo bem?' → other (0.95)"
            )
            
            # call_gpt é síncrono; execute em thread
            resp = await asyncio.to_thread(rag.call_gpt, prompt, model)
            if not resp:
                raise ValueError("NLU returned empty")

            # tentar extrair JSON
            start = resp.find("{")
            end = resp.rfind("}") + 1
            json_text = resp[start:end] if start != -1 and end != -1 else resp
            data = json.loads(json_text)
            intent = (data.get("intent") or "other").lower()
            confidence = float(data.get("confidence") or 0.0)
            
            # Log para monitoramento
            logger.info(f"NLU: '{message[:50]}...' → {intent} ({confidence:.2f})")
            
            # threshold configurável via env
            threshold = float(os.getenv("NLU_PROPERTY_CONF_THRESHOLD", "0.6"))
            return intent == "property_search" and confidence >= threshold
            
        except Exception as e:
            logger.debug("NLU detect failed (%s) — falling back to keyword heuristic", e)
            
            # fallback: heurística melhorada
            keywords = [
                "procuro", "buscar", "apartamento", "casa", "quarto", "quartos", 
                "aluguel", "venda", "vaga", "área", "bairro", "locação", 
                "locar", "alugar", "comprar", "imóvel", "propriedade",
                "preciso", "quero", "gostaria", "interesse"
            ]
            text = (message or "").lower()
            found_keywords = [k for k in keywords if k in text]
            
            # Log do fallback também
            if found_keywords:
                logger.info(f"Fallback: '{message[:50]}...' → property_search (keywords: {found_keywords})")
            else:
                logger.info(f"Fallback: '{message[:50]}...' → other (no keywords)")
                
            return len(found_keywords) > 0

    async def _call_sofia_vision(self, prompt: str, image_base64: str, model_name: Optional[str] = None) -> str:
        """Envio de prompt + imagem (base64) para o GPT via call_gpt (executa em thread)."""
        try:
            model = model_name or os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:alloha-sofia-v1:CMFHyUpi")
            full_prompt = prompt + "\n\n---BEGIN_IMAGE_BASE64---\n" + image_base64 + "\n---END_IMAGE_BASE64---\n\n"
            full_prompt += "Resuma em até 300 caracteres e destaque campos relevantes."
            resp = await asyncio.to_thread(rag.call_gpt, full_prompt, model)
            return resp or "📸 Não consegui analisar a imagem agora."
        except Exception as e:
            logger.exception(f"Erro visão Sofia (OpenAI): {e}")
            return "📸 Não foi possível analisar a imagem agora. Tente novamente mais tarde."

    async def _save_attachment(self, owner_phone: str, storage_url: str, content_type: str, size: int, message_id: str = None, meta: dict = None):
        """
        Salvar metadados de attachments no Firestore (executa em thread).
        TODO: Migrar para Supabase (tabela attachments)
        """
        try:
            logger.warning("⚠️ _save_attachment ainda não migrado para Supabase - funcionalidade desabilitada temporariamente")
            return
            # TODO: Implementar usando supabase_client
            # ...
        except Exception as e:
            logger.debug(f"Erro salvar attachment: {e}")

    async def _save_audit(self, action: str, actor: str = "system", details: dict | None = None):
        """
        Registra auditoria de ações críticas.
        TODO: Migrar para Supabase (tabela audit_logs)
        """
        try:
            logger.warning("⚠️ _save_audit ainda não migrado para Supabase - funcionalidade desabilitada temporariamente")
            return
            # TODO: Implementar usando supabase_client
            # ...
        except Exception as e:
            logger.debug(f"Erro salvar audit: {e}")

    async def _save_embedding_meta(self, doc_id: str, vector_id: str, model: str, meta: dict | None = None):
        """
        Salva metadados de embeddings (vetores são guardados no vector DB).
        """
        try:
            # Lazy init client se ainda não disponível
            client = supabase_client.ensure_client()
            if not client:
                logger.debug("Supabase indisponível; adiando persistência de embedding meta para doc_id=%s", doc_id)
                return

            ok = await asyncio.to_thread(
                supabase_client.save_embedding_metadata,
                doc_id,
                vector_id,
                model,
                meta or {}
            )
            if ok:
                logger.debug("Embedding meta salva (doc_id=%s vector_id=%s)", doc_id, vector_id)
            else:
                logger.warning("Falha ao salvar embedding meta (doc_id=%s vector_id=%s)", doc_id, vector_id)
        except Exception as e:
            logger.debug(f"Erro salvar embedding meta: {e}")

    async def _process_property_search_and_send(self, user_query: str, user_phone: str, history: List[Dict[str, str]]):
        """
        Executa busca de imóveis com novo fluxo:
        1) PRIMEIRO: Buscar imóveis e decidir se deve enviar CTA
        2) Se vai enviar CTA: envia APENAS o CTA (sem resposta natural)
        3) Se NÃO vai enviar CTA: envia resposta natural
        """
        try:
            logger.info("Iniciando fluxo de property_search para %s: %s", user_phone, user_query[:120])
            
            # 1) PRIMEIRO: Buscar imóveis e gerar resposta natural (COM CACHE!)
            answer, structured_properties = await self.process_property_search(user_query, phone_number=user_phone)
            
            if not answer:
                answer = "Desculpe, não encontrei imóveis com essas características no momento."

            # 2) DECIDIR se deve enviar CTA baseado na resposta da Sofia
            should_send_cta = await self._should_send_cta(answer, user_query, structured_properties)
            
            cta_sent = False
            if should_send_cta and structured_properties and getattr(self, "whatsapp_service", None):
                try:
                    # Pega o MELHOR resultado (primeiro da lista já vem ordenado por relevância)
                    best_property = structured_properties[0]
                    logger.debug("Best property selected for CTA: id=%s url=%s title=%s", 
                            best_property.get("id"), best_property.get("url"), best_property.get("title"))
                    
                    # Só envia CTA se tiver URL válida
                    if best_property.get("url") and best_property["url"].startswith("http"):
                        has_method = getattr(self.whatsapp_service, "send_interactive_cta_url", None) is not None
                        logger.debug("WhatsAppService has send_interactive_cta_url=%s", has_method)
                        if has_method:
                            logger.info(f"Enviando CTA para melhor imóvel: {best_property.get('title', 'N/A')}")
                        
                            cta_success = await self.whatsapp_service.send_interactive_cta_url(
                                to=user_phone,
                                image_url=best_property.get("main_image"),
                                body_text=f"{best_property.get('title', 'Imóvel encontrado')}\n\n{best_property.get('description', '')}...",
                                button_text="Ver detalhes",
                                url=best_property["url"],
                                footer_text="Agende sua visita!"
                            )
                        
                            if cta_success:
                                cta_sent = True
                                logger.info("CTA enviado com sucesso!")
                                # ✅ NÃO envia mensagem complementar - só o CTA
                            else:
                                logger.warning("Falha ao enviar CTA")
                        else:
                            logger.warning("WhatsAppService missing send_interactive_cta_url; skipping CTA")
                            
                except Exception as e:
                    logger.error(f"Erro ao enviar CTA: {e}")

            # 3) Se NÃO enviou CTA, envia resposta natural da Sofia
            if not cta_sent and getattr(self, "whatsapp_service", None):
                try:
                    await self.whatsapp_service.send_message(user_phone, answer)
                    logger.info("Resposta da Sofia enviada com sucesso")
                except Exception:
                    logger.exception("Erro ao enviar resposta da Sofia")

            # 4) Persistir mensagem enviada (só se não foi CTA) no Supabase
            if not cta_sent:
                try:
                    conversation = await asyncio.to_thread(
                        supabase_client.get_or_create_conversation,
                        user_phone
                    )
                    await asyncio.to_thread(
                        supabase_client.save_message,
                        conversation['id'],
                        'sent',
                        answer,
                        'text',
                        None,
                        {
                            "ai": True, 
                            "flow": "property_search",
                            "cta_sent": cta_sent,
                            "properties_found": len(structured_properties),
                            "should_send_cta": should_send_cta
                        }
                    )
                except Exception:
                    logger.exception("Falha ao persistir mensagem de property_search no Firestore.")
                
        except Exception as e:
            logger.exception("Erro no fluxo property_search: %s", e)


    async def _should_send_cta(self, sofia_response: str, user_query: str, structured_properties: list) -> bool:
        """
        Decide se deve enviar CTA baseado na resposta da Sofia.
        Usa NLU para analisar se a resposta indica que encontrou imóveis específicos
        ou se está pedindo mais informações do cliente.
        """
        try:
            # Se não tem propriedades estruturadas, não envia CTA
            if not structured_properties:
                logger.debug("Não enviando CTA: nenhuma propriedade estruturada encontrada")
                return False
            
            # Usar LLM para analisar se a resposta da Sofia indica que deve enviar CTA
            model = os.getenv("OPENAI_MODEL", "ft:gpt-4.1-mini-2025-04-14:personal:alloha-sofia-v1:CMFHyUpi")
            prompt = (
                "Analise se a resposta da Sofia indica que ela ENCONTROU IMÓVEIS ESPECÍFICOS "
                "e está apresentando opções concretas, ou se ela está PEDINDO MAIS INFORMAÇÕES "
                "para refinar a busca.\n\n"
                f"Pergunta do cliente: \"{user_query}\"\n"
                f"Resposta da Sofia: \"{sofia_response}\"\n\n"
                "Retorne JSON: {\"should_send_cta\": true/false, \"reason\": \"explicação\"}\n\n"
                "Exemplos:\n"
                "- Se Sofia apresentou imóveis específicos → {\"should_send_cta\": true, \"reason\": \"apresentou opções\"}\n"
                "- Se Sofia pediu mais detalhes/preferências → {\"should_send_cta\": false, \"reason\": \"precisa mais info\"}\n"
                "- Se Sofia disse que não encontrou nada → {\"should_send_cta\": false, \"reason\": \"sem resultados\"}"
            )
            
            resp = await asyncio.to_thread(rag.call_gpt, prompt, model)
            if not resp:
                logger.debug("NLU CTA decision: resposta vazia, não enviando CTA")
                return False

            # Extrair JSON da resposta
            start = resp.find("{")
            end = resp.rfind("}") + 1
            json_text = resp[start:end] if start != -1 and end != -1 else resp
            data = json.loads(json_text)
            
            should_send = data.get("should_send_cta", False)
            reason = data.get("reason", "sem razão")
            
            logger.info(f"NLU CTA decision: should_send={should_send}, reason='{reason}'")
            return should_send
            
        except Exception as e:
            logger.debug(f"Erro na decisão de CTA via NLU: {e}")
            
            # Fallback: heurística simples
            # Se a resposta contém palavras que indicam que está pedindo mais info, não envia CTA
            asking_keywords = [
                "que tal me contar", "mais detalhes", "suas preferências", 
                "refinar a busca", "me conte", "gostaria de saber",
                "qual seu orçamento", "quantos quartos", "qual bairro",
                "para alugar ou comprar", "mais informações"
            ]
            
            response_lower = sofia_response.lower()
            is_asking_more_info = any(keyword in response_lower for keyword in asking_keywords)
            
            if is_asking_more_info:
                logger.info("Fallback CTA decision: Sofia está pedindo mais informações, não enviando CTA")
                return False
            
            # Se tem propriedades e não está pedindo mais info, envia CTA
            logger.info("Fallback CTA decision: enviando CTA (tem propriedades e não está pedindo mais info)")
            return len(structured_properties) > 0


# Instância global do bot
intelligent_bot = IntelligentRealEstateBot()