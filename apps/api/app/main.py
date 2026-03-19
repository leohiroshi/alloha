"""
Alloha Core API

Scope:
- WhatsApp webhook handling
- Canonical /v1 chat + listings + ingest endpoints
- Redis-backed idempotency and model guardrails
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.services import redis_client
from app.services.email_service import resend_configured, send_support_ticket, support_email_to
from app.services.ingest_service import ingest_service
from app.services.model_gateway import model_gateway
from app.services.supabase_client import supabase_client
from app.services.webhook_idempotency import webhook_idempotency
from app.services.whatsapp_service import WhatsAppService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alloha-core")


def _phone_hash(raw: str) -> str:
    return hashlib.sha256((raw or "").encode("utf-8")).hexdigest()[:12]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request_id() -> str:
    return f"req-{uuid.uuid4().hex[:12]}"


def _log_event(event: str, **fields: Any) -> None:
    safe_fields = {k: v for k, v in fields.items() if v is not None}
    logger.info("%s %s", event, safe_fields)


VERIFY_TOKEN = os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "alloha_secret")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
INGEST_CRON_TOKEN = os.getenv("INGEST_CRON_TOKEN", "")
ONBOARDING_SETUP_TOKEN = os.getenv("ONBOARDING_SETUP_TOKEN", "").strip()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
WEB_AUTH_SUCCESS_URL = os.getenv("WEB_AUTH_SUCCESS_URL", "http://localhost:3000/login/success").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()

whatsapp_service = WhatsAppService(ACCESS_TOKEN, PHONE_NUMBER_ID)


app = FastAPI(
    title="Alloha Core API",
    description="Low-cost core API: chat, listings, leads, ingest",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessageRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    channel: str = Field(default="web")


class IngestRunRequest(BaseModel):
    force_full: bool = False


class LeadCaptureRequest(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    topic: Optional[str] = None
    interest: Optional[str] = None


class OnboardingBootstrapRequest(BaseModel):
    business_name: str = Field(default="Alloha Imoveis")
    owner_name: str = Field(default="Equipe Alloha")
    whatsapp_phone: str = Field(default="")
    city: str = Field(default="Sao Paulo")
    force_full_scrape: bool = Field(default=True)


class SupabaseSessionExchangeRequest(BaseModel):
    access_token: str = Field(..., min_length=1)


def _onboarding_defaults() -> Dict[str, Any]:
    return {
        "business_name": "Alloha Imoveis",
        "owner_name": "Equipe Alloha",
        "whatsapp_phone": "",
        "city": "Sao Paulo",
        "force_full_scrape": True,
        "listing_freshness_mode": "first_scrape_only",
    }


def _onboarding_token_is_required() -> bool:
    return bool(ONBOARDING_SETUP_TOKEN)


def _validate_onboarding_token(request: Request) -> None:
    if not _onboarding_token_is_required():
        return
    token = request.headers.get("X-Onboarding-Token", "").strip()
    if token != ONBOARDING_SETUP_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid onboarding token")


def _google_effective_redirect_uri(request: Request) -> str:
    if GOOGLE_REDIRECT_URI:
        return GOOGLE_REDIRECT_URI
    return f"{str(request.base_url).rstrip('/')}/v1/auth/google/callback"


def _extract_bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return ""
    return auth.replace("Bearer ", "", 1).strip()


async def _load_auth_session(token: str) -> Dict[str, Any]:
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token.")

    raw = await redis_client.get(f"auth:session:{token}")
    if not raw:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")

    try:
        return json.loads(raw)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Invalid session payload: {exc}") from exc


async def _require_authenticated_session(request: Request) -> Dict[str, Any]:
    token = _extract_bearer_token(request)
    return await _load_auth_session(token)


async def _persist_auth_session(profile: Dict[str, Any]) -> str:
    session_token = f"sess_{uuid.uuid4().hex}"
    session_saved = await redis_client.set(
        f"auth:session:{session_token}",
        json.dumps(profile),
        ex=7 * 24 * 60 * 60,
    )
    if not session_saved:
        raise HTTPException(status_code=503, detail="Session storage unavailable.")
    return session_token


def _build_supabase_profile(user: Dict[str, Any]) -> Dict[str, Any]:
    user_metadata = user.get("user_metadata") or {}
    app_metadata = user.get("app_metadata") or {}
    email = user.get("email")
    fallback_name = email.split("@", 1)[0] if isinstance(email, str) and "@" in email else "Conta Alloha"

    return {
        "sub": user.get("id"),
        "email": email,
        "name": user_metadata.get("full_name") or user_metadata.get("name") or fallback_name,
        "picture": user_metadata.get("avatar_url") or user_metadata.get("picture"),
        "provider": app_metadata.get("provider") or "email",
        "email_confirmed": bool(user.get("email_confirmed_at")),
        "created_at": _utc_now_iso(),
    }


@app.on_event("startup")
async def startup_event() -> None:
    webhook_idempotency.start()
    await redis_client.get_client()
    _log_event("startup_complete", version="3.0.0")


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "service": "alloha-core-api",
        "version": "3.0.0",
        "status": "active",
        "endpoints": [
            "/health",
            "/webhook",
            "/v1/auth/google/start",
            "/v1/auth/google/callback",
            "/v1/auth/session",
            "/v1/auth/session/exchange",
            "/v1/auth/logout",
            "/v1/onboarding/defaults",
            "/v1/onboarding/bootstrap",
            "/v1/onboarding/status",
            "/v1/chat/messages",
            "/v1/listings/search",
            "/v1/ingest/run",
            "/v1/leads",
            "/v1/system/status",
        ],
    }


@app.get("/health")
async def health() -> Dict[str, Any]:
    redis_ok = bool(await redis_client.get_client())
    return {
        "status": "healthy",
        "service": "alloha-core-api",
        "version": "3.0.0",
        "deploy_profile": os.getenv("DEPLOY_PROFILE", "default"),
        "redis_available": redis_ok,
        "redis_memory_fallback_active": redis_client.using_memory_fallback(),
        "openrouter_configured": bool(os.getenv("OPENROUTER_API_KEY")),
        "resend_configured": resend_configured(),
        "official_feed_configured": bool(os.getenv("OFFICIAL_FEED_URL")),
        "scraper_fallback_enabled": os.getenv("ENABLE_SCRAPER_FALLBACK", "0") == "1",
        "property_embeddings_enabled": os.getenv("ENABLE_PROPERTY_EMBEDDINGS", "0") == "1",
        "timestamp": _utc_now_iso(),
    }


@app.get("/v1/auth/google/start")
async def v1_auth_google_start(
    request: Request,
    return_to: str = Query(default="/dashboard"),
) -> RedirectResponse:
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google auth is not configured.")

    state = uuid.uuid4().hex
    await redis_client.set(
        f"auth:google:state:{state}",
        return_to or "/dashboard",
        ex=10 * 60,
    )
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": _google_effective_redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url=auth_url, status_code=302)


@app.get("/v1/auth/google/callback")
async def v1_auth_google_callback(
    request: Request,
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
) -> RedirectResponse:
    if error:
        return RedirectResponse(url=f"{WEB_AUTH_SUCCESS_URL}?error={error}", status_code=302)
    if not code or not state:
        return RedirectResponse(url=f"{WEB_AUTH_SUCCESS_URL}?error=missing_code_or_state", status_code=302)
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return RedirectResponse(url=f"{WEB_AUTH_SUCCESS_URL}?error=google_not_configured", status_code=302)

    state_key = f"auth:google:state:{state}"
    return_to = await redis_client.get(state_key)
    if not return_to:
        return RedirectResponse(url=f"{WEB_AUTH_SUCCESS_URL}?error=invalid_state", status_code=302)

    client = await redis_client.get_client()
    if client:
        try:
            await client.delete(state_key)
        except Exception:
            pass

    redirect_uri = _google_effective_redirect_uri(request)
    token_payload = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    timeout = aiohttp.ClientTimeout(total=20)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post("https://oauth2.googleapis.com/token", data=token_payload) as token_resp:
                token_body = await token_resp.json(content_type=None)
                if token_resp.status >= 400:
                    return RedirectResponse(url=f"{WEB_AUTH_SUCCESS_URL}?error=token_exchange_failed", status_code=302)
                access_token = token_body.get("access_token")
                if not access_token:
                    return RedirectResponse(url=f"{WEB_AUTH_SUCCESS_URL}?error=missing_access_token", status_code=302)

            async with session.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            ) as profile_resp:
                profile_body = await profile_resp.json(content_type=None)
                if profile_resp.status >= 400:
                    return RedirectResponse(url=f"{WEB_AUTH_SUCCESS_URL}?error=profile_fetch_failed", status_code=302)
    except Exception:
        return RedirectResponse(url=f"{WEB_AUTH_SUCCESS_URL}?error=google_request_failed", status_code=302)

    session_payload = {
        "sub": profile_body.get("sub"),
        "email": profile_body.get("email"),
        "name": profile_body.get("name"),
        "picture": profile_body.get("picture"),
        "provider": "google",
        "email_confirmed": True,
        "created_at": _utc_now_iso(),
    }
    try:
        session_token = await _persist_auth_session(session_payload)
    except HTTPException:
        return RedirectResponse(url=f"{WEB_AUTH_SUCCESS_URL}?error=session_storage_unavailable", status_code=302)

    safe_return_to = return_to if isinstance(return_to, str) and return_to.startswith("/") else "/dashboard"
    query = urlencode({"token": session_token, "return_to": safe_return_to})
    return RedirectResponse(url=f"{WEB_AUTH_SUCCESS_URL}?{query}", status_code=302)


@app.get("/v1/auth/session")
async def v1_auth_session(request: Request) -> Dict[str, Any]:
    profile = await _load_auth_session(_extract_bearer_token(request))
    return {"authenticated": True, "profile": profile}


@app.post("/v1/auth/session/exchange")
async def v1_auth_session_exchange(payload: SupabaseSessionExchangeRequest) -> Dict[str, Any]:
    api_key = SUPABASE_ANON_KEY or os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    if not SUPABASE_URL or not api_key:
        raise HTTPException(status_code=503, detail="Supabase auth is not configured.")

    timeout = aiohttp.ClientTimeout(total=20)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {payload.access_token}",
                    "apikey": api_key,
                },
            ) as user_resp:
                user_body = await user_resp.json(content_type=None)
                if user_resp.status >= 400:
                    raise HTTPException(status_code=401, detail="Invalid Supabase session.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Supabase auth request failed: {exc}") from exc

    profile = _build_supabase_profile(user_body)
    if not profile.get("sub") or not profile.get("email"):
        raise HTTPException(status_code=401, detail="Invalid Supabase user payload.")
    if profile.get("provider") == "email" and not profile.get("email_confirmed"):
        raise HTTPException(status_code=403, detail="Email validation pending.")

    session_token = await _persist_auth_session(profile)
    _log_event(
        "supabase_session_exchanged",
        auth_sub=profile.get("sub"),
        provider=profile.get("provider"),
        email_hash=_phone_hash(profile.get("email") or ""),
    )
    return {"success": True, "session_token": session_token, "profile": profile}


@app.post("/v1/auth/logout")
async def v1_auth_logout(request: Request) -> Dict[str, Any]:
    token = _extract_bearer_token(request)
    if not token:
        return {"success": True}
    client = await redis_client.get_client()
    if client:
        try:
            await client.delete(f"auth:session:{token}")
        except Exception:
            pass
    return {"success": True}


@app.get("/v1/onboarding/defaults")
async def v1_onboarding_defaults(request: Request) -> Dict[str, Any]:
    await _require_authenticated_session(request)
    return {
        "defaults": _onboarding_defaults(),
        "setup_token_required": _onboarding_token_is_required(),
        "timestamp": _utc_now_iso(),
    }


@app.post("/v1/onboarding/bootstrap")
async def v1_onboarding_bootstrap(
    request: Request,
    payload: OnboardingBootstrapRequest = Body(default=OnboardingBootstrapRequest()),
) -> Dict[str, Any]:
    profile = await _require_authenticated_session(request)
    setup_id = f"setup-{uuid.uuid4().hex[:10]}"
    configured_at = _utc_now_iso()
    defaults = _onboarding_defaults()
    config_payload = {
        **defaults,
        **payload.dict(),
        "setup_id": setup_id,
        "configured_at": configured_at,
        "configured_by": {
            "name": profile.get("name"),
            "email": profile.get("email"),
            "sub": profile.get("sub"),
        },
    }
    await redis_client.set(
        "onboarding:config",
        json.dumps(config_payload, ensure_ascii=False),
        ex=30 * 24 * 60 * 60,
    )

    ingest_in_progress = bool(await redis_client.get("jobs:ingest:lock"))
    if ingest_in_progress:
        return {
            "success": True,
            "setup_id": setup_id,
            "started": False,
            "in_progress": True,
            "already_configured": False,
            "message": "Primeiro scrap ja esta em execucao.",
        }

    first_scrape_completed = (await redis_client.get("onboarding:first_scrape:completed")) == "1"
    if first_scrape_completed:
        return {
            "success": True,
            "setup_id": setup_id,
            "started": False,
            "in_progress": False,
            "already_configured": True,
            "message": "Setup inicial ja concluido. Sistema pronto para uso.",
        }

    await redis_client.set("onboarding:first_scrape:started_at", configured_at, ex=30 * 24 * 60 * 60)
    asyncio.create_task(_run_initial_ingest(setup_id, payload.force_full_scrape))
    _log_event(
        "onboarding_bootstrap_started",
        setup_id=setup_id,
        auth_sub=profile.get("sub"),
        business_name=payload.business_name,
        city=payload.city,
        force_full_scrape=payload.force_full_scrape,
    )
    return {
        "success": True,
        "setup_id": setup_id,
        "started": True,
        "in_progress": True,
        "already_configured": False,
        "message": "Setup iniciado. Executando primeiro scrap em background.",
    }


@app.get("/v1/onboarding/status")
async def v1_onboarding_status(request: Request) -> Dict[str, Any]:
    await _require_authenticated_session(request)
    config_raw = await redis_client.get("onboarding:config")
    started_at = await redis_client.get("onboarding:first_scrape:started_at")
    completed_flag = await redis_client.get("onboarding:first_scrape:completed")
    result_raw = await redis_client.get("onboarding:first_scrape:last_result")
    ingest_in_progress = bool(await redis_client.get("jobs:ingest:lock"))

    config_data: Dict[str, Any]
    if config_raw:
        try:
            config_data = json.loads(config_raw)
        except Exception:
            config_data = _onboarding_defaults()
    else:
        config_data = _onboarding_defaults()

    last_result: Optional[Dict[str, Any]] = None
    if result_raw:
        try:
            last_result = json.loads(result_raw)
        except Exception:
            last_result = {"success": False, "error": "invalid_result_payload"}

    return {
        "configured": bool(config_raw),
        "ingest_in_progress": ingest_in_progress,
        "first_scrape_completed": completed_flag == "1",
        "first_scrape_started_at": started_at,
        "setup_token_required": _onboarding_token_is_required(),
        "config": config_data,
        "last_result": last_result,
        "timestamp": _utc_now_iso(),
    }


def _query_listings(
    q: str = "",
    neighborhood: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    bedrooms: Optional[int] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    client = supabase_client.require_client()
    query = client.table("properties").select(
        "property_id,title,description,price,neighborhood,city,bedrooms,bathrooms,main_image,url,status"
    ).eq("status", "active")

    if neighborhood:
        query = query.ilike("neighborhood", f"%{neighborhood}%")
    if min_price is not None:
        query = query.gte("price", min_price)
    if max_price is not None:
        query = query.lte("price", max_price)
    if bedrooms is not None:
        query = query.gte("bedrooms", bedrooms)
    if q:
        query = query.or_(f"title.ilike.%{q}%,description.ilike.%{q}%")

    result = query.limit(min(max(limit, 1), 50)).execute()
    return result.data or []


async def _save_conversation_turn(user_id: str, user_message: str, assistant_message: str) -> None:
    try:
        conversation = await asyncio.to_thread(supabase_client.get_or_create_conversation, user_id)
        await asyncio.to_thread(
            supabase_client.save_message,
            conversation["id"],
            "received",
            user_message,
            "text",
            None,
            {"source": "v1_chat"},
        )
        await asyncio.to_thread(
            supabase_client.save_message,
            conversation["id"],
            "sent",
            assistant_message,
            "text",
            None,
            {"source": "v1_chat"},
        )
    except Exception as exc:
        _log_event("conversation_persist_failed", error=str(exc))


def _compose_listing_context(listings: List[Dict[str, Any]]) -> str:
    if not listings:
        return "Nenhum imóvel disponível foi encontrado para esta consulta."
    lines = ["Imóveis relevantes disponíveis:"]
    for row in listings[:3]:
        lines.append(
            f"- {row.get('title','Imóvel')} | Bairro: {row.get('neighborhood','N/A')} | "
            f"Preço: {row.get('price','N/A')} | URL: {row.get('url','N/A')}"
        )
    return "\n".join(lines)


async def _generate_reply(user_id: str, message: str) -> Dict[str, Any]:
    listings = await asyncio.to_thread(_query_listings, message, None, None, None, None, 3)
    system_prompt = (
        "Você é Sofia, assistente imobiliária da Alloha. "
        "Responda em português, de forma objetiva, e convide o usuário para avançar com visita."
    )
    context = _compose_listing_context(listings)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Pergunta: {message}\n\nContexto:\n{context}"},
    ]
    gateway_result = await model_gateway.chat(user_id=user_id, messages=messages)
    await _save_conversation_turn(user_id, message, gateway_result.reply)
    return {
        "reply": gateway_result.reply,
        "listings": listings,
        "provider": gateway_result.provider,
        "model": gateway_result.model,
        "policy_applied": gateway_result.policy_applied,
        "capacity_limited": gateway_result.capacity_limited,
    }


async def _run_initial_ingest(setup_id: str, force_full: bool) -> None:
    try:
        result = await ingest_service.run(force_full=force_full)
        payload = {
            "setup_id": setup_id,
            "success": result.success,
            "run_id": result.run_id,
            "source_used": result.source_used,
            "total_seen": result.total_seen,
            "inserted_or_updated": result.inserted_or_updated,
            "unchanged": result.unchanged,
            "deactivated": result.deactivated,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "message": result.message,
        }
        await redis_client.set("onboarding:first_scrape:last_result", json.dumps(payload), ex=30 * 24 * 60 * 60)
        await redis_client.set("onboarding:first_scrape:completed", "1" if result.success else "0", ex=30 * 24 * 60 * 60)
        _log_event(
            "onboarding_first_scrape_completed",
            setup_id=setup_id,
            run_id=result.run_id,
            success=result.success,
            changed=result.inserted_or_updated,
            total_seen=result.total_seen,
        )
    except Exception as exc:
        await redis_client.set("onboarding:first_scrape:completed", "0", ex=30 * 24 * 60 * 60)
        await redis_client.set(
            "onboarding:first_scrape:last_result",
            json.dumps(
                {
                    "setup_id": setup_id,
                    "success": False,
                    "error": str(exc),
                    "finished_at": _utc_now_iso(),
                }
            ),
            ex=30 * 24 * 60 * 60,
        )
        _log_event("onboarding_first_scrape_failed", setup_id=setup_id, error=str(exc))


@app.post("/v1/chat/messages")
async def v1_chat_messages(payload: ChatMessageRequest) -> Dict[str, Any]:
    req_id = _request_id()
    start = datetime.now(timezone.utc)
    response = await _generate_reply(payload.user_id, payload.message)
    latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
    _log_event(
        "chat_request_completed",
        request_id=req_id,
        user_hash=_phone_hash(payload.user_id),
        session_id=payload.session_id,
        provider=response.get("provider"),
        model=response.get("model"),
        capacity_limited=response.get("capacity_limited"),
        latency_ms=round(latency_ms, 2),
    )
    response.update({"session_id": payload.session_id, "channel": payload.channel, "latency_ms": latency_ms})
    return response


@app.get("/v1/listings/search")
async def v1_listings_search(
    q: str = Query(default=""),
    neighborhood: Optional[str] = Query(default=None),
    min_price: Optional[float] = Query(default=None),
    max_price: Optional[float] = Query(default=None),
    bedrooms: Optional[int] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
) -> Dict[str, Any]:
    listings = await asyncio.to_thread(
        _query_listings, q, neighborhood, min_price, max_price, bedrooms, limit
    )
    return {"count": len(listings), "listings": listings}


@app.post("/v1/ingest/run")
async def v1_ingest_run(request: Request, payload: IngestRunRequest = Body(default=IngestRunRequest())) -> Dict[str, Any]:
    auth = request.headers.get("Authorization", "")
    expected = f"Bearer {INGEST_CRON_TOKEN}" if INGEST_CRON_TOKEN else ""
    if not expected or auth != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    result = await ingest_service.run(force_full=payload.force_full)
    _log_event(
        "ingest_run_completed",
        job_run_id=result.run_id,
        source=result.source_used,
        total_seen=result.total_seen,
        changed=result.inserted_or_updated,
        deactivated=result.deactivated,
        success=result.success,
    )
    return result.__dict__


@app.post("/v1/leads")
async def v1_capture_lead(payload: LeadCaptureRequest) -> Dict[str, Any]:
    try:
        topic = (payload.topic or "Contato geral").strip() or "Contato geral"
        conversation = await asyncio.to_thread(
            supabase_client.get_or_create_conversation,
            payload.phone,
        )
        requirements: Dict[str, Any] = {}
        if payload.topic:
            requirements["topic"] = topic
        if payload.interest:
            requirements["interest"] = payload.interest
        lead_data = {
            "conversation_id": conversation["id"],
            "name": payload.name,
            "phone_number": payload.phone,
            "email": payload.email,
            "requirements": requirements,
            "source": "contact_form",
            "status": "new",
        }
        result = await asyncio.to_thread(
            lambda: supabase_client.client.table("leads").insert(lead_data).execute()
        )
        lead = (result.data or [{}])[0]
        lead_id = lead.get("id") or f"lead-{uuid.uuid4().hex[:10]}"
        created_at = lead.get("created_at") or _utc_now_iso()

        email_result = await send_support_ticket(
            lead_id=lead_id,
            created_at=created_at,
            topic=topic,
            name=payload.name,
            phone=payload.phone,
            email=payload.email,
            interest=payload.interest,
        )

        _log_event(
            "lead_captured",
            lead_id=lead_id,
            phone_hash=_phone_hash(payload.phone),
            support_email_sent=email_result.support_email_sent,
            acknowledgement_email_sent=email_result.acknowledgement_email_sent,
            email_error=email_result.error,
        )

        message = "Seu suporte foi processado. Vamos avaliar e entraremos em contato."
        if email_result.support_email_sent:
            message = (
                f"Seu suporte foi processado e o ticket chegou em {support_email_to()}. "
                "Vamos avaliar e entraremos em contato."
            )

        return {
            "success": True,
            "lead_id": lead_id,
            "created_at": created_at,
            "message": message,
            "ticket_email": support_email_to(),
            "notification_delivered": email_result.support_email_sent,
            "acknowledgement_sent": email_result.acknowledgement_email_sent,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lead capture failed: {exc}") from exc


@app.get("/v1/system/status")
async def v1_system_status() -> Dict[str, Any]:
    redis_ok = bool(await redis_client.get_client())
    model_metrics = await model_gateway.get_metrics()
    ingest_metrics = {
        "last_run_id": await redis_client.get("metrics:ingest:last_run_id"),
        "last_source": await redis_client.get("metrics:ingest:last_source"),
        "last_finished_at": await redis_client.get("metrics:ingest:last_finished_at"),
        "last_duration_ms": int((await redis_client.get("metrics:ingest:last_duration_ms")) or 0),
        "last_total_seen": int((await redis_client.get("metrics:ingest:last_total_seen")) or 0),
        "last_changed": int((await redis_client.get("metrics:ingest:last_changed")) or 0),
        "last_deactivated": int((await redis_client.get("metrics:ingest:last_deactivated")) or 0),
        "lock_contention_daily": int((await redis_client.get("metrics:ingest:lock_contention")) or 0),
    }
    return {
        "status": "ok",
        "deploy_profile": os.getenv("DEPLOY_PROFILE", "default"),
        "redis_available": redis_ok,
        "redis_memory_fallback_active": redis_client.using_memory_fallback(),
        "ingest_lock_key": "jobs:ingest:lock",
        "official_feed_configured": bool(os.getenv("OFFICIAL_FEED_URL")),
        "scraper_fallback_enabled": os.getenv("ENABLE_SCRAPER_FALLBACK", "0") == "1",
        "property_embeddings_enabled": os.getenv("ENABLE_PROPERTY_EMBEDDINGS", "0") == "1",
        "primary_provider": os.getenv("PRIMARY_PROVIDER", "openrouter_free"),
        "fallback_policy": os.getenv("FALLBACK_POLICY", "hard_stop"),
        "openrouter_model": os.getenv("OPENROUTER_FREE_MODEL", "tngtech/deepseek-r1t2-chimera:free"),
        "support_email": {
            "provider": "resend",
            "configured": resend_configured(),
            "to": support_email_to(),
        },
        "metrics": {
            "model_gateway": model_metrics,
            "ingest": ingest_metrics,
        },
        "timestamp": _utc_now_iso(),
    }


@app.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(request: Request) -> str:
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN and challenge:
        return challenge
    raise HTTPException(status_code=403, detail="Verification failed")


async def _extract_text_message(webhook_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
    entry = webhook_data.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    value = changes.get("value", {})
    if "messages" not in value:
        return None
    message = value["messages"][0]
    msg_type = message.get("type", "text")
    from_number = message.get("from")
    message_id = message.get("id", "")
    if not from_number:
        return None
    if msg_type != "text":
        return {"from_number": from_number, "text": "", "message_id": message_id}
    text = message.get("text", {}).get("body", "")
    return {"from_number": from_number, "text": text, "message_id": message_id}


async def _process_webhook_message(body: Dict[str, Any], fingerprint: str) -> None:
    try:
        extracted = await _extract_text_message(body)
        if not extracted:
            await webhook_idempotency.mark_as_completed(fingerprint, {"skipped": "empty"})
            return
        from_number = extracted["from_number"]
        text = extracted["text"]
        message_id = extracted.get("message_id", "")
        phone_hash = _phone_hash(from_number)

        if not text:
            reply = (
                "Recebi sua mídia. No momento respondo melhor por texto. "
                "Pode descrever o imóvel que procura?"
            )
            await whatsapp_service.send_message(from_number, reply)
            await _save_conversation_turn(from_number, "[non_text_message]", reply)
            await webhook_idempotency.mark_as_completed(fingerprint, {"mode": "non_text"})
            _log_event(
                "webhook_processed",
                phone_hash=phone_hash,
                message_id=message_id,
                mode="non_text",
            )
            return

        result = await _generate_reply(from_number, text)
        await whatsapp_service.send_message(from_number, result["reply"])
        await webhook_idempotency.mark_as_completed(fingerprint, {"mode": "text"})
        _log_event(
            "webhook_processed",
            phone_hash=phone_hash,
            message_id=message_id,
            provider=result["provider"],
            model=result["model"],
            capacity_limited=result["capacity_limited"],
        )
    except Exception as exc:
        await webhook_idempotency.mark_as_failed(fingerprint, str(exc))
        _log_event("webhook_processing_failed", error=str(exc))


@app.post("/webhook")
async def webhook_handler(request: Request) -> Dict[str, Any]:
    body = await request.json()
    if await webhook_idempotency.is_duplicate(body):
        return {"status": "duplicate"}

    fingerprint = await webhook_idempotency.mark_as_processing(body)
    if not fingerprint:
        return {"status": "processing"}

    asyncio.create_task(_process_webhook_message(body, fingerprint))
    return {"status": "accepted"}


def _deprecated_response() -> Dict[str, Any]:
    raise HTTPException(
        status_code=410,
        detail="This endpoint was deprecated. Use /v1/chat/messages, /v1/listings/search or /v1/ingest/run.",
    )


DEPRECATED_GET_PATHS = [
    "/api/fresh-properties",
    "/api/urgency/alerts",
    "/api/stats/dashboard",
    "/dataset/status",
    "/properties/stats",
    "/system/status",
]
DEPRECATED_POST_PATHS = [
    "/api/dual-stack/query",
    "/api/white-label/create",
    "/dataset/expand",
    "/dataset/trigger-update",
    "/run-property-scraper",
    "/test-ai",
    "/test-image-analysis",
    "/update-properties",
    "/query",
]

for path in DEPRECATED_GET_PATHS:
    app.add_api_route(path, _deprecated_response, methods=["GET"], include_in_schema=False)
for path in DEPRECATED_POST_PATHS:
    app.add_api_route(path, _deprecated_response, methods=["POST"], include_in_schema=False)


@app.get("/analytics/{user_phone}", include_in_schema=False)
async def deprecated_analytics(user_phone: str) -> Dict[str, Any]:
    return _deprecated_response()


@app.post("/api/urgency/mark-contacted/{alert_id}", include_in_schema=False)
async def deprecated_mark_contacted(alert_id: str) -> Dict[str, Any]:
    return _deprecated_response()
