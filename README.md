# SkyWindow: Satellite Tasking & Global Hazard Watch 

SkyWindow is a professional-grade, multi-faceted mission planning console. It combines a highly optimized **Satellite Tasking Optimizer** with a live, real-time **Global Hazard Watch** dashboard. Designed to simulate the complexities of earth-observation satellite operations, the platform intelligently schedules satellite passes over prioritized targets based on orbital mechanics, weather conditions, and satellite hardware constraints, while seamlessly integrating emergency tasking from live disaster feeds.

---

##  Features

### 1. Global Hazard Watch (Live Disaster Monitoring)
A real-time, multi-hazard natural disaster monitor covering worldwide events.
- **Earthquakes:** Live seismic data (USGS GeoJSON).
- **Multi-Hazard:** Floods, Tropical Cyclones, Volcanoes, and Droughts (GDACS RSS/GeoJSON).
- **Wildfires:** Real-time VIIRS active fire data (NASA FIRMS).
- **Landslide Risk Proxy:** Combines live Open-Meteo rainfall intensity with known static susceptibility zones (e.g., Himalayas, Andes).
- **Emergency Tasking Integration:** One-click functionality to instantly push a detected hazard to the Mission Planner as a Maximum Priority (Priority 10) emergency target.

### 2. Satellite Mission Planner (SGP4 Orbital Optimizer)
Simulates satellite orbital mechanics and schedules imaging passes.
- **Orbital Propagation:** Uses `skyfield` and SGP4 to calculate accurate satellite ground tracks and field-of-view footprints based on live TLE (Two-Line Element) data from CelesTrak.
- **Weather Constraint Checking:** Automatically fetches live cloud-cover forecasts via the Open-Meteo API. If a target is obscured by clouds (>70%), the scheduler drops the pass to save power.
- **Knapsack Optimization:** Uses a greedy knapsack algorithm to maximize the total priority of captured targets within the strict bounds of:
  - Max passes per day (Thermal limit)
  - Power budget (Watts)
  - Storage budget (GB)
- **Automated Geocoding:** Type a city name (e.g., "Paris") into the search box, and it will automatically resolve the exact coordinates via the OpenStreetMap Nominatim API, panning the map directly to the location.

---

##  Architecture Stack

- **Backend:** Python (FastAPI, Uvicorn)
  - `sgp4`, `skyfield` for orbital physics.
  - Custom heuristic optimization logic.
- **Frontend:** React, TypeScript, Vite
  - Styled with **Tailwind CSS** and **shadcn/ui** for a cinematic, professional Bklit-inspired UI.
  - Interactive maps via **Leaflet / React-Leaflet** using ArcGIS dark base layers.
  - Analytics visualization using **Recharts**.
  - Smooth UI animations via **Framer Motion**.

---

## Installation & Setup

### Prerequisites
- **Python 3.8+**
- **Node.js 18+**

### 1. Backend Setup
Navigate to the `backend` directory, install the Python dependencies, and start the FastAPI server:

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8001
```

*The backend API will be available at `http://127.0.0.1:8001`.*

### 2. Frontend Setup
Open a new terminal window, navigate to the `frontend` directory, install the Node packages, and start the Vite dev server:

```bash
cd frontend
npm install
npm run dev
```

*Vite will automatically proxy `/api` requests to the backend. Open your browser and navigate to `http://127.0.0.1:5173` (or the port Vite specifies).*

---

##  How to Use

1. **Mission Planning:**
   - Select a satellite (e.g., ISS) from the dropdown.
   - Add targets by clicking on the map, OR by typing a location name in the "Search Location" box.
   - Click "Generate Schedule". The backend will compute the orbital path, check the weather, apply the constraints, and return the optimized imaging schedule.
2. **Global Hazard Watch:**
   - Switch to the "Global Hazard Watch" tab.
   - Filter active disasters by severity or type using the switches.
   - Click on any hazard marker on the map to view live details.
   - Click **"+ ADD AS EMERGENCY IMAGING TARGET"** to instantly inject the hazard into your Mission Planner's active target list for immediate satellite tasking.

---

*Project configured and migrated to React for Naresh (`naresh-py`).*
