"""
Webhook Idempotente - Evita Duplicação Fantasma do WhatsApp
Suporta 1000+ chamadas/min sem quebrar limite da API Meta
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

class WebhookIdempotency:
    """Gerenciador de idempotência para webhooks WhatsApp"""
    
    def __init__(self, ttl_minutes: int = 60):
        self.ttl_minutes = ttl_minutes
        self.processed_messages: Dict[str, Dict] = {}
        self.processing_locks: Dict[str, asyncio.Lock] = {}
        
        # Cleanup task
        asyncio.create_task(self._cleanup_expired())
    
    def _generate_message_fingerprint(self, webhook_data: Dict[str, Any]) -> str:
        """Gera fingerprint único da mensagem para detectar duplicatas"""
        try:
            # Extrair dados únicos da mensagem
            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            
            if "messages" not in value:
                return None
            
            message = value["messages"][0]
            
            # Componentes únicos da mensagem
            components = {
                "message_id": message.get("id"),
                "from": message.get("from"),
                "timestamp": message.get("timestamp"),
                "type": message.get("type"),
            }
            
            # Adicionar conteúdo específico do tipo
            if message.get("type") == "text":
                components["body"] = message.get("text", {}).get("body")
            elif message.get("type") == "image":
                components["media_id"] = message.get("image", {}).get("id")
            
            # Gerar hash SHA-256 dos componentes
            fingerprint_str = json.dumps(components, sort_keys=True)
            return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
            
        except Exception as e:
            logger.error(f"Erro ao gerar fingerprint: {e}")
            return None
    
    async def is_duplicate(self, webhook_data: Dict[str, Any]) -> bool:
        """Verifica se a mensagem já foi processada"""
        fingerprint = self._generate_message_fingerprint(webhook_data)
        if not fingerprint:
            return False
        
        # Verificar se já existe
        if fingerprint in self.processed_messages:
            processed_at = self.processed_messages[fingerprint]["processed_at"]
            age_minutes = (datetime.utcnow() - processed_at).total_seconds() / 60
            
            if age_minutes < self.ttl_minutes:
                logger.info(f"Mensagem duplicada detectada: {fingerprint}")
                return True
            else:
                # Expirada, remover
                del self.processed_messages[fingerprint]
        
        return False
    
    async def mark_as_processing(self, webhook_data: Dict[str, Any]) -> Optional[str]:
        """Marca mensagem como em processamento (thread-safe)"""
        fingerprint = self._generate_message_fingerprint(webhook_data)
        if not fingerprint:
            return None
        
        # Criar lock se não existir
        if fingerprint not in self.processing_locks:
            self.processing_locks[fingerprint] = asyncio.Lock()
        
        # Verificar/marcar de forma thread-safe
        async with self.processing_locks[fingerprint]:
            # Verificar novamente (double-check locking)
            if fingerprint in self.processed_messages:
                return None  # Já processada por outra thread
            
            # Marcar como processando
            self.processed_messages[fingerprint] = {
                "status": "processing",
                "started_at": datetime.utcnow(),
                "webhook_data": {
                    "from": webhook_data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("messages", [{}])[0].get("from"),
                    "message_id": webhook_data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {}).get("messages", [{}])[0].get("id")
                }
            }
            
            logger.debug(f"Mensagem marcada para processamento: {fingerprint}")
            return fingerprint
    
    async def mark_as_completed(self, fingerprint: str, result: Dict[str, Any] = None):
        """Marca mensagem como processada com sucesso"""
        if fingerprint in self.processed_messages:
            self.processed_messages[fingerprint].update({
                "status": "completed",
                "processed_at": datetime.utcnow(),
                "result": result or {}
            })
            logger.debug(f"Mensagem completada: {fingerprint}")
    
    async def mark_as_failed(self, fingerprint: str, error: str):
        """Marca mensagem como falhada (permitirá retry)"""
        if fingerprint in self.processed_messages:
            self.processed_messages[fingerprint].update({
                "status": "failed",
                "processed_at": datetime.utcnow(),
                "error": error
            })
            logger.warning(f"Mensagem falhou: {fingerprint} - {error}")
    
    async def _cleanup_expired(self):
        """Task de limpeza de mensagens expiradas"""
        while True:
            try:
                await asyncio.sleep(300)  # Cleanup a cada 5 minutos
                
                cutoff = datetime.utcnow() - timedelta(minutes=self.ttl_minutes)
                expired_keys = []
                
                for fingerprint, data in self.processed_messages.items():
                    processed_at = data.get("processed_at") or data.get("started_at")
                    if processed_at and processed_at < cutoff:
                        expired_keys.append(fingerprint)
                
                # Remover expiradas
                for key in expired_keys:
                    del self.processed_messages[key]
                    if key in self.processing_locks:
                        del self.processing_locks[key]
                
                if expired_keys:
                    logger.info(f"Limpeza: {len(expired_keys)} mensagens expiradas removidas")
                
            except Exception as e:
                logger.error(f"Erro na limpeza de mensagens: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Estatísticas do sistema de idempotência"""
        now = datetime.utcnow()
        
        by_status = {}
        by_age = {"last_hour": 0, "last_day": 0, "older": 0}
        
        for data in self.processed_messages.values():
            # Por status
            status = data.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1
            
            # Por idade
            timestamp = data.get("processed_at") or data.get("started_at")
            if timestamp:
                age_hours = (now - timestamp).total_seconds() / 3600
                if age_hours <= 1:
                    by_age["last_hour"] += 1
                elif age_hours <= 24:
                    by_age["last_day"] += 1
                else:
                    by_age["older"] += 1
        
        return {
            "total_messages": len(self.processed_messages),
            "by_status": by_status,
            "by_age": by_age,
            "ttl_minutes": self.ttl_minutes
        }

# Instância global
webhook_idempotency = WebhookIdempotency()