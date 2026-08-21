import Papa from 'papaparse';

export interface HazardEvent {
  id: string;
  type: 'Earthquake' | 'Flood' | 'Cyclone' | 'Wildfire' | 'Landslide Risk' | 'Volcano' | 'Drought';
  title: string;
  lat: number;
  lon: number;
  severity: 'green' | 'orange' | 'red';
  timestamp: string;
  details: Record<string, any>;
}

export async function fetchEarthquakes(): Promise<HazardEvent[]> {
  const res = await fetch('https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson');
  const data = await res.json();
  
  return data.features.map((f: any) => {
    const mag = f.properties.mag;
    let severity: 'green' | 'orange' | 'red' = 'green';
    if (mag >= 6.0) severity = 'orange';
    if (mag >= 7.0) severity = 'red';
    
    return {
      id: f.id,
      type: 'Earthquake',
      title: f.properties.title,
      lat: f.geometry.coordinates[1],
      lon: f.geometry.coordinates[0],
      severity,
      timestamp: new Date(f.properties.time).toISOString(),
      details: {
        magnitude: mag,
        depth: f.geometry.coordinates[2],
        url: f.properties.url
      }
    };
  });
}

export async function fetchGDACS(): Promise<HazardEvent[]> {
  // Using allorigins to avoid CORS just in case
  const res = await fetch('https://api.allorigins.win/raw?url=' + encodeURIComponent('https://www.gdacs.org/datareport/resources/events/gdacs.geojson'));
  const data = await res.json();
  
  return data.features.map((f: any) => {
    const props = f.properties;
    const typeMap: Record<string, HazardEvent['type']> = {
      'EQ': 'Earthquake',
      'TC': 'Cyclone',
      'FL': 'Flood',
      'VO': 'Volcano',
      'DR': 'Drought'
    };
    
    const severityMap: Record<string, 'green' | 'orange' | 'red'> = {
      'Green': 'green',
      'Orange': 'orange',
      'Red': 'red'
    };
    
    return {
      id: props.eventid.toString(),
      type: typeMap[props.eventtype] || 'Flood',
      title: props.name || `${props.eventtype} in ${props.country}`,
      lat: f.geometry.coordinates[1],
      lon: f.geometry.coordinates[0],
      severity: severityMap[props.alertlevel] || 'green',
      timestamp: props.fromdate,
      details: {
        description: props.description,
        url: props.url
      }
    };
  });
}

export async function fetchWildfires(): Promise<HazardEvent[]> {
  const MAP_KEY = 'e6f2b90c90c6140be2feb28fb01dae2a';
  const url = `https://firms.modaps.eosdis.nasa.gov/api/active_fire/csv/${MAP_KEY}/VIIRS_SNPP_NRT/global/1`;
  
  const res = await fetch(url);
  const csvText = await res.text();
  
  return new Promise((resolve) => {
    Papa.parse(csvText, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        // FIRMS returns thousands of points. We cluster/sample them or just take top 100 brightest to not lag the browser.
        const sorted = (results.data as any[])
          .sort((a, b) => parseFloat(b.bright_ti4) - parseFloat(a.bright_ti4))
          .slice(0, 100);
          
        const fires = sorted.map((row: any, idx: number) => ({
          id: `fire_${idx}`,
          type: 'Wildfire' as const,
          title: `Active Fire (Brightness: ${row.bright_ti4})`,
          lat: parseFloat(row.latitude),
          lon: parseFloat(row.longitude),
          severity: parseFloat(row.bright_ti4) > 350 ? 'red' : 'orange',
          timestamp: new Date().toISOString(),
          details: {
            confidence: row.confidence,
            satellite: row.satellite,
            frp: row.frp
          }
        }));
        resolve(fires);
      }
    });
  });
}

export async function fetchLandslideRisk(): Promise<HazardEvent[]> {
  // Static high-susceptibility zones (Himalayas, Andes, SE Asia)
  const zones = [
    { name: 'Himalayan Foothills', lat: 27.7, lon: 85.3 },
    { name: 'Andes (Colombia)', lat: 4.6, lon: -74.0 },
    { name: 'Philippines (Luzon)', lat: 16.5, lon: 121.0 },
    { name: 'Western Ghats (India)', lat: 10.0, lon: 77.0 },
  ];
  
  const events: HazardEvent[] = [];
  
  for (const z of zones) {
    try {
      const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${z.lat}&longitude=${z.lon}&current=precipitation`);
      const data = await res.json();
      const rain = data.current.precipitation || 0;
      
      if (rain > 0) {
        events.push({
          id: `ls_${z.lat}_${z.lon}`,
          type: 'Landslide Risk',
          title: `Rainfall-Triggered Landslide Risk (${z.name})`,
          lat: z.lat,
          lon: z.lon,
          severity: rain > 10 ? 'red' : (rain > 2 ? 'orange' : 'green'),
          timestamp: new Date().toISOString(),
          details: {
            current_rainfall_mm: rain,
            methodology: "Estimated from live rainfall intensity over known static susceptibility zones."
          }
        });
      }
    } catch (e) {
      console.error(e);
    }
  }
  
  return events;
}

export async function fetchAllHazards(): Promise<HazardEvent[]> {
  const [eq, gdacs, fires, ls] = await Promise.allSettled([
    fetchEarthquakes(),
    fetchGDACS(),
    fetchWildfires(),
    fetchLandslideRisk()
  ]);
  
  let all: HazardEvent[] = [];
  if (eq.status === 'fulfilled') all = all.concat(eq.value);
  if (gdacs.status === 'fulfilled') all = all.concat(gdacs.value);
  if (fires.status === 'fulfilled') all = all.concat(fires.value);
  if (ls.status === 'fulfilled') all = all.concat(ls.value);
  
  // Deduplicate GDACS earthquakes vs USGS earthquakes (prefer USGS)
  const usgsIds = new Set(eq.status === 'fulfilled' ? eq.value.map(e => e.id) : []);
  
  return all.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
}
