from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from tools.fortyguard_loader import load_san_jose_thermal_profile, load_parcel_geojson
from tools.thermal_math import simulate_mitigation
from schemas.simulation import SimulationRequest
from pipeline.orchestrator import PipelineOrchestrator
from agents.report_generator import ReportGeneratorAgent

app = FastAPI(title="ThermoAgent-AI Multi-Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = PipelineOrchestrator()
report_agent = ReportGeneratorAgent()

@app.get("/health")
async def health_check():
    return {"status": "online", "service": "ThermoAgent-AI Engine"}

@app.get("/api/v1/hotspots")
async def get_hotspots():
    """
    Exposes FortyGuard San Jose thermal profile and feeds to Agent 1 & Agent 2.
    """
    pipeline_res = orchestrator.run_pipeline()
    return {
        "status": "success",
        "data": pipeline_res.get("final_geojson"),
        "summary": pipeline_res.get("executive_summary"),
        "steps": pipeline_res.get("steps")
    }

@app.post("/api/v1/simulate")
async def run_simulation(req: SimulationRequest):
    """
    Parametric simulation endpoint calculating projected cooling, annual HVAC savings, and payback period.
    """
    result = simulate_mitigation(
        roof_area_m2=req.roof_area,
        target_albedo=req.target_albedo,
        add_canopy_m2=req.canopy_area
    )
    return {
        "status": "success",
        "parcel_id": req.parcel_id,
        "simulation": result
    }

@app.post("/api/v1/pipeline/run")
async def execute_pipeline(target_albedo: float = 0.70, canopy_area: float = 250.0):
    """
    Triggers full sequential execution of Agent 1 -> Agent 2 -> Agent 3 -> Agent 4.
    """
    pipeline_res = orchestrator.run_pipeline(target_albedo=target_albedo, canopy_area=canopy_area)
    return pipeline_res

@app.get("/api/v1/report/pdf/{parcel_id}")
async def download_pdf_report(parcel_id: str, target_albedo: float = 0.70, canopy_area: float = 250.0):
    """
    Generates and returns an executive PDF thermal audit report for the given parcel ID.
    """
    geojson = load_parcel_geojson()
    parcel_info = {}
    for feat in geojson.get("features", []):
        if feat.get("properties", {}).get("parcel_id") == parcel_id:
            parcel_info = feat.get("properties", {})
            break

    if not parcel_info:
        parcel_info = {
            "parcel_id": parcel_id,
            "name": "San Jose Parcel Property",
            "proposed_use": "Urban Commercial / Mixed-Use",
            "roof_area_m2": 2150.0,
            "albedo": 0.20,
            "temp_delta_f": 4.2
        }

    sim_res = simulate_mitigation(
        roof_area_m2=parcel_info.get("roof_area_m2", 2150.0),
        target_albedo=target_albedo,
        add_canopy_m2=canopy_area
    )

    pdf_bytes = report_agent.generate_pdf_report(
        parcel_id=parcel_id,
        parcel_info=parcel_info,
        sim_result=sim_res
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=thermoagent_audit_{parcel_id}.pdf"}
    )
