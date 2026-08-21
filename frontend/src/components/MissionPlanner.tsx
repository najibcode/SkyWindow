import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMapEvents, useMap } from 'react-leaflet';
import { useTargetStore } from '../store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

function MapClickHandler({ setClickPos }: { setClickPos: (pos: [number, number]) => void }) {
  useMapEvents({
    click(e) {
      setClickPos([e.latlng.lat, e.latlng.lng]);
    },
  });
  return null;
}

function ChangeView({ center }: { center: [number, number] | null }) {
  const map = useMap();
  if (center) {
    map.flyTo(center, 10);
  }
  return null;
}

export default function MissionPlanner() {
  const { targets, addTarget, removeTarget } = useTargetStore();
  const [satellites, setSatellites] = useState<any[]>([]);
  const [selectedSat, setSelectedSat] = useState<string>('');
  const [track, setTrack] = useState<any[]>([]);
  const [schedule, setSchedule] = useState<any>(null);

  const [clickPos, setClickPos] = useState<[number, number] | null>(null);
  const [tgtName, setTgtName] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [tgtWeight, setTgtWeight] = useState(5);

  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch('/api/satellites').then(r => r.json()).then(data => {
      setSatellites(data);
      if (data.length > 0) setSelectedSat(data[0].id.toString());
    });
  }, []);

  useEffect(() => {
    if (!selectedSat) return;
    fetch(`/api/track?satellite_id=${selectedSat}`).then(r => r.json()).then(data => {
      setTrack(data.track);
    });
  }, [selectedSat]);

  const handleAdd = () => {
    if (!clickPos) return alert("Click map first to select coordinates");
    addTarget({
      name: tgtName || `TGT-${targets.length + 1}`,
      lat: clickPos[0],
      lon: clickPos[1],
      weight: tgtWeight
    });
    setTgtName('');
    setSearchQuery('');
  };

  const handleSearch = async () => {
    if (!searchQuery) return;
    try {
      const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}`);
      const data = await res.json();
      if (data && data.length > 0) {
        setClickPos([parseFloat(data[0].lat), parseFloat(data[0].lon)]);
        setTgtName(data[0].display_name.split(',')[0]);
      } else {
        alert("Location not found");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCompute = async () => {
    if (targets.length === 0) return alert("Add targets first");
    setLoading(true);
    try {
      const res = await fetch('/api/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          satellite_id: parseInt(selectedSat),
          targets,
          max_passes_per_day: 5,
          max_cloud_cover: 70,
          power_per_pass: 150,
          storage_per_pass: 12
        })
      });
      const data = await res.json();
      setSchedule(data);
    } catch (e) {
      alert("Error computing schedule");
    } finally {
      setLoading(false);
    }
  };

  const polylineCoords = track.map(p => [p.lat, p.lon] as [number, number]);

  return (
    <div className="flex h-full w-full gap-6">
      {/* Sidebar Controls */}
      <div className="w-1/3 flex flex-col gap-6 overflow-y-auto pr-2">
        <Card>
          <CardHeader>
            <CardTitle>Platform & Targets</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label>Select Satellite</Label>
              <select 
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                value={selectedSat} 
                onChange={(e) => setSelectedSat(e.target.value)}
              >
                {satellites.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>

            <div className="flex flex-col gap-2 mt-4">
              <Label>Search Location (Geocoding)</Label>
              <div className="flex gap-2">
                <Input 
                  placeholder="e.g. Paris, Tokyo" 
                  value={searchQuery} 
                  onChange={e => setSearchQuery(e.target.value)} 
                  onKeyDown={e => e.key === 'Enter' && handleSearch()} 
                />
                <Button onClick={handleSearch} variant="secondary">Find</Button>
              </div>
            </div>

            <div className="flex flex-col gap-2 mt-4">
              <Label>Add New Target (Click map or search above)</Label>
              <div className="flex gap-2">
                <Input placeholder="LAT" value={clickPos ? clickPos[0].toFixed(4) : ''} readOnly />
                <Input placeholder="LON" value={clickPos ? clickPos[1].toFixed(4) : ''} readOnly />
              </div>
              <div className="flex gap-2">
                <Input placeholder="Target Name" value={tgtName} onChange={e => setTgtName(e.target.value)} />
                <Input type="number" placeholder="Priority (1-10)" value={tgtWeight} onChange={e => setTgtWeight(parseInt(e.target.value))} />
              </div>
              <Button onClick={handleAdd}>Append Target</Button>
            </div>

            <div className="flex flex-col gap-2 mt-4">
              <Label>Active Targets</Label>
              {targets.map(t => (
                <div key={t.id} className="flex justify-between items-center bg-muted p-2 rounded text-xs font-mono">
                  <span>{t.name} (PRI: {t.weight})</span>
                  <Button variant="ghost" size="sm" onClick={() => removeTarget(t.id)}>X</Button>
                </div>
              ))}
            </div>

            <Button onClick={handleCompute} disabled={loading} className="w-full mt-4">
              {loading ? "Computing..." : "Generate Schedule"}
            </Button>
          </CardContent>
        </Card>

        {schedule && (
          <Card>
            <CardHeader>
              <CardTitle>Schedule Results</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm font-mono flex flex-col gap-2">
                <div>Naive Passes: {schedule.stats.naive_cloudy_passes}</div>
                <div>Optimized: {schedule.stats.optimal_cloudy_passes}</div>
                <div>Saved: {schedule.stats.saved_passes}</div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Main Map */}
      <div className="w-2/3 h-full min-h-[500px] border border-border rounded-lg overflow-hidden relative">
        <MapContainer center={[20, 0]} zoom={2} style={{ height: '100%', width: '100%', minHeight: '500px' }}>
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          />
          <TileLayer
            url="https://tilecache.rainviewer.com/v2/radar/past_0/256/{z}/{x}/{y}/2/1_1.png"
            opacity={0.6}
          />
          <MapClickHandler setClickPos={setClickPos} />
          <ChangeView center={clickPos} />
          
          {clickPos && (
             <Marker position={clickPos}>
               <Popup>New Target</Popup>
             </Marker>
          )}

          {targets.map(t => (
            <Marker key={t.id} position={[t.lat, t.lon]}>
              <Popup>{t.name}</Popup>
            </Marker>
          ))}

          {polylineCoords.length > 0 && (
            <Polyline positions={polylineCoords} color="rgba(248, 113, 113, 0.8)" weight={2} dashArray="5, 5" />
          )}
        </MapContainer>
      </div>
    </div>
  );
}
