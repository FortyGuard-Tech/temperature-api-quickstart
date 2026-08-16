from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class SimulationRequest(BaseModel):
    parcel_id: Optional[str] = "APN-264-11-032"
    roof_area: float = Field(..., gt=0, description="Roof surface area in m²")
    target_albedo: float = Field(0.7, ge=0.2, le=0.95, description="Target roof solar reflectance index (Albedo)")
    canopy_area: float = Field(250.0, ge=0.0, description="Additional vegetative canopy area in m²")

class SimulationResult(BaseModel):
    projected_temp_drop_f: float
    annual_hvac_savings_usd: float
    payback_years: float
    cool_roof_drop_f: float
    greenery_drop_f: float
    co2_reduction_tons: float
    estimated_retrofit_cost_usd: float

class SimulationResponse(BaseModel):
    status: str = "success"
    parcel_id: Optional[str] = None
    simulation: SimulationResult
