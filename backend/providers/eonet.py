import httpx
import time
import math
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from providers.base import BaseDataProvider
from models.schemas import DisasterEvent, DisasterType, DisasterCategory, DisasterSeverity, TimelineEvent, DataQuality, SourceStatus
from config import settings

class NASAEONETProvider(BaseDataProvider):
    """
    NASA Earth Observatory Natural Event Tracker (EONET v3) Connector.
    Ingests live natural events worldwide (Wildfires, Severe Storms, Volcanoes, Floods, Landslides, etc.)
    with authoritative NASA EOSDIS metadata.
    """
    def __init__(self):
        super().__init__(
            provider_name="NASA Earth Observatory Natural Event Tracker (EONET v3)",
            dataset_name="Global Active Natural Hazards & Satellite Event Observations",
            endpoint=settings.nasa_eonet_url
        )
        self.cached_events: List[DisasterEvent] = []
        self.last_fetch_time: float = 0.0

    async def fetch_data(self, category: Optional[str] = None, limit: int = 100) -> List[DisasterEvent]:
        now = time.time()
        # Return cache if valid
        if self.cached_events and (now - self.last_fetch_time) < settings.disaster_cache_seconds:
            if category:
                return [e for e in self.cached_events if self._matches_category(e, category)]
            return self.cached_events

        url = f"{self.endpoint}?status=open&limit={limit}"
        if category:
            url += f"&category={category}"

        start_t = time.time()
        self.last_check = datetime.utcnow().isoformat() + "Z"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                self.last_latency_ms = int((time.time() - start_t) * 1000)
                
                if resp.status_code == 200:
                    self.current_status = SourceStatus.LIVE
                    self.last_success = self.last_check
                    data = resp.json()
                    events = self._parse_eonet_events(data.get("events", []))
                    if not category:
                        self.cached_events = events
                        self.last_fetch_time = now
                    return events
                else:
                    self.current_status = SourceStatus.STALE
                    self.error_detail = f"HTTP {resp.status_code}"
        except Exception as e:
            self.current_status = SourceStatus.STALE
            self.error_detail = str(e)

        return self.cached_events

    def _matches_category(self, event: DisasterEvent, category: str) -> bool:
        cat_lower = category.lower()
        if "fire" in cat_lower and event.event_type == DisasterType.WILDFIRE:
            return True
        if "storm" in cat_lower and event.event_type == DisasterType.CYCLONE:
            return True
        if "volcano" in cat_lower and event.event_type == DisasterType.VOLCANO:
            return True
        if "flood" in cat_lower and event.event_type == DisasterType.FLOOD:
            return True
        if "landslide" in cat_lower and event.event_type == DisasterType.LANDSLIDE:
            return True
        if "temp" in cat_lower and event.event_type in [DisasterType.HEATWAVE, DisasterType.DROUGHT]:
            return True
        return False

    def _parse_eonet_events(self, raw_events: List[Dict[str, Any]]) -> List[DisasterEvent]:
        parsed: List[DisasterEvent] = []

        for item in raw_events:
            try:
                e_id = item.get("id", "")
                title = item.get("title", "Natural Hazard Event")
                cats = [c.get("id", "") for c in item.get("categories", [])]
                sources = item.get("sources", [])
                geometries = item.get("geometry", [])

                if not geometries:
                    continue

                # Use latest geometry observation
                latest_geom = geometries[-1]
                coords = latest_geom.get("coordinates", [])
                if not coords or len(coords) < 2:
                    continue

                # Handle Point vs Polygon coordinate structure
                if isinstance(coords[0], (int, float)):
                    lon, lat = float(coords[0]), float(coords[1])
                elif isinstance(coords[0], list) and isinstance(coords[0][0], (int, float)):
                    lon, lat = float(coords[0][0]), float(coords[0][1])
                else:
                    continue

                obs_date = latest_geom.get("date", datetime.utcnow().isoformat() + "Z")
                mag_val = latest_geom.get("magnitudeValue")
                mag_unit = latest_geom.get("magnitudeUnit", "")

                # Map categories to DisasterType and DisasterCategory
                event_type, category, sensor, rec_action = self._classify_event(cats, title)

                # Compute affected area & severity
                affected_area_km2, severity, risk_score, wind_speed = self._calculate_severity_metrics(
                    event_type, mag_val, mag_unit, title
                )

                # Generate impact polygon geometry
                impact_radius_km = max(3.0, (affected_area_km2 / math.pi) ** 0.5)
                poly_geom = self._generate_circle_polygon(lat, lon, impact_radius_km)

                # If storm with multiple track points, build track line string
                storm_track_pts = []
                if event_type == DisasterType.CYCLONE and len(geometries) > 1:
                    for g in geometries:
                        c = g.get("coordinates", [])
                        if len(c) >= 2 and isinstance(c[0], (int, float)):
                            storm_track_pts.append({
                                "lat": round(float(c[1]), 4),
                                "lon": round(float(c[0]), 4),
                                "time": g.get("date", ""),
                                "wind_kts": g.get("magnitudeValue")
                            })

                # Build timeline from NASA observations
                timeline = []
                for g in geometries[-4:]:
                    g_date = g.get("date", "")
                    g_mag = g.get("magnitudeValue")
                    g_unit = g.get("magnitudeUnit", "")
                    g_desc = f"NASA satellite detection recorded."
                    if g_mag:
                        g_desc += f" Intensity: {g_mag} {g_unit}."
                    timeline.append(TimelineEvent(
                        time=g_date,
                        title=f"Observation Logged ({event_type.value})",
                        description=g_desc,
                        source="NASA EOSDIS / EONET",
                        severity=severity.value
                    ))

                # Primary source URL
                source_url = sources[0].get("url") if sources else "https://eonet.gsfc.nasa.gov"
                source_id = sources[0].get("id") if sources else "NASA-EONET"

                prov = self.build_provenance(
                    observed_at=obs_date,
                    data_quality=DataQuality.HIGH,
                    methodology="NASA Earth Observing System Data and Information System (EOSDIS) Multi-Satellite Ingestion",
                    limitations="Observational cadence depends on orbital passes (MODIS, VIIRS, Landsat, GOES).",
                    attribution=f"NASA Earth Observatory Natural Event Tracker (EONET v3) / {source_id}"
                )

                # Estimate exposed population based on area
                pop_density = 45 if event_type in [DisasterType.WILDFIRE, DisasterType.VOLCANO] else 180
                est_pop = max(100, int(affected_area_km2 * pop_density))

                event = DisasterEvent(
                    event_id=f"{event_type.value[:2].upper()}-EONET-{e_id.replace('EONET_', '')}",
                    name=title,
                    event_type=event_type,
                    category=category,
                    status="Active",
                    severity=severity,
                    latitude=round(lat, 4),
                    longitude=round(lon, 4),
                    affected_area_km2=round(affected_area_km2, 1),
                    estimated_population=est_pop,
                    wind_speed_kmh=round(wind_speed, 1) if wind_speed else None,
                    risk_score=round(risk_score, 1),
                    start_time=geometries[0].get("date", obs_date),
                    last_updated=obs_date,
                    source_event_id=e_id,
                    provenance=prov,
                    geometry=poly_geom,
                    timeline=timeline,
                    recommended_sensor=sensor,
                    recommended_action=rec_action
                )
                parsed.append(event)
            except Exception as e:
                continue

        return parsed

    def _classify_event(self, categories: List[str], title: str) -> Tuple[DisasterType, DisasterCategory, str, str]:
        title_lower = title.lower()
        cats_lower = [c.lower() for c in categories]

        if any("wildfire" in c for c in cats_lower) or "fire" in title_lower:
            return (
                DisasterType.WILDFIRE,
                DisasterCategory.ENVIRONMENTAL,
                "Thermal / Multispectral (MODIS / Landsat TIRS)",
                "Acquire SWIR Band 12 (Sentinel-2) and Thermal Infrared (Landsat-9) to delineate active combustion fronts and smoke perimeter."
            )
        elif any("severestorms" in c or "storm" in c for c in cats_lower) or any(w in title_lower for w in ["typhoon", "cyclone", "hurricane", "tropical storm"]):
            return (
                DisasterType.CYCLONE,
                DisasterCategory.METEOROLOGICAL,
                "SAR / Microwave (Sentinel-1A)",
                "Deploy C-band Synthetic Aperture Radar (SAR) to penetrate thick convective cloud wall and estimate coastal storm surge footprint."
            )
        elif any("volcano" in c for c in cats_lower) or "volcano" in title_lower:
            return (
                DisasterType.VOLCANO,
                DisasterCategory.GEOLOGICAL,
                "InSAR / Thermal IR (Sentinel-1 / MODIS)",
                "Execute ascending/descending SAR passes to measure summit flank deformation and track atmospheric SO2/ash plumes."
            )
        elif any("flood" in c for c in cats_lower) or "flood" in title_lower:
            return (
                DisasterType.FLOOD,
                DisasterCategory.HYDROLOGICAL,
                "SAR (Sentinel-1A / RISAT)",
                "Perform all-weather radar water mask extraction to monitor river embankment overtopping and inundation expansion."
            )
        elif any("landslide" in c for c in cats_lower) or "landslide" in title_lower:
            return (
                DisasterType.LANDSLIDE,
                DisasterCategory.GEOLOGICAL,
                "High-Resolution InSAR / Optical",
                "Execute differential SAR interferometry (DInSAR) to detect sub-centimeter slope instability and ground movement."
            )
        elif any("drought" in c for c in cats_lower) or "drought" in title_lower:
            return (
                DisasterType.DROUGHT,
                DisasterCategory.METEOROLOGICAL,
                "Multispectral NDVI / Microwave (Sentinel-2 / SMAP)",
                "Calculate Normalized Difference Vegetation Index (NDVI) anomaly and top-layer soil moisture deficit."
            )
        elif any("tempextremes" in c for c in cats_lower) or any(w in title_lower for w in ["heat", "temperature", "warm"]):
            return (
                DisasterType.HEATWAVE,
                DisasterCategory.METEOROLOGICAL,
                "Thermal Infrared (MODIS / Landsat TIRS)",
                "Derive Land Surface Temperature (LST) mapping across urban dense canopy and vulnerable agricultural basins."
            )
        else:
            return (
                DisasterType.OTHER,
                DisasterCategory.ENVIRONMENTAL,
                "Multispectral / Optical",
                "Task multispectral high-resolution imaging to evaluate situational impact."
            )

    def _calculate_severity_metrics(self, event_type: DisasterType, mag_val: Optional[float], mag_unit: str, title: str) -> Tuple[float, DisasterSeverity, float, Optional[float]]:
        # Area in km2
        area_km2 = 25.0
        severity = DisasterSeverity.DEVELOPING
        risk_score = 50.0
        wind_kmh = None

        if event_type == DisasterType.WILDFIRE:
            if mag_val and "acre" in mag_unit.lower():
                area_km2 = max(2.0, mag_val * 0.00404686) # acres to km2
            elif mag_val:
                area_km2 = max(2.0, mag_val)
            else:
                area_km2 = 45.0

            if area_km2 > 100.0:
                severity = DisasterSeverity.CRITICAL
                risk_score = 90.0
            elif area_km2 > 30.0:
                severity = DisasterSeverity.SEVERE
                risk_score = 78.0
            elif area_km2 > 10.0:
                severity = DisasterSeverity.ESCALATING
                risk_score = 64.0
            else:
                severity = DisasterSeverity.DEVELOPING
                risk_score = 45.0

        elif event_type == DisasterType.CYCLONE:
            if mag_val and "kt" in mag_unit.lower():
                wind_kmh = mag_val * 1.852
            elif mag_val:
                wind_kmh = mag_val
            else:
                wind_kmh = 120.0

            area_km2 = round(math.pi * (140.0 ** 2), 1) # ~60,000 km2 storm footprint

            if wind_kmh >= 165.0: # Cat 4/5 or Super Cyclone
                severity = DisasterSeverity.CRITICAL
                risk_score = 96.0
            elif wind_kmh >= 120.0: # Severe Tropical Storm / Hurricane
                severity = DisasterSeverity.CRITICAL
                risk_score = 88.0
            elif wind_kmh >= 85.0: # Tropical Storm
                severity = DisasterSeverity.SEVERE
                risk_score = 75.0
            else:
                severity = DisasterSeverity.ESCALATING
                risk_score = 60.0

        elif event_type == DisasterType.VOLCANO:
            area_km2 = 80.0
            severity = DisasterSeverity.SEVERE
            risk_score = 82.0

        elif event_type == DisasterType.FLOOD:
            area_km2 = 180.0
            severity = DisasterSeverity.CRITICAL
            risk_score = 89.0

        elif event_type == DisasterType.LANDSLIDE:
            area_km2 = 15.0
            severity = DisasterSeverity.SEVERE
            risk_score = 84.0

        elif event_type in [DisasterType.HEATWAVE, DisasterType.DROUGHT]:
            area_km2 = 45000.0
            severity = DisasterSeverity.SEVERE
            risk_score = 76.0

        return area_km2, severity, risk_score, wind_kmh

    def _generate_circle_polygon(self, lat: float, lon: float, radius_km: float, num_points: int = 20) -> Dict[str, Any]:
        coords = []
        r_rad = max(1.0, radius_km) / 6371.0
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)

        for i in range(num_points + 1):
            bearing = 2 * math.pi * i / num_points
            pt_lat = math.asin(math.sin(lat_rad) * math.cos(r_rad) + math.cos(lat_rad) * math.sin(r_rad) * math.cos(bearing))
            pt_lon = lon_rad + math.atan2(math.sin(bearing) * math.sin(r_rad) * math.cos(lat_rad), math.cos(r_rad) - math.sin(lat_rad) * math.sin(pt_lat))
            coords.append([round(math.degrees(pt_lon), 5), round(math.degrees(pt_lat), 5)])

        return {
            "type": "Polygon",
            "coordinates": [coords]
        }

nasa_eonet_provider = NASAEONETProvider()
