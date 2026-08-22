"""Flatten Meta's webhook envelope into :class:`InboundMessage` objects.

The envelope looks like this (trimmed):

.. code-block:: jsonc

    {
      "object": "whatsapp_business_account",
      "entry": [{
        "id": "<WABA id>",
        "changes": [{
          "field": "messages",
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {"display_phone_number": "...", "phone_number_id": "..."},
            "contacts": [{"profile": {"name": "Asha"}, "wa_id": "14155551234"}],
            "messages": [{
              "from": "14155551234",
              "id": "wamid.HBg...",
              "timestamp": "1740000000",
              "type": "text",
              "text": {"body": "how hot is my route?"}
            }]
          }
        }]
      }]
    }

Three things make this messier than it looks:

* ``entry`` and ``changes`` are **arrays** and may legitimately carry more than
  one item, so we iterate rather than index ``[0]``.
* A ``value`` block with no ``messages`` key is normal — that is a delivery or
  read receipt (``statuses``), which we deliberately ignore.
* Every field is optional in practice. A parser that assumes any key exists will
  eventually 500 on a payload shape Meta added after you wrote it, and Meta
  responds to 500s by retrying the same payload for hours.
"""

from __future__ import annotations

import re
from typing import Any, Iterator

from .models import InboundMessage, RiderLocation, parse_timestamp


def _extract_text(message: dict[str, Any]) -> str | None:
    """Pull user-visible text out of whichever field this message type uses."""
    msg_type = message.get("type")

    if msg_type == "text":
        return (message.get("text") or {}).get("body")

    if msg_type == "button":
        # Quick-reply button from a template message.
        return (message.get("button") or {}).get("text")

    if msg_type == "interactive":
        # List picker or reply button — the payload nests one level deeper and
        # the inner key names the widget that produced it.
        interactive = message.get("interactive") or {}
        inner = interactive.get(interactive.get("type", ""), {})
        return inner.get("title") or inner.get("id")

    # Media messages (image/video/document/audio) may carry a caption.
    media = message.get(msg_type or "", {})
    if isinstance(media, dict):
        return media.get("caption")

    return None


def _extract_location(message: dict[str, Any]) -> RiderLocation | None:
    """Build a :class:`RiderLocation` from a shared location pin, if present."""
    location = message.get("location")
    if not isinstance(location, dict):
        return None

    lat, lon = location.get("latitude"), location.get("longitude")
    if lat is None or lon is None:
        return None

    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None

    # Guard against transposed or garbage coordinates before they reach the
    # geometry layer, where they would fail in a much less obvious way.
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None

    return RiderLocation(
        latitude=lat,
        longitude=lon,
        name=location.get("name"),
        address=location.get("address"),
    )


def iter_inbound_messages(payload: dict[str, Any]) -> Iterator[InboundMessage]:
    """Yield one :class:`InboundMessage` per actual message in the payload.

    Status callbacks, unknown ``field`` values, and malformed entries are
    skipped silently — they are routine traffic, not errors.
    """
    if not isinstance(payload, dict):
        return

    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue

        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            # 'messages' is the only field this service subscribes to. Others
            # (account_update, phone_number_quality_update, ...) are ignored.
            if change.get("field") != "messages":
                continue

            value = change.get("value")
            if not isinstance(value, dict):
                continue

            metadata = value.get("metadata") or {}
            phone_number_id = metadata.get("phone_number_id")

            # contacts[] is a parallel array keyed by wa_id — build a lookup so
            # we can attach the rider's display name to their message.
            names: dict[str, str] = {}
            for contact in value.get("contacts") or []:
                if isinstance(contact, dict) and contact.get("wa_id"):
                    profile = contact.get("profile") or {}
                    if profile.get("name"):
                        names[contact["wa_id"]] = profile["name"]

            for message in value.get("messages") or []:
                if not isinstance(message, dict):
                    continue
                sender = message.get("from")
                message_id = message.get("id")
                # Without these two we can neither reply nor dedupe, so drop it.
                if not sender or not message_id:
                    continue

                yield InboundMessage(
                    message_id=message_id,
                    from_number=sender,
                    message_type=message.get("type") or "unknown",
                    timestamp=parse_timestamp(message.get("timestamp")),
                    text=_extract_text(message),
                    location=_extract_location(message),
                    profile_name=names.get(sender),
                    phone_number_id=phone_number_id,
                )


#: ``37.3318, -121.8899`` and friends: optional sign, optional decimals, any
#: mix of comma/whitespace/slash between them. Anchored at both ends so a
#: sentence that merely *contains* two numbers ("in 5, 10 minutes") is ignored.
_COORD_RE = re.compile(
    r"^\s*(?P<lat>[-+]?\d{1,2}(?:\.\d+)?)\s*[,;/\s]\s*(?P<lon>[-+]?\d{1,3}(?:\.\d+)?)\s*$"
)


def coordinates_from_text(text: str | None) -> RiderLocation | None:
    """Parse ``"lat, lon"`` typed as a plain message, or None.

    A convenience path, not the primary one — riders share a location pin. It
    exists because it makes the whole pipeline testable from any WhatsApp
    client without a GPS fix, and because dispatchers paste coordinates.
    """
    if not text:
        return None
    match = _COORD_RE.match(text)
    if not match:
        return None
    try:
        latitude = float(match.group("lat"))
        longitude = float(match.group("lon"))
    except ValueError:
        return None
    # Same bounds check the location-pin path applies.
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return RiderLocation(latitude=latitude, longitude=longitude, name="typed coordinates")
