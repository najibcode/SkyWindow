from skyfield.api import Topos, load, EarthSatellite
from datetime import datetime, timedelta, timezone

ts = load.timescale()

def compute_passes(line1: str, line2: str, lat: float, lon: float, hours_ahead: int = 48, min_elevation_deg: float = 20.0):
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
            # compute max elevation
            difference = sat - location
            topocentric = difference.at(ti)
            alt, az, distance = topocentric.altaz()
            current_pass['max_elevation'] = alt.degrees
        elif event == 2: # set
            current_pass['set'] = event_time
            if 'rise' in current_pass and 'culminate' in current_pass:
                passes.append({
                    'rise_time': current_pass['rise'].isoformat(),
                    'culminate_time': current_pass['culminate'].isoformat(),
                    'set_time': current_pass['set'].isoformat(),
                    'max_elevation_deg': round(current_pass['max_elevation'], 2)
                })
            current_pass = {}
            
    return passes

def compute_ground_track(line1: str, line2: str, start_time: datetime = None, duration_minutes: int = 100, step_minutes: int = 1):
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
            'lat': subpoint.latitude.degrees,
            'lon': subpoint.longitude.degrees,
            'elevation': subpoint.elevation.m
        })
    return track
