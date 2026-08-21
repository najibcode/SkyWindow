from typing import List, Dict, Any, Optional
from datetime import datetime
from satellite.catalog import get_satellite_by_id

def compute_sensor_aware_schedule(
    satellite_id: int,
    targets: List[Dict[str, Any]],
    passes_data: Dict[str, List[Dict[str, Any]]],
    max_passes_per_day: int = 5,
    max_cloud_cover: float = 70.0,
    power_per_pass: float = 150.0,
    storage_per_pass: float = 12.0,
    disaster_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes an optimal imaging mission schedule accounting for:
    - Target priority
    - Satellite sensor modality (SAR vs Optical vs Thermal vs Microwave)
    - True weather & cloud cover constraints
    - Overpass elevation & off-nadir geometry
    - Orbit conflict resolution & daily duty cycle capacity limits
    """
    sat_info = get_satellite_by_id(satellite_id)
    sat_type = sat_info.type if sat_info else "Optical"
    is_sar = "SAR" in sat_type
    is_thermal = "Thermal" in sat_type

    all_passes = []
    
    for t in targets:
        tid = t['id']
        tname = t['name']
        weight = float(t.get('weight', 5.0))
        target_disaster = t.get('disaster_type', disaster_type or "General Observation")

        # Sensor suitability coefficient calculation
        sensor_suitability = 1.0
        if is_sar:
            # SAR is premier for Flood, Cyclone, Landslide, Earthquake deformation
            if any(k in target_disaster.lower() for k in ["flood", "cyclone", "storm", "tsunami", "landslide", "quake"]):
                sensor_suitability = 1.45
            else:
                sensor_suitability = 1.1
        elif is_thermal:
            # Thermal is premier for Wildfire, Heatwave, Volcano
            if any(k in target_disaster.lower() for k in ["fire", "heat", "volcano", "thermal"]):
                sensor_suitability = 1.4
            else:
                sensor_suitability = 1.05
        else: # Optical
            if any(k in target_disaster.lower() for k in ["flood", "cyclone"]):
                sensor_suitability = 0.85 # Clouds likely obscure optical
            else:
                sensor_suitability = 1.25

        for p in passes_data.get(tid, []):
            if p.get('cloud_cover') is None:
                p_with_meta = {
                    **p, 'target_id': tid, 'target_name': tname, 'target_weight': weight,
                    'score': 0, 'reject_reason': 'Missing weather data from API'
                }
                all_passes.append(p_with_meta)
                continue
                
            raw_cc = float(p['cloud_cover'])
            elev = float(p.get('max_elevation_deg', 45.0))
            
            # SAR ignores atmospheric cloud degradation
            effective_cc = raw_cc * 0.05 if is_sar else raw_cc
            
            # Elevation geometric quality factor (passing directly overhead 90° = 1.0, 20° = 0.22)
            elev_weight = min(1.0, max(0.2, elev / 90.0))
            
            # Observation Quality Score: (100 - effective_cloud) * target_weight * elevation_weight * sensor_suitability
            quality_score = (100.0 - effective_cc) * weight * elev_weight * sensor_suitability
            
            audit = (
                f"score=({100.0}-{effective_cc:.1f}% eff_cc) * w({weight}) * "
                f"elev_wt({elev_weight:.2f}) * sensor_mod({sensor_suitability:.2f} [{sat_type}])"
            )
            
            p_with_meta = {
                **p,
                'target_id': tid,
                'target_name': tname,
                'target_weight': weight,
                'sensor_type': sat_type,
                'sensor_suitability': round(sensor_suitability, 2),
                'score': round(quality_score, 2),
                'audit_reason': audit
            }
            all_passes.append(p_with_meta)
                
    # Sort candidate passes by score descending
    all_passes.sort(key=lambda x: x['score'], reverse=True)
    
    scheduled = []
    rejected = []
    
    def is_conflict(p1, p2):
        r1, s1 = datetime.fromisoformat(p1['rise_time'].replace("Z", "+00:00")), datetime.fromisoformat(p1['set_time'].replace("Z", "+00:00"))
        r2, s2 = datetime.fromisoformat(p2['rise_time'].replace("Z", "+00:00")), datetime.fromisoformat(p2['set_time'].replace("Z", "+00:00"))
        return max(r1, r2) < min(s1, s2)

    passes_per_day = {}
    
    for p in all_passes:
        if 'reject_reason' in p:
            rejected.append(p)
            continue
            
        # Cloud threshold check (SAR is exempt from optical cloud threshold rejection)
        if not is_sar and p['cloud_cover'] > max_cloud_cover:
            p['reject_reason'] = f"Cloud cover ({p['cloud_cover']:.0f}%) exceeds optical sensor threshold ({max_cloud_cover:.0f}%)"
            rejected.append(p)
            continue

        # Overpass time overlap conflict
        conflict = False
        for s in scheduled:
            if is_conflict(p, s):
                conflict = True
                break
                
        if conflict:
            p['reject_reason'] = 'Time conflict with higher priority imaging pass'
            rejected.append(p)
            continue
            
        # Daily orbital pass capacity limit
        r1 = datetime.fromisoformat(p['rise_time'].replace("Z", "+00:00"))
        day_str = r1.strftime('%Y-%m-%d')
        if passes_per_day.get(day_str, 0) >= max_passes_per_day:
            p['reject_reason'] = f'Platform daily capacity limit reached ({max_passes_per_day} passes/day)'
            rejected.append(p)
            continue
            
        # Approved
        p['audit_reason'] += ' -> MISSION APPROVED'
        scheduled.append(p)
        passes_per_day[day_str] = passes_per_day.get(day_str, 0) + 1
        
    # Sort scheduled passes chronologically
    scheduled.sort(key=lambda x: x['rise_time'])
    
    # Baseline comparison against naive first-come scheduler
    naive_all = sorted(all_passes, key=lambda x: x['rise_time'])
    naive_scheduled = []
    naive_daily = {}
    for p in naive_all:
        conflict = False
        for s in naive_scheduled:
            if is_conflict(p, s):
                conflict = True
                break
        if conflict:
            continue
        r1 = datetime.fromisoformat(p['rise_time'].replace("Z", "+00:00"))
        day_str = r1.strftime('%Y-%m-%d')
        if naive_daily.get(day_str, 0) >= max_passes_per_day:
            continue
        naive_scheduled.append(p)
        naive_daily[day_str] = naive_daily.get(day_str, 0) + 1

    # Wasted pass metric: passes with >50% cloud cover on optical payloads
    opt_wasted = 0 if is_sar else sum(1 for p in scheduled if p.get('cloud_cover', 0) > 50)
    naive_wasted = 0 if is_sar else sum(1 for p in naive_scheduled if p.get('cloud_cover', 0) > 50)
    
    saved_passes = max(0, naive_wasted - opt_wasted)
    power_saved_wh = saved_passes * power_per_pass
    storage_saved_gb = saved_passes * storage_per_pass
    
    return {
        'scheduled': scheduled,
        'rejected': rejected,
        'stats': {
            'optimal_cloudy_passes': opt_wasted,
            'naive_cloudy_passes': naive_wasted,
            'saved_passes': saved_passes,
            'power_saved_wh': round(power_saved_wh, 1),
            'storage_saved_gb': round(storage_saved_gb, 1),
            'platform_type': sat_type,
            'cloud_penetrating': is_sar
        }
    }
