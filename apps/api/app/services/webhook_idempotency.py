"""
Webhook idempotency with Redis-first storage.

Fallback to in-memory cache when Redis is unavailable.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.services import redis_client

logger = logging.getLogger(__name__)


class WebhookIdempotency:
    def __init__(self, ttl_minutes: int = 60) -> None:
        self.ttl_minutes = ttl_minutes
        self.processed_messages: Dict[str, Dict[str, Any]] = {}
        self.processing_locks: Dict[str, asyncio.Lock] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    @staticmethod
    def _extract_message_identity(webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            entry = webhook_data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            if "messages" not in value:
                return None
            message = value["messages"][0]
            identity = {
                "message_id": message.get("id"),
                "from": message.get("from"),
                "timestamp": message.get("timestamp"),
                "type": message.get("type"),
            }
            if message.get("type") == "text":
                identity["body"] = message.get("text", {}).get("body")
            if message.get("type") == "image":
                identity["media_id"] = message.get("image", {}).get("id")
            return identity
        except Exception:
            return None

    def _generate_message_fingerprint(self, webhook_data: Dict[str, Any]) -> Optional[str]:
        identity = self._extract_message_identity(webhook_data)
        if not identity:
            return None
        raw = json.dumps(identity, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def _redis_key(fingerprint: str) -> str:
        return f"wh:idemp:{fingerprint}"

    async def _redis_get_status(self, fingerprint: str) -> Optional[str]:
        raw = await redis_client.get(self._redis_key(fingerprint))
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return str(data.get("status"))
        except Exception:
            return None

    async def _redis_set_payload(
        self, fingerprint: str, payload: Dict[str, Any], ttl_seconds: Optional[int] = None
    ) -> bool:
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_minutes * 60
        return await redis_client.set(
            self._redis_key(fingerprint), json.dumps(payload, ensure_ascii=False), ex=ttl
        )

    async def _mark_processing_redis(self, fingerprint: str, payload: Dict[str, Any]) -> bool:
        # Acquire a short lock key, then write processing state with TTL.
        lock_key = f"wh:idemp:lock:{fingerprint}"
        if not await redis_client.acquire_lock(lock_key, ttl=15):
            return False
        existing = await self._redis_get_status(fingerprint)
        if existing:
            await redis_client.release_lock(lock_key)
            return False
        ok = await self._redis_set_payload(
            fingerprint,
            {"status": "processing", "started_at": datetime.now(timezone.utc).isoformat(), **payload},
        )
        await redis_client.release_lock(lock_key)
        return ok

    def start(self) -> None:
        if self._cleanup_task is None or self._cleanup_task.done():
            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self._cleanup_expired())
            except RuntimeError:
                logger.warning("WebhookIdempotency.start() called without running loop.")

    async def is_duplicate(self, webhook_data: Dict[str, Any]) -> bool:
        fingerprint = self._generate_message_fingerprint(webhook_data)
        if not fingerprint:
            return False

        # Redis-first
        redis_status = await self._redis_get_status(fingerprint)
        if redis_status in {"processing", "completed"}:
            return True

        # Memory fallback
        if fingerprint in self.processed_messages:
            processed_at = self.processed_messages[fingerprint].get("processed_at") or self.processed_messages[
                fingerprint
            ].get("started_at")
            if isinstance(processed_at, datetime):
                age_minutes = (datetime.now(timezone.utc) - processed_at).total_seconds() / 60
                if age_minutes < self.ttl_minutes:
                    return True
            self.processed_messages.pop(fingerprint, None)
        return False

    async def mark_as_processing(self, webhook_data: Dict[str, Any]) -> Optional[str]:
        fingerprint = self._generate_message_fingerprint(webhook_data)
        if not fingerprint:
            return None

        identity = self._extract_message_identity(webhook_data) or {}
        payload = {"message": identity}

        # Redis-first path
        if await self._mark_processing_redis(fingerprint, payload):
            return fingerprint

        # Memory fallback
        if fingerprint not in self.processing_locks:
            self.processing_locks[fingerprint] = asyncio.Lock()
        async with self.processing_locks[fingerprint]:
            if fingerprint in self.processed_messages:
                return None
            self.processed_messages[fingerprint] = {
                "status": "processing",
                "started_at": datetime.now(timezone.utc),
                **payload,
            }
            return fingerprint

    async def mark_as_completed(self, fingerprint: str, result: Optional[Dict[str, Any]] = None) -> None:
        await self._redis_set_payload(
            fingerprint,
            {
                "status": "completed",
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "result": result or {},
            },
        )
        if fingerprint in self.processed_messages:
            self.processed_messages[fingerprint].update(
                {
                    "status": "completed",
                    "processed_at": datetime.now(timezone.utc),
                    "result": result or {},
                }
            )

    async def mark_as_failed(self, fingerprint: str, error: str) -> None:
        await self._redis_set_payload(
            fingerprint,
            {
                "status": "failed",
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "error": error,
            },
            ttl_seconds=min(self.ttl_minutes * 60, 15 * 60),
        )
        if fingerprint in self.processed_messages:
            self.processed_messages[fingerprint].update(
                {
                    "status": "failed",
                    "processed_at": datetime.now(timezone.utc),
                    "error": error,
                }
            )

    async def _cleanup_expired(self) -> None:
        while True:
            await asyncio.sleep(300)
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.ttl_minutes)
            expired = []
            for fp, data in self.processed_messages.items():
                ts = data.get("processed_at") or data.get("started_at")
                if isinstance(ts, datetime) and ts < cutoff:
                    expired.append(fp)
            for fp in expired:
                self.processed_messages.pop(fp, None)
                self.processing_locks.pop(fp, None)

    def get_stats(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        by_status: Dict[str, int] = {}
        for data in self.processed_messages.values():
            status = str(data.get("status", "unknown"))
            by_status[status] = by_status.get(status, 0) + 1
        return {
            "memory_total_messages": len(self.processed_messages),
            "memory_by_status": by_status,
            "ttl_minutes": self.ttl_minutes,
            "generated_at": now.isoformat(),
        }


webhook_idempotency = WebhookIdempotency()
