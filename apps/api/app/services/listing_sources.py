"""
Listing source adapters.

Priority order for ingestion:
1) Official feed adapter
2) Scraper fallback adapter
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class ListingSourceAdapter(ABC):
    source_name: str

    @abstractmethod
    async def fetch_listings(self) -> List[Dict[str, Any]]:
        raise NotImplementedError


class OfficialFeedAdapter(ListingSourceAdapter):
    source_name = "official_feed"

    def __init__(self) -> None:
        self.feed_url = os.getenv("OFFICIAL_FEED_URL", "").strip()
        self.feed_token = os.getenv("OFFICIAL_FEED_TOKEN", "").strip()
        self.timeout_seconds = int(os.getenv("OFFICIAL_FEED_TIMEOUT_SECONDS", "30"))

    async def fetch_listings(self) -> List[Dict[str, Any]]:
        if not self.feed_url:
            logger.info("OFFICIAL_FEED_URL not configured; skipping official feed adapter.")
            return []

        headers = {"Content-Type": "application/json"}
        if self.feed_token:
            headers["Authorization"] = f"Bearer {self.feed_token}"

        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.feed_url, headers=headers) as resp:
                    if resp.status >= 400:
                        logger.warning(
                            "Official feed request failed status=%s", resp.status
                        )
                        return []
                    payload = await resp.json()
        except Exception as exc:
            logger.warning("Official feed fetch error: %s", exc)
            return []

        listings = payload if isinstance(payload, list) else payload.get("listings", [])
        normalized: List[Dict[str, Any]] = []
        for item in listings:
            if not isinstance(item, dict):
                continue
            listing_id = str(
                item.get("property_id")
                or item.get("id")
                or item.get("external_id")
                or item.get("reference")
                or ""
            ).strip()
            if not listing_id:
                continue
            normalized.append(
                {
                    "property_id": listing_id,
                    "external_id": item.get("external_id") or listing_id,
                    "source": self.source_name,
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "price": item.get("price"),
                    "transaction_type": item.get("transaction_type"),
                    "property_type": item.get("property_type"),
                    "address": item.get("address"),
                    "neighborhood": item.get("neighborhood"),
                    "city": item.get("city"),
                    "state": item.get("state"),
                    "zipcode": item.get("zipcode"),
                    "bedrooms": item.get("bedrooms"),
                    "bathrooms": item.get("bathrooms"),
                    "parking_spaces": item.get("parking_spaces"),
                    "area_total": item.get("area_total"),
                    "area_useful": item.get("area_useful"),
                    "images": item.get("images") or [],
                    "main_image": item.get("main_image"),
                    "status": item.get("status", "active"),
                    "url": item.get("url"),
                    "source_updated_at": item.get("updated_at")
                    or datetime.now(timezone.utc).isoformat(),
                }
            )

        logger.info("Official feed adapter returned %s listings", len(normalized))
        return normalized


class ScraperFallbackAdapter(ListingSourceAdapter):
    source_name = "scraper_fallback"

    def __init__(self) -> None:
        self.enabled = _env_flag("ENABLE_SCRAPER_FALLBACK", default=False)
        self.max_properties = int(os.getenv("SCRAPER_MAX_PROPERTIES", "80"))
        self._scraper: Optional[Any] = None

    def _get_scraper(self) -> Optional[Any]:
        if not self.enabled:
            return None
        if self._scraper is not None:
            return self._scraper
        try:
            from app.services.property_scraper import AllegaPropertyScraper
        except Exception as exc:
            logger.warning("Scraper fallback indisponível: %s", exc)
            return None
        self._scraper = AllegaPropertyScraper(headless=True)
        return self._scraper

    async def fetch_listings(self) -> List[Dict[str, Any]]:
        scraper = self._get_scraper()
        if scraper is None:
            if self.enabled:
                logger.warning("ENABLE_SCRAPER_FALLBACK=1, mas o scraper não pôde ser carregado.")
            else:
                logger.info("ENABLE_SCRAPER_FALLBACK=0; fallback por scraper desativado.")
            return []
        max_per_type = max(1, self.max_properties // 4)
        rows = await scraper.scrape_all_properties(max_per_type=max_per_type)
        normalized: List[Dict[str, Any]] = []
        now_iso = datetime.now(timezone.utc).isoformat()
        for item in rows:
            if not isinstance(item, dict):
                continue
            listing_id = str(
                item.get("property_id")
                or item.get("external_id")
                or item.get("reference")
                or item.get("url")
                or ""
            ).strip()
            if not listing_id:
                continue
            normalized.append(
                {
                    "property_id": listing_id,
                    "external_id": item.get("external_id")
                    or item.get("reference")
                    or listing_id,
                    "source": self.source_name,
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "price": item.get("price"),
                    "transaction_type": item.get("transaction_type"),
                    "property_type": item.get("property_type"),
                    "address": item.get("address"),
                    "neighborhood": item.get("neighborhood"),
                    "city": item.get("city"),
                    "state": item.get("uf") or item.get("state"),
                    "zipcode": item.get("zipcode"),
                    "bedrooms": item.get("bedrooms"),
                    "bathrooms": item.get("bathrooms"),
                    "parking_spaces": item.get("parking_spaces"),
                    "area_total": item.get("area_total") or item.get("area_m2"),
                    "area_useful": item.get("area_useful"),
                    "images": item.get("images") or [],
                    "main_image": (item.get("images") or [None])[0] or item.get("main_image"),
                    "status": item.get("status", "active"),
                    "url": item.get("url"),
                    "source_updated_at": item.get("scraped_at") or now_iso,
                }
            )
        logger.info("Scraper fallback adapter returned %s listings", len(normalized))
        return normalized


def build_default_adapters() -> List[ListingSourceAdapter]:
    adapters: List[ListingSourceAdapter] = [OfficialFeedAdapter()]
    if _env_flag("ENABLE_SCRAPER_FALLBACK", default=False):
        adapters.append(ScraperFallbackAdapter())
    return adapters
