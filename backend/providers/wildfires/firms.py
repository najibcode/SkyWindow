import httpx
import time
import csv
import io
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from providers.base import BaseDataProvider
from models.schemas import DisasterEvent, DisasterType, DisasterCategory, DisasterSeverity, ExposedInfrastructure, TimelineEvent, DataQuality, SourceStatus
from providers.eonet import nasa_eonet_provider
from config import settings

class NASAFIRMSWildfireProvider(BaseDataProvider):
    def __init__(self):
        super().__init__(
            provider_name="NASA FIRMS & EONET",
            dataset_name="VIIRS, MODIS & Geostationary Near Real-Time Active Wildfire Events",
            endpoint="https://firms.modaps.eosdis.nasa.gov"
        )
        self.cached_events: List[DisasterEvent] = []
        self.last_fetch_time: float = 0.0

    async def fetch_data(self, limit: int = 30) -> List[DisasterEvent]:
        now = time.time()
        if self.cached_events and (now - self.last_fetch_time) < settings.disaster_cache_seconds:
            return self.cached_events

        start_t = time.time()
        self.last_check = datetime.utcnow().isoformat() + "Z"

        # 1. If API key present, fetch live FIRMS CSV
        api_key = settings.nasa_firms_api_key
        if api_key:
            url = f"{settings.nasa_firms_url}/{api_key}/VIIRS_SNPP_NRT/world/1"
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    self.last_latency_ms = int((time.time() - start_t) * 1000)
                    if resp.status_code == 200:
                        self.current_status = SourceStatus.LIVE
                        self.last_success = self.last_check
                        events = self._parse_firms_csv(resp.text, limit=limit)
                        if events:
                            self.cached_events = events
                            self.last_fetch_time = now
                            return events
            except Exception as e:
                self.error_detail = str(e)

        # 2. Fetch live active wildfires from NASA EONET v3
        try:
            eonet_fires = await nasa_eonet_provider.fetch_data(category="wildfires", limit=limit)
            if eonet_fires:
                self.current_status = SourceStatus.LIVE
                self.last_success = self.last_check
                self.last_latency_ms = nasa_eonet_provider.last_latency_ms or 50
                self.cached_events = eonet_fires
                self.last_fetch_time = now
                return eonet_fires
        except Exception as e:
            self.current_status = SourceStatus.STALE
            self.error_detail = str(e)

        return self.cached_events

    def _parse_firms_csv(self, csv_text: str, limit: int = 30) -> List[DisasterEvent]:
        reader = csv.DictReader(io.StringIO(csv_text))
        hotspots = []
        for row in reader:
            try:
                lat = float(row.get("latitude", 0))
                lon = float(row.get("longitude", 0))
                brightness = float(row.get("bright_ti4", row.get("brightness", 320)))
                frp = float(row.get("frp", 15.0)) # Fire Radiative Power (MW)
                acq_date = row.get("acq_date", datetime.utcnow().strftime("%Y-%m-%d"))
                acq_time = row.get("acq_time", "1200")
                confidence = row.get("confidence", "nominal")
                satellite = row.get("satellite", "VIIRS-SNPP")
                hotspots.append({
                    "lat": lat, "lon": lon, "brightness": brightness,
                    "frp": frp, "date": acq_date, "time": acq_time,
                    "confidence": confidence, "satellite": satellite
                })
            except Exception:
                continue

        return self._cluster_hotspots_into_events(hotspots, limit)

    def _cluster_hotspots_into_events(self, hotspots: List[Dict[str, Any]], limit: int) -> List[DisasterEvent]:
        events: List[DisasterEvent] = []
        hotspots.sort(key=lambda x: x["frp"], reverse=True)
        
        used = set()
        for i, h in enumerate(hotspots):
            if i in used:
                continue
            used.add(i)
            cluster = [h]
            for j, other in enumerate(hotspots):
                if j not in used:
                    dist = ((h["lat"] - other["lat"])**2 + (h["lon"] - other["lon"])**2)**0.5 * 111.0
                    if dist < 35.0:
                        cluster.append(other)
                        used.add(j)

            total_frp = sum(c["frp"] for c in cluster)
            avg_lat = sum(c["lat"] for c in cluster) / len(cluster)
            avg_lon = sum(c["lon"] for c in cluster) / len(cluster)
            est_area_km2 = round(len(cluster) * 1.8, 1)

            if total_frp > 150:
                severity = DisasterSeverity.CRITICAL
                risk_score = 90.0
            elif total_frp > 75:
                severity = DisasterSeverity.SEVERE
                risk_score = 75.0
            elif total_frp > 30:
                severity = DisasterSeverity.ESCALATING
                risk_score = 60.0
            else:
                severity = DisasterSeverity.DEVELOPING
                risk_score = 42.0

            obs_iso = f"{h['date']}T{h['time'][:2]}:{h['time'][2:]}:00Z" if len(h['time']) == 4 else datetime.utcnow().isoformat() + "Z"
            event_id = f"WF-FIRMS-{int(abs(avg_lat)*100)}-{int(abs(avg_lon)*100)}"
            name = f"Wildfire Hotspot Cluster ({len(cluster)} detections, {round(total_frp, 1)} MW)"

            prov = self.build_provenance(
                observed_at=obs_iso,
                data_quality=DataQuality.HIGH,
                methodology="VIIRS/MODIS 375m/1km Thermal Anomaly Detection (FRP Inversion)",
                attribution="NASA EOSDIS Land, Atmosphere Near real-time Capability for EOS (LANCE)"
            )

            poly = self._generate_fire_perimeter(avg_lat, avg_lon, (est_area_km2 / 3.14)**0.5)

            events.append(DisasterEvent(
                event_id=event_id,
                name=name,
                event_type=DisasterType.WILDFIRE,
                category=DisasterCategory.ENVIRONMENTAL,
                status="Active",
                severity=severity,
                latitude=round(avg_lat, 4),
                longitude=round(avg_lon, 4),
                affected_area_km2=est_area_km2,
                estimated_population=int(est_area_km2 * 18),
                risk_score=risk_score,
                start_time=obs_iso,
                last_updated=datetime.utcnow().isoformat() + "Z",
                provenance=prov,
                geometry=poly,
                timeline=[
                    TimelineEvent(
                        time=obs_iso,
                        title="Thermal Hotspot Cluster Detected",
                        description=f"{len(cluster)} active thermal anomalies detected with total Fire Radiative Power of {total_frp:.1f} MW.",
                        source="NASA VIIRS Sensor",
                        severity=severity.value
                    )
                ],
                recommended_sensor="Thermal / Multispectral (MODIS / Landsat)",
                recommended_action="Task multispectral SWIR/thermal sensors to evaluate fire perimeter and smoke dispersion."
            ))
            if len(events) >= limit:
                break

        return events

    def _generate_fire_perimeter(self, lat: float, lon: float, radius_km: float) -> Dict[str, Any]:
        import math
        coords = []
        r_rad = max(1.5, radius_km) / 6371.0
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)

        for i in range(16 + 1):
            bearing = 2 * math.pi * i / 16
            r_noisy = r_rad * (0.85 + 0.3 * math.sin(i * 1.5))
            pt_lat = math.asin(math.sin(lat_rad) * math.cos(r_noisy) + math.cos(lat_rad) * math.sin(r_noisy) * math.cos(bearing))
            pt_lon = lon_rad + math.atan2(math.sin(bearing) * math.sin(r_noisy) * math.cos(lat_rad), math.cos(r_noisy) - math.sin(lat_rad) * math.sin(pt_lat))
            coords.append([round(math.degrees(pt_lon), 5), round(math.degrees(pt_lat), 5)])

        return {
            "type": "Polygon",
            "coordinates": [coords]
        }

firms_provider = NASAFIRMSWildfireProvider()
