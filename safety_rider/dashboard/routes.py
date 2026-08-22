"""Dashboard API: page, snapshot, SSE stream, and the demo simulator.

Endpoints
---------
``GET  /dashboard``                  the page itself
``GET  /api/dashboard/state``        riders + recent events, for first paint
``GET  /api/dashboard/stream``       Server-Sent Events, one per evaluation
``POST /api/dashboard/simulate``     force a heat spike (demo only)

SSE rather than WebSockets: the traffic is one-way, it is plain HTTP so it
survives the Cloudflare tunnel without an upgrade handshake, and ``EventSource``
reconnects on its own — during a live pitch that last property matters more
than anything a socket would buy.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..config import settings
from ..events import Event, hub
from ..models import RiderLocation
from ..rider_status import evaluate_rider_safety_status
from ..temperature_service import get_hyperlocal_temperature
from ..whatsapp import graph_client
from ..whatsapp.webhook import publish_evaluation

log = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])
STATIC = Path(__file__).parent / "static"

#: Heartbeat interval. Without periodic traffic an idle SSE connection gets
#: reaped by proxies (the tunnel included) after ~60 s and the feed goes quiet
#: with no visible error — the worst failure mode during a demo.
KEEPALIVE_SECONDS = 20.0


@router.get("/dashboard", include_in_schema=False)
async def dashboard_page() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@router.get("/api/dashboard/state")
async def dashboard_state() -> dict:
    """Everything needed to paint the dashboard once, before the stream opens."""
    return {
        "riders": hub.riders(),
        "events": hub.history(),
        "center": {"lat": settings.map_center_lat, "lon": settings.map_center_lon},
        "dev_tools": settings.dev_tools,
        "demo_number_configured": bool(settings.demo_number),
        "mock_mode": settings.mock_temperature,
        "subscribers": hub.subscriber_count,
    }


@router.get("/api/dashboard/stream")
async def dashboard_stream(request: Request) -> StreamingResponse:
    """Stream events as they happen."""

    async def generate():
        async with hub.subscribe() as queue:
            yield f": connected\n\ndata: {json.dumps({'kind': 'system', 'text': 'Live feed connected.', 'status': 'info'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), KEEPALIVE_SECONDS)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"   # comment frame; EventSource ignores it
                    continue
                yield f"data: {payload}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",   # stops nginx-style proxies buffering the stream
        },
    )


class SimulateRequest(BaseModel):
    """Body for the demo simulator.

    Note what is absent: a recipient. The number comes from
    ``SAFETY_RIDER_DEMO_NUMBER``, never from the request — this endpoint is
    reachable through the same public tunnel as the webhook, and one that
    messaged an arbitrary number on request would be an open spam relay.
    """

    latitude: float | None = None
    longitude: float | None = None
    temperature_c: float = Field(default=41.5, ge=-50, le=70)
    rider_label: str = "Demo rider"
    send_whatsapp: bool = True


@router.post("/api/dashboard/simulate")
async def simulate_heat_spike(body: SimulateRequest) -> dict:
    """Force a rider into a high-heat zone and run the real pipeline on it.

    Everything downstream of the temperature is genuine: the same banding
    engine, the same reply text, the same Graph call. Only the temperature is
    forced, and the reply carries the ``SIMULATED`` provenance line so it can
    never be mistaken for a measurement.
    """
    if not settings.dev_tools:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Dev tools are disabled (SAFETY_RIDER_DEV_TOOLS=0).")

    lat = body.latitude if body.latitude is not None else settings.map_center_lat
    lon = body.longitude if body.longitude is not None else settings.map_center_lon
    location = RiderLocation(latitude=lat, longitude=lon, name="Block B")

    # Real reading for provenance/duration, then override the temperature so the
    # band is deterministic for the demo.
    reading = await asyncio.to_thread(get_hyperlocal_temperature, lat, lon)
    forced = body.temperature_c
    hours = reading.hours_above_threshold if reading.ok else None
    result = evaluate_rider_safety_status(forced, hours_above_threshold=hours)

    to_number = settings.demo_number
    sent = False
    error: str | None = None

    if body.send_whatsapp and to_number:
        try:
            await graph_client.send_text(to_number, result.to_whatsapp_text(reading))
            sent = True
        except Exception as exc:  # noqa: BLE001 — surface it, never 500 the demo
            error = str(exc)[:300]
            log.error("Simulate: WhatsApp send failed: %s", error)
    elif body.send_whatsapp and not to_number:
        error = "SAFETY_RIDER_DEMO_NUMBER is not set — nothing was sent."

    publish_evaluation(
        from_number=to_number or "demo",
        location=location,
        status=result,
        reading=reading,
        label=body.rider_label,
    )
    if error:
        hub.publish(Event(kind="system", text=f"Simulate: {error}", status="unknown"))

    return {
        "status": result.status.value,
        "temperature_c": result.temperature_c,
        "rest_protocol": result.rest_protocol,
        "whatsapp_sent": sent,
        "error": error,
        "reply_preview": result.to_whatsapp_text(reading),
    }


@router.post("/api/dashboard/reset", include_in_schema=False)
async def reset() -> dict:
    """Clear riders and feed between demo takes."""
    if not settings.dev_tools:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Dev tools are disabled.")
    hub.clear()
    hub.publish(Event(kind="system", text="Dashboard reset.", status="info"))
    return {"ok": True}
