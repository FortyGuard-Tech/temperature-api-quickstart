"""Safety Rider — heat-exposure intelligence for people moving through a city.

Layers:

* ``safety_rider.config``              — environment configuration.
* ``safety_rider.temperature_service`` — ``getHyperlocalTemperature``: one point
  in, one 2 m air temperature out. Live FortyGuard or a deterministic simulator.
* ``safety_rider.rider_status``        — ``evaluateRiderSafetyStatus``: the
  Safe / Warning / Danger bands and the protocol each one triggers.
* ``safety_rider.heat_risk``           — the richer NOAA/OSHA-threshold engine,
  including the heat-index correction. Cited when a warning must be defended.
* ``safety_rider.heat_layer``          — fetching, caching, and point-querying
  the FortyGuard heatmaps the two engines above share.
* ``safety_rider.whatsapp``            — the Meta WhatsApp Cloud API channel:
  webhook in, Graph API out.

The FortyGuard API wrapper in ``fortyguard/`` is left untouched — this package
consumes it, never modifies it.
"""

__all__ = [
    "config",
    "heat_layer",
    "heat_risk",
    "rider_status",
    "temperature_service",
    "whatsapp",
]
