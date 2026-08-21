# Operational Limitations & Scientific Boundaries

SkyWindow operates under strict scientific standards and explicitly communicates operational boundaries:

## 1. No Deterministic Earthquake Prediction
SkyWindow **does not** claim to predict earthquakes deterministically. The platform provides:
- Real-time seismic detection via USGS NEIC
- Hypocentral depth & magnitude classification
- Aftershock statistical recurrence modeling
- Tsunami triggering potential assessment ($M \ge 6.5$, depth $\le 60\text{ km}$)

## 2. Distinction of Modelled Scenarios vs Official Warnings
Any tsunami inundation, storm surge model, or flood depth simulation produced by SkyWindow is strictly labeled:
> `⚠ MODELLED IMPACT SCENARIO — NOT AN OFFICIAL WARNING`
Official disaster declarations remain under the exclusive jurisdiction of national agencies (e.g. INCOIS, NOAA, IMD, USGS, CWC).

## 3. Optical Cloud Obscuration
Optical sensors (Sentinel-2 MSI, Landsat OLI) cannot penetrate dense atmospheric cloud cover or nighttime darkness. SkyWindow automatically enforces:
- Rejection of optical passes when cloud cover exceeds user threshold.
- Automatic routing to Synthetic Aperture Radar (SAR) for monsoon, cyclone, and flood imaging.

## 4. InSAR Coherence Limits
Interferometric SAR (InSAR) surface displacement mapping requires phase coherence between passes. In heavily vegetated or flooded regions, temporal decorrelation can limit millimeter-accuracy ground deformation measurements.
