# SkyWindow Architecture Overview

SkyWindow is an **AI-Powered Earth Observation & Multi-Disaster Intelligence Platform** integrating satellite astrodynamics, space-agency telemetry, and meteorological forecasting to automate disaster detection, risk scoring, and sensor-aware satellite tasking.

```
                    SKYWINDOW
                        │
        ┌───────────────┴────────────────┐
        │                                │
 SATELLITE INTELLIGENCE          DISASTER INTELLIGENCE
        │                                │
  Satellite Catalog                 Event Ingestion (USGS, GloFAS, FIRMS)
  SGP4 TLE Orbit Engine             Explainable Risk Engine (H x E x V)
  Pass Prediction                   Atmospheric NWP Weather
  Sensor-Aware Tasking              Multi-Temporal Change Detection
        │                                │
        └───────────────┬────────────────┘
                        │
                  GEOINT ENGINE
                        │
        ┌───────────────┼────────────────┐
        │               │                │
Interactive Maps    AI Analyst     Alert Engine
(Leaflet/Radar)     (Grounded)     (Rules/Watchlists)
        │               │                │
        └───────────────┴────────────────┘
                        │
                 DECISION ENGINE
                        │
        ┌───────────────┼────────────────┐
        │               │                │
Executive Reports   Mission Tasks   Data Health
(PDF/JSON/CSV)     (Constellation) (Provenance)
```

## Architectural Pillars

### 1. Zero Hardcoded Live Data Rule
Every dynamic number displayed by SkyWindow originates from an authoritative API (USGS, Open-Meteo, GloFAS, CelesTrak, NASA FIRMS, OpenStreetMap) or a mathematical/geospatial calculation. No fabricated numbers.

### 2. Data Provenance & Lineage
Every API response carries a `DataProvenance` payload recording:
- `provider`
- `dataset`
- `endpoint`
- `observed_at` (ISO timestamp)
- `retrieved_at` (ISO timestamp)
- `status` (`LIVE`, `STALE`, `OFFLINE`)
- `data_quality` (`HIGH`, `MODELLED`)
- `methodology`
- `attribution`

### 3. Sensor-Aware Astrodynamics Scheduler
Upgraded from a naive first-come scheduler to a multi-variable objective optimizer:
$$\text{Task Score} = (100 - \text{Effective Cloud Cover}) \times \text{Target Weight} \times \text{Elevation Weight} \times \text{Sensor Suitability}$$
- **SAR (Radar):** Effective cloud cover = 0% (weather independent, penetrating clouds, rain, and darkness). High suitability for flood, cyclone, deformation.
- **Optical (Multispectral):** Heavily degraded when cloud cover > 50%. High suitability for vegetation (NDVI) and clear-sky damage assessment.
- **Thermal Infrared:** High suitability for active wildfire fronts and volcanic unrest.
