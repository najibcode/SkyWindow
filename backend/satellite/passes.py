from skyfield.api import Topos, load, EarthSatellite
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import math

ts = load.timescale()

def compute_passes(line1: str, line2: str, lat: float, lon: float, hours_ahead: int = 48, min_elevation_deg: float = 20.0) -> List[Dict[str, Any]]:
    """
    Computes upcoming passes for a satellite TLE over a ground station / disaster target coordinate.
    """
    sat = EarthSatellite(line1, line2, 'Satellite', ts)
    location = Topos(latitude_degrees=lat, longitude_degrees=lon)
    
    now = datetime.now(timezone.utc)
    t0 = ts.utc(now.year, now.month, now.day, now.hour, now.minute, now.second)
    
    end_time = now + timedelta(hours=hours_ahead)
    t1 = ts.utc(end_time.year, end_time.month, end_time.day, end_time.hour, end_time.minute, end_time.second)
    
    t, events = sat.find_events(location, t0, t1, altitude_degrees=min_elevation_deg)
    
    passes = []
    current_pass = {}
    
    for ti, event in zip(t, events):
        event_time = ti.utc_datetime()
        if event == 0: # rise
            current_pass['rise'] = event_time
        elif event == 1: # culminate
            current_pass['culminate'] = event_time
            # compute max elevation & topocentric distance
            difference = sat - location
            topocentric = difference.at(ti)
            alt, az, distance = topocentric.altaz()
            current_pass['max_elevation'] = alt.degrees
            current_pass['azimuth'] = az.degrees
            current_pass['range_km'] = distance.km
            current_pass['off_nadir_deg'] = max(0.0, 90.0 - alt.degrees)
        elif event == 2: # set
            current_pass['set'] = event_time
            if 'rise' in current_pass and 'culminate' in current_pass:
                dur_secs = (current_pass['set'] - current_pass['rise']).total_seconds()
                passes.append({
                    'rise_time': current_pass['rise'].isoformat(),
                    'culminate_time': current_pass['culminate'].isoformat(),
                    'set_time': current_pass['set'].isoformat(),
                    'max_elevation_deg': round(current_pass['max_elevation'], 2),
                    'off_nadir_deg': round(current_pass.get('off_nadir_deg', 0.0), 2),
                    'azimuth_deg': round(current_pass.get('azimuth', 0.0), 1),
                    'range_km': round(current_pass.get('range_km', 700.0), 1),
                    'duration_seconds': int(dur_secs)
                })
            current_pass = {}
            
    return passes
