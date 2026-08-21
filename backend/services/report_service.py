import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from disasters.manager import disaster_manager
from providers.weather.open_meteo import open_meteo_provider
from database import get_db

class DisasterReportService:
    """
    Generates structured, comprehensive Disaster Intelligence Reports
    suitable for aerospace operations, disaster response command centers,
    and humanitarian agencies.
    """
    async def generate_incident_report(self, disaster_id: str) -> Dict[str, Any]:
        disaster = await disaster_manager.get_disaster_by_id(disaster_id)
        if not disaster:
            raise ValueError(f"Disaster incident '{disaster_id}' not found.")

        # Ingest current weather context
        weather = await open_meteo_provider.get_weather_forecast(disaster.latitude, disaster.longitude)
        curr_weather = weather.get("current", {})

        report_id = f"REP-{disaster.event_id}-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        now_iso = datetime.utcnow().isoformat() + "Z"

        infra = disaster.exposed_infrastructure or {}
        infra_dict = infra.dict() if hasattr(infra, "dict") else infra

        # Build executive summary
        exec_summary = (
            f"Automated Disaster Intelligence Assessment for {disaster.name} ({disaster.event_type.value}). "
            f"Event is currently classified as {disaster.severity.value.upper()} with an aggregate Risk Score of {disaster.risk_score}/100. "
            f"Delineated geographic impact zone encompasses approximately {disaster.affected_area_km2:.1f} km² with an estimated "
            f"exposed population of {disaster.estimated_population:,} persons. Atmospheric cloud cover is {curr_weather.get('cloud_cover', 'N/A')}%. "
            f"Primary orbital observation recommendation: {disaster.recommended_sensor}."
        )

        content = {
            "report_id": report_id,
            "title": f"Disaster Intelligence & Earth Observation Briefing: {disaster.name}",
            "generated_at": now_iso,
            "classification": "OPERATIONAL // UNCLASSIFIED",
            "executive_summary": exec_summary,
            "disaster_details": {
                "event_id": disaster.event_id,
                "name": disaster.name,
                "type": disaster.event_type.value,
                "category": disaster.category.value,
                "severity": disaster.severity.value,
                "risk_score": disaster.risk_score,
                "coordinates": {"latitude": disaster.latitude, "longitude": disaster.longitude},
                "affected_area_km2": disaster.affected_area_km2,
                "estimated_population": disaster.estimated_population
            },
            "weather_context": {
                "temperature_c": curr_weather.get("temperature_2m"),
                "cloud_cover_pct": curr_weather.get("cloud_cover"),
                "precipitation_mm": curr_weather.get("precipitation"),
                "wind_speed_kmh": curr_weather.get("wind_speed_10m"),
                "surface_pressure_hpa": curr_weather.get("surface_pressure")
            },
            "infrastructure_exposure": infra_dict,
            "satellite_tasking_recommendations": {
                "recommended_sensor": disaster.recommended_sensor,
                "rationale": disaster.recommended_action,
                "preferred_constellation": ["SENTINEL-1A (SAR)", "SENTINEL-2A (Optical)"] if "SAR" in disaster.recommended_sensor else ["LANDSAT 8/9", "TERRA"]
            },
            "timeline": [t.dict() for t in disaster.timeline],
            "data_provenance": disaster.provenance.dict(),
            "limitations_and_uncertainty": (
                "Data is compiled directly from authoritative real-time feeds (USGS, GloFAS, Open-Meteo, ESA, NASA). "
                "Atmospheric obscuration may impact optical sensor effectiveness. InSAR displacement is subject to phase unwrapping coherence thresholds."
            )
        }

        # Store in database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO intelligence_reports (id, title, disaster_id, report_type, summary, content_json, created_at, author)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report_id, content["title"], disaster.event_id, "INCIDENT_BRIEFING",
            exec_summary, json.dumps(content), now_iso, "SkyWindow Autonomous Intelligence Engine"
        ))
        conn.commit()
        conn.close()

        return content

    def get_saved_reports(self) -> list:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM intelligence_reports ORDER BY created_at DESC LIMIT 50')
        rows = cursor.fetchall()
        conn.close()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("content_json"):
                d["content"] = json.loads(d["content_json"])
            results.append(d)
        return results

report_service = DisasterReportService()
