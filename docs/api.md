# SkyWindow REST API Reference

Base URL: `http://localhost:8000/api`

## 1. Satellites & Orbits
- `GET /api/satellites`: Lists all operational satellites with sensor payload metadata.
- `GET /api/satellites/{id}`: Detailed specifications for a specific NORAD ID.
- `GET /api/track?satellite_id={id}`: Returns SGP4 ground track coordinates and current subpoint.
- `GET /api/satellites/{id}/passes?lat={lat}&lon={lon}`: Computes upcoming passes over ground coordinates.

## 2. Disasters & Risk
- `GET /api/disasters`: Lists active disaster events (supports `?category=` and `?severity=` filters).
- `GET /api/disasters/{id}`: Detailed incident briefing and timeline for a disaster.
- `GET /api/disasters/summary`: Aggregated dashboard metrics.
- `GET /api/disasters/geojson`: Full GeoJSON FeatureCollection of disaster geometries.

## 3. Weather & Hydrology
- `GET /api/weather/forecast?lat={lat}&lon={lon}`: High-resolution hourly NWP meteorological forecast.
- `GET /api/weather/cloud-cover?lat={lat}&lon={lon}`: Hourly cloud cover percentage dictionary.
- `GET /api/weather/river-discharge?lat={lat}&lon={lon}`: GloFAS 7-day river discharge forecast ($m^3/s$).

## 4. Tasking & Scheduling
- `POST /api/schedule` (or `POST /api/tasking/optimize`): Generates optimal camera schedule with capacity impact stats.
- `POST /api/tasking/constellation`: Coordinates synchronized multi-satellite observation campaign.
- `GET /api/tasking/queue`: Ranked Earth observation queue across active disasters.
- `POST /api/tasking/nlp`: Converts natural language mission instructions into structured tasking parameters.

## 5. Change Detection & AI
- `POST /api/change-detection`: Computes multi-temporal surface area delta, percentage expansion, and status.
- `POST /api/analyst/query`: Grounded AI Disaster Analyst evidence-based answers.

## 6. Alerts & Reports
- `GET /api/alerts`: Real-time evaluated alert stream.
- `GET /api/alerts/rules` & `POST /api/alerts/rules`: Manage monitoring rules.
- `POST /api/reports/generate/{disaster_id}`: Synthesizes formal incident intelligence report.
- `GET /api/health`: Real-time provider health, latencies, and license attributions.
