"""Hyperlocal 2 m air temperature for a single point.

This is the narrow surface the rest of the service asks questions through:
give it a latitude and longitude, get back a temperature you can act on. It
never raises — a rider waiting on WhatsApp must get an answer, so failure is
returned as data (``TemperatureReading.ok is False``) rather than thrown.

Two things worth knowing before you trust a number that comes out of here:

**Resolution.** FortyGuard resolves 2 m air temperature down to a 60/80/100 m
tile — not 10 m. ``settings.heat_granularity_m`` picks which, and the API
rejects anything else. That is still block-by-block: at 100 m a shaded side
street and the parking lot beside it land in different tiles, which is the
distinction a rider actually feels.

**"Current".** The catalog covers 2021 through today, but *today* means only
the hours that have already elapsed. Asked at 08:00 it returns the overnight
temperatures and nothing else, so a 36 °C afternoon reads as 18 °C and a rider
is told to go. This module therefore reports the most recent **complete** day
(``settings.heat_days_back``) and labels every reading with the date it came
from. :attr:`TemperatureReading.observed_date` is not decoration — show it.
"""

from __future__ import annotations

import hashlib
import logging
import math
from dataclasses import dataclass
from datetime import date, timedelta

from fortyguard import FortyGuardClient
from fortyguard.exceptions import FortyGuardError

from . import heat_layer
from .config import settings

log = logging.getLogger(__name__)

#: Where a reading came from. Carried on every reading so a caller — and the
#: rider — can tell a measurement from a simulation.
SOURCE_LIVE = "live"
SOURCE_MOCK = "mock"
SOURCE_UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class TemperatureReading:
    """One temperature answer for one point.

    :attr:`celsius` is the day's **peak** 2 m air temperature at this tile, not
    its average. Rider safety is decided by the worst part of the ride, and the
    daily mean at this latitude sits ~12 °C below the peak — averaging is how a
    36.9 °C afternoon gets reported as a comfortable 24.8 °C one.
    """

    celsius: float
    latitude: float
    longitude: float
    source: str
    #: The date these figures describe. Never today — see the module docstring.
    observed_date: str | None = None
    #: Same tile, same day: the overnight low and the 24-hour mean.
    daily_min_c: float | None = None
    daily_mean_c: float | None = None
    #: Hours this tile spends above the OSHA high-heat trigger, when the
    #: exceedance layer came back. This is the metric that separates two points
    #: a few blocks apart; the peak above is nearly flat at that scale.
    hours_above_threshold: float | None = None
    #: Tile edge length in metres for a live reading.
    resolution_m: int | None = None
    #: Populated only when :attr:`source` is ``unavailable``.
    error: str | None = None
    #: Why this reading was simulated rather than measured. Diagnostic only —
    #: it is the difference between "demo switch is on" and "the API 500ed",
    #: which look identical from the outside.
    note: str | None = None

    @property
    def ok(self) -> bool:
        """True when :attr:`celsius` is a number worth acting on."""
        return self.source != SOURCE_UNAVAILABLE and math.isfinite(self.celsius)

    @property
    def is_live(self) -> bool:
        return self.source == SOURCE_LIVE

    @property
    def fahrenheit(self) -> float:
        return self.celsius * 9 / 5 + 32

    def __float__(self) -> float:
        """Lets a reading be passed straight into anything expecting a float."""
        return float(self.celsius)

    def describe(self) -> str:
        """One line of provenance, safe to show a rider."""
        if not self.ok:
            return "no temperature data available for this location"
        where = f"{self.resolution_m} m tile" if self.resolution_m else "simulated tile"
        when = self.observed_date or "recent data"
        label = "measured" if self.is_live else "SIMULATED"
        return f"{label}, {where}, {when}"


# ─────────────────────────────────────────────────────────────── public API


def get_hyperlocal_temperature(
    latitude: float,
    longitude: float,
    *,
    force_mock: bool | None = None,
) -> TemperatureReading:
    """Ambient 2 m air temperature at ``(latitude, longitude)``.

    Resolution order:

    1. ``force_mock=True``, or ``SAFETY_RIDER_MOCK_TEMPERATURE=1`` → simulated.
    2. Live disabled (``SAFETY_RIDER_LIVE_HEAT=0``) or no API key → simulated.
    3. Outside U.S. coverage → simulated, flagged as such.
    4. Otherwise → FortyGuard, served from the shared per-(grid cell, date)
       cache so riders a few blocks apart cost one API call between them.

    Falls back to a simulated reading if the live call fails, so this function
    has no failure mode that leaves a rider without an answer. It blocks — the
    FortyGuard endpoints are submit-then-poll — so call it from a worker
    thread, never straight off the event loop.
    """
    if not (math.isfinite(latitude) and math.isfinite(longitude)):
        return TemperatureReading(
            celsius=float("nan"), latitude=latitude, longitude=longitude,
            source=SOURCE_UNAVAILABLE, error="Coordinates were not finite numbers.",
        )

    use_mock = force_mock if force_mock is not None else settings.mock_temperature
    if use_mock:
        return _mock_reading(latitude, longitude, why="mock mode enabled")

    if not (settings.heat_live and settings.fortyguard_api_key):
        return _mock_reading(latitude, longitude, why="live heat disabled or no API key")

    if not heat_layer.is_in_coverage(latitude, longitude):
        # Bail before spending a request: the API is U.S.-only and would fail.
        return _mock_reading(latitude, longitude, why="outside U.S. coverage")

    try:
        return _live_reading(latitude, longitude)
    except (FortyGuardError, ValueError, RuntimeError, OSError) as exc:
        log.warning("Live temperature lookup failed (%s) — simulating instead.", exc)
        return _mock_reading(latitude, longitude, why=f"live lookup failed: {exc}")


