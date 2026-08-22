"""Heat-risk evaluation for a rider at a point in space and time.

**This module is a scaffold.** :func:`check_rider_heat_risk` returns a
structurally complete :class:`HeatRisk` today, but the numbers behind it are
placeholders. The FortyGuard call sequence that replaces them is written out in
:func:`_evaluate_live` below, along with the three constraints that make it less
straightforward than "call the API with a lat/lon".

Thresholds are the published ones the repo's use-case notebooks already cite, so
a recommendation made here can be defended the same way theirs are.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum

from fortyguard import FortyGuardClient
from fortyguard.exceptions import FortyGuardError

from . import heat_layer
from .config import settings
from .models import RiderLocation

log = logging.getLogger(__name__)

# ── Published thresholds (°C — the FortyGuard API's native unit) ────────────
# Reused verbatim from notebooks/use_cases/*.ipynb so the service and the
# notebooks cannot drift apart.
NOAA_CAUTION_C = 27.0    # NOAA heat-index "Caution" onset          (80.6 °F)
NOAA_EXTREME_C = 32.0    # NOAA "Extreme Caution" onset             (89.6 °F)
OSHA_HIGH_C = 32.2       # OSHA high-heat trigger                   (90.0 °F)
DANGER_C = 39.4          # NOAA "Danger" onset                      (103.0 °F)


class RiskLevel(str, Enum):
    """Ordered risk bands. String-valued so they serialise straight to JSON."""

    UNKNOWN = "unknown"
    LOW = "low"
    CAUTION = "caution"
    HIGH = "high"
    EXTREME = "extreme"


#: Emoji prefix per band — WhatsApp renders these inline and they survive being
#: read on a phone in bright sun far better than a colour would.
_BADGE = {
    RiskLevel.UNKNOWN: "❔",
    RiskLevel.LOW: "🟢",
    RiskLevel.CAUTION: "🟡",
    RiskLevel.HIGH: "🟠",
    RiskLevel.EXTREME: "🔴",
}


@dataclass(frozen=True)
class HeatRisk:
    """The result of one evaluation, ready to be rendered into a reply."""

    level: RiskLevel
    #: One-line verdict, e.g. "Extreme heat on your route right now".
    headline: str
    #: Supporting sentence(s) — the measurements the verdict rests on.
    detail: str
    #: What the rider should actually do. Empty for LOW/UNKNOWN.
    advice: list[str] = field(default_factory=list)
    #: Raw measurements, for logging and for the eventual richer reply.
    measurements: dict[str, float] = field(default_factory=dict)
    #: True when the numbers came from a real API call rather than the stub.
    is_live: bool = False

    def to_whatsapp_text(self) -> str:
        """Render as a WhatsApp message body (WhatsApp markdown: *bold*)."""
        lines = [f"{_BADGE[self.level]} *{self.headline}*", "", self.detail]
        if self.advice:
            lines.append("")
            lines.extend(f"• {item}" for item in self.advice)
        if not self.is_live:
            lines.append("")
            lines.append("_Preview data — live heat layer not yet connected._")
        return "\n".join(lines)


def check_rider_heat_risk(rider_location: RiderLocation) -> HeatRisk:
    """Evaluate heat risk for a rider at ``rider_location``.

    Tries the live FortyGuard layers and degrades gracefully: outside U.S.
    coverage, with live evaluation disabled, or on any API failure, it falls
    back to the stub rather than leaving the rider without a reply.

    **Blocking.** The FortyGuard endpoints are submit-then-poll and can take tens
    of seconds. Callers on the event loop must run this in a worker thread — see
    ``safety_rider.whatsapp.webhook.handle_message``.
    """
    log.info(
        "Heat-risk check for %.5f, %.5f",
        rider_location.latitude,
        rider_location.longitude,
    )

    if not heat_layer.is_in_coverage(rider_location.latitude, rider_location.longitude):
        # Bail before spending a request: the API is U.S.-only and would fail.
        return HeatRisk(
            level=RiskLevel.UNKNOWN,
            headline="Outside coverage",
            detail=(
                "Heat data is only available for locations inside the United "
                "States, so I can't assess this route."
            ),
            is_live=False,
        )

    if not (settings.heat_live and settings.fortyguard_api_key):
        log.info("Live heat evaluation disabled or no API key — using stub.")
        return _evaluate_stub(rider_location)

    try:
        return _evaluate_live(rider_location)
    except (FortyGuardError, ValueError, RuntimeError) as exc:
        # A rider waiting on WhatsApp gets a usable answer rather than silence.
        log.warning("Live heat evaluation failed (%s) — falling back to stub.", exc)
        return _evaluate_stub(rider_location)


# The exact name requested in the integration spec. The implementation is
# snake_case to match the rest of the codebase (PEP 8, and every other symbol in
# fortyguard/ and safety_rider/); this alias keeps the agreed call signature.
checkRiderHeatRisk = check_rider_heat_risk  # noqa: N816


def _evaluate_stub(rider_location: RiderLocation) -> HeatRisk:
    """Placeholder evaluation — fixed numbers, correct shape.

    Deliberately returns CAUTION rather than LOW so the reply path, the advice
    bullets, and the badge rendering are all visible while testing.
    """
    return HeatRisk(
        level=RiskLevel.CAUTION,
        headline="Moderate heat on your route",
        detail=(
            f"At your location ({rider_location.latitude:.4f}, "
            f"{rider_location.longitude:.4f}) the surface is running near "
            f"{NOAA_CAUTION_C:.0f} °C, which is the NOAA Caution threshold."
        ),
        advice=[
            "Carry water and drink before you feel thirsty.",
            "Take a shaded break every 30–40 minutes.",
        ],
        measurements={"peak_temp_c": NOAA_CAUTION_C},
        is_live=False,
    )


def _evaluate_live(rider_location: RiderLocation) -> HeatRisk:
    """Measure heat risk from live (or cached) FortyGuard layers.

    Sequence, and why it is in this order:

    1. ``tcm`` heatmap over an AOI around the rider → the tile's daily peak, in °C.
    2. ``exceedance`` heatmap over the same AOI → hours that tile spends above
       the OSHA high-heat trigger today. **This is the discriminating metric.**
       Below city scale the snapshot in step 1 is nearly flat (~0.9 °C across a
       1.2 km² area) while exceedance spreads 15+ hours over the same ground.
    3. ``env_params`` at the rider's point, anchored to the peak from step 1 —
       which is why it cannot run first; the endpoint needs that anchor.

    Both heatmaps come from :mod:`safety_rider.heat_layer`, which snaps the
    location to a shared grid cell and caches per (cell, date), so this is
    usually zero API calls.
    """
    client = FortyGuardClient()
    # The last COMPLETE day — never today. See settings.heat_days_back.
    study_date = (date.today() - timedelta(days=settings.heat_days_back)).isoformat()

    tcm_layer, exceedance_layer = heat_layer.fetch_layers(
        client,
        rider_location.latitude,
        rider_location.longitude,
        study_date=study_date,
        threshold_c=OSHA_HIGH_C,
    )

    tile = tcm_layer.lookup(rider_location.latitude, rider_location.longitude)
    if tile is None:
        raise ValueError("Rider location fell outside the fetched heat layer.")

    # tcm tiles carry temperature fields; analysis layers carry `value` instead.
    peak_c = tile.get("max_temperature")
    mean_c = tile.get("average_temperature")
    if peak_c is None:
        raise ValueError("Heat tile carried no max_temperature.")
    peak_c = float(peak_c)

    hours_above: float | None = None
    if exceedance_layer is not None:
        exceedance_tile = exceedance_layer.lookup(
            rider_location.latitude, rider_location.longitude
        )
        if exceedance_tile and exceedance_tile.get("value") is not None:
            hours_above = float(exceedance_tile["value"])

    measurements: dict[str, float] = {"peak_temp_c": round(peak_c, 2)}
    if mean_c is not None:
        measurements["mean_temp_c"] = round(float(mean_c), 2)
    if hours_above is not None:
        measurements["hours_above_osha_c"] = round(hours_above, 1)

    # Comfort curve at the rider's point, anchored to the measured peak.
    heat_index_c = _hot_hour_heat_index(client, rider_location, peak_c, study_date)
    if heat_index_c is not None:
        measurements["heat_index_c"] = round(heat_index_c, 1)

    level = classify(peak_c, hours_above)
    return HeatRisk(
        level=level,
        headline=_headline_for(level),
        detail=_detail_for(peak_c, hours_above, heat_index_c, study_date),
        advice=_advice_for(level, hours_above),
        measurements=measurements,
        is_live=True,
    )


def _hot_hour_heat_index(
    client: FortyGuardClient,
    rider_location: RiderLocation,
    peak_c: float,
    study_date: str,
) -> float | None:
    """Heat index at the hour that is actually hot, or None if unavailable.

    ``env_params`` applies a single ``temperature`` anchor across all 24 hours
    and varies only humidity, so ``heat_index_celsius`` tracks humidity and
    **peaks overnight** — it is a humidity-sensitivity curve, not a forecast.
    Reading it at the wrong hour produces alarming nonsense (the repo's own
    sample data hits 70 °C at 05:00). So we locate the hour where
    ``apparent_temperature_celsius`` — which does follow the real diurnal cycle —
    is highest, and read heat index only there.

    Failure here is non-fatal: the heatmap answer already stands on its own.
    """
    # One env_params call cost 2,900 credits in the verification run, so it is
    # cached on the same (grid cell, date) key as the heat layers rather than
    # re-billed per rider.
    cell_lat, cell_lon = heat_layer.grid_key(
        rider_location.latitude, rider_location.longitude
    )
    cache_path = (
        heat_layer.cache_dir().parent / "env_params"
        / f"env_params_rider_{cell_lat:.5f}_{cell_lon:.5f}_{study_date}.json"
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = heat_layer.cached_or_live(
            cache_path,
            f"env_params {study_date}",
            client.environmental_parameters,
            latitude=cell_lat,
            longitude=cell_lon,
            temperature=peak_c,
            start_date=study_date,
            filter_type=3,
            analysis=["heat_index_celsius", "apparent_temperature_celsius"],
            verbose=False,
            timeout=settings.heat_timeout_s,
        )
    except (FortyGuardError, ValueError, RuntimeError) as exc:
        log.warning("env_params unavailable (%s) — skipping heat index.", exc)
        return None

    apparent = _series(result, "apparent_temperature_celsius")
    heat_index = _series(result, "heat_index_celsius")
    if not apparent or not heat_index:
        return None

    hot_hour = max(range(len(apparent)), key=lambda i: apparent[i])
    if hot_hour >= len(heat_index):
        return None
    return heat_index[hot_hour]


def _series(result: dict, name: str) -> list[float]:
    """Pull one named 24-hour series out of an env_params result.

    The real envelope nests them two levels down::

        {"metadata": {...},
         "locations": [{"lat":…, "lon":…, "temperature":…,
                        "parameters": {"heat_index_celsius": [24 floats], …}}]}

    Verified against ``data/env_params/*.json``. Reading the top level instead —
    as an earlier version did — silently yields nothing, and the failure is
    invisible because the caller treats a missing series as "unavailable".
    """
    locations = result.get("locations")
    if not isinstance(locations, list) or not locations:
        return []
    parameters = (locations[0] or {}).get("parameters")
    if not isinstance(parameters, dict):
        return []

    raw = parameters.get(name)
    if not isinstance(raw, list):
        return []

    out: list[float] = []
    for item in raw:
        if item is None:
            # Some parameters (methane_ppb, co2_ppm) come back as all-None.
            return []
        try:
            out.append(float(item))
        except (TypeError, ValueError):
            return []
    return out


def _headline_for(level: RiskLevel) -> str:
    return {
        RiskLevel.LOW: "Clear to ride",
        RiskLevel.CAUTION: "Moderate heat on your route",
        RiskLevel.HIGH: "High heat on your route",
        RiskLevel.EXTREME: "Extreme heat — consider not riding",
        RiskLevel.UNKNOWN: "Couldn't assess this route",
    }[level]


def _detail_for(
    peak_c: float,
    hours_above: float | None,
    heat_index_c: float | None,
    basis_date: str | None = None,
) -> str:
    """State the measurements the verdict rests on, leading with duration.

    Names the date the figures come from. The service measures the last
    complete day, so claiming these are *today's* numbers would overstate what
    the data supports.
    """
    parts = [f"Peak where you are: *{peak_c:.1f} °C* ({_f(peak_c):.0f} °F)."]
    if hours_above is not None:
        if hours_above >= 1:
            parts.append(
                f"You'd be above the OSHA high-heat line ({OSHA_HIGH_C:.1f} °C) "
                f"for about *{hours_above:.0f} hours*."
            )
        else:
            parts.append(
                f"It stays below the OSHA high-heat line ({OSHA_HIGH_C:.1f} °C) "
                f"all day."
            )
    if heat_index_c is not None:
        parts.append(
            f"Heat index at the hottest hour: {heat_index_c:.0f} °C "
            f"({_f(heat_index_c):.0f} °F)."
        )
    if basis_date:
        # Be explicit about the basis: these are measurements from a complete
        # past day, not a forecast for the ride about to happen.
        parts.append(f"_Based on {basis_date}, the most recent complete day._")
    return " ".join(parts)


def _advice_for(level: RiskLevel, hours_above: float | None) -> list[str]:
    """Actions keyed to the band. Empty for LOW — don't nag when it's fine."""
    if level is RiskLevel.LOW:
        return []
    advice = {
        RiskLevel.CAUTION: [
            "Carry water and drink before you feel thirsty.",
            "Take a shaded break every 30–40 minutes.",
        ],
        RiskLevel.HIGH: [
            "Carry more water than you think you need.",
            "Break in shade every 20 minutes (OSHA high-heat guidance).",
            "Shift the trip to early morning or after sunset if you can.",
        ],
        RiskLevel.EXTREME: [
            "Postpone the ride if it is not essential.",
            "If you must ride: shade breaks every 15 minutes, water constantly.",
            "Know the signs of heat stroke — confusion, no sweating, nausea.",
            "Tell someone your route before you set off.",
        ],
    }.get(level, [])
    if hours_above is not None and hours_above >= 6:
        advice.append(
            f"This is a long exposure day ({hours_above:.0f} h above threshold) — "
            "a short trip now is safer than a long one later."
        )
    return advice


def _f(celsius: float) -> float:
    """°C → °F. Conversion happens at display time only; stored values stay °C."""
    return celsius * 9 / 5 + 32


def classify(peak_temp_c: float, hours_above_threshold: float | None = None) -> RiskLevel:
    """Map measurements onto a risk band.

    Split out from the evaluation so the banding logic is unit-testable without
    an API key, and so the live and stub paths cannot classify differently.
    ``hours_above_threshold`` escalates a band when exposure is sustained — the
    duration-over-peak principle from constraint (b) above.
    """
    if peak_temp_c >= DANGER_C:
        level = RiskLevel.EXTREME
    elif peak_temp_c >= OSHA_HIGH_C:
        level = RiskLevel.HIGH
    elif peak_temp_c >= NOAA_CAUTION_C:
        level = RiskLevel.CAUTION
    else:
        level = RiskLevel.LOW

    # Sustained exposure escalates one band: four hours at 33 °C is a harder day
    # than twenty minutes at 34 °C, and the snapshot alone cannot say so.
    if hours_above_threshold is not None and hours_above_threshold >= 4.0:
        order = [RiskLevel.LOW, RiskLevel.CAUTION, RiskLevel.HIGH, RiskLevel.EXTREME]
        idx = order.index(level)
        level = order[min(idx + 1, len(order) - 1)]

    return level
