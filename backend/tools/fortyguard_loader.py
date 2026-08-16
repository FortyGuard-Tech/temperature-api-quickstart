import json
from pathlib import Path
from typing import Dict, Any, List, Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

def load_san_jose_thermal_profile(parcel_id: str = "APN-264-11-032") -> Dict[str, Any]:
    """
    Loads FortyGuard San Jose thermal profile datasets: TCM heatmaps, satellite surface data, and env parameters.
    """
    heatmap_file = DATA_DIR / "heatmaps/heatmap_parcel_portfolio_san_jose_2026-08-03_tcm.json"
    satellite_file = DATA_DIR / f"satellite/satellite_parcel_portfolio_san_jose_{parcel_id}_2026-08-03.json"
    env_file = DATA_DIR / f"env_params/env_params_parcel_portfolio_san_jose_{parcel_id}_2026-08-03.json"
    streetview_file = DATA_DIR / f"street_view/streetview_parcel_portfolio_san_jose_{parcel_id}.json"
    
    if not satellite_file.exists():
        satellite_file = DATA_DIR / "satellite/satellite_parcel_diridon_san_jose_2024-07-15.json"
    if not env_file.exists():
        env_file = DATA_DIR / "env_params/env_params_parcel_diridon_san_jose_2024-07-15.json"
    if not streetview_file.exists():
        streetview_file = DATA_DIR / "street_view/streetview_parcel_diridon_san_jose.json"

    heatmap, satellite, env, street_view = {}, {}, {}, {}

    if heatmap_file.exists():
        with open(heatmap_file, "r", encoding="utf-8") as f:
            heatmap = json.load(f)
            
    if satellite_file.exists():
        with open(satellite_file, "r", encoding="utf-8") as f:
            satellite = json.load(f)

    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            env = json.load(f)
            
    if streetview_file.exists():
        with open(streetview_file, "r", encoding="utf-8") as f:
            street_view = json.load(f)

    return {
        "parcel_id": parcel_id,
        "heatmap": heatmap,
        "satellite": satellite,
        "env": env,
        "street_view": street_view
    }

def load_parcel_geojson() -> Dict[str, Any]:
    """Load base geographic parcel boundary GeoJSON file."""
    geojson_path = DATA_DIR / "parcel_portfolio_san_jose_sample.geojson"
    if geojson_path.exists():
        with open(geojson_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"type": "FeatureCollection", "features": []}

def load_all_heatmap_tiles(sample_step: int = 1) -> Dict[str, Any]:
    """
    Loads all 2,224 FortyGuard 2m ambient thermal heatmap polygon grid tiles.
    Converts tile temperatures to Fahrenheit (°F) and calculates thermal anomaly deltas.
    """
    path = DATA_DIR / "heatmaps/heatmap_parcel_portfolio_san_jose_2026-08-03_tcm.json"
    if not path.exists():
        return {"type": "FeatureCollection", "features": []}

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_features = data.get("map_data", {}).get("features", [])
    processed_features = []

    # Baseline ambient temp in San Jose core (°F)
    baseline_f = 78.0

    for idx, feat in enumerate(raw_features[::sample_step]):
        props = dict(feat.get("properties", {}))
        avg_c = props.get("average_temperature", 25.0)
        max_c = props.get("max_temperature", 30.0)
        min_c = props.get("min_temperature", 20.0)

        avg_f = round(avg_c * 1.8 + 32.0, 2)
        max_f = round(max_c * 1.8 + 32.0, 2)
        min_f = round(min_c * 1.8 + 32.0, 2)
        delta_f = round(avg_f - baseline_f, 2)

        props["avg_temp_f"] = avg_f
        props["max_temp_f"] = max_f
        props["min_temp_f"] = min_f
        props["temp_delta_f"] = delta_f
        props["is_hotspot"] = delta_f >= 3.5

        processed_features.append({
            "type": "Feature",
            "id": feat.get("id", str(idx)),
            "properties": props,
            "geometry": feat.get("geometry")
        })

    return {
        "type": "FeatureCollection",
        "features": processed_features
    }

def load_us_sample_locations() -> Dict[str, Any]:
    """
    Returns US multi-city FortyGuard dataset points (San Jose, CA; Manhattan, NY; Chicago, IL).
    """
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "city": "San Jose",
                    "state": "CA",
                    "name": "San Jose FortyGuard Microclimate Region",
                    "dataset_points": 2224,
                    "avg_temp_f": 86.2,
                    "temp_delta_f": 5.2,
                    "is_hotspot": True,
                    "location_type": "Primary Urban Heat Island Benchmark"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-121.8906, 37.3361]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "city": "New York",
                    "state": "NY",
                    "name": "Lower Manhattan Thermal Corridor",
                    "dataset_points": 150,
                    "avg_temp_f": 88.5,
                    "temp_delta_f": 4.6,
                    "is_hotspot": True,
                    "location_type": "Dense Urban Canyon Sample"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-74.0060, 40.7128]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "city": "Chicago",
                    "state": "IL",
                    "name": "Chicago Loop District",
                    "dataset_points": 180,
                    "avg_temp_f": 84.1,
                    "temp_delta_f": 3.8,
                    "is_hotspot": True,
                    "location_type": "Lakefront Microclimate Sample"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-87.6298, 41.8781]
                }
            }
        ]
    }
