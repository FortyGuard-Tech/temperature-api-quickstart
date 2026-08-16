from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ParcelProperties(BaseModel):
    parcel_id: str
    name: Optional[str] = None
    city: str = "San Jose"
    state: str = "CA"
    lot_acres: float = 1.0
    zoning: Optional[str] = None
    proposed_use: Optional[str] = None
    proposed_gsf: Optional[float] = None
    stories: Optional[int] = None
    temp_delta_f: float = 0.0
    ambient_temp_f: float = 85.0
    priority_score: float = 0.0
    is_hotspot: bool = False
    albedo: float = 0.25
    canopy_pct: float = 0.10
    roof_area_m2: float = 1000.0

class HotspotFeature(BaseModel):
    type: str = "Feature"
    properties: ParcelProperties
    geometry: Dict[str, Any]

class HotspotsResponse(BaseModel):
    status: str = "success"
    total_parcels: int
    hotspot_count: int
    avg_ambient_temp_f: float
    max_temp_delta_f: float
    data: Dict[str, Any]
