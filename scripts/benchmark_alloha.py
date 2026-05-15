from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import aiohttp
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]


QUERIES: list[dict[str, Any]] = [
    {"label": "agua_verde_3q", "message": "Quero apartamento de 3 quartos no Agua Verde para comprar", "listing": {"q": "apartamento 3 quartos", "neighborhood": "Agua Verde", "bedrooms": "3", "limit": "10"}},
    {"label": "batel_alto_padrao", "message": "Tem imovel de alto padrao no Batel ate 2 milhoes?", "listing": {"q": "alto padrao Batel", "neighborhood": "Batel", "max_price": "2000000", "limit": "10"}},
    {"label": "centro_aluguel", "message": "Procuro aluguel no Centro perto de comercio", "listing": {"q": "alugar Centro comercio", "neighborhood": "Centro", "limit": "10"}},
    {"label": "sobrado_atuba", "message": "Me mostre sobrados no Atuba com 3 quartos e garagem", "listing": {"q": "sobrado Atuba garagem", "neighborhood": "Atuba", "bedrooms": "3", "limit": "10"}},
    {"label": "santa_felicidade_casa", "message": "Casa em Santa Felicidade com quintal e 4 quartos", "listing": {"q": "casa quintal", "neighborhood": "Santa Felicidade", "bedrooms": "4", "limit": "10"}},
    {"label": "baixo_orcamento", "message": "Tenho ate 400 mil, quais opcoes boas existem?", "listing": {"q": "oportunidade", "max_price": "400000", "limit": "10"}},
    {"label": "investimento_terreno", "message": "Quero terreno para investimento em Curitiba", "listing": {"q": "terreno investimento Curitiba", "limit": "10"}},
    {"label": "comercial_sala", "message": "Preciso de sala comercial pequena para alugar", "listing": {"q": "sala comercial alugar", "limit": "10"}},
    {"label": "visita_hoje", "message": "Consigo visitar algum apartamento hoje a tarde?", "listing": {"q": "apartamento", "limit": "10"}},
    {"label": "lead_financiamento", "message": "Sou comprador financiado, entrada de 120 mil e renda familiar de 18 mil", "listing": {"q": "financiamento", "limit": "10"}},
    {"label": "pinheirinho_3q", "message": "Apartamento no Pinheirinho com 3 quartos e uma vaga", "listing": {"q": "apartamento 3 quartos vaga", "neighborhood": "Pinheirinho", "bedrooms": "3", "limit": "10"}},
    {"label": "boa_vista_sobrado", "message": "Sobrado no Boa Vista com 4 dormitorios", "listing": {"q": "sobrado 4 dormitorios", "neighborhood": "Boa Vista", "bedrooms": "4", "limit": "10"}},
    {"label": "bigorrilho_loft", "message": "Existe loft ou apartamento compacto no Bigorrilho?", "listing": {"q": "loft compacto", "neighborhood": "Bigorrilho", "limit": "10"}},
    {"label": "xaxim_familia", "message": "Familia grande procurando casa no Xaxim com 4 quartos", "listing": {"q": "casa familia", "neighborhood": "Xaxim", "bedrooms": "4", "limit": "10"}},
    {"label": "boqueirao_triplex", "message": "Triplex no Boqueirao ate 900 mil", "listing": {"q": "triplex Boqueirao", "neighborhood": "Boqueirao", "max_price": "900000", "limit": "10"}},
    {"label": "merces_apartamento", "message": "Apartamento nas Merces com boa localizacao", "listing": {"q": "apartamento boa localizacao", "neighborhood": "Merces", "limit": "10"}},
    {"label": "reboucas_comercial", "message": "Sala comercial no Reboucas para atendimento", "listing": {"q": "sala comercial atendimento", "neighborhood": "Reboucas", "limit": "10"}},
    {"label": "agua_verde_luxo", "message": "Casa ou sobrado de luxo no Agua Verde", "listing": {"q": "luxo sobrado casa", "neighborhood": "Agua Verde", "limit": "10"}},
    {"label": "urgente_mudanca", "message": "Preciso mudar em ate 30 dias, aluguel com 2 quartos", "listing": {"q": "aluguel 2 quartos", "bedrooms": "2", "limit": "10"}},
    {"label": "permuta", "message": "Aceita permuta por veiculo ou imovel menor?", "listing": {"q": "aceita permuta", "limit": "10"}},
    {"label": "mobiliado", "message": "Tem sobrado novo mobiliado pronto para morar?", "listing": {"q": "sobrado novo mobiliado", "limit": "10"}},
    {"label": "condominio_fechado", "message": "Terreno em condominio fechado com projeto aprovado", "listing": {"q": "terreno condominio fechado projeto aprovado", "limit": "10"}},
    {"label": "cristo_rei_comercial", "message": "Imovel comercial no Cristo Rei para clinica", "listing": {"q": "comercial clinica", "neighborhood": "Cristo Rei", "limit": "10"}},
    {"label": "cidade_industrial_locacao", "message": "Casa para alugar na Cidade Industrial com churrasqueira", "listing": {"q": "casa alugar churrasqueira", "neighborhood": "Cidade Industrial", "limit": "10"}},
    {"label": "cabral_qualificacao", "message": "Quero comprar no Cabral, posso dar 30% de entrada e visitar no sabado", "listing": {"q": "comprar visitar sabado", "neighborhood": "Cabral", "limit": "10"}},
    {"label": "alto_da_xv", "message": "Apartamento no Alto da XV perto de escolas", "listing": {"q": "apartamento escolas", "neighborhood": "Alto da XV", "limit": "10"}},
    {"label": "jardim_botanico_terreno", "message": "Terreno no Jardim Botanico com duas casas", "listing": {"q": "terreno duas casas", "neighborhood": "Jardim Botanico", "limit": "10"}},
    {"label": "sao_braz_terreno", "message": "Terreno grande em Sao Braz", "listing": {"q": "terreno grande", "neighborhood": "Sao Braz", "limit": "10"}},
    {"label": "lead_corretor", "message": "Pode pedir para um corretor me chamar? Meu interesse e compra ate 750 mil", "listing": {"q": "compra 750 mil", "max_price": "750000", "limit": "10"}},
    {"label": "visita_documentos", "message": "Quais documentos preciso para proposta e agendamento de visita?", "listing": {"q": "proposta visita", "limit": "10"}},
]


