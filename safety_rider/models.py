"""Domain types shared across the service.

``RiderLocation`` lives here rather than under ``whatsapp/`` because it is not a
WhatsApp concept: the risk engine, the heat layer, and any future channel (SMS,
a web form, a GPX upload) all speak in terms of it. Keeping it channel-neutral
also breaks the import cycle that otherwise forms between ``heat_risk`` and
``whatsapp``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiderLocation:
    """A point a rider shared, or one we resolved for them.

    ``latitude``/``longitude`` are WGS-84 decimal degrees. Note the ordering
    trap that bites everywhere in this repo: GeoJSON wants ``[longitude,
    latitude]``, while WhatsApp — and this dataclass — use latitude first.
    """

    latitude: float
    longitude: float
    name: str | None = None
    address: str | None = None

    @property
    def geojson_coordinates(self) -> list[float]:
        """``[lon, lat]`` — the order the FortyGuard API expects."""
        return [self.longitude, self.latitude]
