import os
from pydantic import BaseModel
from typing import Optional

class Settings(BaseModel):
    # App
    app_name: str = "SkyWindow AI Earth Observation & Disaster Intelligence Platform"
    app_version: str = "2.0.0"
    debug: bool = False
    
    # Storage & Database
    db_path: str = os.getenv("SKYWINDOW_DB_PATH", "skywindow.db")
    tle_cache_dir: str = os.getenv("TLE_CACHE_DIR", "tle_cache")
    tle_cache_hours: float = float(os.getenv("TLE_CACHE_HOURS", "4.0"))
    
    # External API Endpoints
    usgs_api_url: str = os.getenv("USGS_API_URL", "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson")
    usgs_significant_url: str = os.getenv("USGS_SIGNIFICANT_URL", "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson")
    open_meteo_weather_url: str = os.getenv("OPEN_METEO_WEATHER_URL", "https://api.open-meteo.com/v1/forecast")
    open_meteo_flood_url: str = os.getenv("OPEN_METEO_FLOOD_URL", "https://flood-api.open-meteo.com/v1/flood")
    open_meteo_marine_url: str = os.getenv("OPEN_METEO_MARINE_URL", "https://marine-api.open-meteo.com/v1/marine")
    open_meteo_geocoding_url: str = os.getenv("OPEN_METEO_GEOCODING_URL", "https://geocoding-api.open-meteo.com/v1/search")
    celestrak_api_url: str = os.getenv("CELESTRAK_API_URL", "https://celestrak.org/NORAD/elements/gp.php")
    nasa_eonet_url: str = os.getenv("NASA_EONET_URL", "https://eonet.gsfc.nasa.gov/api/v3/events")
    nasa_firms_url: str = os.getenv("NASA_FIRMS_URL", "https://firms.modaps.eosdis.nasa.gov/api/area/csv")
    nasa_firms_api_key: Optional[str] = os.getenv("NASA_FIRMS_API_KEY", None)
    osm_overpass_url: str = os.getenv("OSM_OVERPASS_URL", "https://overpass-api.de/api/interpreter")
    
    # Operational Mode: 'live', 'hybrid' (live with demo fallback when offline), 'demo'
    operational_mode: str = os.getenv("OPERATIONAL_MODE", "hybrid")
    
    # Cache settings
    weather_cache_seconds: int = int(os.getenv("WEATHER_CACHE_SECONDS", "1800")) # 30 mins
    disaster_cache_seconds: int = int(os.getenv("DISASTER_CACHE_SECONDS", "300")) # 5 mins

settings = Settings()
