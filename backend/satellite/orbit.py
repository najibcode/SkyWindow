from skyfield.api import Topos, load, EarthSatellite
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import math

ts = load.timescale()

def compute_ground_track(line1: str, line2: str, start_time: Optional[datetime] = None, duration_minutes: int = 100, step_minutes: int = 1) -> List[Dict[str, Any]]:
    """Calculates ground track points for orbital projection."""
    sat = EarthSatellite(line1, line2, 'Satellite', ts)
    
    if start_time is None:
        start_time = datetime.now(timezone.utc)
        
    track = []
    for m in range(0, duration_minutes, step_minutes):
        t_dt = start_time + timedelta(minutes=m)
        ti = ts.utc(t_dt.year, t_dt.month, t_dt.day, t_dt.hour, t_dt.minute, t_dt.second)
        geocentric = sat.at(ti)
        subpoint = geocentric.subpoint()
        track.append({
            'time': t_dt.isoformat(),
            'lat': round(subpoint.latitude.degrees, 4),
            'lon': round(subpoint.longitude.degrees, 4),
            'elevation_km': round(subpoint.elevation.km, 1)
        })
    return track

def compute_satellite_footprint(lat: float, lon: float, swath_km: float = 250.0) -> Dict[str, Any]:
    """Generates a GeoJSON polygon representing the sensor ground swath footprint."""
    half_swath = swath_km / 2.0
    r_rad = half_swath / 6371.0
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    # Approximate rectangular swath oriented along orbit
    corners = []
    bearings = [45, 135, 225, 315, 45]
    for b_deg in bearings:
        bearing = math.radians(b_deg)
        pt_lat = math.asin(math.sin(lat_rad) * math.cos(r_rad) + math.cos(lat_rad) * math.sin(r_rad) * math.cos(bearing))
        pt_lon = lon_rad + math.atan2(math.sin(bearing) * math.sin(r_rad) * math.cos(lat_rad), math.cos(r_rad) - math.sin(lat_rad) * math.sin(pt_lat))
        corners.append([round(math.degrees(pt_lon), 4), round(math.degrees(pt_lat), 4)])

    return {
        "type": "Polygon",
        "coordinates": [corners]
    }
