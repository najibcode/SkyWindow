from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from datetime import datetime

class SourceStatus(str, Enum):
    LIVE = "LIVE"
    STALE = "STALE"
    DEGRADED = "DEGRADED"
    DEMO = "DEMO"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"

class DataQuality(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    MODELLED = "MODELLED"

class DataProvenance(BaseModel):
    provider: str
    dataset: str
    endpoint: Optional[str] = None
    url: Optional[str] = None
    observed_at: Optional[str] = None
    retrieved_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    freshness_seconds: Optional[int] = None
    status: SourceStatus = SourceStatus.LIVE
    data_quality: DataQuality = DataQuality.HIGH
    methodology: Optional[str] = None
    limitations: Optional[str] = None
    attribution: Optional[str] = None

class DisasterCategory(str, Enum):
    HYDROLOGICAL = "Hydrological"
    GEOLOGICAL = "Geological"
    OCEANIC = "Oceanic"
    METEOROLOGICAL = "Meteorological"
    ENVIRONMENTAL = "Environmental"
    CRYOSPHERIC = "Cryospheric"

class DisasterType(str, Enum):
    FLOOD = "Flood"
    FLASH_FLOOD = "Flash Flood"
    EARTHQUAKE = "Earthquake"
    TSUNAMI = "Tsunami"
    CYCLONE = "Cyclone"
    WILDFIRE = "Wildfire"
    LANDSLIDE = "Landslide"
    VOLCANO = "Volcano"
    HEATWAVE = "Heatwave"
    DROUGHT = "Drought"
    STORM_SURGE = "Storm Surge"
    AVALANCHE = "Avalanche"

class DisasterSeverity(str, Enum):
    MONITORING = "Monitoring"
    DETECTED = "Detected"
    DEVELOPING = "Developing"
    ESCALATING = "Escalating"
    SEVERE = "Severe"
    CRITICAL = "Critical"
    RESOLVED = "Resolved"

class TimelineEvent(BaseModel):
    time: str
    title: str
    description: str
    source: str
    severity: Optional[str] = "Info"

class ExposedInfrastructure(BaseModel):
    hospitals: int = 0
    schools: int = 0
    bridges: int = 0
    airports: int = 0
    roads_km: float = 0.0
    critical_facilities: List[str] = []
    source: str = "OpenStreetMap Overpass / Spatial Analytics"

class DisasterEvent(BaseModel):
    event_id: str
    name: str
    event_type: DisasterType
    category: DisasterCategory
    status: str = "Active"
    severity: DisasterSeverity
    latitude: float
    longitude: float
    geometry: Optional[Dict[str, Any]] = None # GeoJSON geometry
    depth_km: Optional[float] = None
    magnitude: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    affected_area_km2: Optional[float] = None
    estimated_population: Optional[int] = None
    exposed_infrastructure: Optional[ExposedInfrastructure] = None
    risk_score: float = Field(default=50.0, ge=0.0, le=100.0)
    risk_breakdown: Optional[Dict[str, float]] = None
    start_time: str
    last_updated: str
    source_event_id: Optional[str] = None
    provenance: DataProvenance
    timeline: List[TimelineEvent] = []
    recommended_sensor: str = "SAR"
    recommended_action: Optional[str] = None
    tsunami_potential: Optional[bool] = None
    is_official_warning: Optional[bool] = None

class SatelliteSensor(BaseModel):
    name: str
    sensor_type: str # SAR, Optical, Thermal, Multispectral, Hyperspectral, Microwave
    resolution_m: float
    swath_km: float
    day_night_capable: bool
    cloud_penetrating: bool

class SatelliteInfo(BaseModel):
    id: int
    name: str
    norad_id: int
    operator: str
    country: str
    type: str # SAR, Optical, Multispectral, etc.
    desc: str
    revisit: str
    recommended_capacity: int = 5
    orbit_type: str = "LEO Sun-Synchronous"
    altitude_km: float = 700.0
    inclination_deg: float = 98.2
    sensors: List[SatelliteSensor] = []
    status: str = "Operational"

class TargetInput(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    weight: float = 5.0
    disaster_id: Optional[str] = None
    target_type: Optional[str] = "Disaster Core"

class PassObservation(BaseModel):
    satellite_id: int
    satellite_name: str
    target_id: str
    target_name: str
    target_weight: float
    rise_time: str
    culminate_time: str
    set_time: str
    max_elevation_deg: float
    cloud_cover: Optional[float] = None
    sensor_type: str
    sensor_suitability: float = 1.0 # 0.0 - 1.0
    sun_elevation_deg: Optional[float] = None
    score: float = 0.0
    status: str = "SCHEDULED" # SCHEDULED or REJECTED
    reject_reason: Optional[str] = None
    audit_reason: Optional[str] = None
    off_nadir_deg: Optional[float] = None

class ScheduleRequest(BaseModel):
    satellite_id: int
    targets: List[TargetInput]
    max_passes_per_day: int = 5
    max_cloud_cover: float = 70.0
    power_per_pass: float = 150.0
    storage_per_pass: float = 12.0
    disaster_id: Optional[str] = None
    sensor_preference: Optional[str] = None

class ConstellationPlanRequest(BaseModel):
    satellite_ids: List[int]
    targets: List[TargetInput]
    campaign_name: str = "Multi-Satellite Observation Campaign"
    duration_hours: int = 48
    max_cloud_cover: float = 70.0

class ScheduleResult(BaseModel):
    scheduled: List[Dict[str, Any]]
    rejected: List[Dict[str, Any]]
    stats: Dict[str, Any]
    tle_info: Dict[str, Any]
    provenance: DataProvenance

class ChangeDetectionRequest(BaseModel):
    event_id: str
    target_lat: float
    target_lon: float
    baseline_date: str
    current_date: str
    feature_type: str = "water_extent" # water_extent, burn_scar, structural, vegetation

class ChangeDetectionResult(BaseModel):
    event_id: str
    feature_type: str
    baseline_date: str
    current_date: str
    baseline_area_km2: float
    current_area_km2: float
    delta_area_km2: float
    percentage_change: float
    expansion_status: str # EXPANDING, RECEDING, STABLE
    confidence: float
    methodology: str
    provenance: DataProvenance

class AnalystQueryRequest(BaseModel):
    query: str
    context_disaster_id: Optional[str] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None

class AnalystResponse(BaseModel):
    answer: str
    evidence_points: List[str]
    suggested_actions: List[str]
    related_disasters: List[str] = []
    recommended_satellite_tasks: List[Dict[str, Any]] = []
    confidence: float = 0.85
    data_sources: List[str] = []
    provenance: DataProvenance

class NaturalLanguageTaskingRequest(BaseModel):
    instruction: str # e.g., "Monitor the Kerala flood for SAR imagery over the next 48 hours"

class NaturalLanguageTaskingResponse(BaseModel):
    parsed_target_name: str
    latitude: float
    longitude: float
    disaster_type: str
    recommended_sensor: str
    priority: int
    duration_hours: int
    objective: str
    suggested_satellites: List[str]
    proposed_plan: Dict[str, Any]
    explanation: str

class AlertRule(BaseModel):
    id: str
    name: str
    disaster_type: str
    min_severity: str = "Severe"
    min_magnitude: Optional[float] = None
    max_distance_km: float = 500.0
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    notify_email: Optional[str] = None
    notify_webhook: Optional[str] = None
    is_active: bool = True

class AlertItem(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    disaster_id: str
    disaster_name: str
    severity: str
    title: str
    message: str
    created_at: str
    is_read: bool = False
    source: str

class MonitoredArea(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    radius_km: float = 50.0
    monitored_types: List[str]
    created_at: str
    notes: Optional[str] = None

class DataSourceHealth(BaseModel):
    source_id: str
    name: str
    provider: str
    category: str # Seismic, Meteorological, Hydrological, Orbital, Thermal, Geospatial
    endpoint: str
    status: SourceStatus
    latency_ms: Optional[int] = None
    last_check: str
    last_success: Optional[str] = None
    freshness_seconds: Optional[int] = None
    data_type: str
    update_frequency: str
    license: str
    attribution: str
    error_detail: Optional[str] = None
