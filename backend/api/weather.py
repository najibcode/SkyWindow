from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from providers.weather.open_meteo import open_meteo_provider

router = APIRouter(prefix="/api/weather", tags=["Weather"])

@router.get("/forecast")
async def get_forecast(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lon: float = Query(..., ge=-180.0, le=180.0)
):
    """Retrieves high-resolution hourly and current meteorological parameters from Open-Meteo."""
    try:
        return await open_meteo_provider.get_weather_forecast(lat, lon)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch weather: {str(e)}")

@router.get("/cloud-cover")
async def get_cloud_cover(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lon: float = Query(..., ge=-180.0, le=180.0)
):
    """Returns hourly cloud cover percentage map for pass scheduling."""
    try:
        return await open_meteo_provider.get_cloud_cover_forecast(lat, lon)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cloud forecast: {str(e)}")

@router.get("/river-discharge")
async def get_river_discharge(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lon: float = Query(..., ge=-180.0, le=180.0)
):
    """Returns ECMWF GloFAS 7-day river discharge forecast (m³/s)."""
    try:
        return await open_meteo_provider.get_river_discharge_forecast(lat, lon)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch hydrology data: {str(e)}")
