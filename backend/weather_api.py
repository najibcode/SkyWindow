import httpx
from datetime import datetime

async def get_cloud_cover_forecast(lat: float, lon: float) -> dict:
    """
    Fetches hourly cloud cover forecast from Open-Meteo for the next 7 days.
    Returns a dict mapping ISO hourly timestamps (e.g., '2023-10-12T14:00') to cloud cover %.
    """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=cloudcover&timezone=UTC"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        
        times = data['hourly']['time']
        cloudcovers = data['hourly']['cloudcover']
        
        forecast = {}
        for t, cc in zip(times, cloudcovers):
            forecast[t] = cc
        return forecast

def get_cloud_cover_at_time(forecast: dict, pass_time_iso: str) -> float:
    """
    Extracts the cloud cover % closest to the pass time.
    pass_time_iso is expected to be a full ISO 8601 string like '2026-08-21T14:15:22+00:00'.
    """
    try:
        # Parse the pass time
        pt = datetime.fromisoformat(pass_time_iso)
        # Round to nearest hour
        if pt.minute >= 30:
            from datetime import timedelta
            pt = pt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        else:
            pt = pt.replace(minute=0, second=0, microsecond=0)
            
        # Open-Meteo uses 'YYYY-MM-DDTHH:00' format in UTC without timezone info
        target_time_str = pt.strftime('%Y-%m-%dT%H:00')
        return forecast.get(target_time_str, None)
    except Exception as e:
        return None
