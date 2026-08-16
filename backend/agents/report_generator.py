import io
import json
from typing import Dict, Any, Optional
from pathlib import Path

class ReportGeneratorAgent:
    """
    Agent 4: GeoJSON & PDF Generator
    Synthesizes outputs from Agents 1-3 into enriched GeoJSON feature collections
    and printable executive PDF thermal mitigation audit reports.
    """

    def run(self, pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        audit = pipeline_data.get("building_audit", {})
        simulation = pipeline_data.get("mitigation_simulation", {})
        geojson = audit.get("processed_geojson", {"type": "FeatureCollection", "features": []})
        
        # Enrich GeoJSON features with simulation outcomes
        sim_map = {s["parcel_id"]: s for s in simulation.get("simulations", [])}
        
        enriched_features = []
        for feature in geojson.get("features", []):
            props = dict(feature.get("properties", {}))
            pid = props.get("parcel_id")
            if pid in sim_map:
                sim_res = sim_map[pid].get("simulation_result", {})
                props["projected_temp_drop_f"] = sim_res.get("projected_temp_drop_f")
                props["annual_hvac_savings_usd"] = sim_res.get("annual_hvac_savings_usd")
                props["payback_years"] = sim_res.get("payback_years")
            
            enriched_features.append({
                "type": "Feature",
                "properties": props,
                "geometry": feature.get("geometry")
            })
            
        enriched_geojson = {
            "type": "FeatureCollection",
            "features": enriched_features
        }

        return {
            "status": "completed",
            "agent_name": "ReportGeneratorAgent",
            "enriched_features_count": len(enriched_features),
            "geojson": enriched_geojson,
            "executive_summary": {
                "total_parcels": len(enriched_features),
                "citywide_annual_savings_usd": simulation.get("total_citywide_annual_savings_usd", 0.0),
                "total_co2_reduction_tons": simulation.get("total_co2_reduction_tons_yr", 0.0),
                "highest_risk_parcel": audit.get("highest_priority_parcel", {}).get("name")
            }
        }

    def generate_pdf_report(self, parcel_id: str, parcel_info: Dict[str, Any], sim_result: Dict[str, Any]) -> bytes:
        """Generates a downloadable PDF report for a given parcel using ReportLab."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        except ImportError:
            # Fallback text PDF generation if reportlab is not imported
            pdf_bytes = f"PDF Audit Report for Parcel {parcel_id}\n\n".encode("utf-8")
            pdf_bytes += f"Structure Name: {parcel_info.get('name', 'San Jose Parcel')}\n".encode("utf-8")
            pdf_bytes += f"Projected Cooling: -{sim_result.get('projected_temp_drop_f', 0.0)}°F\n".encode("utf-8")
            pdf_bytes += f"Annual Savings: ${sim_result.get('annual_hvac_savings_usd', 0.0)}/yr\n".encode("utf-8")
            return pdf_bytes

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=8
        )
        subtitle_style = ParagraphStyle(
            'SubTitleStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=14
        )
        heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#10b981'),
            spaceBefore=10,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontSize=9.5,
            textColor=colors.HexColor('#334155'),
            leading=13
        )

        story.append(Paragraph("<b>FortyGuard ThermoAgent-AI Audit Report</b>", title_style))
        story.append(Paragraph(f"Parcel Identifier: <b>{parcel_id}</b> | City: San Jose, CA | Date: 2026-08-03", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=15))

        story.append(Paragraph("<b>1. Structure Baseline Analysis</b>", heading_style))
        summary_text = (
            f"Building Name: <b>{parcel_info.get('name', 'N/A')}</b><br/>"
            f"Proposed Use: <b>{parcel_info.get('proposed_use', 'N/A')}</b><br/>"
            f"Rooftop Surface Area: <b>{parcel_info.get('roof_area_m2', 2000)} m²</b><br/>"
            f"Baseline SRI / Albedo: <b>{parcel_info.get('albedo', 0.20)}</b><br/>"
            f"Urban Heat Island ΔT: <b>+{parcel_info.get('temp_delta_f', 4.2)}°F</b> above baseline"
        )
        story.append(Paragraph(summary_text, body_style))
        story.append(Spacer(1, 10))

        story.append(Paragraph("<b>2. Parametric Cooling & Economic ROI Model</b>", heading_style))
        
        table_data = [
            ["Metric", "Model Outcome"],
            ["Projected Ambient Cooling", f"-{sim_result.get('projected_temp_drop_f', 0.0)} °F"],
            ["Cool Roof Contribution", f"-{sim_result.get('cool_roof_drop_f', 0.0)} °F"],
            ["Canopy Greening Drop", f"-{sim_result.get('greenery_drop_f', 0.0)} °F"],
            ["Annual HVAC Energy Offset", f"${sim_result.get('annual_hvac_savings_usd', 0.0):,.2f} / yr"],
            ["Estimated Retrofit Capital Cost", f"${sim_result.get('estimated_retrofit_cost_usd', 0.0):,.2f}"],
            ["Estimated Investment Payback", f"{sim_result.get('payback_years', 0.0)} Years"],
            ["Annual Carbon Offset", f"{sim_result.get('co2_reduction_tons', 0.0)} Metric Tons CO2e"]
        ]
        
        t = Table(table_data, colWidths=[240, 240])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#ffffff')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#ffffff'), colors.HexColor('#f8fafc')])
        ]))
        story.append(t)
        story.append(Spacer(1, 15))

        story.append(Paragraph("<b>3. Actionable Intervention Recommendations</b>", heading_style))
        recs = (
            "• Upgrade rooftop material to high-SRI white elastomer coating (Target SRI >= 80, Albedo >= 0.70).<br/>"
            "• Plant shade tree perimeter canopy to maximize micro-climate evapotranspiration.<br/>"
            "• Submit retrofit documentation for San Jose Commercial Energy Efficiency rebates."
        )
        story.append(Paragraph(recs, body_style))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
