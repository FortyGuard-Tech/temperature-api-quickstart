"""Normalised shapes for the bits of Meta's webhook payload we care about.

Meta's envelope is deeply nested and carries several things that are *not*
messages (delivery receipts, read receipts, errors, account updates). Rather
than pass raw dicts around, the parser flattens the parts we act on into these
small dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

# Re-exported so channel code can keep importing it from here, but defined in
# safety_rider.models — it is a domain type, not a WhatsApp one.
from ..models import RiderLocation


@dataclass(frozen=True)
class InboundMessage:
    """One message from one rider, flattened out of the webhook envelope."""

    #: Meta's message id (``wamid.***``). Stable across retries — dedupe on it.
    message_id: str
    #: Sender's phone number in E.164 without the leading '+' (e.g. "14155551234").
    #: This is also the value you pass back as ``to`` when replying.
    from_number: str
    #: ``text`` | ``location`` | ``image`` | ``interactive`` | ... — Meta's own type string.
    message_type: str
    #: When Meta says the message was sent.
    timestamp: datetime
    #: Body of a text message, or the caption of a media message. None otherwise.
    text: str | None = None
    #: Present only when the rider shared a location pin.
    location: RiderLocation | None = None
    #: Display name from the contacts block, when Meta includes it.
    profile_name: str | None = None
    #: The business phone number ID this arrived on — echo it when replying so a
    #: multi-number deployment answers from the number the rider wrote to.
    phone_number_id: str | None = None

    @property
    def is_actionable(self) -> bool:
        """True when there is something for the risk engine to work with."""
        return self.location is not None or bool(self.text)


def parse_timestamp(raw: str | int | None) -> datetime:
    """Meta sends a Unix epoch as a *string*. Fall back to now() if absent."""
    try:
        return datetime.fromtimestamp(int(raw), tz=timezone.utc)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return datetime.now(tz=timezone.utc)


__all__ = ["RiderLocation", "InboundMessage", "parse_timestamp"]
