from __future__ import annotations

import html
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

import aiohttp
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
SUPPORT_EMAIL_TO = os.getenv("SUPPORT_EMAIL_TO", "contato@alloha.app").strip()
SUPPORT_EMAIL_FROM = os.getenv("SUPPORT_EMAIL_FROM", "Alloha <contato@alloha.app>").strip()
SUPPORT_EMAIL_ACK_ENABLED = os.getenv("SUPPORT_EMAIL_ACK_ENABLED", "true").strip().lower() not in {
    "0",
    "false",
    "no",
}


@dataclass
class SupportEmailResult:
    support_email_sent: bool
    acknowledgement_email_sent: bool
    error: Optional[str] = None


def resend_configured() -> bool:
    return bool(RESEND_API_KEY and SUPPORT_EMAIL_TO and SUPPORT_EMAIL_FROM)


def support_email_to() -> str:
    return SUPPORT_EMAIL_TO or "contato@alloha.app"


async def _send_email(payload: dict[str, Any]) -> tuple[bool, Optional[str]]:
    if not resend_configured():
        return False, "resend_not_configured"

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    timeout = aiohttp.ClientTimeout(total=20)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(RESEND_API_URL, headers=headers, json=payload) as response:
                body = await response.text()
                if response.status >= 400:
                    logger.warning("resend_request_failed status=%s body=%s", response.status, body[:500])
                    return False, f"resend_status_{response.status}"
    except Exception as exc:  # pragma: no cover
        logger.warning("resend_request_error error=%s", exc)
        return False, str(exc)

    return True, None


def _support_subject(topic: str, name: str) -> str:
    safe_topic = (topic or "Contato via formulario").strip()
    safe_name = (name or "Lead sem nome").strip()
    return f"[Alloha Support] {safe_topic} - {safe_name}"


def _support_text(
    *,
    lead_id: str,
    created_at: str,
    topic: str,
    name: str,
    phone: str,
    email: Optional[str],
    interest: Optional[str],
) -> str:
    return "\n".join(
        [
            "Novo ticket de suporte recebido pelo formulario do site.",
            "",
            f"Ticket: {lead_id}",
            f"Recebido em: {created_at}",
            f"Assunto: {topic or 'Contato geral'}",
            f"Nome: {name}",
            f"Telefone: {phone}",
            f"Email: {email or 'nao informado'}",
            "",
            "Mensagem:",
            interest or "Sem mensagem adicional.",
        ]
    )


def _support_html(
    *,
    lead_id: str,
    created_at: str,
    topic: str,
    name: str,
    phone: str,
    email: Optional[str],
    interest: Optional[str],
) -> str:
    return f"""
    <div style="font-family:Arial,Helvetica,sans-serif;background:#0b0b0b;color:#f7f7f7;padding:24px;">
      <div style="max-width:640px;margin:0 auto;background:#111;border:1px solid rgba(255,255,255,0.08);border-radius:20px;padding:28px;">
        <p style="margin:0 0 12px;font-size:12px;letter-spacing:0.18em;text-transform:uppercase;color:#ffb88a;">Alloha Support</p>
        <h1 style="margin:0 0 20px;font-size:28px;line-height:1.1;">Novo ticket recebido</h1>
        <p style="margin:0 0 24px;color:#cfcfcf;line-height:1.7;">O formulario de suporte do site recebeu uma nova solicitacao e ja foi processado.</p>
        <div style="display:grid;gap:12px;">
          <div style="padding:14px 16px;border-radius:14px;background:#171717;border:1px solid rgba(255,255,255,0.06);"><strong>Ticket:</strong> {html.escape(lead_id)}</div>
          <div style="padding:14px 16px;border-radius:14px;background:#171717;border:1px solid rgba(255,255,255,0.06);"><strong>Recebido em:</strong> {html.escape(created_at)}</div>
          <div style="padding:14px 16px;border-radius:14px;background:#171717;border:1px solid rgba(255,255,255,0.06);"><strong>Assunto:</strong> {html.escape(topic or 'Contato geral')}</div>
          <div style="padding:14px 16px;border-radius:14px;background:#171717;border:1px solid rgba(255,255,255,0.06);"><strong>Nome:</strong> {html.escape(name)}</div>
          <div style="padding:14px 16px;border-radius:14px;background:#171717;border:1px solid rgba(255,255,255,0.06);"><strong>Telefone:</strong> {html.escape(phone)}</div>
          <div style="padding:14px 16px;border-radius:14px;background:#171717;border:1px solid rgba(255,255,255,0.06);"><strong>Email:</strong> {html.escape(email or 'nao informado')}</div>
        </div>
        <div style="margin-top:18px;padding:18px;border-radius:16px;background:rgba(255,85,0,0.08);border:1px solid rgba(255,143,77,0.18);">
          <p style="margin:0 0 8px;font-size:12px;letter-spacing:0.16em;text-transform:uppercase;color:#ffbf96;">Mensagem</p>
          <p style="margin:0;line-height:1.7;color:#f4e6dc;">{html.escape(interest or 'Sem mensagem adicional.')}</p>
        </div>
      </div>
    </div>
    """.strip()


