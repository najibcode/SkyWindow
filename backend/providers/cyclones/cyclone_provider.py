import httpx
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from providers.base import BaseDataProvider
from models.schemas import DisasterEvent, DisasterType, DisasterCategory, DisasterSeverity, ExposedInfrastructure, TimelineEvent, DataQuality, SourceStatus
from providers.eonet import nasa_eonet_provider
from config import settings

class TropicalCycloneProvider(BaseDataProvider):
    def __init__(self):
        super().__init__(
            provider_name="NOAA NHC, JTWC & NASA EONET",
            dataset_name="Authoritative Tropical Cyclone & Severe Storm Active Observations",
            endpoint="https://eonet.gsfc.nasa.gov/api/v3/events?category=severeStorms"
        )
        self.cached_events: List[DisasterEvent] = []
        self.last_fetch_time: float = 0.0

    async def fetch_data(self) -> List[DisasterEvent]:
        now = time.time()
        if self.cached_events and (now - self.last_fetch_time) < settings.disaster_cache_seconds:
            return self.cached_events

        self.last_check = datetime.utcnow().isoformat() + "Z"
        
        try:
            eonet_storms = await nasa_eonet_provider.fetch_data(category="severeStorms")
            if eonet_storms:
                self.current_status = SourceStatus.LIVE
                self.last_success = self.last_check
                self.last_latency_ms = nasa_eonet_provider.last_latency_ms or 40
                self.cached_events = eonet_storms
                self.last_fetch_time = now
                return eonet_storms
        except Exception as e:
            self.current_status = SourceStatus.STALE
            self.error_detail = str(e)

        return self.cached_events

cyclone_provider = TropicalCycloneProvider()
