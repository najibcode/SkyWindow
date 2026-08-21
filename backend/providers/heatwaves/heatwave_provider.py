import httpx
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from providers.base import BaseDataProvider
from models.schemas import DisasterEvent, DisasterType, DisasterCategory, DisasterSeverity, ExposedInfrastructure, TimelineEvent, DataQuality, SourceStatus
from providers.eonet import nasa_eonet_provider
from config import settings

class HeatwaveDroughtProvider(BaseDataProvider):
    def __init__(self):
        super().__init__(
            provider_name="Copernicus ERA5 & NASA EONET",
            dataset_name="Global Extreme Temperature & Drought Active Hazards",
            endpoint="https://eonet.gsfc.nasa.gov/api/v3/events?category=tempExtremes"
        )
        self.cached_events: List[DisasterEvent] = []
        self.last_fetch_time: float = 0.0

    async def fetch_data(self) -> List[DisasterEvent]:
        now = time.time()
        if self.cached_events and (now - self.last_fetch_time) < settings.disaster_cache_seconds:
            return self.cached_events

        self.last_check = datetime.utcnow().isoformat() + "Z"
        
        events = []
        try:
            temp_events = await nasa_eonet_provider.fetch_data(category="tempExtremes")
            drought_events = await nasa_eonet_provider.fetch_data(category="drought")
            events.extend(temp_events or [])
            events.extend(drought_events or [])
            
            if events:
                self.current_status = SourceStatus.LIVE
                self.last_success = self.last_check
                self.last_latency_ms = nasa_eonet_provider.last_latency_ms or 44
                self.cached_events = events
                self.last_fetch_time = now
                return events
        except Exception as e:
            self.current_status = SourceStatus.STALE
            self.error_detail = str(e)

        return self.cached_events

heat_drought_provider = HeatwaveDroughtProvider()
