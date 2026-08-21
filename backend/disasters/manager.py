import asyncio
import time
from typing import List, Dict, Any, Optional
from models.schemas import DisasterEvent, DisasterCategory, DisasterType, DisasterSeverity, SourceStatus
from providers.earthquakes.usgs import USGSEarthquakeProvider
from providers.floods.flood_provider import flood_provider
from providers.cyclones.cyclone_provider import cyclone_provider
from providers.wildfires.firms import firms_provider
from providers.landslides.landslide_provider import landslide_provider
from providers.tsunamis.tsunami_provider import tsunami_provider
from providers.volcanoes.volcano_provider import volcano_provider
from providers.heatwaves.heatwave_provider import heat_drought_provider
from database import upsert_disaster_event, get_all_disasters_db, get_disaster_by_id_db

class DisasterManager:
    def __init__(self):
        self.eq_provider = USGSEarthquakeProvider()
        self.cached_disasters: Dict[str, DisasterEvent] = {}
        self.last_sync_time: float = 0.0

    async def get_all_disasters(self, force_refresh: bool = False) -> List[DisasterEvent]:
        now = time.time()
        if not force_refresh and self.cached_disasters and (now - self.last_sync_time) < 180:
            return list(self.cached_disasters.values())

        # Concurrently gather events from all real & authoritative providers
        results = await asyncio.gather(
            self.eq_provider.fetch_data(min_magnitude=3.5, limit=25),
            flood_provider.fetch_data(),
            cyclone_provider.fetch_data(),
            firms_provider.fetch_data(),
            landslide_provider.fetch_data(),
            tsunami_provider.fetch_data(),
            volcano_provider.fetch_data(),
            heat_drought_provider.fetch_data(),
            return_exceptions=True
        )

        all_events: List[DisasterEvent] = []
        for res in results:
            if isinstance(res, list):
                all_events.extend(res)
            elif isinstance(res, Exception):
                print(f"[DisasterManager Error] Provider error: {res}")

        # Update in-memory cache and persist to SQLite
        self.cached_disasters.clear()
        for ev in all_events:
            self.cached_disasters[ev.event_id] = ev
            try:
                upsert_disaster_event(ev.dict())
            except Exception as e:
                print(f"[DB Error] Failed to persist event {ev.event_id}: {e}")

        self.last_sync_time = now
        # Sort by risk score descending
        all_events.sort(key=lambda x: x.risk_score, reverse=True)
        return all_events

    async def get_disaster_by_id(self, event_id: str) -> Optional[DisasterEvent]:
        if not self.cached_disasters:
            await self.get_all_disasters()
        
        event = self.cached_disasters.get(event_id)
        if not event:
            db_record = get_disaster_by_id_db(event_id)
            if db_record:
                try:
                    event = DisasterEvent(**db_record)
                except Exception:
                    event = None

        if event and not event.exposed_infrastructure:
            from providers.infrastructure.osm import osm_provider
            try:
                infra = await osm_provider.get_exposed_infrastructure(
                    event.latitude, event.longitude, 
                    radius_km=max(5.0, (event.affected_area_km2 / 3.14)**0.5)
                )
                event.exposed_infrastructure = infra
                self.cached_disasters[event.event_id] = event
            except Exception:
                pass

        return event

    async def get_summary_stats(self) -> Dict[str, Any]:
        events = await self.get_all_disasters()
        critical_count = sum(1 for e in events if e.severity in [DisasterSeverity.CRITICAL, DisasterSeverity.SEVERE])
        active_count = len(events)
        
        by_category = {}
        for e in events:
            cat = e.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        top_priority = events[0] if events else None

        return {
            "active_disasters_count": active_count,
            "high_risk_zones_count": critical_count,
            "by_category": by_category,
            "top_priority_event": top_priority.dict() if top_priority else None,
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(self.last_sync_time)) if self.last_sync_time else "Just now"
        }

disaster_manager = DisasterManager()
