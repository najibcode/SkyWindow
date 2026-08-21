from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from satellite.catalog import get_all_satellites_info, get_satellite_by_id
from satellite.orbit import compute_ground_track
from satellite.passes import compute_passes
from providers.satellites.celestrak import celestrak_provider
from models.schemas import SatelliteInfo

router = APIRouter(prefix="/api", tags=["Satellites"])

@router.get("/satellites", response_model=List[Dict[str, Any]])
def list_satellites():
    """Returns the full Earth Observation satellite catalog."""
    return get_all_satellites_info()

@router.get("/satellites/{satellite_id}")
def get_satellite(satellite_id: int):
    sat = get_satellite_by_id(satellite_id)
    if not sat:
        raise HTTPException(status_code=404, detail="Satellite not found in catalog")
    return sat.dict()

@router.get("/track")
async def get_track(satellite_id: int = Query(..., description="NORAD Catalog ID")):
    """Computes real-time SGP4 orbital ground track from CelesTrak TLE."""
    try:
        name, line1, line2, age_hours = await celestrak_provider.fetch_tle(satellite_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch TLE: {str(e)}")
    
    track = compute_ground_track(line1, line2)
    return {
        "name": name,
        "satellite_id": satellite_id,
        "tle_age_hours": age_hours,
        "track": track
    }

@router.get("/satellites/{satellite_id}/passes")
async def get_satellite_passes(
    satellite_id: int,
    lat: float = Query(..., ge=-90.0, le=90.0),
    lon: float = Query(..., ge=-180.0, le=180.0),
    hours_ahead: int = Query(48, ge=1, le=168),
    min_elevation: float = Query(20.0, ge=5.0, le=85.0)
):
    """Calculates upcoming orbital observation passes over ground coordinates."""
    try:
        name, line1, line2, _ = await celestrak_provider.fetch_tle(satellite_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch TLE: {str(e)}")
        
    passes = compute_passes(line1, line2, lat, lon, hours_ahead=hours_ahead, min_elevation_deg=min_elevation)
    return {
        "satellite_id": satellite_id,
        "satellite_name": name,
        "target_coordinates": {"latitude": lat, "longitude": lon},
        "passes_count": len(passes),
        "passes": passes
    }
