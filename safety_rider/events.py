"""In-process event hub and rider registry backing the live dashboard.

Two things live here:

* :class:`RiderState` — where each rider is and how hot it is there. The map
  draws from this.
* :class:`Hub` — a fan-out bus. The webhook pipeline publishes one event per
  evaluation; every open dashboard receives it over Server-Sent Events.

**Scope: one process.** Subscribers are :class:`asyncio.Queue` objects held in
memory, so this works for a single uvicorn worker and breaks silently the
moment you run two — the rider who hits worker B never appears on a dashboard
streaming from worker A. That is the right trade for a hackathon demo and the
wrong one for production; swap the hub for Redis pub/sub when you scale out.
The dedup cache in :mod:`safety_rider.whatsapp.webhook` has the same limit and
should move at the same time.

Slow or dead subscribers are dropped rather than allowed to apply backpressure:
a browser tab that stops reading must never be able to stall the pipeline that
answers riders.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator

log = logging.getLogger(__name__)

#: How many past events a newly-opened dashboard is replayed. Enough that a
#: judge opening the page mid-demo sees the story so far, not an empty panel.
HISTORY_LIMIT = 100

#: Dropped if a subscriber falls this far behind — see the module docstring.
QUEUE_MAXSIZE = 200


def mask_number(number: str) -> str:
    """``14155550123`` → ``+14155****123``.

    The dashboard is built to be screen-shared in a pitch video, so a rider's
    full number must not be the default. Set ``SAFETY_RIDER_DASHBOARD_UNMASK=1``
    to show it in full when you are demoing to yourself.
    """
    digits = "".join(ch for ch in number if ch.isdigit())
    if not digits:
        # Not a phone number at all (e.g. the "demo" placeholder). Pass it
        # through rather than emitting a bare "+".
        return number
    if len(digits) <= 8:
        return "+" + digits
    return f"+{digits[:5]}****{digits[-3:]}"


@dataclass
class RiderState:
    """One rider's latest known position and heat status."""

    rider_id: str
    latitude: float
    longitude: float
    status: str = "unknown"          # safe | warning | danger | unknown
    temperature_c: float | None = None
    hours_above_threshold: float | None = None
    label: str | None = None
    source: str = "unknown"          # live | mock | unavailable
    observed_date: str | None = None
    updated_at: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Event:
    """One line in the live alert feed."""

    kind: str                        # evaluation | message | system
    text: str
    status: str = "info"             # safe | warning | danger | unknown | info
    rider_id: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    temperature_c: float | None = None
    at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Hub:
    """Fan-out event bus plus the current rider snapshot."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._riders: dict[str, RiderState] = {}
        self._history: deque[Event] = deque(maxlen=HISTORY_LIMIT)

    # ── state ──────────────────────────────────────────────────────────────

    def upsert_rider(self, state: RiderState) -> None:
        self._riders[state.rider_id] = state

    def riders(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._riders.values()]

    def history(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._history]

    def clear(self) -> None:
        """Reset between demo runs."""
        self._riders.clear()
        self._history.clear()

    # ── pub/sub ────────────────────────────────────────────────────────────

    def publish(self, event: Event) -> None:
        """Record an event and push it to every live dashboard.

        Synchronous and non-blocking on purpose: it is called from the message
        pipeline, which must never wait on a browser.
        """
        self._history.append(event)
        payload = json.dumps(event.to_dict())
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                # Subscriber is not draining. Drop it rather than stall here.
                log.warning("Dropping a saturated dashboard subscriber.")
                self._subscribers.discard(queue)

    @contextlib.asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[str]]:
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=QUEUE_MAXSIZE)
        self._subscribers.add(queue)
        log.info("Dashboard subscribed (%d live).", len(self._subscribers))
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)
            log.info("Dashboard unsubscribed (%d live).", len(self._subscribers))

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


#: Module-level singleton. Imported by both the pipeline and the dashboard.
hub = Hub()
