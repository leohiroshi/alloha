"""
Cache de Sessão - Últimas 50 propriedades mostradas por usuário
Reduz 30% das buscas vetoriais repetitivas
TTL: 24h
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class SessionCache:
    """Cache de propriedades mostradas por usuário"""
    
    def __init__(self, max_properties_per_user: int = 50, ttl_hours: int = 24):
        self.max_properties = max_properties_per_user
        self.ttl = timedelta(hours=ttl_hours)
        
        # Estrutura: {phone_hash: {"properties": [id1, id2, ...], "updated_at": datetime}}
        self._cache: Dict[str, Dict] = {}
    
    def add_shown_properties(self, phone_hash: str, property_ids: List[str]):
        """Adiciona propriedades mostradas ao cache"""
        
        now = datetime.utcnow()
        
        if phone_hash not in self._cache:
            self._cache[phone_hash] = {
                "properties": [],
                "updated_at": now
            }
        
        # Adicionar novas propriedades (evitar duplicatas)
        existing = set(self._cache[phone_hash]["properties"])
        new_props = [pid for pid in property_ids if pid not in existing]
        
        self._cache[phone_hash]["properties"].extend(new_props)
        self._cache[phone_hash]["updated_at"] = now
        
        # Manter apenas as últimas N propriedades
        if len(self._cache[phone_hash]["properties"]) > self.max_properties:
            self._cache[phone_hash]["properties"] = \
                self._cache[phone_hash]["properties"][-self.max_properties:]
        
        logger.debug(f"Cache updated for {phone_hash}: {len(self._cache[phone_hash]['properties'])} properties")
    
    def get_shown_properties(self, phone_hash: str) -> List[str]:
        """Retorna propriedades já mostradas (dentro do TTL)"""
        
        if phone_hash not in self._cache:
            return []
        
        # Verificar TTL
        age = datetime.utcnow() - self._cache[phone_hash]["updated_at"]
        
        if age > self.ttl:
            # Expirado - limpar
            del self._cache[phone_hash]
            logger.debug(f"Cache expired for {phone_hash}")
            return []
        
        return self._cache[phone_hash]["properties"].copy()
    
    def clear_user_cache(self, phone_hash: str):
        """Limpa cache de um usuário específico"""
        if phone_hash in self._cache:
            del self._cache[phone_hash]
            logger.info(f"Cache cleared for {phone_hash}")
    
    def clear_all(self):
        """Limpa todo o cache"""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"All cache cleared ({count} users)")
    
    def cleanup_expired(self):
        """Remove entradas expiradas (executar periodicamente)"""
        
        now = datetime.utcnow()
        expired_users = []
        
        for phone_hash, data in self._cache.items():
            age = now - data["updated_at"]
            if age > self.ttl:
                expired_users.append(phone_hash)
        
        for phone_hash in expired_users:
            del self._cache[phone_hash]
        
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired cache entries")
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas do cache"""
        
        total_users = len(self._cache)
        total_properties = sum(len(data["properties"]) for data in self._cache.values())
        
        avg_properties = total_properties / total_users if total_users > 0 else 0
        
        return {
            "total_users": total_users,
            "total_properties_cached": total_properties,
            "avg_properties_per_user": avg_properties,
            "max_properties_per_user": self.max_properties,
            "ttl_hours": self.ttl.total_seconds() / 3600
        }


# Instância global
session_cache = SessionCache(max_properties_per_user=50, ttl_hours=24)
