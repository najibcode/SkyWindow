# SkyWindow - Satellite Tasking Optimizer

SkyWindow is a professional-grade, user-friendly mission planning console for satellite tasking. It allows users to optimize satellite operations by calculating orbital passes, estimating cloud cover, and scheduling imaging tasks based on power, storage, and weather constraints.

## Features

- **Automated Orbit Calculation:** Uses up-to-date TLE (Two-Line Element) data to predict when satellites will pass over specific target coordinates.
- **Weather Integration:** Integrates with Open-Meteo to fetch hourly cloud cover forecasts, prioritizing optical imagery when skies are clear.
- **Mission Planning Engine:** Automatically builds an optimal imaging schedule constrained by daily pass limits, power availability, and onboard storage.
- **Interactive UI:** A cinematic, professional frontend that supports map-click interaction and automated geocoding.
- **Data Transparency:** All displayed data (TLEs, weather predictions) are traceable, helping educate users on satellite mission planning.

## Architecture

- **Backend:** Python (FastAPI)
- **Frontend:** HTML, CSS, Vanilla JavaScript
- **Database:** SQLite (for logging predictions and calibrations)
- **External APIs:** 
  - [Celestrak](https://celestrak.org/) (for TLEs)
  - [Open-Meteo](https://open-meteo.com/) (for Cloud Cover)

## Setup & Installation

### Prerequisites
- Python 3.8+
- Node.js (Optional, only if using an HTTP server for frontend development)

### 1. Install Backend Dependencies

Navigate to the `backend` directory and install the required Python packages:

```bash
cd backend
pip install -r requirements.txt
```

### 2. Run the Application

The frontend is served directly by the FastAPI backend. Simply run the backend server:

```bash
cd backend
uvicorn main:app --reload
```

Open your browser and navigate to `http://127.0.0.1:8000` to use the application.

## Usage

1. **Select a Satellite:** Choose from the available satellite list.
2. **Add Targets:** Input the target locations (latitude, longitude) you want to task.
3. **Set Constraints:** Adjust the maximum cloud cover, power usage, and storage limits.
4. **Generate Schedule:** Click "Generate Schedule" to compute the optimal mission plan.

## License

This project is licensed under the MIT License.
