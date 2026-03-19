"""
Supabase Client - Drop-in replacement
Suporta busca híbrida (vector + full-text), cache, e idempotency.
"""

from __future__ import annotations

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
import hashlib
import re
from uuid import uuid4
from dotenv import load_dotenv
from supabase import create_client, Client

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except ImportError:  # pragma: no cover
    SentenceTransformer = None  # type: ignore

try:
    import openai  # type: ignore
except ImportError:  # pragma: no cover
    openai = None  # type: ignore

try:
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover
    np = None  # type: ignore

# Carregar variáveis de ambiente
load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Cliente Supabase com features avançadas (lazy init).

    - Não quebra o import caso variáveis não estejam presentes.
    - Usa ensure_client() para inicialização tardia.
    """

    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        self.client: Optional[Client] = None
        self.embedding_model: Optional[Any] = None
        self.available = False
        # Embeddings ficam desligados por padrão no perfil low-cost do Cloud Run.
        self.enable_property_embeddings = os.getenv("ENABLE_PROPERTY_EMBEDDINGS", "0") == "1"
        self.use_openai_embeddings = (
            self.enable_property_embeddings and os.getenv("USE_OPENAI_EMBEDDINGS", "0") == "1"
        )
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_embed_model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
        self.openai_embed_dim = int(os.getenv("PROPERTY_EMBED_DIM", "384"))
        self.openai_client = None
        # Rate limiting / cooldown controls for embeddings
        self._last_embedding_at: Optional[datetime] = None
        self._min_embed_interval_ms = int(os.getenv("EMBEDDING_MIN_INTERVAL_MS", "250"))  # throttle burst
        self._openai_cooldown_until: Optional[datetime] = None
        self._openai_cooldown_seconds = int(os.getenv("OPENAI_EMBED_COOLDOWN_SECONDS", "900"))  # 15 min default after quota 429
        self._init_if_possible(initial=True)

    def _init_if_possible(self, initial: bool = False):
        if self.available:
            return
        if not self.supabase_url or not self.supabase_key:
            if initial:
                logger.warning("⚠️ Supabase não configurado no startup (faltando SUPABASE_URL ou SUPABASE_SERVICE_KEY). Inicialização será tentada novamente quando necessário.")
            return
        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            self.available = True
            logger.info("✅ Supabase client inicializado (lazy)")
        except Exception as e:
            logger.error(f"❌ Falha ao inicializar Supabase: {e}")

    def ensure_client(self) -> Optional[Client]:
        """Garante que o client esteja inicializado, tentando lazy init."""
        if not self.available:
            # Recarregar env (caso .env tenha sido carregado depois)
            self.supabase_url = os.getenv("SUPABASE_URL")
            self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
            self._init_if_possible(initial=False)
        return self.client

    def require_client(self) -> Client:
        """Obtém o client ou lança erro claro caso indisponível."""
        client = self.ensure_client()
        if not client:
            raise RuntimeError("Supabase ainda não configurado (defina SUPABASE_URL e SUPABASE_SERVICE_KEY).")
        return client

    def _ensure_openai_client(self) -> Optional[Any]:
        if not self.use_openai_embeddings or not self.openai_api_key:
            return None
        if self.openai_client is not None:
            return self.openai_client
        if openai is None:
            logger.warning("OpenAI SDK não instalado; embeddings remotos desativados.")
            return None
        try:
            self.openai_client = openai.OpenAI(api_key=self.openai_api_key, timeout=30)
        except Exception as exc:
            logger.warning(f"⚠️ Falha ao inicializar cliente OpenAI: {exc}")
            self.openai_client = None
        return self.openai_client

    def _ensure_local_embedding_model(self) -> Optional[Any]:
        if not self.enable_property_embeddings:
            return None
        if self.embedding_model is not None:
            return self.embedding_model
        if SentenceTransformer is None:
            logger.warning("sentence-transformers não está instalado; embeddings locais indisponíveis.")
            return None
        try:
            self.embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            logger.info("✅ Modelo local de embeddings carregado sob demanda.")
        except Exception as exc:
            logger.warning(f"⚠️ Falha ao carregar modelo local de embeddings: {exc}")
            self.embedding_model = None
        return self.embedding_model
    
    # ================================================================
    # PROPERTIES - Busca híbrida avançada
    # ================================================================
    
    def vector_search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        similarity_threshold: float = 0.30,
        query_text: Optional[str] = None,
        fallback_lexical: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Busca semântica usando função RPC vector_property_search (pgvector) com fallback opcional.
        
        Args:
            query_embedding: Embedding da query (384 dims para all-MiniLM-L6-v2)
            limit: Número máximo de resultados (match_count na função SQL)
            filters: Filtros adicionais (aplicados pós-RPC)
            similarity_threshold: Similaridade mínima (0-1). A função converte internamente.
            query_text: Texto original da busca (usado para fallback lexical se necessário)
            fallback_lexical: Se True, tenta ILIKE em title/description quando vetor falha ou retorna vazio
        
        Returns:
            Lista de dicts normalizados (campos que a função retornar ou fallback lexical)
        """
        try:
            params = {
                'query_embedding': query_embedding,
                'match_threshold': similarity_threshold,
                'match_count': limit
            }

            result = self.client.rpc('vector_property_search', params).execute()

            data = result.data or []
            if not data:
                logger.info("⚠️ vector_property_search sem resultados (threshold=%.2f)" % similarity_threshold)
                # Fallback lexical opcional
                if fallback_lexical and query_text:
                    lexical = self._lexical_property_fallback(query_text, limit)
                    if lexical:
                        logger.info(f"🔎 Fallback lexical retornou {len(lexical)} resultados")
                        return lexical
                return []

            # Aplicar filtros adicionais pós-RPC
            if filters:
                data = self._apply_metadata_filters(data, filters)

            logger.info(f"🔍 Vector search retornou {len(data)} resultados (após filtros)")
            return data
        except Exception as e:
            logger.error(f"❌ Erro no vector_search: {e}")
            logger.warning("⚠️ Verifique se a função vector_property_search existe no Supabase")
            # Fallback se possível
            if fallback_lexical and query_text:
                try:
                    lexical = self._lexical_property_fallback(query_text, limit)
                    if lexical:
                        logger.info(f"🔎 Fallback lexical (erro RPC) retornou {len(lexical)} resultados")
                        return lexical
                except Exception as fe:
                    logger.debug(f"Falha no fallback lexical: {fe}")
            return []
    
    def search_properties(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Busca híbrida: vector similarity + full-text search
        70% weight em semantic, 30% em keyword matching
        """
        try:
            # Gerar embedding da query (padrao 384; configuravel via env)
            query_embedding = self._generate_embedding(query[:2000]) or []
            
            # Executar busca híbrida usando função SQL
            result = self.client.rpc(
                'hybrid_property_search',
                {
                    'query_embedding': query_embedding,
                    'query_text': query,
                    'match_threshold': 0.7,
                    'max_results': limit
                }
            ).execute()
            
            properties = result.data
            
            # Aplicar filtros adicionais (preço, tipo, etc)
            if filters:
                properties = self._apply_filters(properties, filters)
            
            logger.info(f"🔍 Busca híbrida retornou {len(properties)} imóveis")
            return properties
            
        except Exception as e:
            logger.error(f"❌ Erro na busca híbrida: {e}")
            return []
    
    def get_property(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Busca imóvel por ID"""
        try:
            result = self.client.table('properties')\
                .select('*')\
                .eq('property_id', property_id)\
                .single()\
                .execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar imóvel {property_id}: {e}")
            return None
    
    def upsert_property(self, property_data: Dict[str, Any]) -> Optional[str]:
        """
        Insere ou atualiza imóvel (com embedding automático)
        """
        try:
            prepared = self._prepare_property_record(property_data)
            if not prepared:
                return None

            if self.enable_property_embeddings:
                text_for_embedding = f"{prepared.get('title', '')} {prepared.get('description', '')}".strip()[:4000]
                embedding = self._generate_embedding(text_for_embedding)
                if embedding is not None:
                    prepared['embedding'] = embedding
            prepared['updated_at'] = datetime.utcnow().isoformat()

            logger.debug(f"Upsert property_id={prepared.get('property_id')} source={prepared.get('source')}")

            result = self.client.table('properties') \
                .upsert(prepared, on_conflict='property_id') \
                .execute()

            if not result.data or len(result.data) == 0:
                logger.error(f"❌ Upsert não retornou dados para {prepared.get('property_id')}")
                return None

            property_id = result.data[0]['property_id']
            logger.debug(f"✅ Imóvel {property_id} salvo/atualizado")
            return property_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar imóvel {property_data.get('property_id', 'unknown')}: {e}")
            logger.error(f"   Tipo do erro: {type(e).__name__}")
            logger.error(f"   Detalhes: {str(e)[:200]}")
            return None
    
    # ================================================================
    # CONVERSATIONS - State Machine
    # ================================================================
    
    def get_or_create_conversation(self, phone_number: str) -> Dict[str, Any]:
        """Busca ou cria conversa (thread-safe)"""
        try:
            # Tentar buscar existente
            result = self.client.table('conversations')\
                .select('*')\
                .eq('phone_number', phone_number)\
                .execute()
            
            if result.data:
                conversation = result.data[0]
                
                # Atualizar last_message_at
                self.client.table('conversations')\
                    .update({'last_message_at': datetime.utcnow().isoformat()})\
                    .eq('id', conversation['id'])\
                    .execute()
                
                return conversation
            
            # Criar nova
            new_conversation = {
                'phone_number': phone_number,
                'state': 'pending',
                'urgency_score': 1,
                'last_message_at': datetime.utcnow().isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.client.table('conversations')\
                .insert(new_conversation)\
                    .execute()
            
            logger.info(f"✅ Nova conversa criada: {phone_number}")
            return result.data[0]
            
        except Exception as e:
            logger.error(f"❌ Erro em get_or_create_conversation: {e}")
            raise

    def set_user_name(self, phone_number: str, user_name: str) -> bool:
        """Define ou atualiza o user_name da conversa associada ao número.
        Cria a conversa se ainda não existir.
        """
        try:
            if not user_name or not user_name.strip():
                return False
            user_name = user_name.strip()[:120]
            result = self.client.table('conversations')\
                .select('id, user_name')\
                .eq('phone_number', phone_number)\
                .limit(1)\
                .execute()
            if result.data:
                conv = result.data[0]
                if conv.get('user_name') != user_name:
                    self.client.table('conversations')\
                        .update({'user_name': user_name, 'updated_at': datetime.utcnow().isoformat()})\
                        .eq('id', conv['id'])\
                        .execute()
                return True
            # criar\atualizar
            new_conv = {
                'phone_number': phone_number,
                'user_name': user_name,
                'state': 'pending',
                'urgency_score': 1,
                'last_message_at': datetime.utcnow().isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }
            self.client.table('conversations').insert(new_conv).execute()
            return True
        except Exception as e:
            logger.debug(f"Falha ao definir user_name para {phone_number}: {e}")
            return False

    def get_user_profile(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Recupera dados agregados do usuário (conversa + lead)."""
        try:
            profile: Dict[str, Any] = {"phone_number": phone_number}

            conversation_result = self.client.table('conversations')\
                .select('*')\
                .eq('phone_number', phone_number)\
                .order('last_message_at', desc=True)\
                .limit(1)\
                .execute()

            conversation = conversation_result.data[0] if conversation_result.data else None
            if conversation:
                profile['conversation'] = conversation
                profile['state'] = conversation.get('state')
                profile['last_message_at'] = conversation.get('last_message_at')
                profile['urgency_score'] = conversation.get('urgency_score')
                profile['metadata'] = conversation.get('metadata') or {}

            lead_result = self.client.table('leads')\
                .select('*')\
                .eq('phone_number', phone_number)\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()

            lead = lead_result.data[0] if lead_result.data else None
            if lead:
                profile['lead'] = lead

            return profile

        except Exception as e:
            logger.error(f"❌ Erro ao buscar profile do usuário {phone_number}: {e}")
            return None
    
    def update_conversation_state(
        self, 
        conversation_id: str, 
        new_state: str,
        urgency_score: Optional[int] = None
    ) -> bool:
        """Atualiza estado da conversa"""
        try:
            updates = {
                'state': new_state,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if urgency_score is not None:
                updates['urgency_score'] = urgency_score
            
            self.client.table('conversations')\
                .update(updates)\
                .eq('id', conversation_id)\
                .execute()
            
            logger.info(f"✅ Conversa {conversation_id} → {new_state}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao atualizar estado: {e}")
            return False

    def get_user_stats(self, phone_number: str) -> Dict[str, Any]:
        """Calcula estatísticas de conversas e mensagens de um usuário."""
        try:
            default_stats = {
                'total_conversations': 0,
                'total_messages': 0,
                'first_contact': None,
                'last_contact': None,
                'messages_today': 0,
                'received_messages': 0,
                'sent_messages': 0,
                'last_state': None,
                'last_urgency_score': None
            }

            conversations_result = self.client.table('conversations')\
                .select('id, state, urgency_score, created_at, last_message_at')\
                .eq('phone_number', phone_number)\
                .order('created_at', desc=True)\
                .execute()

            conversations = conversations_result.data or []
            if not conversations:
                return default_stats

            conversation_ids = [conv['id'] for conv in conversations]

            messages_query = self.client.table('messages')\
                .select('id, direction, created_at')\
                .in_('conversation_id', conversation_ids)\
                .order('created_at')\
                .execute()

            messages = messages_query.data or []

            def _parse(ts: Any) -> Optional[datetime]:
                if ts is None:
                    return None
                if isinstance(ts, datetime):
                    return ts
                if isinstance(ts, str):
                    try:
                        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    except Exception:
                        return None
                return None

            timestamps = [dt for dt in (_parse(msg.get('created_at')) for msg in messages) if dt]
            if not timestamps:
                first_contact = _parse(conversations[-1].get('created_at'))
                last_contact = _parse(conversations[0].get('last_message_at'))
            else:
                first_contact = min(timestamps)
                last_contact = max(timestamps)

            today = datetime.now(timezone.utc).date()
            messages_today = sum(1 for ts in timestamps if ts.astimezone(timezone.utc).date() == today)

            sent_messages = sum(1 for msg in messages if msg.get('direction') == 'sent')
            received_messages = sum(1 for msg in messages if msg.get('direction') in ('received', 'inbound'))

            latest_conversation = conversations[0]

            stats = {
                'total_conversations': len(conversations),
                'total_messages': len(messages),
                'first_contact': first_contact.isoformat() if first_contact else None,
                'last_contact': last_contact.isoformat() if last_contact else None,
                'messages_today': messages_today,
                'received_messages': received_messages,
                'sent_messages': sent_messages,
                'last_state': latest_conversation.get('state'),
                'last_urgency_score': latest_conversation.get('urgency_score')
            }

            return stats

        except Exception as e:
            logger.error(f"❌ Erro ao calcular stats do usuário {phone_number}: {e}")
            return {
                'total_conversations': 0,
                'total_messages': 0,
                'first_contact': None,
                'last_contact': None,
                'messages_today': 0,
                'received_messages': 0,
                'sent_messages': 0,
                'last_state': None,
                'last_urgency_score': None
            }
    
    # ================================================================
    # MESSAGES - Com TTL automático
    # ================================================================
    
    def save_message(
        self, 
        conversation_id: str,
        direction: str,
        content: str,
        message_type: str = 'text',
        whatsapp_message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Salva mensagem (TTL de 90 dias configurado via pg_cron)"""
        try:
            message_data = {
                'conversation_id': conversation_id,
                'direction': direction,
                'content': content,
                'message_type': message_type,
                'whatsapp_message_id': whatsapp_message_id,
                'status': 'sent',
                'metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.client.table('messages')\
                .insert(message_data)\
                .execute()
            
            message_id = result.data[0]['id']
            return message_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar mensagem: {e}")
            return None
    
    def get_conversation_messages(
        self, 
        conversation_id: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Busca histórico de mensagens"""
        try:
            result = self.client.table('messages')\
                .select('*')\
                .eq('conversation_id', conversation_id)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar mensagens: {e}")
            return []
    
    # ================================================================
    # WEBHOOK IDEMPOTENCY
    # ================================================================
    
    def is_duplicate_webhook(self, fingerprint: str) -> bool:
        """Verifica se webhook já foi processado"""
        try:
            result = self.client.table('webhook_idempotency')\
                .select('id')\
                .eq('fingerprint', fingerprint)\
                .execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar idempotência: {e}")
            return False
    
    def mark_webhook_processing(
        self, 
        fingerprint: str,
        whatsapp_message_id: Optional[str] = None,
        ttl_hours: int = 24
    ) -> bool:
        """Marca webhook como em processamento"""
        try:
            idempotency_data = {
                'fingerprint': fingerprint,
                'whatsapp_message_id': whatsapp_message_id,
                'status': 'processing',
                'expires_at': (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.client.table('webhook_idempotency')\
                .insert(idempotency_data)\
                .execute()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao marcar idempotência: {e}")
            return False
    
    # ================================================================
    # EMBEDDING CACHE
    # ================================================================
    
    def get_cached_embedding(self, text: str) -> Optional[Any]:
        """Busca embedding no cache"""
        if np is None:
            return None
        try:
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            
            result = self.client.table('embedding_cache')\
                .select('embedding, expires_at')\
                .eq('text_hash', text_hash)\
                .single()\
                .execute()
            
            if result.data:
                # Verificar se não expirou
                expires_at = datetime.fromisoformat(result.data['expires_at'].replace('Z', '+00:00'))
                
                if expires_at > datetime.utcnow():
                    # Atualizar hit count
                    self.client.table('embedding_cache')\
                        .update({
                            'hit_count': result.data.get('hit_count', 0) + 1,
                            'last_hit_at': datetime.utcnow().isoformat()
                        })\
                        .eq('text_hash', text_hash)\
                        .execute()
                    
                    return np.array(result.data['embedding'])
            
            return None
            
        except Exception as e:
            logger.debug(f"Cache miss para texto: {text[:50]}...")
            return None
    
    def cache_embedding(self, text: str, embedding: Any, ttl_days: int = 30) -> bool:
        """Salva embedding no cache"""
        if np is None:
            return False
        try:
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            
            cache_data = {
                'text_hash': text_hash,
                'text_content': text[:500],  # Limitar tamanho
                'embedding': embedding.tolist(),
                'model': self.openai_embed_model if (self.use_openai_embeddings and self.openai_client) else 'all-MiniLM-L6-v2',
                'hit_count': 0,
                'expires_at': (datetime.utcnow() + timedelta(days=ttl_days)).isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.client.table('embedding_cache')\
                .upsert(cache_data, on_conflict='text_hash')\
                .execute()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao cachear embedding: {e}")
            return False

    # ================================================================
    # EMBEDDING METADATA (para rastrear vetores gerados externamente)
    # ================================================================

    def save_embedding_metadata(
        self,
        doc_id: str,
        vector_id: str,
        model: str,
        meta: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Persiste metadados sobre embeddings gerados.

        Espera existir uma tabela embedding_metadata com colunas sugeridas:
            id uuid (default gen_random_uuid()) primary key
            doc_id text
            vector_id text
            model text
            meta jsonb
            created_at timestamptz default now()
            UNIQUE(vector_id)
        """
        try:
            data = {
                'doc_id': doc_id,
                'vector_id': vector_id,
                'model': model,
                'meta': meta or {},
                'created_at': datetime.utcnow().isoformat()
            }
            self.client.table('embedding_metadata')\
                .upsert(data, on_conflict='vector_id')\
                .execute()
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao salvar embedding_metadata: {e}")
            return False
    
    # ================================================================
    # URGENCY ALERTS
    # ================================================================
    
    def create_urgency_alert(
        self,
        conversation_id: str,
        urgency_level: int,
        reason: str,
        indicators: List[str]
    ) -> Optional[str]:
        """Cria alerta de urgência"""
        try:
            alert_data = {
                'conversation_id': conversation_id,
                'urgency_level': urgency_level,
                'reason': reason,
                'indicators': indicators,
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.client.table('urgency_alerts')\
                .insert(alert_data)\
                .execute()
            
            alert_id = result.data[0]['id']
            logger.info(f"🚨 Alerta de urgência criado: nível {urgency_level}")
            
            return alert_id
            
        except Exception as e:
            logger.error(f"❌ Erro ao criar alerta: {e}")
            return None
    
    # ================================================================
    # HELPER FUNCTIONS
    # ================================================================
    
    def _apply_metadata_filters(
        self,
        results: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Aplica filtros aos metadados dos resultados de vector search"""
        filtered: List[Dict[str, Any]] = []

        for result in results:
            metadata = result.get('metadata', {})
            
            # Filtro de preço mínimo
            if 'min_price' in filters:
                if metadata.get('price', 0) < filters['min_price']:
                    continue
            
            # Filtro de preço máximo
            if 'max_price' in filters:
                if metadata.get('price', float('inf')) > filters['max_price']:
                    continue
            
            # Filtro de tipo de imóvel
            if 'property_type' in filters:
                if metadata.get('property_type') != filters['property_type']:
                    continue
            
            # Filtro de quartos
            if 'bedrooms' in filters:
                if metadata.get('bedrooms', 0) < filters['bedrooms']:
                    continue

            filtered.append(result)

        return filtered
    
    def _apply_filters(
        self, 
        properties: List[Dict[str, Any]], 
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Aplica filtros adicionais aos resultados"""
        filtered = properties
        
        if 'min_price' in filters:
            filtered = [p for p in filtered if p.get('price', 0) >= filters['min_price']]
        
        if 'max_price' in filters:
            filtered = [p for p in filtered if p.get('price', float('inf')) <= filters['max_price']]
        
        if 'property_type' in filters:
            filtered = [p for p in filtered if p.get('property_type') == filters['property_type']]
        
        if 'bedrooms' in filters:
            filtered = [p for p in filtered if p.get('bedrooms', 0) >= filters['bedrooms']]
        
        return filtered

    def _lexical_property_fallback(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fallback simples usando ILIKE em title / description / ai_analysis.
        Retorna formato aproximado ao da função vetorial.
        """
        try:
            # Sanitizar query para evitar % consecutivos
            q = (query or '').strip()
            if not q:
                return []
            pattern = f"%{q[:60]}%"  # limitar tamanho

            # Preferir ai_analysis se existir
            result = self.client.table('properties') \
                .select('property_id, title, description, ai_analysis, url, price, bedrooms') \
                .or_(
                    f"title.ilike.{pattern},description.ilike.{pattern},ai_analysis.ilike.{pattern}"
                ) \
                .limit(limit) \
                .execute()

            rows = result.data or []
            normalized = []
            for r in rows:
                normalized.append({
                    'property_id': r.get('property_id'),
                    'title': r.get('title'),
                    'description': r.get('ai_analysis') or r.get('description'),
                    'url': r.get('url'),
                    'price': r.get('price'),
                    'bedrooms_int': r.get('bedrooms'),
                    'similarity': None,  # sem score semântico
                    'fallback': True
                })
            return normalized
        except Exception as e:
            logger.debug(f"Falha fallback lexical: {e}")
            return []

    # ================================================================
    # INTERNAL - NORMALIZATION FOR SCRAPED PROPERTIES
    # ================================================================
    def _prepare_property_record(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transforma dict cru do scraper em registro compatível com tabela properties.
        Remove campos desconhecidos (ex: ai_analysis, ai_enhanced) que causam 400.
        """
        if not raw:
            return None

        # Derivar property_id (preferência: reference -> property_id -> hash URL -> uuid)
        reference = raw.get('reference') or raw.get('property_id')
        if not reference:
            url = raw.get('url') or ''
            if url:
                # gerar slug curta baseada na URL
                slug_part = re.sub(r'[^a-zA-Z0-9]+', '-', url.split('/')[-1])[:40].strip('-')
                reference = f"url-{slug_part or uuid4().hex[:8]}"
            else:
                reference = f"scr-{uuid4().hex[:10]}"

        # Price: extrair números
        raw_price = str(raw.get('price') or '').replace('\u00a0', ' ')
        price_value = None
        if raw_price:
            m = re.search(r'([\d\.\,]+)', raw_price)
            if m:
                num = m.group(1).replace('.', '').replace(',', '.')
                try:
                    price_value = float(num)
                except Exception:
                    price_value = None

        # Address JSONB
        address = None
        if any(raw.get(k) for k in ('address','neighborhood','city','uf')):
            address = raw.get('address') if isinstance(raw.get('address'), dict) else {}
            address = address or {}
            if raw.get('neighborhood'):
                address['district'] = raw.get('neighborhood')
            if raw.get('city'):
                address['city'] = raw.get('city')
            if raw.get('uf'):
                address['state'] = raw.get('uf')

        images = raw.get('images') if isinstance(raw.get('images'), list) else []
        features = raw.get('features') if isinstance(raw.get('features'), list) else []

        prepared: Dict[str, Any] = {
            'property_id': reference,
            'title': (raw.get('title') or 'Imóvel sem título')[:500],
            'description': (raw.get('description') or '')[:5000],
            'price': price_value,
            'address': address,
            'bedrooms': raw.get('bedrooms'),
            'bathrooms': raw.get('bathrooms'),
            'area_m2': raw.get('area_m2'),
            'property_type': raw.get('property_type'),
            'status': raw.get('status') or 'active',
            'images': images or None,
            'amenities': features[:50] or None,
            'owner_info': None,
            'source': raw.get('source') or 'allega_scraper',
            'external_id': raw.get('reference') or reference,
            'last_sync_at': datetime.utcnow().isoformat(),
            'source_updated_at': raw.get('source_updated_at'),
            'content_hash': raw.get('content_hash'),
            'last_seen_at': raw.get('last_seen_at'),
            'is_deleted': raw.get('is_deleted'),
            'created_at': datetime.utcnow().isoformat(),  # só usado se inserir
            'ai_analysis': (raw.get('ai_analysis') or '')[:500],
            'url': raw.get('url')
        }

        # Remover chaves None para não sobrescrever existente com null desnecessário
        prepared = {k: v for k, v in prepared.items() if v is not None}

        # Log de campos ignorados (debug)
        ignored = sorted(set(raw.keys()) - set(prepared.keys()))
        noisy = [k for k in ignored if k.startswith('ai_') or k in ('url', 'scraped_at')]
        if noisy:
            logger.debug(f"Ignorando campos não suportados no upsert: {noisy}")

        if not prepared.get('property_id'):
            logger.error("Registro sem property_id após normalização – descartando")
            return None
        return prepared

    # ================================================================
    # INTERNAL - EMBEDDING GENERATION (OpenAI + fallback)
    # ================================================================
    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """Gera embedding para texto.

        Estratégia:
          1. Se OpenAI habilitado e cliente disponível -> tenta gerar 1536 dims.
          2. Em falha -> fallback local 384 dims com zero-padding até 1536 (quando em modo OpenAI).
          3. Se OpenAI desabilitado -> só local.
        """
        if not text:
            return None
        if not self.enable_property_embeddings:
            return None

        try:
            # Simple client-side throttling
            now = datetime.utcnow()
            if self._last_embedding_at:
                delta_ms = (now - self._last_embedding_at).total_seconds() * 1000
                if delta_ms < self._min_embed_interval_ms:
                    # sleep blocking small (acceptable, low volume) to smooth spikes
                    wait_ms = self._min_embed_interval_ms - int(delta_ms)
                    if wait_ms > 0:
                        import time
                        time.sleep(wait_ms / 1000.0)
            self._last_embedding_at = datetime.utcnow()

            # Cooldown if we previously hit quota 429
            if self._openai_cooldown_until and datetime.utcnow() < self._openai_cooldown_until:
                logger.debug("OpenAI embedding em cooldown — usando fallback local diretamente")
            else:
                self._ensure_openai_client()

            if self.use_openai_embeddings and self.openai_client:
                try:
                    resp = self.openai_client.embeddings.create(
                        model=self.openai_embed_model,
                        input=[text]
                    )
                    vec = resp.data[0].embedding
                    if len(vec) != self.openai_embed_dim:
                        raise ValueError(f"Dimensão retornada {len(vec)} != {self.openai_embed_dim}")
                    return vec
                except Exception as oe:
                    msg = str(oe)
                    # Detect quota / 429 to start longer cooldown
                    if 'insufficient_quota' in msg or '429' in msg:
                        self._openai_cooldown_until = datetime.utcnow() + timedelta(seconds=self._openai_cooldown_seconds)
                        logger.warning(
                            f"Falha OpenAI embedding (quota/429) — iniciando cooldown até {self._openai_cooldown_until.isoformat()}"
                        )
                    else:
                        logger.warning(f"Falha OpenAI embedding: {oe} — fallback local")
                    # continue to fallback

            # Local encode fallback
            embedding_model = self._ensure_local_embedding_model()
            if embedding_model is None:
                return None
            local_vec = embedding_model.encode([text])[0].tolist()
            if self.use_openai_embeddings:
                if len(local_vec) < self.openai_embed_dim:
                    diff = self.openai_embed_dim - len(local_vec)
                    local_vec.extend([0.0] * diff)
                elif len(local_vec) > self.openai_embed_dim:
                    local_vec = local_vec[:self.openai_embed_dim]
            return local_vec
        except Exception as e:
            logger.error(f"❌ Erro ao gerar embedding: {e}")
            return None

# Singleton instance
supabase_client = SupabaseClient()

# -------------------------------------------------------------------
# SUGESTÃO DE SCHEMA (executar manualmente no Supabase) para embedding_metadata:
#
# CREATE TABLE IF NOT EXISTS embedding_metadata (
#   id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
#   doc_id text,
#   vector_id text UNIQUE,
#   model text NOT NULL,
#   meta jsonb DEFAULT '{}'::jsonb,
#   created_at timestamptz DEFAULT now()
# );
#
# CREATE INDEX IF NOT EXISTS idx_embedding_metadata_doc_id ON embedding_metadata(doc_id);
# CREATE INDEX IF NOT EXISTS idx_embedding_metadata_model ON embedding_metadata(model);
# -------------------------------------------------------------------
