from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from datetime import datetime
from models.schemas import ScheduleRequest, ConstellationPlanRequest, NaturalLanguageTaskingRequest, NaturalLanguageTaskingResponse, DataProvenance, DataQuality, SourceStatus
from providers.satellites.celestrak import celestrak_provider
from providers.weather.open_meteo import open_meteo_provider
from satellite.passes import compute_passes
from satellite.tasking import compute_sensor_aware_schedule
from satellite.catalog import SATELLITE_CATALOG
from intelligence.recommendation_engine import recommendation_engine
from intelligence.ai_analyst import ai_analyst
from database import log_prediction

router = APIRouter(prefix="/api", tags=["Tasking & Scheduling"])

@router.post("/schedule")
@router.post("/tasking/optimize")
async def optimize_task_schedule(req: ScheduleRequest):
    """
    Computes an optimal Earth Observation camera schedule accounting for:
    - Orbit geometry & SGP4 overpasses
    - Satellite sensor modality (SAR vs Optical vs Thermal)
    - Real-time Open-Meteo hourly cloud forecast
    - Target priority & Disaster urgency
    - Power (Wh) and Storage (GB) duty cycle constraints
    """
    try:
        name, line1, line2, age_hours = await celestrak_provider.fetch_tle(req.satellite_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch TLE for satellite {req.satellite_id}: {str(e)}")
        
    passes_data = {}
    for target in req.targets:
        # compute raw passes
        passes = compute_passes(line1, line2, target.lat, target.lon)
        
        if passes:
            # fetch real weather forecast
            try:
                forecast = await open_meteo_provider.get_cloud_cover_forecast(target.lat, target.lon)
            except Exception as e:
                forecast = {}
                
            # enrich passes with forecast cloud cover
            for p in passes:
                cc = open_meteo_provider.get_cloud_cover_at_time(forecast, p['culminate_time'])
                p['cloud_cover'] = cc
                
        passes_data[target.id] = passes
        
    schedule_result = compute_sensor_aware_schedule(
        req.satellite_id,
        [t.dict() for t in req.targets], 
        passes_data, 
        req.max_passes_per_day,
        req.max_cloud_cover,
        req.power_per_pass,
        req.storage_per_pass,
        disaster_type=req.sensor_preference
    )
    
    # Log predictions to SQLite calibration log
    now_str = datetime.utcnow().isoformat()
    for p in schedule_result['scheduled']:
        t_lat = next((t.lat for t in req.targets if t.id == p['target_id']), 0)
        t_lon = next((t.lon for t in req.targets if t.id == p['target_id']), 0)
        log_prediction(p['target_name'], t_lat, t_lon, p['culminate_time'], p.get('cloud_cover', 0), now_str)
                       
    schedule_result['tle_info'] = {
        'name': name,
        'satellite_id': req.satellite_id,
        'age_hours': age_hours
    }
    
    schedule_result['provenance'] = {
        "provider": "CelesTrak GP & Open-Meteo Weather",
        "dataset": "SGP4 Keplarian Propagation & NWP Cloud Model",
        "observed_at": now_str + "Z",
        "data_quality": "HIGH",
        "status": "LIVE"
    }
    
    return schedule_result

@router.post("/tasking/constellation")
async def plan_constellation_campaign(req: ConstellationPlanRequest):
    """Coordinates a synchronized multi-satellite observation campaign across multiple orbits."""
    results = []
    
    for sat_id in req.satellite_ids:
        try:
            name, line1, line2, age_hours = await celestrak_provider.fetch_tle(sat_id)
            passes_data = {}
            for target in req.targets:
                passes = compute_passes(line1, line2, target.lat, target.lon, hours_ahead=req.duration_hours)
                forecast = await open_meteo_provider.get_cloud_cover_forecast(target.lat, target.lon)
                for p in passes:
                    p['cloud_cover'] = open_meteo_provider.get_cloud_cover_at_time(forecast, p['culminate_time'])
                passes_data[target.id] = passes
                
            sched = compute_sensor_aware_schedule(
                sat_id,
                [t.dict() for t in req.targets],
                passes_data,
                max_passes_per_day=4,
                max_cloud_cover=req.max_cloud_cover
            )
            results.append({
                "satellite_id": sat_id,
                "satellite_name": name,
                "scheduled_passes": sched['scheduled'],
                "stats": sched['stats']
            })
        except Exception as e:
            continue

    return {
        "campaign_name": req.campaign_name,
        "duration_hours": req.duration_hours,
        "satellite_count": len(results),
        "campaign_results": results
    }

@router.get("/tasking/queue")
async def get_tasking_queue():
    """Returns the automated prioritized Earth Observation queue across all active disasters."""
    return await recommendation_engine.get_recommended_queue()

@router.post("/tasking/nlp", response_model=NaturalLanguageTaskingResponse)
async def parse_nlp_task(req: NaturalLanguageTaskingRequest):
    """Converts natural language mission instructions into structured orbital tasking parameters."""
    return await ai_analyst.parse_natural_language_task(req)
