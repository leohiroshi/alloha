"""Redis Client utilitário

Fornece inicialização lazy de um cliente assíncrono Redis para:
- Session cache distribuído
- Embedding cache (chaves simples)
- Rate limiting
- Locks simples (SET NX)

Env vars suportadas:
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=opcional
REDIS_TLS=1 (se precisar forçar rediss://)

Fallback automático: se não conseguir conectar, funções retornam None ou comportamento no-op,
permitindo que a aplicação continue usando caches em memória.
"""
from __future__ import annotations
import os
import asyncio
import logging
from typing import Optional, Any, Callable

try:
    import redis.asyncio as redis  # type: ignore
    from redis.asyncio import Redis as RedisType  # type: ignore
except ImportError:  # pragma: no cover
    redis = None  # type: ignore
    class RedisType:  # minimal stub
        ...

logger = logging.getLogger(__name__)

_redis_client: Optional[RedisType] = None
_init_lock = asyncio.Lock()

DEFAULT_TIMEOUT = 2.5  # segundos para operações simples


def _build_url() -> Optional[str]:
    url = os.getenv("REDIS_URL")
    if not url:
        host = os.getenv("REDIS_HOST", "localhost")
        port = os.getenv("REDIS_PORT", "6379")
        db = os.getenv("REDIS_DB", "0")
        scheme = "rediss" if os.getenv("REDIS_TLS") == "1" else "redis"
        url = f"{scheme}://{host}:{port}/{db}"
    return url


async def get_client() -> Optional[RedisType]:
    global _redis_client
    if redis is None:
        return None
    if _redis_client is not None:
        return _redis_client
    async with _init_lock:
        if _redis_client is not None:
            return _redis_client
        url = _build_url()
        if not url:
            return None
        try:
            password = os.getenv("REDIS_PASSWORD") or None
            _redis_client = redis.from_url(url, password=password, decode_responses=True, socket_timeout=3, retry_on_timeout=True)
            # teste ping rápido
            await asyncio.wait_for(_redis_client.ping(), timeout=3)
            logger.info(f"Redis conectado: {url}")
        except Exception as e:  # pragma: no cover
            logger.warning(f"Falha ao conectar no Redis ({url}): {e}")
            _redis_client = None
    return _redis_client


async def close():  # pragma: no cover
    global _redis_client
    if _redis_client:
        try:
            await _redis_client.close()
        except Exception:
            pass
        _redis_client = None


async def get(key: str) -> Optional[str]:
    client = await get_client()
    if not client:
        return None
    try:
        return await asyncio.wait_for(client.get(key), timeout=DEFAULT_TIMEOUT)
    except Exception:
        return None


async def set(key: str, value: Any, ex: int | None = None):
    client = await get_client()
    if not client:
        return False
    try:
        await asyncio.wait_for(client.set(key, value, ex=ex), timeout=DEFAULT_TIMEOUT)
        return True
    except Exception:
        return False


async def incr(key: str, ex: int | None = None) -> int:
    client = await get_client()
    if not client:
        return 0
    try:
        val = await asyncio.wait_for(client.incr(key), timeout=DEFAULT_TIMEOUT)
        if ex:
            await client.expire(key, ex)
        return int(val)
    except Exception:
        return 0


async def acquire_lock(lock_key: str, ttl: int = 10) -> bool:
    client = await get_client()
    if not client:
        return False
    try:
        # SET key value NX EX ttl
        res = await client.set(lock_key, "1", ex=ttl, nx=True)
        return bool(res)
    except Exception:
        return False


async def release_lock(lock_key: str):  # pragma: no cover
    client = await get_client()
    if not client:
        return
    try:
        await client.delete(lock_key)
    except Exception:
        pass


async def rate_limit(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Retorna (permitido, restante)."""
    current = await incr(key, ex=window_seconds)
    remaining = max(0, limit - current)
    return (current <= limit, remaining)


async def cached(key: str, ttl: int, producer: Callable[[], Any]):
    """Decorator util para cache simples: tenta get, senão chama producer e set."""
    cached_val = await get(key)
    if cached_val is not None:
        return cached_val
    value = await producer()
    try:
        await set(key, value, ex=ttl)
    except Exception:
        pass
    return value
