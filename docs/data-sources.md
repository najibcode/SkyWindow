# SkyWindow Data Sources & Authoritative Feeds

| Provider | Dataset | Data Type | Update Frequency | License | Attribution |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **NASA EONET v3** | Earth Observatory Natural Event Tracker | Active Wildfires, Cyclones, Typhoons, Volcanoes, Floods | Real-time / NRT | Public Domain (NASA Open Data) | NASA Earth Science Data Systems (ESDS) Program |
| **U.S. Geological Survey (USGS)** | Real-time GeoJSON Earthquake Feed | Seismic Epicenter, Magnitude ($M$), Hypocenter Depth | Real-time (1–5 min) | Public Domain (CC0) | U.S. Geological Survey Earthquake Hazards Program |
| **Open-Meteo & ECMWF** | Global Numerical Weather Prediction (NWP) | Hourly Cloud Cover (0–100%), Precipitation, Wind, Pressure | Hourly | CC BY 4.0 | Open-Meteo Weather API & ECMWF IFS |
| **Copernicus EMS GloFAS** | Global Flood Awareness System | Gridded River Discharge ($m^3/s$) & Return Periods | Daily | Copernicus Open Access | Copernicus Emergency Management Service (GloFAS) |
| **CelesTrak / Space-Track** | NORAD General Perturbations (GP) TLE | SGP4 Keplarian Two-Line Orbital Elements | Every 2–4 hours | Public Orbit Catalog | CelesTrak (Dr. T.S. Kelso) & Space-Track |
| **NASA FIRMS / LANCE** | VIIRS 375m & MODIS 1km Hotspots | Active Fire Thermal Anomalies & Radiative Power (FRP) | Every 3 hours | NASA Open Data Policy | NASA LANCE EOSDIS |
| **OpenStreetMap Foundation** | Overpass API | Critical Infrastructure (Hospitals, Schools, Bridges, Airports, Highways) | Real-time | ODbL | © OpenStreetMap contributors |
| **RainViewer API** | Global Radar & Precipitation Tiles | Live Reflectivity Radar | Every 10 min | RainViewer Free Tier | RainViewer Real-time Weather Radar |

## Zero Fabrication Policy
1. Every dynamic metric originates from an authoritative API endpoint or inspectable mathematical astrodynamics calculation.
2. If an external API is temporarily unreachable, the feed enters `status: DEGRADED` or `status: STALE` with clear lineage timestamps (`observed_at`).
3. The platform displays verifiable provenance for every event, satellite pass, and weather prediction.
