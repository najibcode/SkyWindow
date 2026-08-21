from typing import List, Dict
from datetime import datetime

def compute_schedule(targets: List[Dict], passes_data: Dict[str, List[Dict]], max_passes_per_day: int = 5, max_cloud_cover: float = 70.0, power_per_pass: float = 150.0, storage_per_pass: float = 12.0) -> Dict:
    """
    targets: [{'id': 't1', 'lat': 12, 'lon': 34, 'weight': 10, 'name': 'City A'}, ...]
    passes_data: {'t1': [{'rise_time': ..., 'culminate_time': ..., 'set_time': ..., 'cloud_cover': 20, 'max_elevation_deg': 45}, ...]}
    
    Returns a schedule and stats.
    """
    all_passes = []
    
    for t in targets:
        tid = t['id']
        tname = t['name']
        weight = t['weight']
        for p in passes_data.get(tid, []):
            # Check for missing weather data gracefully
            if p.get('cloud_cover') is None:
                p_with_meta = {**p, 'target_id': tid, 'target_name': tname, 'target_weight': weight, 'score': 0, 'reject_reason': 'Missing weather data from API'}
                all_passes.append(p_with_meta)
                continue
                
            cc = p['cloud_cover']
            elev = p.get('max_elevation_deg', 0)
            
            # Elevation weight: passing directly overhead (90 deg) is best (1.0), lower is worse.
            elev_weight = elev / 90.0 if elev <= 90 else 1.0
            
            # Score formula: (100 - cloud_cover) * target_weight * elevation_weight
            score = (100 - cc) * weight * elev_weight
            
            audit = f"score=({100}-{cc}) * w({weight}) * elev_wt({elev_weight:.2f})"
            
            p_with_meta = {
                **p,
                'target_id': tid,
                'target_name': tname,
                'target_weight': weight,
                'score': score,
                'audit_reason': audit
            }
            all_passes.append(p_with_meta)
                
    # Sort by score descending for optimizer
    all_passes.sort(key=lambda x: x['score'], reverse=True)
    
    scheduled = []
    rejected = []
    
    # Simple conflict detection: overlapping times
    def is_conflict(p1, p2):
        r1, s1 = datetime.fromisoformat(p1['rise_time']), datetime.fromisoformat(p1['set_time'])
        r2, s2 = datetime.fromisoformat(p2['rise_time']), datetime.fromisoformat(p2['set_time'])
        return max(r1, r2) < min(s1, s2)

    passes_per_day = {} # track capacity
    
    for p in all_passes:
        if 'reject_reason' in p:
            rejected.append(p)
            continue
            
        # Optimizer check: reject outright if it violates cloud threshold
        if p['cloud_cover'] > max_cloud_cover:
            p['reject_reason'] = f"Cloud cover ({p['cloud_cover']}%) exceeds max threshold ({max_cloud_cover}%)"
            rejected.append(p)
            continue

        # Check conflict with already scheduled
        conflict = False
        for s in scheduled:
            if is_conflict(p, s):
                conflict = True
                break
                
        if conflict:
            p['reject_reason'] = 'Time conflict with higher priority pass'
            rejected.append(p)
            continue
            
        # Check daily capacity
        r1 = datetime.fromisoformat(p['rise_time'])
        day_str = r1.strftime('%Y-%m-%d')
        if passes_per_day.get(day_str, 0) >= max_passes_per_day:
            p['reject_reason'] = f'Capacity limit reached ({max_passes_per_day}/day)'
            rejected.append(p)
            continue
            
        # Schedule it
        p['audit_reason'] += ' -> APPROVED'
        scheduled.append(p)
        passes_per_day[day_str] = passes_per_day.get(day_str, 0) + 1
        
    # Sort scheduled chronologically
    scheduled.sort(key=lambda x: x['rise_time'])
    
    # Calculate baseline comparison (naive scheduler)
    # Naive: just take the first N passes chronologically without looking at weather/priority or thresholds
    naive_all_passes = sorted(all_passes, key=lambda x: x['rise_time'])
    naive_scheduled = []
    naive_passes_per_day = {}
    for p in naive_all_passes:
        conflict = False
        for s in naive_scheduled:
            if is_conflict(p, s):
                conflict = True
                break
        if conflict:
            continue
            
        r1 = datetime.fromisoformat(p['rise_time'])
        day_str = r1.strftime('%Y-%m-%d')
        if naive_passes_per_day.get(day_str, 0) >= max_passes_per_day:
            continue
            
        naive_scheduled.append(p)
        naive_passes_per_day[day_str] = naive_passes_per_day.get(day_str, 0) + 1
        
    # Impact simulator
    # Cloudy passes considered wasted (> 50% cloud cover)
    opt_wasted = sum(1 for p in scheduled if p.get('cloud_cover') is not None and p['cloud_cover'] > 50)
    naive_wasted = sum(1 for p in naive_scheduled if p.get('cloud_cover') is not None and p['cloud_cover'] > 50)
    
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
            'power_saved_wh': power_saved_wh,
            'storage_saved_gb': storage_saved_gb
        }
    }
