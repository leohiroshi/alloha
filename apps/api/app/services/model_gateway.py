"""
Model Gateway

OpenRouter free-first policy with hard-stop fallback.
Adds Redis-backed budget and rate controls.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import aiohttp

from app.services import redis_client

logger = logging.getLogger(__name__)


@dataclass
class ModelGatewayResult:
    reply: str
    provider: str
    model: str
    policy_applied: str
    capacity_limited: bool


class ModelGateway:
    def __init__(self) -> None:
        self.primary_provider = os.getenv("PRIMARY_PROVIDER", "openrouter_free")
        self.fallback_policy = os.getenv("FALLBACK_POLICY", "hard_stop")
        self.hard_stop_message = os.getenv(
            "HARD_STOP_MESSAGE",
            "Estamos no limite de capacidade gratuita agora. Tente novamente em alguns minutos.",
        )
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_endpoint = os.getenv(
            "OPENROUTER_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions"
        )
        self.openrouter_model = os.getenv(
            "OPENROUTER_FREE_MODEL", "tngtech/deepseek-r1t2-chimera:free"
        )

        # Guardrails
        self.user_rpm_limit = int(os.getenv("OPENROUTER_USER_RPM_LIMIT", "20"))
        self.user_rpd_limit = int(os.getenv("OPENROUTER_USER_RPD_LIMIT", "50"))
        self.global_rpd_limit = int(os.getenv("OPENROUTER_GLOBAL_RPD_LIMIT", "500"))

        self.request_timeout_seconds = int(os.getenv("MODEL_TIMEOUT_SECONDS", "25"))

    @staticmethod
    def _current_utc_day() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _metric_key(self, metric: str) -> str:
        return f"metrics:model_gateway:{self._current_utc_day()}:{metric}"

    async def _inc_metric(self, metric: str, ex_seconds: int = 3 * 24 * 60 * 60) -> None:
        try:
            await redis_client.incr(self._metric_key(metric), ex=ex_seconds)
        except Exception:
            pass

    async def _read_metric(self, metric: str) -> int:
        try:
            raw = await redis_client.get(self._metric_key(metric))
            return int(raw or 0)
        except Exception:
            return 0

    async def _check_limits(self, user_id: str) -> Tuple[bool, str]:
        day = self._current_utc_day()
        user_minute_key = f"mg:user:{user_id}:m"
        user_day_key = f"mg:user:{user_id}:d:{day}"
        global_day_key = f"mg:global:d:{day}"

        allowed_minute, _ = await redis_client.rate_limit(
            user_minute_key, self.user_rpm_limit, 60
        )
        if not allowed_minute:
            return False, "user_rpm_limit"

        allowed_day, _ = await redis_client.rate_limit(
            user_day_key, self.user_rpd_limit, 24 * 60 * 60
        )
        if not allowed_day:
            return False, "user_rpd_limit"

        allowed_global, _ = await redis_client.rate_limit(
            global_day_key, self.global_rpd_limit, 24 * 60 * 60
        )
        if not allowed_global:
            return False, "global_rpd_limit"

        return True, "ok"

    async def _openrouter_chat(self, messages: List[Dict[str, Any]]) -> ModelGatewayResult:
        if not self.openrouter_api_key:
            await self._inc_metric("hard_stop_total")
            await self._inc_metric("hard_stop_no_api_key")
            return ModelGatewayResult(
                reply=self.hard_stop_message,
                provider="openrouter",
                model=self.openrouter_model,
                policy_applied="hard_stop_no_api_key",
                capacity_limited=True,
            )

        payload = {
            "model": self.openrouter_model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 512,
        }
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
        }

        timeout = aiohttp.ClientTimeout(total=self.request_timeout_seconds)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.openrouter_endpoint, headers=headers, json=payload
                ) as resp:
                    raw_text = await resp.text()
                    if resp.status >= 400:
                        logger.warning(
                            "OpenRouter request failed status=%s body=%s",
                            resp.status,
                            raw_text[:300],
                        )
                        await self._inc_metric("hard_stop_total")
                        await self._inc_metric(f"hard_stop_upstream_{resp.status}")
                        return ModelGatewayResult(
                            reply=self.hard_stop_message,
                            provider="openrouter",
                            model=self.openrouter_model,
                            policy_applied=f"hard_stop_upstream_{resp.status}",
                            capacity_limited=True,
                        )

                    data = await resp.json()
                    reply = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                        .strip()
                    )
                    if not reply:
                        await self._inc_metric("hard_stop_total")
                        await self._inc_metric("hard_stop_empty_response")
                        return ModelGatewayResult(
                            reply=self.hard_stop_message,
                            provider="openrouter",
                            model=self.openrouter_model,
                            policy_applied="hard_stop_empty_response",
                            capacity_limited=True,
                        )

                    await self._inc_metric("success_total")
                    await self._inc_metric("success_openrouter")
                    return ModelGatewayResult(
                        reply=reply,
                        provider="openrouter",
                        model=self.openrouter_model,
                        policy_applied="primary_openrouter_free",
                        capacity_limited=False,
                    )
        except Exception as exc:
            logger.warning("OpenRouter request exception: %s", exc)
            await self._inc_metric("hard_stop_total")
            await self._inc_metric("hard_stop_exception")
            return ModelGatewayResult(
                reply=self.hard_stop_message,
                provider="openrouter",
                model=self.openrouter_model,
                policy_applied="hard_stop_exception",
                capacity_limited=True,
            )

    async def chat(self, user_id: str, messages: List[Dict[str, Any]]) -> ModelGatewayResult:
        allowed, reason = await self._check_limits(user_id)
        if not allowed:
            await self._inc_metric("hard_stop_total")
            await self._inc_metric(f"hard_stop_{reason}")
            return ModelGatewayResult(
                reply=self.hard_stop_message,
                provider=self.primary_provider,
                model=self.openrouter_model,
                policy_applied=f"hard_stop_{reason}",
                capacity_limited=True,
            )

        if self.primary_provider == "openrouter_free":
            return await self._openrouter_chat(messages)

        # Unknown provider: enforce hard stop because fallback policy is explicit.
        await self._inc_metric("hard_stop_total")
        await self._inc_metric("hard_stop_unknown_provider")
        return ModelGatewayResult(
            reply=self.hard_stop_message,
            provider=self.primary_provider,
            model=self.openrouter_model,
            policy_applied="hard_stop_unknown_provider",
            capacity_limited=True,
        )

    async def get_metrics(self) -> Dict[str, int]:
        return {
            "success_total": await self._read_metric("success_total"),
            "success_openrouter": await self._read_metric("success_openrouter"),
            "hard_stop_total": await self._read_metric("hard_stop_total"),
            "hard_stop_user_rpm_limit": await self._read_metric("hard_stop_user_rpm_limit"),
            "hard_stop_user_rpd_limit": await self._read_metric("hard_stop_user_rpd_limit"),
            "hard_stop_global_rpd_limit": await self._read_metric("hard_stop_global_rpd_limit"),
            "hard_stop_no_api_key": await self._read_metric("hard_stop_no_api_key"),
            "hard_stop_exception": await self._read_metric("hard_stop_exception"),
        }


model_gateway = ModelGateway()
