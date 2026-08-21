from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from models.schemas import DataProvenance, SourceStatus, DataQuality

class BaseDataProvider(ABC):
    def __init__(self, provider_name: str, dataset_name: str, endpoint: str):
        self.provider_name = provider_name
        self.dataset_name = dataset_name
        self.endpoint = endpoint
        self.last_check: Optional[str] = None
        self.last_success: Optional[str] = None
        self.last_latency_ms: Optional[int] = None
        self.current_status: SourceStatus = SourceStatus.LIVE
        self.error_detail: Optional[str] = None

    @abstractmethod
    async def fetch_data(self, **kwargs) -> Any:
        """Fetch raw data from external source or fallback cache."""
        pass

    def build_provenance(self, observed_at: Optional[str] = None, data_quality: DataQuality = DataQuality.HIGH, methodology: Optional[str] = None, limitations: Optional[str] = None, attribution: Optional[str] = None) -> DataProvenance:
        now_dt = datetime.utcnow()
        freshness_secs = None
        if observed_at:
            try:
                # Calculate freshness in seconds
                obs_clean = observed_at.replace("Z", "+00:00") if "Z" in observed_at else observed_at
                obs_dt = datetime.fromisoformat(obs_clean)
                freshness_secs = max(0, int((now_dt.timestamp() - obs_dt.timestamp())))
            except Exception:
                freshness_secs = None

        return DataProvenance(
            provider=self.provider_name,
            dataset=self.dataset_name,
            endpoint=self.endpoint,
            url=self.endpoint,
            observed_at=observed_at or now_dt.isoformat() + "Z",
            retrieved_at=now_dt.isoformat() + "Z",
            freshness_seconds=freshness_secs,
            status=self.current_status,
            data_quality=data_quality,
            methodology=methodology,
            limitations=limitations,
            attribution=attribution or f"Data provided by {self.provider_name} ({self.dataset_name})"
        )
