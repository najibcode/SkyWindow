from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os
import time
from datetime import datetime

from tle_manager import fetch_tle, get_satellite_list
from orbit_calc import compute_passes, compute_ground_track
from weather_api import get_cloud_cover_forecast, get_cloud_cover_at_time
from scheduler_opt import compute_schedule
from database import log_prediction, update_actual_forecast, get_calibration_log

app = FastAPI()

class TargetInput(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    weight: float

class ScheduleRequest(BaseModel):
    satellite_id: int
    targets: List[TargetInput]
    max_passes_per_day: int = 5
    max_cloud_cover: float = 70.0
    power_per_pass: float = 150.0
    storage_per_pass: float = 12.0

@app.get("/api/satellites")
def get_satellites():
    return get_satellite_list()

@app.post("/api/schedule")
async def create_schedule(req: ScheduleRequest):
    try:
        name, line1, line2, age_hours = await fetch_tle(req.satellite_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch TLE: {str(e)}")
        
    passes_data = {}
    for target in req.targets:
        # compute raw passes
        passes = compute_passes(line1, line2, target.lat, target.lon)
        
        if passes:
            # fetch weather
            try:
                forecast = await get_cloud_cover_forecast(target.lat, target.lon)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to fetch weather for {target.name}: {str(e)}")
                
            # enrich passes with weather
            for p in passes:
                cc = get_cloud_cover_at_time(forecast, p['culminate_time'])
                p['cloud_cover'] = cc
                
        passes_data[target.id] = passes
        
    schedule_result = compute_schedule(
        [t.dict() for t in req.targets], 
        passes_data, 
        req.max_passes_per_day,
        req.max_cloud_cover,
        req.power_per_pass,
        req.storage_per_pass
    )
    
    # log predictions for scheduled passes
    now_str = datetime.now().isoformat()
    for p in schedule_result['scheduled']:
        log_prediction(p['target_name'], 
                       next((t.lat for t in req.targets if t.id == p['target_id']), 0),
                       next((t.lon for t in req.targets if t.id == p['target_id']), 0),
                       p['culminate_time'], 
                       p['cloud_cover'], 
                       now_str)
                       
    schedule_result['tle_info'] = {
        'name': name,
        'age_hours': age_hours
    }
    
    return schedule_result

@app.get("/api/track")
async def get_track(satellite_id: int):
    try:
        name, line1, line2, _ = await fetch_tle(satellite_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch TLE: {str(e)}")
    
    track = compute_ground_track(line1, line2)
    return {"name": name, "track": track}

@app.post("/api/update_forecast_log")
async def update_log():
    logs = get_calibration_log()
    now = datetime.now()
    updates = 0
    for row in logs:
        if row['actual_cloud_cover'] is None:
            pt = datetime.fromisoformat(row['pass_time'])
            # if pass time has elapsed
            if pt.timestamp() < now.timestamp():
                try:
                    # fetch current "forecast" which acts as observation for past hour
                    forecast = await get_cloud_cover_forecast(row['lat'], row['lon'])
                    cc = get_cloud_cover_at_time(forecast, row['pass_time'])
                    if cc is not None:
                        update_actual_forecast(row['pass_time'], row['lat'], row['lon'], cc, now.isoformat())
                        updates += 1
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Calibration log update failed for target {row['target_name']}: {str(e)}")
    return {"status": "ok", "updates_made": updates}
    
@app.get("/api/calibration")
def get_calibration():
    return get_calibration_log()

# Serve frontend
frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