@dataclass
class Sample:
    label: str
    ok: bool
    latency_ms: float
    status: int | None = None
    count: int | None = None
    error: str | None = None
    extra: dict[str, Any] | None = None


def load_env() -> None:
    load_dotenv(ROOT / ".env", override=False)


def secret_values() -> list[str]:
    values: list[str] = []
    for key, value in os.environ.items():
        if not value:
            continue
        upper = key.upper()
        if any(token in upper for token in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
            values.append(value)
    supabase_url = os.getenv("SUPABASE_URL")
    if supabase_url:
        values.append(supabase_url)
    return sorted(set(values), key=len, reverse=True)


def sanitize(text: Any) -> str:
    raw = str(text)
    for value in secret_values():
        if value:
            raw = raw.replace(value, "[redacted]")
    return raw.replace(os.getenv("SUPABASE_URL", "") or "\0", "[redacted]")


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = max(0, min(len(ordered) - 1, math.ceil((pct / 100.0) * len(ordered)) - 1))
    return ordered[idx]


def summarize(samples: list[Sample]) -> dict[str, Any]:
    ok = [s for s in samples if s.ok]
    latencies = [s.latency_ms for s in ok]
    all_latencies = [s.latency_ms for s in samples]
    errors = [s for s in samples if not s.ok]
    return {
        "requests": len(samples),
        "successes": len(ok),
        "errors": len(errors),
        "error_rate": round((len(errors) / len(samples) * 100) if samples else 0.0, 2),
        "cold_ms": round(samples[0].latency_ms, 2) if samples else None,
        "all_requests_mean_ms": round(statistics.mean(all_latencies), 2) if all_latencies else None,
        "all_requests_p50_ms": round(percentile(all_latencies, 50), 2) if all_latencies else None,
        "all_requests_p95_ms": round(percentile(all_latencies, 95), 2) if all_latencies else None,
        "all_requests_p99_ms": round(percentile(all_latencies, 99), 2) if all_latencies else None,
        "warm": {
            "requests": max(0, len(samples) - 1),
            "all_requests_mean_ms": round(statistics.mean([s.latency_ms for s in samples[1:]]), 2)
            if samples[1:]
            else None,
            "all_requests_p50_ms": round(percentile([s.latency_ms for s in samples[1:]], 50), 2)
            if samples[1:]
            else None,
            "all_requests_p95_ms": round(percentile([s.latency_ms for s in samples[1:]], 95), 2)
            if samples[1:]
            else None,
            "all_requests_p99_ms": round(percentile([s.latency_ms for s in samples[1:]], 99), 2)
            if samples[1:]
            else None,
            "mean_ms": round(statistics.mean([s.latency_ms for s in samples[1:] if s.ok]), 2)
            if any(s.ok for s in samples[1:])
            else None,
            "p50_ms": round(percentile([s.latency_ms for s in samples[1:] if s.ok], 50), 2)
            if any(s.ok for s in samples[1:])
            else None,
            "p95_ms": round(percentile([s.latency_ms for s in samples[1:] if s.ok], 95), 2)
            if any(s.ok for s in samples[1:])
            else None,
            "p99_ms": round(percentile([s.latency_ms for s in samples[1:] if s.ok], 99), 2)
            if any(s.ok for s in samples[1:])
            else None,
        },
        "all_success_mean_ms": round(statistics.mean(latencies), 2) if latencies else None,
        "all_success_p50_ms": round(percentile(latencies, 50), 2) if latencies else None,
        "all_success_p95_ms": round(percentile(latencies, 95), 2) if latencies else None,
        "all_success_p99_ms": round(percentile(latencies, 99), 2) if latencies else None,
        "sample_errors": [
            {"label": s.label, "status": s.status, "error": sanitize(s.error)[:300]}
            for s in errors[:5]
        ],
    }


async def rest_count(session: aiohttp.ClientSession, table: str, filters: dict[str, str]) -> dict[str, Any]:
    supabase_url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY") or ""
    if not supabase_url or not key:
        return {"ok": False, "error": "Supabase env missing"}

    params = {"select": "property_id", **filters}
    url = f"{supabase_url}/rest/v1/{table}?{urlencode(params)}"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Prefer": "count=exact",
        "Range": "0-0",
    }
    start = time.perf_counter()
    try:
        async with session.get(url, headers=headers) as resp:
            body = await resp.text()
            elapsed = (time.perf_counter() - start) * 1000
            content_range = resp.headers.get("content-range", "")
            total = None
            if "/" in content_range:
                try:
                    total = int(content_range.rsplit("/", 1)[1])
                except ValueError:
                    total = None
            return {
                "ok": resp.status < 400,
                "status": resp.status,
                "count": total,
                "latency_ms": round(elapsed, 2),
                "error": None if resp.status < 400 else sanitize(body)[:300],
            }
    except Exception as exc:
        return {"ok": False, "error": sanitize(exc)}


