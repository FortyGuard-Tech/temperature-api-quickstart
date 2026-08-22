"""FastAPI application for the Safety Rider service.

Run locally::

    pip install -r requirements-service.txt
    uvicorn safety_rider.app:app --reload --port 8000

Then expose it to Meta — the Cloud API only calls **public HTTPS** URLs, so a
localhost port will not do::

    ngrok http 8000

Paste ``https://<your-ngrok-subdomain>.ngrok-free.app/webhook/whatsapp`` into the
Meta App Dashboard as the Callback URL, with ``WHATSAPP_VERIFY_TOKEN`` as the
Verify Token, then subscribe to the **messages** field.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import ConfigurationError, settings, validate_startup
from .dashboard import router as dashboard_router
from .dashboard.routes import STATIC as DASHBOARD_STATIC
from .whatsapp import router as whatsapp_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

app = FastAPI(
    title="Safety Rider",
    description="Heat-exposure intelligence for riders, delivered over WhatsApp.",
    version="0.1.0",
)

app.include_router(whatsapp_router)
app.include_router(dashboard_router)
# Leaflet is vendored rather than pulled from a CDN: a pitch demo must not be
# able to fail because someone else's network did.
app.mount("/dashboard/static", StaticFiles(directory=DASHBOARD_STATIC), name="dashboard-static")


@app.on_event("startup")
async def _startup() -> None:
    """Warn loudly about missing configuration without refusing to boot.

    Booting anyway is deliberate: during setup you often have the verify token
    before you have an access token, and you need the service reachable to
    complete Meta's handshake at all.
    """
    try:
        validate_startup()
        log.info("Configuration OK — outbound messaging enabled.")
    except ConfigurationError as exc:
        log.warning("%s", exc)
        log.warning(
            "Service is running in degraded mode: replies will be logged, not sent."
        )
    if not settings.fortyguard_api_key:
        log.warning("FORTYGUARD_API_KEY is not set — heat risk will use stub data.")
    if settings.dev_tools:
        log.warning(
            "Dev tools ENABLED: POST /api/dashboard/simulate sends a real "
            "WhatsApp message to SAFETY_RIDER_DEMO_NUMBER. Set "
            "SAFETY_RIDER_DEV_TOOLS=0 to disable."
        )
    log.info("Dashboard: http://127.0.0.1:8000/dashboard")


@app.get("/health", tags=["ops"])
async def health() -> dict[str, object]:
    """Liveness probe, plus an at-a-glance view of what is configured.

    Reports only booleans — never echo secrets from an unauthenticated endpoint.
    """
    return {
        "status": "ok",
        "configured": {
            "verify_token": bool(settings.verify_token),
            "app_secret": bool(settings.app_secret),
            "access_token": bool(settings.access_token),
            "phone_number_id": bool(settings.phone_number_id),
            "fortyguard_api_key": bool(settings.fortyguard_api_key),
        },
        "graph_api_version": settings.graph_api_version,
    }
