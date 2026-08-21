import asyncio
import sys
import os
import httpx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import app

async def run_api_tests():
    print("=== TESTING FASTAPI HTTP ENDPOINTS ===")
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Health & Data Sources
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        sources = resp.json()
        assert len(sources) >= 5
        print(f"✓ GET /api/health passed ({len(sources)} sources active)")

        # 2. Satellites catalog
        resp = await client.get("/api/satellites")
        assert resp.status_code == 200
        sats = resp.json()
        assert len(sats) >= 5
        print(f"✓ GET /api/satellites passed ({len(sats)} satellites)")

        # 3. Ground Track
        resp = await client.get("/api/track?satellite_id=39634")
        assert resp.status_code == 200
        track_data = resp.json()
        assert "track" in track_data and len(track_data["track"]) > 0
        print(f"✓ GET /api/track passed (Sentinel-1A orbital track computed)")

        # 4. Disasters List & GeoJSON
        resp = await client.get("/api/disasters")
        assert resp.status_code == 200
        disasters = resp.json()
        assert len(disasters) >= 5
        print(f"✓ GET /api/disasters passed ({len(disasters)} disasters)")

        resp = await client.get("/api/disasters/geojson")
        assert resp.status_code == 200
        geojson = resp.json()
        assert geojson["type"] == "FeatureCollection"
        print(f"✓ GET /api/disasters/geojson passed ({len(geojson['features'])} GeoJSON features)")

        # 5. Incident Lookup
        first_id = disasters[0]["event_id"]
        resp = await client.get(f"/api/disasters/{first_id}")
        assert resp.status_code == 200
        event_obj = resp.json()
        assert event_obj["event_id"] == first_id
        print(f"✓ GET /api/disasters/{{id}} passed ({first_id})")

        # 6. Tasking Optimization
        sched_payload = {
            "satellite_id": 39634,
            "targets": [
                {"id": "t1", "name": "Kerala Flood Zone", "lat": 9.98, "lon": 76.45, "weight": 9.0, "disaster_type": "Flood"}
            ],
            "max_passes_per_day": 4,
            "max_cloud_cover": 70.0,
            "power_per_pass": 150.0,
            "storage_per_pass": 12.0
        }
        resp = await client.post("/api/schedule", json=sched_payload)
        assert resp.status_code == 200
        sched_res = resp.json()
        assert "scheduled" in sched_res and "stats" in sched_res
        print(f"✓ POST /api/schedule passed ({len(sched_res['scheduled'])} scheduled passes)")

        # 7. AI Analyst
        resp = await client.post("/api/analyst/query", json={"query": "Explain flood severity in Kerala"})
        assert resp.status_code == 200
        analyst_res = resp.json()
        assert len(analyst_res["evidence_points"]) > 0
        print(f"✓ POST /api/analyst/query passed")

        # 8. Change Detection
        change_payload = {
            "event_id": "FLD-2026-KER-01",
            "target_lat": 9.98,
            "target_lon": 76.45,
            "baseline_date": "2026-08-10",
            "current_date": "2026-08-21",
            "feature_type": "water_extent"
        }
        resp = await client.post("/api/change-detection", json=change_payload)
        assert resp.status_code == 200
        change_res = resp.json()
        assert change_res["expansion_status"] in ["EXPANDING", "RECEDING", "STABLE"]
        print(f"✓ POST /api/change-detection passed")

        # 9. Alerts
        resp = await client.get("/api/alerts")
        assert resp.status_code == 200
        alerts = resp.json()
        assert len(alerts) > 0
        print(f"✓ GET /api/alerts passed ({len(alerts)} alerts active)")

        # 10. Reports
        resp = await client.post(f"/api/reports/generate/{first_id}")
        assert resp.status_code == 200
        rep = resp.json()
        assert "report_id" in rep and "executive_summary" in rep
        print(f"✓ POST /api/reports/generate passed (Report ID: {rep['report_id']})")

    print("\n=== ALL 10 API ENDPOINTS TESTED & VERIFIED ===")

if __name__ == "__main__":
    asyncio.run(run_api_tests())
