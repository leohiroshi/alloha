"""
Listing ingestion service.

Features:
- Official feed first, scraper fallback
- Redis distributed lock
- Change detection by content_hash
- Deactivate unseen listings after two missed runs
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from app.services import redis_client
from app.services.listing_sources import build_default_adapters, ListingSourceAdapter
from app.services.supabase_client import supabase_client

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    success: bool
    run_id: str
    source_used: str
    total_seen: int
    inserted_or_updated: int
    unchanged: int
    deactivated: int
    lock_acquired: bool
    started_at: str
    finished_at: str
    message: str


class ListingIngestService:
    def __init__(self, adapters: Optional[List[ListingSourceAdapter]] = None) -> None:
        self.adapters = adapters or build_default_adapters()
        self.lock_key = "jobs:ingest:lock"
        self.lock_ttl_seconds = 50 * 60
        self.run_counter_key = "jobs:ingest:runs"

    @staticmethod
    def _hash_payload(item: Dict[str, Any]) -> str:
        canonical = {
            "title": item.get("title"),
            "description": item.get("description"),
            "price": item.get("price"),
            "status": item.get("status"),
            "bedrooms": item.get("bedrooms"),
            "bathrooms": item.get("bathrooms"),
            "area_total": item.get("area_total"),
            "transaction_type": item.get("transaction_type"),
            "property_type": item.get("property_type"),
            "neighborhood": item.get("neighborhood"),
            "city": item.get("city"),
        }
        raw = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_property_id(item: Dict[str, Any]) -> Optional[str]:
        prop_id = str(
            item.get("property_id")
            or item.get("external_id")
            or item.get("reference")
            or item.get("url")
            or ""
        ).strip()
        return prop_id or None

    async def _load_existing_map(self) -> Dict[str, Dict[str, Any]]:
        client = supabase_client.require_client()
        result = client.table("properties").select(
            "property_id, status, content_hash, is_deleted"
        ).execute()
        rows = result.data or []
        return {row.get("property_id"): row for row in rows if row.get("property_id")}

    async def _deactivate_missed(self, seen_ids: Set[str]) -> int:
        client = supabase_client.require_client()
        result = client.table("properties").select("property_id, status").eq(
            "status", "active"
        ).execute()
        rows = result.data or []
        deactivated = 0
        now_iso = datetime.now(timezone.utc).isoformat()
        for row in rows:
            prop_id = row.get("property_id")
            if not prop_id or prop_id in seen_ids:
                continue

            missed_key = f"ingest:missed:{prop_id}"
            misses = await redis_client.incr(missed_key, ex=3 * 24 * 60 * 60)
            if misses < 2:
                continue
            try:
                client.table("properties").update(
                    {
                        "status": "inactive",
                        "is_deleted": True,
                        "updated_at": now_iso,
                    }
                ).eq("property_id", prop_id).execute()
                deactivated += 1
            except Exception as exc:
                logger.warning("Failed to deactivate property %s: %s", prop_id, exc)
        return deactivated

    async def run(self, force_full: bool = False) -> IngestResult:
        started_at = datetime.now(timezone.utc)
        run_id = f"ing-{uuid.uuid4().hex[:10]}"
        lock_acquired = await redis_client.acquire_lock(
            self.lock_key, ttl=self.lock_ttl_seconds
        )
        if not lock_acquired:
            try:
                await redis_client.incr("metrics:ingest:lock_contention", ex=24 * 60 * 60)
            except Exception:
                pass
            now_iso = datetime.now(timezone.utc).isoformat()
            return IngestResult(
                success=False,
                run_id=run_id,
                source_used="none",
                total_seen=0,
                inserted_or_updated=0,
                unchanged=0,
                deactivated=0,
                lock_acquired=False,
                started_at=now_iso,
                finished_at=now_iso,
                message="Another ingest run is currently active.",
            )

        source_used = "none"
        listings: List[Dict[str, Any]] = []
        for adapter in self.adapters:
            try:
                rows = await adapter.fetch_listings()
            except Exception as exc:
                logger.warning("Adapter %s failed: %s", adapter.source_name, exc)
                rows = []
            if rows:
                source_used = adapter.source_name
                listings = rows
                break

        inserted_or_updated = 0
        unchanged = 0
        seen_ids: Set[str] = set()
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            if not listings:
                finished_at = datetime.now(timezone.utc)
                message = "No listing source configured or no listings were returned."
                try:
                    await redis_client.set("metrics:ingest:last_total_seen", 0, ex=7 * 24 * 60 * 60)
                    await redis_client.set("metrics:ingest:last_changed", 0, ex=7 * 24 * 60 * 60)
                    await redis_client.set("metrics:ingest:last_unchanged", 0, ex=7 * 24 * 60 * 60)
                    await redis_client.set("metrics:ingest:last_deactivated", 0, ex=7 * 24 * 60 * 60)
                    await redis_client.set("metrics:ingest:last_source", source_used, ex=7 * 24 * 60 * 60)
                    await redis_client.set("metrics:ingest:last_finished_at", finished_at.isoformat(), ex=7 * 24 * 60 * 60)
                except Exception:
                    pass
                return IngestResult(
                    success=False,
                    run_id=run_id,
                    source_used=source_used,
                    total_seen=0,
                    inserted_or_updated=0,
                    unchanged=0,
                    deactivated=0,
                    lock_acquired=True,
                    started_at=started_at.isoformat(),
                    finished_at=finished_at.isoformat(),
                    message=message,
                )

            existing = await self._load_existing_map()
            for raw in listings:
                prop_id = self._normalize_property_id(raw)
                if not prop_id:
                    continue
                seen_ids.add(prop_id)
                content_hash = self._hash_payload(raw)
                prev = existing.get(prop_id, {})
                prev_hash = prev.get("content_hash")

                if not force_full and prev_hash and prev_hash == content_hash:
                    unchanged += 1
                    continue

                record = {
                    **raw,
                    "property_id": prop_id,
                    "external_id": raw.get("external_id") or prop_id,
                    "source": raw.get("source") or source_used,
                    "content_hash": content_hash,
                    "source_updated_at": raw.get("source_updated_at") or now_iso,
                    "last_seen_at": now_iso,
                    "is_deleted": False,
                    "status": raw.get("status") or "active",
                }
                # Upsert base record through existing normalization path.
                # Optional new columns are best-effort updates to avoid breakage if DB migration is pending.
                saved = supabase_client.upsert_property(record)
                if not saved:
                    continue

                try:
                    supabase_client.client.table("properties").update(
                        {
                            "content_hash": content_hash,
                            "source_updated_at": record["source_updated_at"],
                            "last_seen_at": now_iso,
                            "is_deleted": False,
                            "updated_at": now_iso,
                        }
                    ).eq("property_id", prop_id).execute()
                except Exception as exc:
                    logger.debug(
                        "Optional columns update skipped for property_id=%s: %s",
                        prop_id,
                        exc,
                    )

                inserted_or_updated += 1
                await redis_client.set(f"ingest:missed:{prop_id}", "0", ex=3 * 24 * 60 * 60)

            deactivated = await self._deactivate_missed(seen_ids)
            await redis_client.incr(self.run_counter_key, ex=24 * 60 * 60)
            finished_at = datetime.now(timezone.utc)
            try:
                await redis_client.set("metrics:ingest:last_total_seen", len(seen_ids), ex=7 * 24 * 60 * 60)
                await redis_client.set("metrics:ingest:last_changed", inserted_or_updated, ex=7 * 24 * 60 * 60)
                await redis_client.set("metrics:ingest:last_unchanged", unchanged, ex=7 * 24 * 60 * 60)
                await redis_client.set("metrics:ingest:last_deactivated", deactivated, ex=7 * 24 * 60 * 60)
                await redis_client.set("metrics:ingest:last_source", source_used, ex=7 * 24 * 60 * 60)
                await redis_client.set("metrics:ingest:last_finished_at", finished_at.isoformat(), ex=7 * 24 * 60 * 60)
            except Exception:
                pass
            return IngestResult(
                success=True,
                run_id=run_id,
                source_used=source_used,
                total_seen=len(seen_ids),
                inserted_or_updated=inserted_or_updated,
                unchanged=unchanged,
                deactivated=deactivated,
                lock_acquired=True,
                started_at=started_at.isoformat(),
                finished_at=finished_at.isoformat(),
                message="Ingest completed.",
            )
        finally:
            try:
                elapsed_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
                await redis_client.set("metrics:ingest:last_duration_ms", elapsed_ms, ex=7 * 24 * 60 * 60)
                await redis_client.set("metrics:ingest:last_run_id", run_id, ex=7 * 24 * 60 * 60)
            except Exception:
                pass
            await redis_client.release_lock(self.lock_key)


ingest_service = ListingIngestService()
