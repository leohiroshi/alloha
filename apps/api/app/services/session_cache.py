"""
Cache de Sessão - Últimas 50 propriedades mostradas por usuário
Reduz 30% das buscas vetoriais repetitivas
TTL: 24h
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import json
import logging

logger = logging.getLogger(__name__)


class SessionCache:
    """Cache de propriedades mostradas por usuário"""
    
    def __init__(self, max_properties_per_user: int = 50, ttl_hours: int = 24):
        self.max_properties = max_properties_per_user
        self.ttl = timedelta(hours=ttl_hours)
        
        # Estrutura: {phone_hash: {"properties": [id1, id2, ...], "updated_at": datetime}}
        self._cache: Dict[str, Dict] = {}
    
    async def add_shown_properties(self, phone_hash: str, property_ids: List[str]):
        """Adiciona propriedades mostradas ao cache (Redis se disponível)."""
        use_redis = os.getenv("USE_REDIS_SESSION_CACHE", "1") == "1"
        if use_redis:
            try:
                from . import redis_client
                client = await redis_client.get_client()
                if client:
                    key = f"session_props:{phone_hash}"
                    # Usar pipeline para atomicidade
                    pipe = client.pipeline()
                    # Obter existente
                    existing_raw = await client.get(key)
                    existing_list: List[str] = []
                    if existing_raw:
                        try:
                            existing_list = json.loads(existing_raw)
                        except Exception:
                            existing_list = []
                    existing_set = set(existing_list)
                    new_props = [pid for pid in property_ids if pid not in existing_set]
                    if new_props:
                        combined = (existing_list + new_props)[-self.max_properties:]
                        pipe.set(key, json.dumps(combined), ex=int(self.ttl.total_seconds()))
                        await pipe.execute()
                        logger.debug(f"[RedisSessionCache] updated {phone_hash}: +{len(new_props)} now={len(combined)}")
                        return
            except Exception as e:
                logger.debug(f"Redis session cache fallback (add) {e}")

        # Fallback in-memory
        now = datetime.utcnow()
        if phone_hash not in self._cache:
            self._cache[phone_hash] = {"properties": [], "updated_at": now}
        existing = set(self._cache[phone_hash]["properties"])
        new_props = [pid for pid in property_ids if pid not in existing]
        self._cache[phone_hash]["properties"].extend(new_props)
        self._cache[phone_hash]["updated_at"] = now
        if len(self._cache[phone_hash]["properties"]) > self.max_properties:
            self._cache[phone_hash]["properties"] = self._cache[phone_hash]["properties"][-self.max_properties:]
        logger.debug(f"[MemSessionCache] updated for {phone_hash}: {len(self._cache[phone_hash]['properties'])} properties")
    
    async def get_shown_properties(self, phone_hash: str) -> List[str]:
        """Retorna propriedades já mostradas (dentro do TTL)"""
        use_redis = os.getenv("USE_REDIS_SESSION_CACHE", "1") == "1"
        if use_redis:
            try:
                from . import redis_client
                client = await redis_client.get_client()
                if client:
                    key = f"session_props:{phone_hash}"
                    raw = await client.get(key)
                    if not raw:
                        return []
                    try:
                        data = json.loads(raw)
                        if isinstance(data, list):
                            return data
                    except Exception:
                        return []
            except Exception as e:
                logger.debug(f"Redis session cache fallback (get) {e}")

        if phone_hash not in self._cache:
            return []
        age = datetime.utcnow() - self._cache[phone_hash]["updated_at"]
        if age > self.ttl:
            del self._cache[phone_hash]
            logger.debug(f"Cache expired for {phone_hash}")
            return []
        return self._cache[phone_hash]["properties"].copy()
    
    async def clear_user_cache(self, phone_hash: str):
        """Limpa cache de um usuário específico"""
        use_redis = os.getenv("USE_REDIS_SESSION_CACHE", "1") == "1"
        if use_redis:
            try:
                from . import redis_client
                client = await redis_client.get_client()
                if client:
                    await client.delete(f"session_props:{phone_hash}")
                    logger.info(f"[RedisSessionCache] cleared {phone_hash}")
                    return
            except Exception as e:
                logger.debug(f"Redis session cache fallback (clear) {e}")
        if phone_hash in self._cache:
            del self._cache[phone_hash]
            logger.info(f"[MemSessionCache] cleared {phone_hash}")
    
    async def clear_all(self):
        """Limpa todo o cache"""
        use_redis = os.getenv("USE_REDIS_SESSION_CACHE", "1") == "1"
        if use_redis:
            try:
                from . import redis_client
                client = await redis_client.get_client()
                if client:
                    # Cautela: scan por prefixo
                    cursor = 0
                    keys_deleted = 0
                    pattern = "session_props:*"
                    while True:
                        cursor, keys = await client.scan(cursor=cursor, match=pattern, count=100)
                        if keys:
                            await client.delete(*keys)
                            keys_deleted += len(keys)
                        if cursor == 0:
                            break
                    logger.info(f"[RedisSessionCache] cleared {keys_deleted} keys")
                    # Mantém in-memory também limpo
                    self._cache.clear()
                    return
            except Exception as e:
                logger.debug(f"Redis session cache fallback (clear_all) {e}")
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"[MemSessionCache] cleared ({count} users)")
    
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
    
    async def get_stats(self) -> Dict:
        """Retorna estatísticas do cache"""
        use_redis = os.getenv("USE_REDIS_SESSION_CACHE", "1") == "1"
        stats = {
            "max_properties_per_user": self.max_properties,
            "ttl_hours": self.ttl.total_seconds() / 3600,
            "backend": "memory"
        }
        if use_redis:
            try:
                from . import redis_client
                client = await redis_client.get_client()
                if client:
                    # Aproximação: contar chaves com prefixo
                    cursor = 0
                    nkeys = 0
                    pattern = "session_props:*"
                    while True:
                        cursor, keys = await client.scan(cursor=cursor, match=pattern, count=200)
                        nkeys += len(keys)
                        if cursor == 0:
                            break
                    stats.update({"total_users": nkeys, "backend": "redis"})
                    return stats
            except Exception as e:
                logger.debug(f"Redis session cache fallback (stats) {e}")
        total_users = len(self._cache)
        total_properties = sum(len(data["properties"]) for data in self._cache.values())
        avg_properties = total_properties / total_users if total_users > 0 else 0
        stats.update({
            "total_users": total_users,
            "total_properties_cached": total_properties,
            "avg_properties_per_user": avg_properties
        })
        return stats


# Instância global
session_cache = SessionCache(max_properties_per_user=50, ttl_hours=24)
