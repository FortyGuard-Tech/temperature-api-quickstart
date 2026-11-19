"""Ready-made sample payloads so the notebooks run out of the box."""

# A small (~1 km²) polygon over lower Manhattan, suitable for a Basic-tier heatmap.
MANHATTAN_POLYGON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-74.0170, 40.7051],
                    [-74.0031, 40.7051],
                    [-74.0031, 40.7180],
                    [-74.0170, 40.7180],
                    [-74.0170, 40.7051],
                ]],
            },
        }
    ],
}

# A ~10.2 x 10.2 km polygon (~104 km² / ~40 mi²) covering central San Jose, CA —
# sized for a citywide urban-planner use case and within the Premium-tier heatmap
# area cap. Spans downtown, Japantown, SJSU, North San Jose, the West Side,
# Willow Glen, and the East Side.
SAN_JOSE_POLYGON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-121.9430, 37.2930],
                    [-121.8280, 37.2930],
                    [-121.8280, 37.3850],
                    [-121.9430, 37.3850],
                    [-121.9430, 37.2930],
                ]],
            },
        }
    ],
}

# A point in downtown Chicago — used as a default for satellite / street view.
CHICAGO_POINT = {"latitude": 41.8781, "longitude": -87.6298}

# Filter types accepted by endpoints that take a `date_time` object.
FILTER_TYPES = {
    "single_hour": 1,
    "range_of_hours": 2,
    "single_day": 3,
    "range_of_days": 4,
}

# Analysis categories for the Heat Intelligence endpoint.
HEAT_INTEL_ANALYSES = (
    "geographic",
    "environmental",
    "urban",
    "events",
    "anthropogenic",
)
