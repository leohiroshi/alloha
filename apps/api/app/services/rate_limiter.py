"""Rate Limiter simples baseado em Redis.

Uso:
from app.services.rate_limiter import allow
ok, remaining = await allow("msg:user_phone", limit=20, window=60)

Fallback: se Redis indisponível sempre permite (para não quebrar fluxo principal).
"""
from __future__ import annotations
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

async def allow(key: str, limit: int, window: int) -> Tuple[bool, int]:
    try:
        from . import redis_client
        allowed, remaining = await redis_client.rate_limit(f"rl:{key}", limit, window)
        return allowed, remaining
    except Exception as e:  # pragma: no cover
        logger.debug(f"Rate limiter fallback (allow all) {e}")
        return True, limit
