"""Outbound side of the WhatsApp Cloud API — sending a reply via Graph.

**Placeholder status:** the request is built and signed correctly and will work
against the real Graph API once ``WHATSAPP_ACCESS_TOKEN`` and
``WHATSAPP_PHONE_NUMBER_ID`` are set. With them unset, :func:`send_text` logs
what it *would* have sent and returns without a network call, so the webhook can
be exercised end-to-end before any Meta credentials exist.

Two Meta rules that will bite otherwise:

* **The 24-hour customer service window.** Free-form messages are only allowed
  within 24 hours of the rider's last inbound message. Outside it, Graph rejects
  the send and you must use a pre-approved *template* instead — see
  :func:`send_template`.
* **Recipient allow-list in test mode.** Until the app is published, Graph only
  delivers to numbers explicitly added in the WhatsApp Manager. A 200 response
  does not by itself mean a phone buzzed.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import settings

log = logging.getLogger(__name__)

#: Graph is generally fast, but a hung outbound call must not wedge a worker.
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class WhatsAppSendError(RuntimeError):
    """Graph rejected an outbound message."""


def _configured() -> bool:
    return bool(settings.access_token and settings.phone_number_id)


async def _post(payload: dict[str, Any], *, description: str) -> dict[str, Any] | None:
    """POST to the Graph messages endpoint, or log-and-skip if unconfigured."""
    if not _configured():
        # PLACEHOLDER PATH — no credentials, so no network call.
        log.warning(
            "WhatsApp not configured (WHATSAPP_ACCESS_TOKEN / "
            "WHATSAPP_PHONE_NUMBER_ID missing) — would have sent %s: %s",
            description,
            payload,
        )
        return None

    headers = {
        "Authorization": f"Bearer {settings.access_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as http:
        response = await http.post(settings.messages_url, json=payload, headers=headers)

    if response.status_code >= 400:
        # Graph puts the useful part in body.error.message; the status code
        # alone rarely says what was wrong with the payload.
        raise WhatsAppSendError(
            f"Graph {response.status_code} sending {description}: {response.text[:500]}"
        )

    log.info("Sent %s to Graph", description)
    return response.json()


async def send_text(
    to_number: str,
    body: str,
    *,
    preview_url: bool = False,
) -> dict[str, Any] | None:
    """Send a plain text message to a rider.

    ``to_number`` is E.164 without the leading '+', exactly as it arrives in the
    webhook's ``from`` field. WhatsApp caps a text body at 4096 characters, so
    long bodies are truncated rather than rejected by Graph.
    """
    if len(body) > 4096:
        body = body[:4093] + "..."

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "text",
        "text": {"preview_url": preview_url, "body": body},
    }
    return await _post(payload, description=f"text to {to_number}")


async def send_template(
    to_number: str,
    template_name: str,
    language_code: str = "en_US",
    components: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Send a pre-approved template — the only option outside the 24-hour window.

    A heat *alert* the service initiates (rather than one a rider asked for)
    always goes out this way, so this is the path a proactive warning will use.
    """
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "template",
        "template": {"name": template_name, "language": {"code": language_code}},
    }
    if components:
        payload["template"]["components"] = components
    return await _post(payload, description=f"template '{template_name}' to {to_number}")


async def mark_as_read(message_id: str) -> dict[str, Any] | None:
    """Show the rider a blue tick so they know the bot picked the message up."""
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    return await _post(payload, description=f"read receipt for {message_id}")
