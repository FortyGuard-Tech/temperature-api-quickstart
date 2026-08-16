import time
from typing import Dict, Any
from agents.anomaly_detector import AnomalyDetectorAgent
from agents.building_auditor import BuildingAuditorAgent
from agents.mitigation_simulator import MitigationSimulatorAgent
from agents.report_generator import ReportGeneratorAgent

class PipelineOrchestrator:
    """
    Sequential Orchestrator coordinating Multi-Agent execution:
    Agent 1 (Anomaly Detector) -> Agent 2 (Building Auditor) -> Agent 3 (Mitigation Simulator) -> Agent 4 (Report Generator)
    """
    def __init__(self):
        self.anomaly_detector = AnomalyDetectorAgent()
        self.building_auditor = BuildingAuditorAgent()
        self.mitigation_simulator = MitigationSimulatorAgent()
        self.report_generator = ReportGeneratorAgent()

    def run_pipeline(self, target_albedo: float = 0.70, canopy_area: float = 250.0) -> Dict[str, Any]:
        start_time = time.time()
        steps_log = []

        # Step 1: Anomaly Detector Agent
        t0 = time.time()
        anomaly_res = self.anomaly_detector.run()
        steps_log.append({
            "agent_name": "AnomalyDetectorAgent",
            "status": "success",
            "execution_time_ms": round((time.time() - t0) * 1000, 2),
            "summary": f"Detected {anomaly_res['anomalies_detected_count']} heat anomalies out of {anomaly_res['total_parcels_scanned']} parcels scanned.",
            "data": anomaly_res
        })

        # Step 2: Building Auditor Agent
        t1 = time.time()
        audit_res = self.building_auditor.run(anomaly_res)
        steps_log.append({
            "agent_name": "BuildingAuditorAgent",
            "status": "success",
            "execution_time_ms": round((time.time() - t1) * 1000, 2),
            "summary": f"Audited {audit_res['audited_count']} structures and computed urban heat priority scores.",
            "data": audit_res
        })

        # Step 3: Mitigation Simulator Agent
        t2 = time.time()
        sim_res = self.mitigation_simulator.run(audit_res, target_albedo=target_albedo, default_canopy_m2=canopy_area)
        steps_log.append({
            "agent_name": "MitigationSimulatorAgent",
            "status": "success",
            "execution_time_ms": round((time.time() - t2) * 1000, 2),
            "summary": f"Modeled ROI for cool roofs (Albedo={target_albedo}) and {canopy_area}m² canopy expansion. Total savings: ${sim_res['total_citywide_annual_savings_usd']:,.2f}/yr.",
            "data": sim_res
        })

        # Step 4: Report Generator Agent
        t3 = time.time()
        pipeline_context = {
            "anomaly_detection": anomaly_res,
            "building_audit": audit_res,
            "mitigation_simulation": sim_res
        }
        report_res = self.report_generator.run(pipeline_context)
        steps_log.append({
            "agent_name": "ReportGeneratorAgent",
            "status": "success",
            "execution_time_ms": round((time.time() - t3) * 1000, 2),
            "summary": f"Generated enriched GeoJSON feature collection with {report_res['enriched_features_count']} structures.",
            "data": report_res
        })

        total_time_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "status": "success",
            "total_execution_time_ms": total_time_ms,
            "steps": steps_log,
            "final_geojson": report_res.get("geojson"),
            "executive_summary": report_res.get("executive_summary")
        }