async def supabase_counts(session: aiohttp.ClientSession) -> dict[str, Any]:
    active = await rest_count(session, "properties", {"status": "eq.active"})
    active_not_deleted = await rest_count(
        session,
        "properties",
        {"status": "eq.active", "is_deleted": "is.false"},
    )
    with_embeddings = await rest_count(
        session,
        "properties",
        {"status": "eq.active", "embedding": "not.is.null"},
    )
    with_embeddings_not_deleted = await rest_count(
        session,
        "properties",
        {"status": "eq.active", "is_deleted": "is.false", "embedding": "not.is.null"},
    )
    return {
        "active_status": active,
        "active_not_deleted": active_not_deleted,
        "active_with_embedding": with_embeddings,
        "active_not_deleted_with_embedding": with_embeddings_not_deleted,
    }


async def api_get_json(session: aiohttp.ClientSession, url: str) -> tuple[int, Any, str]:
    async with session.get(url) as resp:
        text = await resp.text()
        try:
            return resp.status, json.loads(text), text
        except Exception:
            return resp.status, None, text


async def api_post_json(session: aiohttp.ClientSession, url: str, payload: dict[str, Any]) -> tuple[int, Any, str]:
    async with session.post(url, json=payload) as resp:
        text = await resp.text()
        try:
            return resp.status, json.loads(text), text
        except Exception:
            return resp.status, None, text


