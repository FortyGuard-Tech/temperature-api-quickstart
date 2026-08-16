from typing import Dict, Any, List
from tools.thermal_math import compute_priority_score

class BuildingAuditorAgent:
    """
    Agent 2: Building Causality & Priority Scorer
    Audits parcel geometry, rooftop area, baseline SRI/Albedo, and surround canopy cover.
    Calculates urban heat causality score and assigns intervention priority rankings.
    """

    def run(self, anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
        features = anomaly_data.get("processed_geojson", {}).get("features", [])
        
        audited_parcels = []
        
        # Default physical parameters per parcel
        parcel_defaults = {
            "APN-259-27-014": {"albedo": 0.18, "canopy_pct": 0.05, "roof_area_m2": 3500.0},
            "APN-264-11-032": {"albedo": 0.20, "canopy_pct": 0.08, "roof_area_m2": 2150.0},
            "APN-249-40-008": {"albedo": 0.35, "canopy_pct": 0.25, "roof_area_m2": 3700.0},
            "APN-467-22-105": {"albedo": 0.22, "canopy_pct": 0.10, "roof_area_m2": 2880.0},
            "APN-259-33-041": {"albedo": 0.20, "canopy_pct": 0.04, "roof_area_m2": 4600.0},
            "APN-472-09-017": {"albedo": 0.30, "canopy_pct": 0.18, "roof_area_m2": 3000.0}
        }

        updated_features = []
        for feature in features:
            props = dict(feature.get("properties", {}))
            pid = props.get("parcel_id", "UNKNOWN")
            
            defaults = parcel_defaults.get(pid, {"albedo": 0.22, "canopy_pct": 0.10, "roof_area_m2": 2500.0})
            
            albedo = defaults["albedo"]
            canopy_pct = defaults["canopy_pct"]
            roof_area_m2 = defaults["roof_area_m2"]
            
            priority_score = compute_priority_score(roof_area_m2, albedo, canopy_pct)
            
            props["albedo"] = albedo
            props["canopy_pct"] = canopy_pct
            props["roof_area_m2"] = roof_area_m2
            props["priority_score"] = priority_score
            
            # Primary thermal driver classification
            if albedo < 0.25 and canopy_pct < 0.10:
                causality = "Severe dark surface absorption & zero tree canopy cover"
            elif albedo < 0.25:
                causality = "Low SRI dark rooftop thermal retention"
            else:
                causality = "Unshaded asphalt paving and surrounding micro-climate"
                
            props["causality_diagnosis"] = causality
            
            updated_features.append({
                "type": "Feature",
                "properties": props,
                "geometry": feature.get("geometry")
            })
            
            audited_parcels.append({
                "parcel_id": pid,
                "name": props.get("name"),
                "priority_score": priority_score,
                "roof_area_m2": roof_area_m2,
                "albedo": albedo,
                "canopy_pct": canopy_pct,
                "causality_diagnosis": causality,
                "is_hotspot": props.get("is_hotspot", False)
            })

        # Rank parcels by priority score descending
        audited_parcels.sort(key=lambda x: x["priority_score"], reverse=True)

        return {
            "status": "completed",
            "agent_name": "BuildingAuditorAgent",
            "audited_count": len(audited_parcels),
            "highest_priority_parcel": audited_parcels[0] if audited_parcels else None,
            "audited_parcels": audited_parcels,
            "processed_geojson": {
                "type": "FeatureCollection",
                "features": updated_features
            }
        }
