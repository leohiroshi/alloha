from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse, urlunparse

import aiohttp


DEFAULT_TIMEOUT_SECONDS = 12
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; AllohaSiteInspector/1.0; +https://www.alloha.app)"
)


def normalize_site_url(raw_url: str) -> str:
    candidate = (raw_url or "").strip()
    if not candidate:
        return ""

    if "://" not in candidate:
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""

    normalized_path = parsed.path if parsed.path not in {"", "/"} else ""
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc.lower(),
            normalized_path,
            "",
            "",
            "",
        )
    )


def get_supported_scraper_hosts() -> set[str]:
    raw_hosts = os.getenv("SCRAPER_SUPPORTED_HOSTS", "")
    hosts = {
        host.strip().lower()
        for host in raw_hosts.split(",")
        if host.strip()
    }
    hosts.update({"allegaimoveis.com", "www.allegaimoveis.com"})
    return hosts


def is_scraper_fallback_enabled() -> bool:
    return os.getenv("ENABLE_SCRAPER_FALLBACK", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _extract_title(html: str) -> Optional[str]:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return title or None


def _extract_generator(html: str) -> Optional[str]:
    patterns = [
        r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)["\']',
        r'"generator"\s*:\s*"([^"]+)"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    if "__NEXT_DATA__" in html:
        return "Next.js"
    if "wp-content" in html or "wordpress" in html.lower():
        return "WordPress"
    return None


async def inspect_real_estate_site(site_url: str) -> Dict[str, Any]:
    normalized_url = normalize_site_url(site_url)
    if not normalized_url:
        return {
            "provided": False,
            "submitted_url": site_url,
            "normalized_url": "",
            "reachable": False,
            "http_status": None,
            "final_url": None,
            "host": None,
            "page_title": None,
            "platform_hint": None,
            "scrape_supported": False,
            "recommended_source": "site_required",
            "ready_for_ingest": False,
            "message": "Informe a URL do site da imobiliária para validar a fonte dos imóveis.",
        }

    parsed = urlparse(normalized_url)
    host = (parsed.netloc or "").lower()
    supported_hosts = get_supported_scraper_hosts()
    official_feed_configured = bool(os.getenv("OFFICIAL_FEED_URL", "").strip())
    scraper_fallback_enabled = is_scraper_fallback_enabled()

    inspection: Dict[str, Any] = {
        "provided": True,
        "submitted_url": site_url,
        "normalized_url": normalized_url,
        "reachable": False,
        "http_status": None,
        "final_url": normalized_url,
        "host": host,
        "page_title": None,
        "platform_hint": None,
        "scrape_supported": host in supported_hosts,
        "scraper_fallback_enabled": scraper_fallback_enabled,
        "recommended_source": "manual_review",
        "ready_for_ingest": False,
        "message": "",
    }

    timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT_SECONDS)
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(normalized_url, allow_redirects=True) as response:
                html = await response.text(errors="ignore")
                inspection["http_status"] = response.status
                inspection["reachable"] = response.status < 400
                inspection["final_url"] = str(response.url)
                inspection["page_title"] = _extract_title(html)
                inspection["platform_hint"] = _extract_generator(html)
    except Exception as exc:
        inspection["message"] = (
            "Não foi possível acessar o site informado agora. "
            f"Detalhe técnico: {exc}"
        )
        return inspection

    if official_feed_configured:
        inspection["recommended_source"] = "official_feed"
        inspection["ready_for_ingest"] = inspection["reachable"]
        inspection["message"] = (
            "Site validado. A carga pode seguir pela fonte oficial já configurada."
        )
        return inspection

    if inspection["scrape_supported"] and scraper_fallback_enabled:
        inspection["recommended_source"] = "scraper_fallback"
        inspection["ready_for_ingest"] = inspection["reachable"]
        inspection["message"] = (
            "Site validado e compatível com o adaptador atual de scrape."
        )
        return inspection

    if inspection["scrape_supported"] and not scraper_fallback_enabled:
        inspection["recommended_source"] = "scraper_supported_but_disabled"
        inspection["ready_for_ingest"] = False
        inspection["message"] = (
            "O site é compatível com o scraper atual, mas o scraper fallback está desligado neste ambiente."
        )
        return inspection

    inspection["recommended_source"] = "manual_review"
    inspection["ready_for_ingest"] = False
    inspection["message"] = (
        "Recebemos o site, mas o scraper atual ainda não suporta esse portal. "
        "Vamos precisar adaptar a fonte antes da primeira importação."
    )
    return inspection