#: The camelCase name from the integration spec. The implementation is
#: snake_case to match every other symbol in this repo (PEP 8); this alias keeps
#: the agreed call signature working.
getHyperlocalTemperature = get_hyperlocal_temperature  # noqa: N816


# ──────────────────────────────────────────────────────────────── live path


def _live_reading(latitude: float, longitude: float) -> TemperatureReading:
    """Read the rider's tile out of the cached FortyGuard layers."""
    from .heat_risk import OSHA_HIGH_C  # local import: heat_risk imports us back

    client = FortyGuardClient()
    study_date = (date.today() - timedelta(days=settings.heat_days_back)).isoformat()

    tcm_layer, exceedance_layer = heat_layer.fetch_layers(
        client, latitude, longitude, study_date=study_date, threshold_c=OSHA_HIGH_C,
    )

    tile = tcm_layer.lookup(latitude, longitude)
    if tile is None:
        raise ValueError("Point fell outside the fetched heat layer.")

    # tcm tiles carry min/average/max temperature in °C. (The vendored SDK
    # docstring says °F; the data disagrees — a San Jose August tile reads
    # 16.8/24.8/36.9, which is only coherent as Celsius.)
    peak = tile.get("max_temperature")
    if peak is None:
        raise ValueError("Heat tile carried no max_temperature.")

    hours_above: float | None = None
    if exceedance_layer is not None:
        exceedance_tile = exceedance_layer.lookup(latitude, longitude)
        if exceedance_tile and exceedance_tile.get("value") is not None:
            hours_above = float(exceedance_tile["value"])

    mean = tile.get("average_temperature")
    low = tile.get("min_temperature")

    return TemperatureReading(
        celsius=round(float(peak), 2),
        latitude=latitude,
        longitude=longitude,
        source=SOURCE_LIVE,
        observed_date=study_date,
        daily_min_c=round(float(low), 2) if low is not None else None,
        daily_mean_c=round(float(mean), 2) if mean is not None else None,
        hours_above_threshold=round(hours_above, 1) if hours_above is not None else None,
        resolution_m=settings.heat_granularity_m,
    )


# ──────────────────────────────────────────────────────────────── mock path


def _mock_reading(latitude: float, longitude: float, *, why: str) -> TemperatureReading:
    """A plausible, **deterministic** stand-in for a live measurement.

    Deterministic on purpose. A random value makes a demo unreproducible and
    makes a failing test unfixable; hashing the grid cell and date means the
    same pin returns the same number all day, and a different pin returns a
    different one. ``SAFETY_RIDER_MOCK_TEMP_C`` overrides it outright, which is
    how you demo the Danger branch on a mild afternoon.
    """
    observed = (date.today() - timedelta(days=settings.heat_days_back)).isoformat()
    cell_lat, cell_lon = heat_layer.grid_key(latitude, longitude)

    override = settings.mock_temp_c
    if override is not None:
        peak = float(override)
    else:
        # 0.0–1.0 from the cell and date, spread across 26–44 °C so all three
        # safety bands are reachable by moving the pin around a city.
        seed = f"{cell_lat:.5f},{cell_lon:.5f},{observed}".encode()
        unit = int(hashlib.sha256(seed).hexdigest()[:8], 16) / 0xFFFFFFFF
        peak = round(26.0 + unit * 18.0, 1)

    # A diurnal range that matches the real tiles we have on disk (~12 °C peak
    # to mean, ~20 °C peak to overnight low), so downstream code exercising
    # mean/min sees realistic proportions rather than round numbers.
    mean = round(peak - 12.1, 1)
    low = round(peak - 20.1, 1)

    # Rough exceedance: hours above the OSHA line scale with how far the peak
    # clears it. Zero when the day never gets there.
    from .heat_risk import OSHA_HIGH_C  # local import: see _live_reading

    hours = round(max(0.0, min(14.0, (peak - OSHA_HIGH_C) * 1.6)), 1)

    log.info("Simulated temperature for %.5f,%.5f (%s): %.1f °C",
             latitude, longitude, why, peak)

    return TemperatureReading(
        celsius=peak,
        latitude=latitude,
        longitude=longitude,
        source=SOURCE_MOCK,
        observed_date=observed,
        daily_min_c=low,
        daily_mean_c=mean,
        hours_above_threshold=hours,
        resolution_m=None,
        note=why,
    )
