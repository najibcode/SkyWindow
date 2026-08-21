# Disaster Intelligence & Risk Engine

SkyWindow processes multi-hazard intelligence across six major categories:

## 1. Hydrological (Floods & River Runoff)
- **Inputs:** GloFAS 7-day river discharge forecast, Open-Meteo precipitation anomaly, Sentinel-1 SAR dual-polarization water masks.
- **Outputs:** Inundated surface area ($\text{km}^2$), expansion delta vs pre-monsoon baseline, exposed infrastructure assets (hospitals, schools, road networks).
- **Sensor:** Synthetic Aperture Radar (SAR) is prioritized to bypass monsoon cloud obscuration.

## 2. Geological (Earthquakes, Landslides, Volcanoes)
- **Inputs:** USGS NEIC moment magnitude ($M$), focal depth (km), distance to coast, NASA LHASA 2.0 precipitation-slope stability index, Smithsonian GVP thermal unrest feeds.
- **Outputs:** Impact radius, aftershock risk, tsunami trigger potential ($M \ge 6.5$, depth $\le 60\text{ km}$), slope coherence loss.
- **Sensor:** InSAR for sub-centimeter surface deformation; High-resolution Optical for surface rupture mapping.

## 3. Oceanic (Tsunamis & Storm Surges)
- **Inputs:** Deep-water hydrodynamic shallow-water wave equation $v = \sqrt{g \cdot d}$, official NOAA/INCOIS tsunami bulletins, coastal bathymetric run-up.
- **Policy:** Explicitly marks simulated run-up as `MODELLED IMPACT SCENARIO — NOT AN OFFICIAL WARNING`.

## 4. Meteorological (Tropical Cyclones, Heatwaves, Droughts)
- **Inputs:** Dvorak satellite intensity estimation, track forecast coordinates, ERA5 maximum daytime temperature anomalies, SPI-3 standardized precipitation indices.
- **Outputs:** Gale-force wind radii ($>120\text{ km/h}$), track projection cone, urban heat island LST maps.

## 5. Environmental (Wildfires & Deforestation)
- **Inputs:** NASA VIIRS 375m & MODIS 1km active fire hotspots, Fire Radiative Power (MW), Normalized Burn Ratio (NBR).
- **Outputs:** Active fire perimeters, expansion fronts, smoke dispersion corridors.
- **Sensor:** Thermal Infrared (TIRS) and SWIR band differencing.

## 6. Explainable Risk Framework
$$R = \text{Hazard } (40\%) + \text{Demographic Exposure } (35\%) + \text{Vulnerability } (25\%)$$
Every risk score exposes its exact parameter weights and uncertainty bounds.
