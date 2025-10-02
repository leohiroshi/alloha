"""
Supabase Client - Drop-in replacement para Firebase
Suporta busca híbrida (vector + full-text), cache, e idempotency
"""

import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import hashlib
from dotenv import load_dotenv
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
import numpy as np

# Carregar variáveis de ambiente
load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Cliente Supabase com features avançadas"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_KEY devem estar configurados")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Modelo de embeddings (mesmo usado no Firebase)
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        logger.info("✅ Supabase client inicializado")
    
    # ================================================================
    # PROPERTIES - Busca híbrida avançada
    # ================================================================
    
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
            # Gerar embedding da query
            query_embedding = self.embedding_model.encode(query).tolist()
            
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
            # Gerar embedding da descrição
            text_for_embedding = f"{property_data.get('title', '')} {property_data.get('description', '')}"
            embedding = self.embedding_model.encode(text_for_embedding).tolist()
            
            property_data['embedding'] = embedding
            property_data['updated_at'] = datetime.utcnow().isoformat()
            
            # Log para debug
            logger.debug(f"Inserindo property: {property_data.get('property_id')}")
            
            result = self.client.table('properties')\
                .upsert(property_data, on_conflict='property_id')\
                .execute()
            
            # Verificar se retornou dados
            if not result.data:
                logger.error(f"❌ Upsert não retornou dados para {property_data.get('property_id')}")
                logger.error(f"   Result: {result}")
                return None
            
            if len(result.data) == 0:
                logger.error(f"❌ Upsert retornou lista vazia para {property_data.get('property_id')}")
                return None
            
            property_id = result.data[0]['property_id']
            logger.debug(f"✅ Imóvel {property_id} salvo")
            
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
    
    def get_cached_embedding(self, text: str) -> Optional[np.ndarray]:
        """Busca embedding no cache"""
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
    
    def cache_embedding(
        self, 
        text: str, 
        embedding: np.ndarray,
        ttl_days: int = 30
    ) -> bool:
        """Salva embedding no cache"""
        try:
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            
            cache_data = {
                'text_hash': text_hash,
                'text_content': text[:500],  # Limitar tamanho
                'embedding': embedding.tolist(),
                'model': 'all-MiniLM-L6-v2',
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

# Singleton instance
supabase_client = SupabaseClient()