def _ack_text(*, lead_id: str, topic: str) -> str:
    return "\n".join(
        [
            "Recebemos seu contato na Alloha.",
            "",
            f"Referencia: {lead_id}",
            f"Assunto: {topic or 'Contato geral'}",
            "",
            "Seu suporte foi processado. Vamos avaliar e entraremos em contato.",
        ]
    )


def _ack_html(*, lead_id: str, topic: str) -> str:
    return f"""
    <div style="font-family:Arial,Helvetica,sans-serif;background:#0b0b0b;color:#f7f7f7;padding:24px;">
      <div style="max-width:620px;margin:0 auto;background:#111;border:1px solid rgba(255,255,255,0.08);border-radius:20px;padding:28px;">
        <p style="margin:0 0 12px;font-size:12px;letter-spacing:0.18em;text-transform:uppercase;color:#ffb88a;">Alloha</p>
        <h1 style="margin:0 0 16px;font-size:28px;line-height:1.1;">Recebemos seu contato</h1>
        <p style="margin:0 0 18px;line-height:1.7;color:#d6d6d6;">Seu suporte foi processado. Vamos avaliar e entraremos em contato.</p>
        <div style="padding:16px;border-radius:16px;background:rgba(255,85,0,0.08);border:1px solid rgba(255,143,77,0.18);">
          <p style="margin:0 0 6px;"><strong>Referencia:</strong> {html.escape(lead_id)}</p>
          <p style="margin:0;"><strong>Assunto:</strong> {html.escape(topic or 'Contato geral')}</p>
        </div>
      </div>
    </div>
    """.strip()


async def send_support_ticket(
    *,
    lead_id: str,
    created_at: str,
    topic: str,
    name: str,
    phone: str,
    email: Optional[str],
    interest: Optional[str],
) -> SupportEmailResult:
    support_payload: dict[str, Any] = {
        "from": SUPPORT_EMAIL_FROM,
        "to": support_email_to(),
        "subject": _support_subject(topic, name),
        "text": _support_text(
            lead_id=lead_id,
            created_at=created_at,
            topic=topic,
            name=name,
            phone=phone,
            email=email,
            interest=interest,
        ),
        "html": _support_html(
            lead_id=lead_id,
            created_at=created_at,
            topic=topic,
            name=name,
            phone=phone,
            email=email,
            interest=interest,
        ),
    }
    if email:
        support_payload["reply_to"] = email

    support_email_sent, error = await _send_email(support_payload)
    acknowledgement_email_sent = False

    if support_email_sent and email and SUPPORT_EMAIL_ACK_ENABLED:
        acknowledgement_email_sent, ack_error = await _send_email(
            {
                "from": SUPPORT_EMAIL_FROM,
                "to": email,
                "subject": "Recebemos seu contato na Alloha",
                "text": _ack_text(lead_id=lead_id, topic=topic),
                "html": _ack_html(lead_id=lead_id, topic=topic),
            }
        )
        if not acknowledgement_email_sent and not error:
            error = ack_error

    return SupportEmailResult(
        support_email_sent=support_email_sent,
        acknowledgement_email_sent=acknowledgement_email_sent,
        error=error,
    )
