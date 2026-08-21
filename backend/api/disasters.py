from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from disasters.manager import disaster_manager
from models.schemas import DisasterEvent, DisasterCategory, DisasterSeverity

router = APIRouter(prefix="/api/disasters", tags=["Disasters"])

@router.get("", response_model=List[DisasterEvent])
async def list_disasters(
    category: Optional[str] = Query(None, description="Filter by Disaster Category"),
    severity: Optional[str] = Query(None, description="Filter by Severity"),
    refresh: bool = Query(False, description="Force refresh from external feeds")
):
    """Returns all active real-time multi-disaster intelligence events."""
    events = await disaster_manager.get_all_disasters(force_refresh=refresh)
    
    if category:
        events = [e for e in events if e.category.value.lower() == category.lower()]
    if severity:
        events = [e for e in events if e.severity.value.lower() == severity.lower()]
        
    return events

@router.get("/summary")
async def get_summary():
    """Returns high-level global disaster operational dashboard metrics."""
    return await disaster_manager.get_summary_stats()

@router.get("/geojson")
async def get_disasters_geojson():
    """Returns all disaster geometries formatted as a GeoJSON FeatureCollection."""
    events = await disaster_manager.get_all_disasters()
    features = []
    
    for ev in events:
        props = {
            "event_id": ev.event_id,
            "name": ev.name,
            "event_type": ev.event_type.value,
            "category": ev.category.value,
            "severity": ev.severity.value,
            "risk_score": ev.risk_score,
            "affected_area_km2": ev.affected_area_km2,
            "estimated_population": ev.estimated_population,
            "recommended_sensor": ev.recommended_sensor,
            "source_provider": ev.provenance.provider,
            "last_updated": ev.last_updated
        }
        
        # Use polygon geometry if available, else Point geometry
        geom = ev.geometry or {
            "type": "Point",
            "coordinates": [ev.longitude, ev.latitude]
        }
        
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": geom
        })
        
    return {
        "type": "FeatureCollection",
        "features": features
    }

@router.get("/{event_id}", response_model=DisasterEvent)
async def get_disaster(event_id: str):
    """Retrieves full incident briefing and telemetry for a specific disaster ID."""
    event = await disaster_manager.get_disaster_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Disaster event '{event_id}' not found.")
    return event