async def benchmark_listings(session: aiohttp.ClientSession, api_base: str) -> list[Sample]:
    samples: list[Sample] = []
    for query in QUERIES:
        params = urlencode(query["listing"])
        url = f"{api_base.rstrip('/')}/v1/listings/search?{params}"
        start = time.perf_counter()
        try:
            status, data, text = await api_get_json(session, url)
            elapsed = (time.perf_counter() - start) * 1000
            ok = status < 400
            samples.append(
                Sample(
                    label=query["label"],
                    ok=ok,
                    latency_ms=elapsed,
                    status=status,
                    count=data.get("count") if isinstance(data, dict) else None,
                    error=None if ok else text,
                )
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            samples.append(Sample(label=query["label"], ok=False, latency_ms=elapsed, error=sanitize(exc)))
    return samples


async def benchmark_chat(session: aiohttp.ClientSession, api_base: str) -> list[Sample]:
    samples: list[Sample] = []
    for idx, query in enumerate(QUERIES, start=1):
        payload = {
            "session_id": f"audit-session-{int(time.time())}-{idx}",
            "user_id": f"audit-user-{int(time.time())}-{idx}",
            "message": query["message"],
            "channel": "benchmark",
        }
        start = time.perf_counter()
        try:
            status, data, text = await api_post_json(
                session, f"{api_base.rstrip('/')}/v1/chat/messages", payload
            )
            elapsed = (time.perf_counter() - start) * 1000
            ok = status < 400
            extra = {}
            if isinstance(data, dict):
                extra = {
                    "capacity_limited": data.get("capacity_limited"),
                    "policy_applied": data.get("policy_applied"),
                    "provider": data.get("provider"),
                    "model": data.get("model"),
                    "listings_count": len(data.get("listings") or []),
                    "reported_latency_ms": data.get("latency_ms"),
                }
            samples.append(
                Sample(
                    label=query["label"],
                    ok=ok,
                    latency_ms=elapsed,
                    status=status,
                    count=extra.get("listings_count"),
                    error=None if ok else text,
                    extra=extra,
                )
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            samples.append(Sample(label=query["label"], ok=False, latency_ms=elapsed, error=sanitize(exc)))
    return samples


def import_supabase_client() -> Any | None:
    api_path = ROOT / "apps" / "api"
    if str(api_path) not in sys.path:
        sys.path.insert(0, str(api_path))
    try:
        from app.services.supabase_client import supabase_client

        return supabase_client
    except Exception as exc:
        return {"import_error": sanitize(exc)}


async def vector_rpc_probe() -> dict[str, Any]:
    client = import_supabase_client()
    if isinstance(client, dict):
        return {"ok": False, **client}
    try:
        client.require_client()
    except Exception as exc:
        return {"ok": False, "error": sanitize(exc)}

    probes: dict[str, Any] = {}
    for dim in (384, 1536):
        start = time.perf_counter()
        try:
            result = client.client.rpc(
                "vector_property_search",
                {
                    "query_embedding": [0.0] * dim,
                    "match_threshold": 0.0,
                    "match_count": 1,
                },
            ).execute()
            elapsed = (time.perf_counter() - start) * 1000
            probes[f"vector_property_search_{dim}d"] = {
                "ok": True,
                "latency_ms": round(elapsed, 2),
                "rows": len(result.data or []),
            }
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            probes[f"vector_property_search_{dim}d"] = {
                "ok": False,
                "latency_ms": round(elapsed, 2),
                "error": sanitize(exc)[:300],
            }
    return {"ok": True, "probes": probes}


async def benchmark_vector_retrieval() -> dict[str, Any]:
    client = import_supabase_client()
    if isinstance(client, dict):
        return {"available": False, **client}
    try:
        client.require_client()
    except Exception as exc:
        return {"available": False, "error": sanitize(exc)}

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        return {"available": False, "error": f"sentence_transformers unavailable: {sanitize(exc)}"}

    start_load = time.perf_counter()
    try:
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    except Exception as exc:
        return {"available": False, "error": f"embedding model load failed: {sanitize(exc)}"}
    model_load_ms = (time.perf_counter() - start_load) * 1000

    samples: list[Sample] = []
    for query in QUERIES:
        start = time.perf_counter()
        try:
            vector = model.encode([query["message"]], show_progress_bar=False, convert_to_numpy=True)[0].tolist()
            if len(vector) != 384:
                vector = vector[:384] if len(vector) > 384 else vector + ([0.0] * (384 - len(vector)))
            result = client.client.rpc(
                "vector_property_search",
                {
                    "query_embedding": vector,
                    "match_threshold": 0.30,
                    "match_count": 10,
                },
            ).execute()
            elapsed = (time.perf_counter() - start) * 1000
            samples.append(
                Sample(
                    label=query["label"],
                    ok=True,
                    latency_ms=elapsed,
                    status=200,
                    count=len(result.data or []),
                    extra={"embedding_dim": len(vector)},
                )
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            samples.append(Sample(label=query["label"], ok=False, latency_ms=elapsed, error=sanitize(exc)))
    return {
        "available": True,
        "model_load_ms": round(model_load_ms, 2),
        "embedding_dim_used": 384,
        "summary": summarize(samples),
        "result_counts": {
            "min": min((s.count or 0) for s in samples) if samples else None,
            "max": max((s.count or 0) for s in samples) if samples else None,
            "mean": round(statistics.mean([(s.count or 0) for s in samples]), 2) if samples else None,
        },
    }


async def main_async(args: argparse.Namespace) -> dict[str, Any]:
    timeout = aiohttp.ClientTimeout(total=args.timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        counts = await supabase_counts(session)
        rpc_probe = await vector_rpc_probe()

        health: dict[str, Any] = {}
        try:
            start = time.perf_counter()
            status, data, text = await api_get_json(session, f"{args.api_base.rstrip('/')}/health")
            health = {
                "ok": status < 400,
                "status": status,
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                "data": data if status < 400 else sanitize(text)[:300],
            }
        except Exception as exc:
            health = {"ok": False, "error": sanitize(exc)}

        listings_samples = [] if args.skip_api else await benchmark_listings(session, args.api_base)
        chat_samples = [] if args.skip_chat else await benchmark_chat(session, args.api_base)

    vector = {"available": False, "skipped": True}
    if not args.skip_vector:
        vector = await benchmark_vector_retrieval()

    chat_policies: dict[str, int] = {}
    chat_capacity_limited = 0
    for sample in chat_samples:
        if sample.extra:
            policy = sample.extra.get("policy_applied")
            if policy:
                chat_policies[policy] = chat_policies.get(policy, 0) + 1
            if sample.extra.get("capacity_limited"):
                chat_capacity_limited += 1

    return {
        "benchmark": {
            "query_count": len(QUERIES),
            "api_base": "localhost" if "127.0.0.1" in args.api_base or "localhost" in args.api_base else "[redacted]",
            "timeout_seconds": args.timeout,
        },
        "supabase": {
            "configured": bool(os.getenv("SUPABASE_URL") and (os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY"))),
            "counts": counts,
            "vector_rpc_probe": rpc_probe,
        },
        "api_health": health,
        "listings_search": {
            "summary": summarize(listings_samples),
            "result_counts": {
                "min": min((s.count or 0) for s in listings_samples) if listings_samples else None,
                "max": max((s.count or 0) for s in listings_samples) if listings_samples else None,
                "mean": round(statistics.mean([(s.count or 0) for s in listings_samples]), 2) if listings_samples else None,
            },
        },
        "chat_messages": {
            "summary": summarize(chat_samples),
            "capacity_limited_count": chat_capacity_limited,
            "policies": chat_policies,
            "result_counts": {
                "min": min((s.count or 0) for s in chat_samples) if chat_samples else None,
                "max": max((s.count or 0) for s in chat_samples) if chat_samples else None,
                "mean": round(statistics.mean([(s.count or 0) for s in chat_samples]), 2) if chat_samples else None,
            },
        },
        "vector_retrieval": vector,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark tecnico do backend Alloha sem expor secrets.")
    parser.add_argument("--api-base", default=os.getenv("ALLOHA_API_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--timeout", type=float, default=35.0)
    parser.add_argument("--skip-api", action="store_true")
    parser.add_argument("--skip-chat", action="store_true")
    parser.add_argument("--skip-vector", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    load_env()
    args = parse_args()
    result = asyncio.run(main_async(args))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
