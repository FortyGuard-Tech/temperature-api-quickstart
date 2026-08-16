from typing import Dict, Any

def compute_priority_score(roof_area_m2: float, albedo: float, canopy_pct: float) -> float:
    """
    Priority Score = [Roof Area (m²) × (1 - Albedo)] / [Canopy Percentage (50m) + 0.1]
    Higher score indicates higher vulnerability and priority for cool roof / greening intervention.
    """
    safe_canopy = max(0.0, float(canopy_pct))
    safe_albedo = min(1.0, max(0.0, float(albedo)))
    score = (roof_area_m2 * (1.0 - safe_albedo)) / (safe_canopy + 0.1)
    return round(score, 2)

def simulate_mitigation(roof_area_m2: float, target_albedo: float, add_canopy_m2: float) -> Dict[str, Any]:
    """
    Modeled cool roof & vegetative canopy thermal mitigation calculations.
    - Modeled at ~2.5°F drop per 1,000m² retrofitted cool roof (SRI >= 80)
    - Modeled at 1.0°F to 3.2°F drop for vegetative canopy expansion (avg 1.8°F / 1000m²)
    """
    safe_roof = max(10.0, float(roof_area_m2))
    safe_target_albedo = max(0.2, min(0.95, float(target_albedo)))
    safe_canopy = max(0.0, float(add_canopy_m2))

    cool_roof_drop = (safe_roof / 1000.0) * 2.5 * (safe_target_albedo - 0.2)
    greenery_drop = (safe_canopy / 1000.0) * 1.8
    
    total_delta_t = cool_roof_drop + greenery_drop
    annual_savings_usd = safe_roof * 4.50  # $4.50/m² peak chiller offset
    retrofit_cost = safe_roof * 25.0       # Estimated retrofitting cost ($25/m²)
    
    payback_years = (retrofit_cost / annual_savings_usd) if annual_savings_usd > 0 else 0.0
    co2_reduction_tons = safe_roof * 0.015  # ~15kg CO2 offset per m² per year

    return {
        "projected_temp_drop_f": round(total_delta_t, 2),
        "annual_hvac_savings_usd": round(annual_savings_usd, 2),
        "payback_years": round(payback_years, 1),
        "cool_roof_drop_f": round(cool_roof_drop, 2),
        "greenery_drop_f": round(greenery_drop, 2),
        "co2_reduction_tons": round(co2_reduction_tons, 2),
        "estimated_retrofit_cost_usd": round(retrofit_cost, 2)
    }
