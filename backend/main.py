from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime

from config import settings
from database import init_db, get_calibration_log, update_actual_forecast
from providers.weather.open_meteo import open_meteo_provider

# Import API routers
from api.satellites import router as satellites_router
from api.disasters import router as disasters_router
from api.weather import router as weather_router
from api.tasking import router as tasking_router
from api.change_detection import router as change_router
from api.analyst import router as analyst_router
from api.alerts import router as alerts_router
from api.reports import router as reports_router
from api.health import router as health_router

# Initialize database
init_db()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-Powered Earth Observation & Multi-Disaster Intelligence Platform"
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all modular routers
app.include_router(satellites_router)
app.include_router(disasters_router)
app.include_router(weather_router)
app.include_router(tasking_router)
app.include_router(change_router)
app.include_router(analyst_router)
app.include_router(alerts_router)
app.include_router(reports_router)
app.include_router(health_router)

# Legacy calibration endpoints for backwards compatibility
@app.get("/api/calibration")
def get_calibration():
    return get_calibration_log()

@app.post("/api/update_forecast_log")
async def update_log():
    logs = get_calibration_log()
    now = datetime.utcnow()
    updates = 0
    for row in logs:
        if row['actual_cloud_cover'] is None:
            try:
                pt = datetime.fromisoformat(row['pass_time'].replace("Z", "+00:00"))
                if pt.timestamp() < now.timestamp():
                    forecast = await open_meteo_provider.get_cloud_cover_forecast(row['lat'], row['lon'])
                    cc = open_meteo_provider.get_cloud_cover_at_time(forecast, row['pass_time'])
                    if cc is not None:
                        update_actual_forecast(row['pass_time'], row['lat'], row['lon'], cc, now.isoformat())
                        updates += 1
            except Exception:
                continue
    return {"status": "ok", "updates_made": updates}

# Serve frontend static assets
frontend_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend')
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
