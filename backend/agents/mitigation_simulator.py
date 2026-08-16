from typing import Dict, Any, List
from tools.thermal_math import simulate_mitigation

class MitigationSimulatorAgent:
    """
    Agent 3: Cool Roof & Greenery ROI Simulator
    Simulates thermal cooling impact and financial payback for cool roofs and tree canopy expansion.
    """

    def run(self, audit_data: Dict[str, Any], target_albedo: float = 0.70, default_canopy_m2: float = 250.0) -> Dict[str, Any]:
        audited_parcels = audit_data.get("audited_parcels", [])
        
        simulations = []
        total_projected_savings_usd = 0.0
        total_co2_reduction_tons = 0.0

        for parcel in audited_parcels:
            roof_area = parcel.get("roof_area_m2", 2000.0)
            sim_res = simulate_mitigation(
                roof_area_m2=roof_area,
                target_albedo=target_albedo,
                add_canopy_m2=default_canopy_m2
            )
            
            total_projected_savings_usd += sim_res["annual_hvac_savings_usd"]
            total_co2_reduction_tons += sim_res["co2_reduction_tons"]
            
            simulations.append({
                "parcel_id": parcel.get("parcel_id"),
                "name": parcel.get("name"),
                "baseline_albedo": parcel.get("albedo"),
                "target_albedo": target_albedo,
                "canopy_added_m2": default_canopy_m2,
                "simulation_result": sim_res
            })

        return {
            "status": "completed",
            "agent_name": "MitigationSimulatorAgent",
            "simulated_count": len(simulations),
            "target_albedo_applied": target_albedo,
            "canopy_expansion_m2_applied": default_canopy_m2,
            "total_citywide_annual_savings_usd": round(total_projected_savings_usd, 2),
            "total_co2_reduction_tons_yr": round(total_co2_reduction_tons, 2),
            "simulations": simulations
        }
