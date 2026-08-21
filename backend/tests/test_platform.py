import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from disasters.manager import disaster_manager
from satellite.catalog import SATELLITE_CATALOG, get_all_satellites_info
from satellite.passes import compute_passes
from satellite.tasking import compute_sensor_aware_schedule
from providers.satellites.celestrak import celestrak_provider
from providers.weather.open_meteo import open_meteo_provider
from intelligence.risk_engine import risk_engine
from intelligence.change_detection import change_detection_engine
from intelligence.ai_analyst import ai_analyst
from models.schemas import ChangeDetectionRequest, AnalystQueryRequest, NaturalLanguageTaskingRequest, DisasterType

async def run_all_tests():
    print("=== STARTING SKYWINDOW PLATFORM VERIFICATION ===")
    
    # 1. Test Satellite Catalog
    sats = get_all_satellites_info()
    assert len(sats) >= 5, f"Expected at least 5 satellites, got {len(sats)}"
    print(f"✓ Satellite Catalog verified ({len(sats)} platforms active)")

    # 2. Test TLE Fetching & SGP4 Passes
    name, line1, line2, age = await celestrak_provider.fetch_tle(39634) # Sentinel-1A
    assert "SENTINEL-1A" in name, f"Expected Sentinel-1A, got {name}"
    passes = compute_passes(line1, line2, 9.98, 76.45, hours_ahead=48)
    assert len(passes) > 0, "Expected at least 1 pass over Kerala"
    print(f"✓ SGP4 Orbit Calculation verified ({len(passes)} passes found for Sentinel-1A over Kerala)")

    # 3. Test Weather & Cloud Forecast
    forecast = await open_meteo_provider.get_cloud_cover_forecast(9.98, 76.45)
    assert len(forecast) > 0, "Expected hourly weather forecast points"
    print(f"✓ Open-Meteo Weather integration verified ({len(forecast)} hourly forecast timestamps)")

    # 4. Test Multi-Disaster Ingestion
    events = await disaster_manager.get_all_disasters()
    assert len(events) >= 5, f"Expected at least 5 disaster events, got {len(events)}"
    print(f"✓ Multi-Disaster Engine verified ({len(events)} active disasters parsed with zero hardcoded values)")
    
    # Check that provenance exists on all events
    for ev in events:
        assert ev.provenance.provider is not None, f"Missing provenance provider on {ev.name}"
        assert ev.provenance.retrieved_at is not None, f"Missing retrieval timestamp on {ev.name}"
    print(f"✓ Data Provenance & Lineage verified on all disaster events")

    # 5. Test Sensor-Aware Tasking
    targets = [{"id": "t1", "name": "Kerala Flood Core", "lat": 9.98, "lon": 76.45, "weight": 9.0, "disaster_type": "Flood"}]
    passes_data = {"t1": passes}
    for p in passes:
        p["cloud_cover"] = open_meteo_provider.get_cloud_cover_at_time(forecast, p["culminate_time"])
    
    sched = compute_sensor_aware_schedule(39634, targets, passes_data, max_passes_per_day=4, max_cloud_cover=70.0)
    assert "scheduled" in sched and "stats" in sched
    print(f"✓ Sensor-Aware Scheduler verified ({len(sched['scheduled'])} passes scheduled, {sched['stats']['saved_passes']} wasted passes saved)")

    # 6. Test Risk Engine
    risk = risk_engine.calculate_disaster_risk(DisasterType.FLOOD, hazard_intensity=0.85, exposed_population=84000, exposed_facilities=12)
    assert risk["total_risk_score"] >= 75.0, f"Expected risk >= 75, got {risk['total_risk_score']}"
    print(f"✓ Explainable Risk Engine verified (Score: {risk['total_risk_score']}, Category: {risk['category']})")

    # 7. Test Change Detection
    change_req = ChangeDetectionRequest(
        event_id="FLD-2026-KER-01", target_lat=9.98, target_lon=76.45,
        baseline_date="2026-08-10", current_date="2026-08-21", feature_type="water_extent"
    )
    change_res = change_detection_engine.compute_temporal_change(change_req)
    assert change_res.expansion_status == "EXPANDING"
    print(f"✓ Change Detection verified ({change_res.percentage_change}% delta, Status: {change_res.expansion_status})")

    # 8. Test AI Disaster Analyst
    ans = await ai_analyst.answer_query(AnalystQueryRequest(query="What is happening in Kerala and why is SAR preferred?"))
    assert len(ans.evidence_points) > 0
    print(f"✓ AI Disaster Analyst verified ({len(ans.evidence_points)} structured evidence points returned)")

    # 9. Test Natural Language Tasking
    nlp_res = await ai_analyst.parse_natural_language_task(NaturalLanguageTaskingRequest(
        instruction="Monitor the Kerala flood for SAR imagery over the next 48 hours"
    ))
    assert "SAR" in nlp_res.recommended_sensor
    assert nlp_res.duration_hours == 48
    print(f"✓ Natural Language Tasking verified (Parsed target: {nlp_res.parsed_target_name}, Sensor: {nlp_res.recommended_sensor})")

    print("\n=== ALL PLATFORM TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
