from datetime import datetime, timezone
from typing import List, Dict, Any
from disasters.manager import disaster_manager
from satellite.catalog import SATELLITE_CATALOG

class ObservationRecommendationEngine:
    """
    Ranks active disaster events into an optimal Earth Observation Queue,
    matching each event with the best satellite platform and sensor payload.
    """
    async def get_recommended_queue(self) -> List[Dict[str, Any]]:
        disasters = await disaster_manager.get_all_disasters()
        queue = []

        for d in disasters:
            dtype = d.event_type.value.lower()
            
            # Match best satellite platform
            if "flood" in dtype or "cyclone" in dtype or "storm" in dtype:
                best_sat = SATELLITE_CATALOG[39634] # Sentinel-1A SAR
                reason = "All-weather SAR penetration through heavy precipitation and cloud canopy"
                sensor = "C-SAR (5m)"
            elif "fire" in dtype or "heat" in dtype or "volcano" in dtype:
                best_sat = SATELLITE_CATALOG[25994] # Terra MODIS / Landsat
                reason = "High-sensitivity Thermal Infrared channels for heat flux delineation"
                sensor = "Thermal IR / SWIR"
            elif "earthquake" in dtype or "landslide" in dtype:
                best_sat = SATELLITE_CATALOG[39634] # Sentinel-1 InSAR
                reason = "Interferometric SAR (InSAR) for sub-centimeter line-of-sight surface deformation"
                sensor = "InSAR / Optical"
            else:
                best_sat = SATELLITE_CATALOG[40697] # Sentinel-2A Optical
                reason = "10m high-resolution multispectral visual verification"
                sensor = "MSI 13-Band Optical"

            queue.append({
                "disaster_id": d.event_id,
                "disaster_name": d.name,
                "event_type": d.event_type.value,
                "severity": d.severity.value,
                "risk_score": d.risk_score,
                "latitude": d.latitude,
                "longitude": d.longitude,
                "recommended_satellite_id": best_sat.id,
                "recommended_satellite_name": best_sat.name,
                "recommended_sensor": sensor,
                "rationale": reason,
                "urgency": "CRITICAL" if d.risk_score >= 85 else ("HIGH" if d.risk_score >= 70 else "STANDARD")
            })

        # Sort queue by risk score descending
        queue.sort(key=lambda x: x["risk_score"], reverse=True)
        return queue

recommendation_engine = ObservationRecommendationEngine()
