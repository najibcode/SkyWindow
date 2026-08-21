import os
import time
import httpx

CACHE_DIR = "tle_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_DURATION_SECONDS = 4 * 3600  # 4 hours

# Popular EO satellites + ISS with metadata
SATELLITES = {
    "ISS": {"id": 25544, "type": "Space Station", "desc": "International Space Station. Has optical cameras but mostly for human spaceflight. Low inclination orbit.", "revisit": "Multiple per day", "recommended_capacity": 5},
    "LANDSAT 8": {"id": 39084, "type": "Optical", "desc": "NASA/USGS optical Earth observation. Cannot see through clouds. Great for land use, agriculture.", "revisit": "16 days", "recommended_capacity": 2},
    "LANDSAT 9": {"id": 49260, "type": "Optical", "desc": "Sister to Landsat 8, high-res optical imaging.", "revisit": "16 days", "recommended_capacity": 2},
    "SENTINEL-1A": {"id": 39634, "type": "SAR (Radar)", "desc": "ESA Synthetic Aperture Radar. CAN see through clouds and at night. Weather does not affect it as much.", "revisit": "12 days", "recommended_capacity": 3},
    "SENTINEL-2A": {"id": 40697, "type": "Optical", "desc": "ESA high-res optical. Good for vegetation. Needs clear skies.", "revisit": "5 days", "recommended_capacity": 3},
    "TERRA": {"id": 25994, "type": "Optical/Thermal", "desc": "NASA flagship Earth observing satellite (MODIS).", "revisit": "1-2 days", "recommended_capacity": 4},
    "AQUA": {"id": 27424, "type": "Microwave/Optical", "desc": "NASA satellite focusing on water cycle. Has instruments that can penetrate clouds.", "revisit": "1-2 days", "recommended_capacity": 4}
}

async def fetch_tle(norad_id: int) -> tuple[str, str, str, float]:
    """Fetches TLE from Celestrak. Returns (name, line1, line2, age_in_hours)."""
    cache_file = os.path.join(CACHE_DIR, f"{norad_id}.txt")
    
    # Check cache
    if os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        if time.time() - mtime < CACHE_DURATION_SECONDS:
            with open(cache_file, "r") as f:
                lines = f.read().strip().split("\n")
                if len(lines) == 3:
                    return lines[0].strip(), lines[1].strip(), lines[2].strip(), (time.time() - mtime)/3600
    
    # Fetch from Celestrak
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=tle"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        text = response.text.strip()
        lines = text.split("\n")
        if len(lines) == 3:
            with open(cache_file, "w") as f:
                f.write(text)
            return lines[0].strip(), lines[1].strip(), lines[2].strip(), 0.0
        else:
            raise ValueError(f"Invalid TLE format received for {norad_id}:\n{text}")

def get_satellite_list():
    return [{"name": name, **data} for name, data in SATELLITES.items()]
