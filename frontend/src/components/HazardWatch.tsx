import React, { useEffect, useState, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { fetchAllHazards, type HazardEvent } from '../lib/hazardApi';
import { useTargetStore } from '../store';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';

function ChangeView({ center }: { center: [number, number] }) {
  const map = useMap();
  map.setView(center, 6);
  return null;
}

export default function HazardWatch() {
  const [events, setEvents] = useState<HazardEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<Record<string, boolean>>({
    Earthquake: true, Flood: true, Cyclone: true, Wildfire: true, 'Landslide Risk': true, Volcano: true, Drought: true
  });
  const [severityFilter, setSeverityFilter] = useState({ red: true, orange: true, green: true });
  const [selectedEvent, setSelectedEvent] = useState<HazardEvent | null>(null);
  const [mapCenter, setMapCenter] = useState<[number, number] | null>(null);

  const { addTarget } = useTargetStore();

  const loadData = async () => {
    setLoading(true);
    const data = await fetchAllHazards();
    setEvents(data);
    setLoading(false);
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5 * 60 * 1000); // live refresh 5m
    return () => clearInterval(interval);
  }, []);

  const filteredEvents = useMemo(() => {
    return events.filter(e => filters[e.type] && severityFilter[e.severity]);
  }, [events, filters, severityFilter]);

  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    events.forEach(e => {
      counts[e.type] = (counts[e.type] || 0) + 1;
    });
    return Object.entries(counts).map(([name, count]) => ({ name, count }));
  }, [events]);

  const getMarkerIcon = (type: string, severity: string) => {
    const colors = { red: '#ef4444', orange: '#f97316', green: '#10b981' };
    const color = colors[severity as keyof typeof colors] || '#666';
    return L.divIcon({
      className: 'custom-icon',
      html: `<div style="background:${color};width:14px;height:14px;border-radius:50%;border:2px solid #fff;box-shadow: 0 0 10px ${color};"></div>`,
      iconSize: [14, 14],
      iconAnchor: [7, 7]
    });
  };

  const handleAddEmergencyTarget = () => {
    if (!selectedEvent) return;
    addTarget({
      name: `EMG: ${selectedEvent.title.substring(0, 10).toUpperCase()}`,
      lat: selectedEvent.lat,
      lon: selectedEvent.lon,
      weight: 10 // Max priority
    });
    alert("Emergency Target Added to Mission Planner!");
  };

  const handleExport = () => {
    const json = JSON.stringify(filteredEvents, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `hazard_export_${Date.now()}.json`;
    a.click();
  };

  return (
    <div className="flex h-full w-full gap-6">
      {/* Left Sidebar */}
      <div className="w-[350px] flex flex-col gap-4 overflow-y-auto pr-2">
        <Card className="border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Filter & Controls</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-col gap-2 text-sm">
              <Label className="text-muted-foreground mb-1">Hazard Types</Label>
              {Object.keys(filters).map(type => (
                <div key={type} className="flex items-center justify-between">
                  <span>{type}</span>
                  <Switch 
                    checked={filters[type]} 
                    onCheckedChange={(c) => setFilters(prev => ({...prev, [type]: c}))}
                  />
                </div>
              ))}
            </div>
            
            <div className="flex flex-col gap-2 text-sm mt-2">
              <Label className="text-muted-foreground mb-1">Severity Levels</Label>
              {['red', 'orange', 'green'].map(sev => (
                <div key={sev} className="flex items-center justify-between capitalize">
                  <span className={`text-${sev === 'red' ? 'red-500' : sev === 'orange' ? 'orange-500' : 'emerald-500'}`}>{sev}</span>
                  <Switch 
                    checked={(severityFilter as any)[sev]} 
                    onCheckedChange={(c) => setSeverityFilter(prev => ({...prev, [sev]: c}))}
                  />
                </div>
              ))}
            </div>

            <Button variant="outline" size="sm" onClick={loadData} disabled={loading}>
              {loading ? 'Refetching...' : 'Force Refresh Feed'}
            </Button>
            <Button variant="secondary" size="sm" onClick={handleExport}>
              Export Current Snapshot (JSON)
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Active Events Trend</CardTitle>
          </CardHeader>
          <CardContent className="h-[200px] w-full p-0 px-2 pb-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={typeCounts} margin={{top: 10, right: 10, left: -20, bottom: 0}}>
                <XAxis dataKey="name" tick={{fontSize: 10}} interval={0} angle={-30} textAnchor="end" />
                <YAxis tick={{fontSize: 10}} />
                <Tooltip contentStyle={{backgroundColor: '#09090b', borderColor: '#27272a'}} />
                <Bar dataKey="count" fill="#fafafa" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Main Map */}
      <div className="flex-1 relative rounded-lg border border-border overflow-hidden bg-[#09090b]">
        <div className="absolute top-4 left-4 z-[1000] bg-background/80 backdrop-blur border border-border p-3 rounded-lg flex gap-4">
          <div className="text-sm font-mono flex flex-col">
            <span className="text-muted-foreground">TOTAL ACTIVE</span>
            <span className="text-2xl font-bold">{filteredEvents.length}</span>
          </div>
          <div className="text-xs text-muted-foreground flex flex-col justify-end">
            LIVE UPDATING<br/>
            {events.length === 0 && loading ? 'FETCHING DATA...' : 'DATA SOURCED'}
          </div>
        </div>

        <MapContainer center={[20, 0]} zoom={2} style={{ height: '100%', width: '100%', minHeight: '500px' }} zoomControl={false}>
          <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}" />
          {mapCenter && <ChangeView center={mapCenter} />}
          
          {filteredEvents.map(ev => (
            <Marker 
              key={ev.id} 
              position={[ev.lat, ev.lon]} 
              icon={getMarkerIcon(ev.type, ev.severity)}
              eventHandlers={{ click: () => setSelectedEvent(ev) }}
            />
          ))}
        </MapContainer>

        {/* Detail Panel */}
        <AnimatePresence>
          {selectedEvent && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="absolute bottom-4 right-4 z-[1000] w-[350px]"
            >
              <Card className="bklit-glass border-border/50 shadow-xl">
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-start">
                    <Badge variant="outline" className={
                      selectedEvent.severity === 'red' ? 'text-red-500 border-red-500/50' : 
                      selectedEvent.severity === 'orange' ? 'text-orange-500 border-orange-500/50' : 'text-emerald-500 border-emerald-500/50'
                    }>
                      {selectedEvent.type.toUpperCase()}
                    </Badge>
                    <button onClick={() => setSelectedEvent(null)} className="text-muted-foreground hover:text-foreground">×</button>
                  </div>
                  <CardTitle className="text-lg leading-tight mt-2">{selectedEvent.title}</CardTitle>
                  <div className="text-xs text-muted-foreground font-mono mt-1">
                    {new Date(selectedEvent.timestamp).toLocaleString()}
                  </div>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[120px] mb-4 text-sm bg-muted/50 p-3 rounded-md">
                    {Object.entries(selectedEvent.details).map(([k, v]) => (
                      <div key={k} className="mb-1">
                        <span className="text-muted-foreground capitalize">{k}: </span>
                        <span className="font-medium break-words">{v}</span>
                      </div>
                    ))}
                  </ScrollArea>
                  <Button className="w-full bg-red-900 hover:bg-red-800 text-white" onClick={handleAddEmergencyTarget}>
                    + ADD AS EMERGENCY IMAGING TARGET
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
