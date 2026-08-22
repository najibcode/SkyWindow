const API_BASE = '/api';

// Global state
let map, taskMap;
let disasterMarkers = [];
let disasterPolygons = [];
let trackLayer, taskTrackLayer;
let allDisasters = [];
let activeDisaster = null;
let satelliteList = [];
let targets = [];
let currentSchedule = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initClock();
    initNavigation();
    initMaps();
    fetchSatellites();
    fetchDisasters();
    fetchSummaryStats();
    fetchAlerts();
    fetchHealth();
    bindEvents();
});

function initClock() {
    setInterval(() => {
        const now = new Date();
        document.getElementById('clock').innerText = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
    }, 1000);
}

function initNavigation() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const viewId = tab.getAttribute('data-view');
            document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
            const targetPanel = document.getElementById(viewId);
            if (targetPanel) {
                targetPanel.classList.add('active');
            }

            // Invalidate Leaflet map size on tab switch
            setTimeout(() => {
                if (map) map.invalidateSize();
                if (taskMap) taskMap.invalidateSize();
            }, 100);

            // Lazy load specific view content
            if (viewId === 'view-disasters') renderDisasterCatalog();
            if (viewId === 'view-health') fetchHealth();
            if (viewId === 'view-alerts') { fetchAlerts(); fetchAlertRules(); }
            if (viewId === 'view-reports') populateReportDropdown();
            if (viewId === 'view-change') populateChangeDetectionDropdown();
            if (viewId === 'view-tasking' && !taskTrackLayer) updateTrack(true);
        });
    });
}

function initMaps() {
    // 1. Main Operations Map (Hardware-accelerated Canvas rendering)
    map = L.map('map', { zoomControl: true, attributionControl: false, preferCanvas: true }).setView([18, 78], 3);
    
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 17
    }).addTo(map);

    const radarLayer = L.tileLayer('https://tilecache.rainviewer.com/v2/radar/past_0/256/{z}/{x}/{y}/2/1_1.png', {
        maxZoom: 17, opacity: 0.55
    });
    if (document.getElementById('chk-layer-radar').checked) {
        radarLayer.addTo(map);
    }

    document.getElementById('chk-layer-radar').addEventListener('change', (e) => {
        if (e.target.checked) map.addLayer(radarLayer);
        else map.removeLayer(radarLayer);
    });

    map.on('mousemove', (e) => {
        document.getElementById('map-cursor-coords').innerText = `LAT: ${e.latlng.lat.toFixed(4)} | LON: ${e.latlng.lng.toFixed(4)}`;
    });

    map.on('click', (e) => {
        document.getElementById('target-lat').value = e.latlng.lat.toFixed(4);
        document.getElementById('target-lon').value = e.latlng.lng.toFixed(4);
    });

    // 2. Tasking Map (Hardware-accelerated Canvas rendering)
    taskMap = L.map('task-map', { zoomControl: true, attributionControl: false, preferCanvas: true }).setView([18, 78], 3);
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 17
    }).addTo(taskMap);
}

function bindEvents() {
    // Search feed
    document.getElementById('feed-search').addEventListener('input', filterFeed);
    const sevFilter = document.getElementById('disaster-filter-severity');
    if (sevFilter) sevFilter.addEventListener('change', filterFeed);
    
    // Category pills
    document.querySelectorAll('#feed-category-pills .pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('#feed-category-pills .pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            filterFeed();
        });
    });

    document.getElementById('btn-refresh-feed').addEventListener('click', () => fetchDisasters(true));
    
    // Tasking events
    document.getElementById('btn-add-target').addEventListener('click', addTarget);
    document.getElementById('btn-compute').addEventListener('click', computeSchedule);
    document.getElementById('sat-select').addEventListener('change', handleSatChange);
    document.getElementById('btn-search-loc').addEventListener('click', searchLocation);
    document.getElementById('btn-export').addEventListener('click', exportCSV);
    
    // Modals
    document.getElementById('btn-close-modal').addEventListener('click', () => {
        document.getElementById('modal-explain').classList.add('hidden');
    });
    document.getElementById('btn-close-incident').addEventListener('click', () => {
        document.getElementById('modal-incident').classList.add('hidden');
    });

    // Quick Task deploy
    document.getElementById('btn-quick-task').addEventListener('click', () => {
        if (activeDisaster) {
            deployDisasterToTasking(activeDisaster);
        } else if (allDisasters.length > 0) {
            deployDisasterToTasking(allDisasters[0]);
        }
    });

    // AI Analyst Chat
    document.getElementById('btn-chat-send').addEventListener('click', sendAnalystQuery);
    document.getElementById('chat-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendAnalystQuery();
    });

    // Natural language tasking
    document.getElementById('btn-parse-nlp').addEventListener('click', parseNlpTasking);

    // Constellation
    document.getElementById('btn-run-constellation').addEventListener('click', runConstellationPlanner);

    // Change Detection
    document.getElementById('btn-run-change').addEventListener('click', runChangeDetection);

    // Alert Rule
    document.getElementById('btn-create-rule').addEventListener('click', createAlertRule);

    // Reports
    document.getElementById('btn-generate-report').addEventListener('click', generateSelectedReport);

    // Simulation
    document.getElementById('btn-run-simulation').addEventListener('click', runSimulation);
    document.getElementById('sim-intensity-slider').addEventListener('input', (e) => {
        document.getElementById('sim-intensity-val').innerText = `+${e.target.value}% Anomaly`;
    });

    // Health
    document.getElementById('btn-check-health').addEventListener('click', fetchHealth);
}

// -------------------------------------------------------------
// SATELLITE CATALOG & TRACK
// -------------------------------------------------------------
async function fetchSatellites() {
    try {
        const res = await fetch(`${API_BASE}/satellites`);
        satelliteList = await res.json();
        const select = document.getElementById('sat-select');
        select.innerHTML = '';
        
        satelliteList.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.innerText = `${s.name} [${s.type}] (NORAD: ${s.norad_id})`;
            select.appendChild(opt);
        });
        handleSatChange();
    } catch (e) {
        console.error('Error fetching satellites:', e);
    }
}

function handleSatChange() {
    const satId = document.getElementById('sat-select').value;
    const sat = satelliteList.find(s => s.id == satId);
    
    if (sat) {
        document.getElementById('sat-type').innerText = sat.type || '--';
        document.getElementById('sat-revisit').innerText = sat.revisit || '--';
        document.getElementById('sat-desc').innerText = sat.desc || '--';
        
        const box = document.getElementById('sat-info-box');
        let schematicWrap = box.querySelector('.sat-schematic-wrap');
        if (!schematicWrap) {
            schematicWrap = document.createElement('div');
            schematicWrap.className = 'sat-schematic-wrap';
            box.prepend(schematicWrap);
        }
        schematicWrap.innerHTML = `
            ${getSatelliteSchematicSvg(sat.name)}
            <div class="sat-schematic-meta">
                <div style="font-size:12px; font-weight:600; color:var(--text-primary);">${sat.name}</div>
                <div style="font-size:10px; font-family:var(--font-mono); color:var(--text-accent);">NORAD ID: ${sat.norad_id || sat.id}</div>
                <div style="font-size:10px; color:var(--text-muted);">Swath: ~250km | Orbit: Sun-Sync LEO</div>
            </div>
        `;
        
        if (sat.recommended_capacity) {
            document.getElementById('capacity-limit').value = sat.recommended_capacity;
        }
    }
    updateTrack(false);
    updateTrack(true);
}

async function updateTrack(isTaskMap = false) {
    const satId = document.getElementById('sat-select').value;
    if (!satId) return;
    
    try {
        const res = await fetch(`${API_BASE}/track?satellite_id=${satId}`);
        const data = await res.json();
        const targetMapObj = isTaskMap ? taskMap : map;
        
        if (isTaskMap && taskTrackLayer) taskMap.removeLayer(taskTrackLayer);
        if (!isTaskMap && trackLayer) map.removeLayer(trackLayer);
        
        const latlngs = data.track.map(pt => [pt.lat, pt.lon]);
        const lines = [];
        let currentLine = [latlngs[0]];
        for (let i = 1; i < latlngs.length; i++) {
            if (Math.abs(latlngs[i][1] - latlngs[i-1][1]) > 180) {
                lines.push(currentLine);
                currentLine = [latlngs[i]];
            } else {
                currentLine.push(latlngs[i]);
            }
        }
        lines.push(currentLine);
        
        const layer = L.polyline(lines, { color: '#ef4444', weight: 2, dashArray: '4,4' }).addTo(targetMapObj);
        
        L.circleMarker(latlngs[0], {
            radius: 6, color: '#fff', weight: 2, fillColor: '#ef4444', fillOpacity: 1
        }).addTo(layer);

        if (isTaskMap) taskTrackLayer = layer;
        else trackLayer = layer;
    } catch (e) {
        console.error('Track fetch failed', e);
    }
}

// -------------------------------------------------------------
// DISASTERS & MAP RENDERING
// -------------------------------------------------------------
async function fetchDisasters(forceRefresh = false) {
    try {
        const url = `${API_BASE}/disasters${forceRefresh ? '?refresh=true' : ''}`;
        const res = await fetch(url);
        allDisasters = await res.json();
        renderFeedList(allDisasters);
        renderMapDisasters(allDisasters);
        fetchSummaryStats();
        populateReportDropdown();
        populateChangeDetectionDropdown();
        
        if (allDisasters.length > 0 && !activeDisaster) {
            selectDisaster(allDisasters[0]);
        }
    } catch (e) {
        console.error('Failed to load disasters', e);
    }
}

async function fetchSummaryStats() {
    try {
        const res = await fetch(`${API_BASE}/disasters/summary`);
        const stats = await res.json();
        document.getElementById('tel-active-events').innerText = stats.active_disasters_count;
        document.getElementById('tel-critical-zones').innerText = `${stats.high_risk_zones_count} CRITICAL`;
    } catch (e) {
        console.error(e);
    }
}

function getHazardSvg(eventType) {
    const t = (eventType || '').toLowerCase();
    if (t.includes('fire') || t.includes('wildfire')) {
        return `<svg class="hazard-svg-glyph" viewBox="0 0 24 24" fill="none" stroke="#F97316" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>`;
    }
    if (t.includes('flood') || t.includes('water') || t.includes('tsunami')) {
        return `<svg class="hazard-svg-glyph" viewBox="0 0 24 24" fill="none" stroke="#38BDF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h20"/><path d="M2 6c3 0 3 3 6 3s3-3 6-3 3 3 6 3 3-3 6-3"/><path d="M2 18c3 0 3 3 6 3s3-3 6-3 3 3 6 3 3-3 6-3"/></svg>`;
    }
    if (t.includes('earthquake') || t.includes('seismic') || t.includes('quake')) {
        return `<svg class="hazard-svg-glyph" viewBox="0 0 24 24" fill="none" stroke="#EF4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h4l3-9 4 18 3-9h6"/></svg>`;
    }
    if (t.includes('cyclone') || t.includes('storm') || t.includes('hurricane') || t.includes('typhoon')) {
        return `<svg class="hazard-svg-glyph" viewBox="0 0 24 24" fill="none" stroke="#A855F7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 2a10 10 0 0 0-7.07 17.07"/><path d="M12 22a10 10 0 0 0 7.07-17.07"/></svg>`;
    }
    if (t.includes('volcano')) {
        return `<svg class="hazard-svg-glyph" viewBox="0 0 24 24" fill="none" stroke="#EAB308" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m8 3 4 8 5-5 5 15H2L8 3z"/></svg>`;
    }
    return `<svg class="hazard-svg-glyph" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
}

function getSatelliteSchematicSvg(name) {
    const n = (name || '').toLowerCase();
    if (n.includes('iss') || n.includes('zarya') || n.includes('station')) {
        return `<svg class="sat-schematic-svg" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <line x1="10" y1="50" x2="90" y2="50" stroke="#64748B" stroke-width="2"/>
            <rect x="42" y="44" width="16" height="12" rx="2" fill="#1E293B" stroke="#38BDF8" stroke-width="1.5"/>
            <line x1="50" y1="36" x2="50" y2="64" stroke="#94A3B8" stroke-width="1.5"/>
            <rect x="12" y="24" width="14" height="22" rx="1" fill="#0F172A" stroke="#38BDF8" stroke-width="1"/>
            <rect x="12" y="54" width="14" height="22" rx="1" fill="#0F172A" stroke="#38BDF8" stroke-width="1"/>
            <rect x="74" y="24" width="14" height="22" rx="1" fill="#0F172A" stroke="#38BDF8" stroke-width="1"/>
            <rect x="74" y="54" width="14" height="22" rx="1" fill="#0F172A" stroke="#38BDF8" stroke-width="1"/>
            <circle cx="50" cy="50" r="3" fill="#38BDF8"/>
        </svg>`;
    }
    if (n.includes('sentinel-1') || n.includes('sar')) {
        return `<svg class="sat-schematic-svg" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="40" y="35" width="20" height="30" rx="2" fill="#1E293B" stroke="#38BDF8" stroke-width="1.5"/>
            <rect x="5" y="44" width="30" height="12" rx="1" fill="#0F172A" stroke="#64748B" stroke-width="1"/>
            <line x1="15" y1="44" x2="15" y2="56" stroke="#334155"/>
            <line x1="25" y1="44" x2="25" y2="56" stroke="#334155"/>
            <rect x="65" y="44" width="30" height="12" rx="1" fill="#0F172A" stroke="#64748B" stroke-width="1"/>
            <line x1="75" y1="44" x2="75" y2="56" stroke="#334155"/>
            <line x1="85" y1="44" x2="85" y2="56" stroke="#334155"/>
            <path d="M30 68 L70 68 L64 74 L36 74 Z" fill="#38BDF8" fill-opacity="0.3" stroke="#38BDF8" stroke-width="1.5"/>
            <circle cx="50" cy="48" r="3" fill="#38BDF8"/>
        </svg>`;
    }
    if (n.includes('sentinel-2') || n.includes('optical')) {
        return `<svg class="sat-schematic-svg" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="38" y="30" width="24" height="36" rx="2" fill="#1E293B" stroke="#10B981" stroke-width="1.5"/>
            <rect x="5" y="42" width="28" height="14" rx="1" fill="#0F172A" stroke="#64748B" stroke-width="1"/>
            <line x1="14" y1="42" x2="14" y2="56" stroke="#334155"/>
            <line x1="23" y1="42" x2="23" y2="56" stroke="#334155"/>
            <circle cx="50" cy="68" r="8" fill="#0F172A" stroke="#10B981" stroke-width="1.5"/>
            <circle cx="50" cy="68" r="4" fill="#10B981" fill-opacity="0.5"/>
        </svg>`;
    }
    if (n.includes('landsat')) {
        return `<svg class="sat-schematic-svg" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <polygon points="50,26 68,36 68,64 50,74 32,64 32,36" fill="#1E293B" stroke="#F59E0B" stroke-width="1.5"/>
            <rect x="68" y="42" width="28" height="16" rx="1" fill="#0F172A" stroke="#64748B" stroke-width="1"/>
            <line x1="77" y1="42" x2="77" y2="58" stroke="#334155"/>
            <line x1="87" y1="42" x2="87" y2="58" stroke="#334155"/>
            <circle cx="44" cy="50" r="5" fill="#F59E0B" fill-opacity="0.4" stroke="#F59E0B" stroke-width="1.5"/>
            <circle cx="56" cy="50" r="3" fill="#EF4444" stroke="#EF4444" stroke-width="1"/>
        </svg>`;
    }
    return `<svg class="sat-schematic-svg" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="36" y="32" width="28" height="32" rx="2" fill="#1E293B" stroke="#F59E0B" stroke-width="1.5"/>
        <rect x="6" y="40" width="25" height="16" rx="1" fill="#0F172A" stroke="#64748B" stroke-width="1"/>
        <rect x="69" y="40" width="25" height="16" rx="1" fill="#0F172A" stroke="#64748B" stroke-width="1"/>
        <circle cx="50" cy="48" r="6" fill="#F59E0B" fill-opacity="0.4" stroke="#F59E0B" stroke-width="1"/>
    </svg>`;
}

function renderFeedList(disasters) {
    const list = document.getElementById('disaster-feed-list');
    list.innerHTML = '';
    
    if (disasters.length === 0) {
        list.innerHTML = '<div class="empty-state">No matching disasters found.</div>';
        return;
    }

    disasters.forEach(d => {
        const isCrit = d.severity === 'Critical';
        const isSev = d.severity === 'Severe';
        const div = document.createElement('div');
        div.className = `disaster-feed-item ${isCrit ? 'critical' : (isSev ? 'severe' : '')}`;
        if (activeDisaster && activeDisaster.event_id === d.event_id) {
            div.classList.add('active');
        }
        
        div.innerHTML = `
            <div class="df-header">
                <div class="df-title-wrap">
                    ${getHazardSvg(d.event_type)}
                    <span class="df-title">${d.name}</span>
                </div>
                <span class="badge-mini ${isCrit ? 'status-alert' : (isSev ? 'status-warn' : 'status-ok')}">● ${d.severity}</span>
            </div>
            <div class="df-meta">
                <span>${d.event_type} · ${d.affected_area_km2 ? d.affected_area_km2.toFixed(1) + ' km²' : 'Point Hazard'}</span>
                <span class="df-risk font-mono">Risk ${d.risk_score ? d.risk_score.toFixed(0) : 50}/100</span>
            </div>
        `;
        div.addEventListener('click', () => {
            document.querySelectorAll('.disaster-feed-item').forEach(el => el.classList.remove('active'));
            div.classList.add('active');
            selectDisaster(d);
            map.setView([d.latitude, d.longitude], 6);
        });
        list.appendChild(div);
    });
}

function filterFeed() {
    const search = document.getElementById('feed-search').value.toLowerCase();
    const activePill = document.querySelector('#feed-category-pills .pill.active');
    const cat = activePill ? activePill.getAttribute('data-cat') : 'ALL';
    const sevElem = document.getElementById('disaster-filter-severity');
    const sev = sevElem ? sevElem.value : 'ALL';
    
    const filtered = allDisasters.filter(d => {
        const matchesSearch = d.name.toLowerCase().includes(search) || d.event_type.toLowerCase().includes(search);
        const matchesCat = cat === 'ALL' || d.category === cat;
        const matchesSev = sev === 'ALL' || d.severity.toLowerCase() === sev.toLowerCase();
        return matchesSearch && matchesCat && matchesSev;
    });
    renderFeedList(filtered);
}

function renderMapDisasters(disasters) {
    // Clear existing markers
    disasterMarkers.forEach(m => map.removeLayer(m));
    disasterPolygons.forEach(p => map.removeLayer(p));
    disasterMarkers = [];
    disasterPolygons = [];

    disasters.forEach(d => {
        const color = getDisasterColor(d.event_type);
        
        // Render polygon if present
        if (d.geometry && d.geometry.type === 'Polygon') {
            const poly = L.geoJSON(d.geometry, {
                style: { color: color, weight: 2, fillOpacity: 0.25 }
            }).addTo(map);
            disasterPolygons.push(poly);
        }

        // Marker
        const marker = L.circleMarker([d.latitude, d.longitude], {
            radius: d.severity === 'Critical' ? 8 : 6,
            color: '#fff',
            weight: 1.5,
            fillColor: color,
            fillOpacity: 0.9
        }).addTo(map);

        marker.bindPopup(`
            <div style="font-family:var(--font-sans); min-width:200px;">
                <div style="font-weight:700; font-size:13px; color:#fff;">${d.name}</div>
                <div style="font-family:var(--font-mono); font-size:10px; color:var(--text-accent); margin: 3px 0;">${d.event_type.toUpperCase()} • ${d.severity.toUpperCase()}</div>
                <div style="font-family:var(--font-mono); font-size:10px; color:#aaa;">Risk Score: <strong style="color:#ef4444;">${d.risk_score}/100</strong></div>
                <div style="font-family:var(--font-mono); font-size:10px; color:#aaa;">Sensor: <strong>${d.recommended_sensor}</strong></div>
                <div style="margin-top:8px; display:flex; gap:4px;">
                    <button class="btn btn-small btn-primary" onclick="window.viewIncidentModal('${d.event_id}')">OPEN INCIDENT</button>
                    <button class="btn btn-small btn-secondary" onclick="window.quickTaskFromMap('${d.event_id}')">TASK SAT</button>
                </div>
            </div>
        `);

        marker.on('click', () => selectDisaster(d));
        disasterMarkers.push(marker);
    });
}

function getDisasterColor(type) {
    const t = type.toLowerCase();
    if (t.includes('flood')) return '#38bdf8'; // Blue
    if (t.includes('earthquake')) return '#ef4444'; // Red
    if (t.includes('cyclone') || t.includes('storm')) return '#a855f7'; // Purple
    if (t.includes('fire')) return '#f97316'; // Orange
    if (t.includes('tsunami')) return '#06b6d4'; // Cyan
    if (t.includes('volcano')) return '#eab308'; // Amber
    if (t.includes('landslide')) return '#84cc16'; // Lime
    return '#f43f5e';
}

function getSpectrumMarkerLeft(sensor) {
    const s = (sensor || '').toLowerCase();
    if (s.includes('sar') || s.includes('radar')) return '88%';
    if (s.includes('tir') || s.includes('thermal')) return '68%';
    if (s.includes('swir') || s.includes('infrared')) return '48%';
    if (s.includes('nir')) return '28%';
    return '10%';
}

function selectDisaster(d) {
    activeDisaster = d;
    const card = document.getElementById('priority-intel-card');
    const isCrit = d.severity === 'Critical';
    const isSev = d.severity === 'Severe';
    
    card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
            <strong style="font-size:13px; font-weight:600; color:var(--text-primary);">${d.name}</strong>
            <span class="badge-mini ${isCrit ? 'status-alert' : (isSev ? 'status-warn' : 'status-ok')}">● ${d.severity}</span>
        </div>
        <div class="info-row"><span class="label">Hazard Classification</span> <span>${d.event_type} (${d.category})</span></div>
        <div class="info-row"><span class="label">Calculated Risk</span> <span class="font-mono font-semibold ${isCrit ? 'status-alert' : (isSev ? 'status-warn' : 'status-ok')}">${d.risk_score}/100</span></div>
        <div class="info-row"><span class="label">Estimated Impact Area</span> <span class="font-mono">${d.affected_area_km2 ? d.affected_area_km2.toFixed(1) + ' km²' : 'Localized'}</span></div>
        <div class="info-row"><span class="label">Population Exposure</span> <span class="font-mono">${d.estimated_population ? d.estimated_population.toLocaleString() : 'Analyzing...'}</span></div>
        <div class="info-row"><span class="label">Recommended Sensor</span> <span class="font-semibold" style="color:var(--text-primary);">${d.recommended_sensor}</span></div>
        
        <div class="spectrum-visualizer">
            <div class="spectrum-labels">
                <span>VIS (400nm)</span>
                <span>NIR</span>
                <span>SWIR</span>
                <span>TIR (10µm)</span>
                <span>SAR (5.4GHz)</span>
            </div>
            <div class="spectrum-track">
                <div class="spectrum-marker" style="left: ${getSpectrumMarkerLeft(d.recommended_sensor)};"></div>
            </div>
        </div>

        <div style="margin-top:8px; border-top:1px solid var(--border-subtle); padding-top:8px; font-size:11px; color:var(--text-secondary); line-height:1.4;">
            <strong style="color:var(--text-muted); font-size:10px;">TACTICAL RATIONALE:</strong> ${d.recommended_action || 'Execute high-resolution orbital reconnaissance.'}
        </div>
        <button class="btn btn-small btn-secondary w-full mt-2" onclick="window.viewIncidentModal('${d.event_id}')">Open Full Incident Workspace &rarr;</button>
    `;

    document.getElementById('next-obs-sat').innerText = d.recommended_sensor.includes('SAR') ? 'SENTINEL-1A (SAR)' : 'SENTINEL-2A (Optical)';
    document.getElementById('next-obs-sensor').innerText = d.recommended_sensor;
}

window.quickTaskFromMap = function(eventId) {
    const d = allDisasters.find(x => x.event_id === eventId);
    if (d) deployDisasterToTasking(d);
};

window.viewIncidentModal = function(eventId) {
    const d = allDisasters.find(x => x.event_id === eventId);
    if (!d) return;

    document.getElementById('inc-title').innerText = d.name.toUpperCase();
    document.getElementById('inc-badge').innerText = d.severity.toUpperCase();
    document.getElementById('inc-badge').className = `badge-mini ${d.severity === 'Critical' ? 'status-alert' : 'status-warn'}`;

    const body = document.getElementById('incident-body');
    const infra = d.exposed_infrastructure || {};

    let timelineHtml = '<div class="incident-timeline">';
    (d.timeline || []).forEach(t => {
        timelineHtml += `
            <div class="timeline-item">
                <div class="timeline-time">${t.time.replace('T', ' ').substring(0, 19)} [${t.source}]</div>
                <div class="timeline-title">${t.title}</div>
                <div class="timeline-desc">${t.description}</div>
            </div>
        `;
    });
    timelineHtml += '</div>';

    body.innerHTML = `
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:15px;">
            <div class="intel-card">
                <h3>INCIDENT PARAMETERS</h3>
                <div class="info-row"><span class="label">EVENT ID:</span> <span class="font-mono">${d.event_id}</span></div>
                <div class="info-row"><span class="label">STATUS:</span> <span class="status-ok">${d.status}</span></div>
                <div class="info-row"><span class="label">COORDINATES:</span> <span class="font-mono">${d.latitude.toFixed(4)}°N, ${d.longitude.toFixed(4)}°E</span></div>
                <div class="info-row"><span class="label">AFFECTED REGION:</span> <span>${d.affected_area_km2 ? d.affected_area_km2.toFixed(1) + ' km²' : 'Epicenter'}</span></div>
                <div class="info-row"><span class="label">EXPOSED POPULATION:</span> <span class="font-bold">${d.estimated_population ? d.estimated_population.toLocaleString() : 'N/A'}</span></div>
            </div>
            <div class="intel-card">
                <h3>EXPOSED INFRASTRUCTURE (OSM INTERSECTION)</h3>
                <div class="info-row"><span class="label">HOSPITALS IN ZONE:</span> <span class="font-bold status-alert">${infra.hospitals || 0}</span></div>
                <div class="info-row"><span class="label">SCHOOLS:</span> <span>${infra.schools || 0}</span></div>
                <div class="info-row"><span class="label">BRIDGES:</span> <span>${infra.bridges || 0}</span></div>
                <div class="info-row"><span class="label">AIRPORTS:</span> <span>${infra.airports || 0}</span></div>
                <div class="info-row"><span class="label">ROAD CORRIDORS:</span> <span>${infra.roads_km ? infra.roads_km.toFixed(1) + ' km' : '0 km'}</span></div>
            </div>
        </div>

        <div class="intel-card mb-2">
            <h3>EXPLAINABLE RISK SCORE: ${d.risk_score}/100</h3>
            <div style="font-size:11px; color:var(--text-dim);">
                Calculated via $R = H \\times E \\times V$: Hazard Intensity (${d.category}) + Demographic Exposure (${d.estimated_population ? d.estimated_population.toLocaleString() : '0'} residents) + Infrastructure Exposure.
            </div>
        </div>

        <div class="intel-card mb-2">
            <h3>INCIDENT CHRONOLOGY & TIMELINE</h3>
            ${timelineHtml}
        </div>

        <div class="provenance-badge-box mb-2">
            <strong>DATA PROVENANCE & LINEAGE:</strong><br>
            Provider: <em>${d.provenance ? d.provenance.provider : 'USGS/Copernicus'}</em> | Dataset: <em>${d.provenance ? d.provenance.dataset : 'Live Feed'}</em> | Observed: <em>${d.provenance ? d.provenance.observed_at : 'Recent'}</em>
        </div>

        <button class="btn btn-primary w-full" onclick="window.deployFromIncident('${d.event_id}')">DEPLOY SATELLITE OBSERVATION MISSION →</button>
    `;

    document.getElementById('modal-incident').classList.remove('hidden');
};

window.deployFromIncident = function(eventId) {
    document.getElementById('modal-incident').classList.add('hidden');
    const d = allDisasters.find(x => x.event_id === eventId);
    if (d) deployDisasterToTasking(d);
};

function deployDisasterToTasking(d) {
    // Switch to tasking tab
    const taskTab = document.querySelector('.nav-tab[data-view="view-tasking"]');
    if (taskTab) taskTab.click();

    // Auto-populate target
    targets = [{
        id: `t_${Date.now()}`,
        name: d.name.split('-')[0].substring(0, 20).toUpperCase(),
        lat: d.latitude,
        lon: d.longitude,
        weight: d.severity === 'Critical' ? 10 : 8,
        disaster_type: d.event_type
    }];
    renderTargets();

    // Select suitable satellite
    const select = document.getElementById('sat-select');
    if (d.recommended_sensor.includes('SAR')) {
        select.value = '39634'; // Sentinel-1A
    } else if (d.recommended_sensor.includes('Thermal')) {
        select.value = '25994'; // Terra MODIS
    } else {
        select.value = '40697'; // Sentinel-2A
    }
    handleSatChange();

    taskMap.setView([d.latitude, d.longitude], 6);
}

// -------------------------------------------------------------
// DISASTER CENTER VIEW
// -------------------------------------------------------------
function renderDisasterCatalog() {
    const grid = document.getElementById('disaster-catalog-grid');
    grid.innerHTML = '';

    allDisasters.forEach(d => {
        const card = document.createElement('div');
        card.className = 'disaster-card';
        const isCrit = d.severity === 'Critical';
        const isSev = d.severity === 'Severe';

        card.innerHTML = `
            <div>
                <div class="dc-header">
                    <div>
                        <div class="dc-title font-semibold" style="font-size:13px; color:var(--text-primary);">${d.name}</div>
                        <div class="dc-type text-muted" style="font-size:11px;">${d.event_type} · ${d.category}</div>
                    </div>
                    <span class="badge-mini ${isCrit ? 'status-alert' : (isSev ? 'status-warn' : 'status-ok')}">● ${d.severity}</span>
                </div>
                <div class="dc-body mt-2">
                    <div class="info-row"><span class="label">Calculated Risk</span> <strong class="font-mono ${isCrit ? 'status-alert' : ''}">${d.risk_score}/100</strong></div>
                    <div class="info-row"><span class="label">Impact Area</span> <span class="font-mono">${d.affected_area_km2 ? d.affected_area_km2.toFixed(1) + ' km²' : 'Localized'}</span></div>
                    <div class="info-row"><span class="label">Exposed Population</span> <span class="font-mono">${d.estimated_population ? d.estimated_population.toLocaleString() : 'N/A'}</span></div>
                    <div class="info-row"><span class="label">Optimal Sensor</span> <span>${d.recommended_sensor}</span></div>
                </div>
            </div>
            <div class="dc-footer mt-2" style="display:flex; gap:6px;">
                <button class="btn btn-small btn-secondary flex-1" onclick="window.viewIncidentModal('${d.event_id}')">Incident View</button>
                <button class="btn btn-small btn-primary flex-1" onclick="window.quickTaskFromMap('${d.event_id}')">Task Platform &rarr;</button>
            </div>
        `;
        grid.appendChild(card);
    });
}

// -------------------------------------------------------------
// SATELLITE TASKING & SCHEDULING (ENHANCED SKYWINDOW)
// -------------------------------------------------------------
function addTarget() {
    const nameInput = document.getElementById('target-name');
    const latInput = document.getElementById('target-lat');
    const lonInput = document.getElementById('target-lon');
    const weightInput = document.getElementById('target-weight');
    
    const name = nameInput.value.trim().toUpperCase() || `TGT-${targets.length + 1}`;
    const lat = parseFloat(latInput.value);
    const lon = parseFloat(lonInput.value);
    const weight = parseFloat(weightInput.value) || 5;
    
    if (isNaN(lat) || isNaN(lon)) {
        alert('Please enter valid latitude and longitude coordinates.');
        return;
    }
    
    const id = `t_${Date.now()}`;
    targets.push({ id, name, lat, lon, weight });
    renderTargets();
    
    nameInput.value = '';
    latInput.value = '';
    lonInput.value = '';
}

function renderTargets() {
    const list = document.getElementById('targets-list');
    list.innerHTML = '';
    targets.forEach(t => {
        const div = document.createElement('div');
        div.className = 'target-item';
        div.innerHTML = `
            <div>
                <strong>${t.name}</strong> [PRI: ${t.weight}]<br>
                <span style="font-size:10px; color:var(--text-dim);">${t.lat.toFixed(4)}°N, ${t.lon.toFixed(4)}°E</span>
            </div>
            <button class="del-btn" onclick="removeTarget('${t.id}')">×</button>
        `;
        list.appendChild(div);
    });
}

window.removeTarget = function(id) {
    targets = targets.filter(t => t.id !== id);
    renderTargets();
};

async function searchLocation() {
    const query = document.getElementById('target-search').value;
    if (!query) return;
    const btn = document.getElementById('btn-search-loc');
    btn.innerText = '...';
    btn.disabled = true;
    
    try {
        const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=1`);
        const data = await res.json();
        if (data && data.length > 0) {
            const lat = parseFloat(data[0].lat).toFixed(4);
            const lon = parseFloat(data[0].lon).toFixed(4);
            document.getElementById('target-lat').value = lat;
            document.getElementById('target-lon').value = lon;
            document.getElementById('target-name').value = data[0].display_name.split(',')[0].toUpperCase();
            taskMap.setView([lat, lon], 5);
        } else {
            alert('Location not found.');
        }
    } catch (e) {
        alert('Geocoding error.');
    } finally {
        btn.innerText = 'FIND';
        btn.disabled = false;
    }
}

async function computeSchedule() {
    const satId = document.getElementById('sat-select').value;
    const capacity = parseInt(document.getElementById('capacity-limit').value);
    const maxCloud = parseFloat(document.getElementById('max-cloud-cover').value) || 100;
    const powerPer = parseFloat(document.getElementById('power-per-pass').value) || 150;
    const storagePer = parseFloat(document.getElementById('storage-per-pass').value) || 12;
    
    if (targets.length === 0) {
        alert('Please add at least one target location.');
        return;
    }
    
    const btn = document.getElementById('btn-compute');
    btn.disabled = true;
    btn.innerText = 'COMPUTING PASSES & WEATHER...';
    
    try {
        const res = await fetch(`${API_BASE}/schedule`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                satellite_id: parseInt(satId),
                targets: targets,
                max_passes_per_day: capacity,
                max_cloud_cover: maxCloud,
                power_per_pass: powerPer,
                storage_per_pass: storagePer
            })
        });
        
        if (!res.ok) throw new Error('API Error');
        const data = await res.json();
        currentSchedule = data;
        renderSchedule(data);
        document.getElementById('btn-export').disabled = false;
    } catch (e) {
        alert('Schedule computation failed.');
    } finally {
        btn.disabled = false;
        btn.innerText = 'GENERATE SENSOR-AWARE SCHEDULE';
    }
}

function renderSchedule(data) {
    document.getElementById('stat-naive').innerText = data.stats.naive_cloudy_passes;
    document.getElementById('stat-opt').innerText = data.stats.optimal_cloudy_passes;
    document.getElementById('stat-saved').innerText = data.stats.saved_passes;
    document.getElementById('stat-storage').innerText = data.stats.storage_saved_gb.toFixed(1);
    
    const container = document.getElementById('schedule-results');
    container.innerHTML = '';
    
    if (data.scheduled.length === 0 && data.rejected.length === 0) {
        container.innerHTML = '<div class="empty-state">NO OBSERVATION PASSES FOUND IN NEXT 48H</div>';
        return;
    }
    
    const all = [
        ...data.scheduled.map(p => ({ ...p, status: 'SCHEDULED' })),
        ...data.rejected.map(p => ({ ...p, status: 'REJECTED' }))
    ].sort((a,b) => new Date(a.rise_time) - new Date(b.rise_time));
    
    all.forEach(p => {
        const cc = p.cloud_cover;
        const ccClass = cc < 30 ? 'status-ok' : (cc < 70 ? 'status-warn' : 'status-alert');
        const isRej = p.status === 'REJECTED';
        
        const el = document.createElement('div');
        el.className = `schedule-item ${isRej ? 'opacity-60' : ''}`;
        
        el.innerHTML = `
            <div class="sched-header">
                <span style="font-weight:700;">${p.target_name}</span>
                <span class="badge-mini ${isRej ? 'status-alert' : 'status-ok'}">${p.status}</span>
            </div>
            <div class="sched-body">
                <div class="info-row"><span>OVERPASS UTC:</span> <strong class="font-mono">${p.culminate_time.replace('T', ' ').substring(0, 16)}</strong></div>
                <div class="info-row"><span>MAX ELEVATION:</span> <span>${p.max_elevation_deg}°</span></div>
                <div class="info-row"><span>SENSOR MODALITY:</span> <span class="text-accent">${p.sensor_type || 'Optical'}</span></div>
                <div class="info-row"><span>FORECAST CLOUDS:</span> <span class="${ccClass}">${cc !== null ? cc + '%' : 'N/A'}</span></div>
                ${cc !== null ? `
                <div class="weather-bar-container">
                    <div class="weather-bar" style="width:${cc}%; background:${cc < 30 ? 'var(--text-success)' : (cc < 70 ? 'var(--text-warn)' : 'var(--text-alert)')}"></div>
                </div>` : ''}
                ${p.reject_reason ? `<div style="color:var(--text-alert); font-size:10px; margin-top:4px;">REASON: ${p.reject_reason}</div>` : ''}
            </div>
            <div class="sched-footer">
                <span style="font-size:10px; color:var(--text-dim);">PRIORITY: ${p.target_weight}</span>
                <button class="btn btn-small btn-secondary btn-audit">DECISION AUDIT</button>
            </div>
        `;
        
        el.querySelector('.btn-audit').addEventListener('click', () => showAudit(p, data.tle_info));
        container.appendChild(el);
    });
}

function showAudit(pass, tleInfo) {
    const modal = document.getElementById('modal-explain');
    const body = document.getElementById('explain-body');
    
    body.innerHTML = `
        <div class="audit-row"><span class="audit-label">TARGET NAME</span><span>${pass.target_name}</span></div>
        <div class="audit-row"><span class="audit-label">TARGET PRIORITY</span><span>${pass.target_weight}</span></div>
        <div class="audit-row"><span class="audit-label">ORBIT MODEL</span><span>SGP4 Keplarian Propagation</span></div>
        <div class="audit-row"><span class="audit-label">TLE PLATFORM</span><span>${tleInfo.name}</span></div>
        <div class="audit-row"><span class="audit-label">CULMINATE TIME (UTC)</span><span class="font-mono">${pass.culminate_time.replace('T', ' ')}</span></div>
        <div class="audit-row"><span class="audit-label">MAX ELEVATION</span><span>${pass.max_elevation_deg}°</span></div>
        <div class="audit-row"><span class="audit-label">FORECAST CLOUD COVER</span><span>${pass.cloud_cover !== null ? pass.cloud_cover + '%' : 'UNAVAILABLE'}</span></div>
        <div class="audit-row"><span class="audit-label">SENSOR MODALITY</span><span class="text-accent">${pass.sensor_type || 'Optical'}</span></div>
        <div class="audit-row"><span class="audit-label">DECISION FORMULA</span><span style="font-size:10px;">${pass.audit_reason || 'Standard SGP4 Objective Function'}</span></div>
        <div class="audit-row"><span class="audit-label">STATUS</span><span style="color:${pass.reject_reason ? 'var(--text-alert)' : 'var(--text-success)'}">${pass.reject_reason ? 'REJECTED' : 'SCHEDULED'}</span></div>
        ${pass.reject_reason ? `<div class="audit-row"><span class="audit-label">REJECTION REASON</span><span style="color:var(--text-alert)">${pass.reject_reason}</span></div>` : ''}
    `;
    modal.classList.remove('hidden');
}

function exportCSV() {
    if (!currentSchedule) return;
    let csv = "TARGET,STATUS,RISE_TIME,CULMINATE_TIME,SET_TIME,MAX_ELEV,CLOUD_COVER,SCORE,REASON\n";
    const all = [
        ...currentSchedule.scheduled.map(p => ({ ...p, status: 'SCHEDULED' })),
        ...currentSchedule.rejected.map(p => ({ ...p, status: 'REJECTED' }))
    ].sort((a,b) => new Date(a.rise_time) - new Date(b.rise_time));
    
    all.forEach(p => {
        csv += `${p.target_name},${p.status},${p.rise_time},${p.culminate_time},${p.set_time},${p.max_elevation_deg},${p.cloud_cover},${p.score},"${p.reject_reason || 'Approved'}"\n`;
    });
    
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `skywindow_schedule_${Date.now()}.csv`;
    a.click();
}

// -------------------------------------------------------------
// CONSTELLATION PLANNING
// -------------------------------------------------------------
async function runConstellationPlanner() {
    const campaignName = document.getElementById('const-campaign-name').value;
    const duration = parseInt(document.getElementById('const-duration').value);
    const checkboxes = document.querySelectorAll('.sat-checkboxes input[type=checkbox]:checked');
    const satIds = Array.from(checkboxes).map(c => parseInt(c.value));
    
    if (targets.length === 0) {
        targets = [{ id: 't_const', name: 'Kerala Flood Zone', lat: 9.98, lon: 76.45, weight: 9, disaster_type: 'Flood' }];
    }

    const container = document.getElementById('constellation-results');
    container.innerHTML = '<div class="empty-state">Optimizing multi-satellite constellation passes...</div>';

    try {
        const res = await fetch(`${API_BASE}/tasking/constellation`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                satellite_ids: satIds,
                targets: targets,
                campaign_name: campaignName,
                duration_hours: duration
            })
        });
        const data = await res.json();
        renderConstellationResults(data);
    } catch (e) {
        container.innerHTML = '<div class="empty-state text-alert">Constellation optimization failed.</div>';
    }
}

function renderConstellationResults(data) {
    const container = document.getElementById('constellation-results');
    container.innerHTML = '';

    data.campaign_results.forEach(res => {
        const div = document.createElement('div');
        div.className = 'intel-card';
        let passesList = '';
        res.scheduled_passes.forEach(p => {
            passesList += `<div class="info-row"><span class="font-mono">${p.culminate_time.replace('T', ' ').substring(0, 16)}</span> <span class="status-ok font-bold">${p.max_elevation_deg}° Elev (Clouds: ${p.cloud_cover}%)</span></div>`;
        });

        div.innerHTML = `
            <div class="dc-header">
                <strong>${res.satellite_name}</strong>
                <span class="badge-mini status-ok">${res.scheduled_passes.length} PASSES APPROVED</span>
            </div>
            <div style="font-size:11px; margin-top:8px;">
                ${passesList || '<div class="empty-state">No cloud-optimal passes found in window.</div>'}
            </div>
        `;
        container.appendChild(div);
    });
}

function populateChangeDetectionDropdown() {
    const select = document.getElementById('change-disaster-select');
    if (!select) return;
    select.innerHTML = '';
    allDisasters.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.event_id;
        opt.innerText = `${d.name} (${d.event_type})`;
        select.appendChild(opt);
    });
}

// -------------------------------------------------------------
// CHANGE DETECTION
// -------------------------------------------------------------
async function runChangeDetection() {
    const disasterId = document.getElementById('change-disaster-select').value;
    const feature = document.getElementById('change-feature-select').value;
    const baseDate = document.getElementById('change-base-date').value;
    const currDate = document.getElementById('change-curr-date').value;

    const selectedDisaster = allDisasters.find(x => x.event_id === disasterId);
    const targetLat = selectedDisaster ? selectedDisaster.latitude : 0.0;
    const targetLon = selectedDisaster ? selectedDisaster.longitude : 0.0;

    const container = document.getElementById('change-results-card');
    container.innerHTML = '<div class="empty-state">Executing multi-temporal satellite differencing...</div>';

    try {
        const res = await fetch(`${API_BASE}/change-detection`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                event_id: disasterId,
                target_lat: targetLat,
                target_lon: targetLon,
                baseline_date: baseDate,
                current_date: currDate,
                feature_type: feature
            })
        });
        const data = await res.json();
        
        container.innerHTML = `
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px;">
                <div class="intel-card">
                    <h3 style="font-size:12px; font-weight:600; color:var(--text-primary); margin-bottom:8px;">TEMPORAL SURFACE DELTA</h3>
                    <div class="info-row"><span class="label">Baseline Extent (${data.baseline_date}):</span> <span class="font-mono">${data.baseline_area_km2.toFixed(1)} km²</span></div>
                    <div class="info-row"><span class="label">Post-Event Extent (${data.current_date}):</span> <span class="font-mono font-bold">${data.current_area_km2.toFixed(1)} km²</span></div>
                    <div class="info-row"><span class="label">Area Expansion:</span> <strong style="color:var(--status-critical);">+${data.delta_area_km2.toFixed(1)} km²</strong></div>
                    <div class="info-row"><span class="label">Relative Anomaly:</span> <strong style="color:var(--status-critical);">+${data.percentage_change}%</strong></div>
                    <div class="info-row"><span class="label">Classification:</span> <span class="badge-mini status-alert">● ${data.expansion_status}</span></div>
                </div>
                <div class="intel-card">
                    <h3 style="font-size:12px; font-weight:600; color:var(--text-primary); margin-bottom:8px;">ALGORITHM & PROVENANCE</h3>
                    <div style="font-size:11px; color:var(--text-secondary); margin-bottom:8px; line-height:1.5;">${data.methodology}</div>
                    <div class="info-row"><span class="label">Algorithmic Confidence:</span> <span class="status-ok font-bold">${(data.confidence * 100).toFixed(0)}%</span></div>
                    <div class="info-row"><span class="label">Observation Source:</span> <span class="font-semibold">${data.provenance.provider}</span></div>
                </div>
            </div>

            <!-- Visual Raster Differencing Viewports -->
            <div class="change-raster-grid">
                <div class="raster-viewport">
                    <div class="raster-header">
                        <span>BASELINE OBSERVATION (T₀: ${data.baseline_date})</span>
                        <span class="badge-mini status-ok">NORMAL BASELINE</span>
                    </div>
                    <div class="raster-img-box">
                        <svg class="raster-svg-canvas" viewBox="0 0 400 200" xmlns="http://www.w3.org/2000/svg">
                            <!-- Background Terrain -->
                            <rect width="400" height="200" fill="#0C1017"/>
                            <!-- Subtle Grid Lines -->
                            <path d="M0 50 H400 M0 100 H400 M0 150 H400 M100 0 V200 M200 0 V200 M300 0 V200" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
                            <!-- Normal Water Body / River -->
                            <path d="M0 110 Q100 130 200 100 T400 120 L400 140 Q300 120 200 120 T0 130 Z" fill="#1E293B" stroke="#334155" stroke-width="1.5"/>
                            <text x="12" y="24" fill="#64748B" font-size="10" font-family="JetBrains Mono">POL: VV+VH DUAL-POL | REF: 0.12</text>
                            <text x="330" y="185" fill="#64748B" font-size="9" font-family="JetBrains Mono">SCALE: 1:50k</text>
                        </svg>
                    </div>
                </div>

                <div class="raster-viewport" style="border-color: rgba(239, 68, 68, 0.4);">
                    <div class="raster-header" style="background: rgba(239, 68, 68, 0.08);">
                        <span>ACTIVE DIFFERENCE MASK (T₁: ${data.current_date})</span>
                        <span class="badge-mini status-alert">+${data.percentage_change}% ANOMALY</span>
                    </div>
                    <div class="raster-img-box">
                        <svg class="raster-svg-canvas" viewBox="0 0 400 200" xmlns="http://www.w3.org/2000/svg">
                            <rect width="400" height="200" fill="#0C1017"/>
                            <path d="M0 50 H400 M0 100 H400 M0 150 H400 M100 0 V200 M200 0 V200 M300 0 V200" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>
                            <!-- Expanded Inundated Area (Blue Glow) -->
                            <path d="M0 70 Q90 160 200 70 T400 160 L400 180 Q280 90 200 150 T0 160 Z" fill="rgba(56, 189, 248, 0.25)" stroke="#38BDF8" stroke-width="2"/>
                            <!-- Active Delta Highlight -->
                            <circle cx="180" cy="110" r="30" fill="rgba(239, 68, 68, 0.25)" stroke="#EF4444" stroke-width="1.5" stroke-dasharray="3,3"/>
                            <text x="12" y="24" fill="#38BDF8" font-size="10" font-family="JetBrains Mono">DIFF MASK: INUNDATION DELTA DETECTED</text>
                            <text x="145" y="115" fill="#EF4444" font-size="9" font-family="JetBrains Mono" font-weight="bold">HIGH DELTA ZONE</text>
                            <text x="330" y="185" fill="#64748B" font-size="9" font-family="JetBrains Mono">SCALE: 1:50k</text>
                        </svg>
                    </div>
                </div>
            </div>
        `;
    } catch (e) {
        container.innerHTML = '<div class="empty-state text-alert">Change detection execution failed.</div>';
    }
}

// -------------------------------------------------------------
// AI ANALYST & NLP TASKING
// -------------------------------------------------------------
async function sendAnalystQuery() {
    const input = document.getElementById('chat-input');
    const query = input.value.trim();
    if (!query) return;

    const messages = document.getElementById('chat-messages');
    
    // Append user message
    const userMsg = document.createElement('div');
    userMsg.className = 'chat-msg user-msg';
    userMsg.innerHTML = `<div class="msg-author">OPERATOR</div><div>${query}</div>`;
    messages.appendChild(userMsg);
    input.value = '';

    // Placeholder bot message
    const botMsg = document.createElement('div');
    botMsg.className = 'chat-msg system-msg';
    botMsg.innerHTML = `<div class="msg-author">SKYWINDOW ANALYST</div><div>Analyzing satellite telemetry and hydrological data...</div>`;
    messages.appendChild(botMsg);
    messages.scrollTop = messages.scrollHeight;

    try {
        const res = await fetch(`${API_BASE}/analyst/query`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ query: query })
        });
        const data = await res.json();

        let evidenceHtml = '<ul style="margin:6px 0 0 15px; font-size:11px; color:var(--text-dim);">';
        (data.evidence_points || []).forEach(e => {
            evidenceHtml += `<li>${e}</li>`;
        });
        evidenceHtml += '</ul>';

        botMsg.innerHTML = `
            <div class="msg-author">SKYWINDOW ANALYST (Confidence: ${(data.confidence * 100).toFixed(0)}%)</div>
            <div style="white-space:pre-wrap;">${data.answer}</div>
            <div style="margin-top:8px; border-top:1px dashed var(--border-color); padding-top:6px;">
                <strong style="font-size:10px; color:var(--text-accent);">STRUCTURED EVIDENCE POINTS:</strong>
                ${evidenceHtml}
            </div>
        `;
        messages.scrollTop = messages.scrollHeight;
    } catch (e) {
        botMsg.innerHTML = `<div class="msg-author">SKYWINDOW ANALYST</div><div class="status-alert">Error processing analyst query.</div>`;
    }
}

async function parseNlpTasking() {
    const text = document.getElementById('nlp-task-input').value.trim();
    if (!text) return;

    const output = document.getElementById('nlp-plan-output');
    output.classList.remove('hidden');
    output.innerHTML = '<div class="empty-state">Parsing mission parameters...</div>';

    try {
        const res = await fetch(`${API_BASE}/tasking/nlp`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ instruction: text })
        });
        const data = await res.json();

        output.innerHTML = `
            <div class="intel-card">
                <h3>PROPOSED FLIGHT & IMAGING PLAN</h3>
                <div class="info-row"><span class="label">TARGET AREA:</span> <span class="font-bold">${data.parsed_target_name}</span></div>
                <div class="info-row"><span class="label">COORDINATES:</span> <span class="font-mono">${data.latitude.toFixed(4)}°N, ${data.longitude.toFixed(4)}°E</span></div>
                <div class="info-row"><span class="label">SENSOR MODALITY:</span> <span class="text-accent font-bold">${data.recommended_sensor}</span></div>
                <div class="info-row"><span class="label">DURATION:</span> <span>${data.duration_hours} Hours</span></div>
                <div class="info-row"><span class="label">RECOMMENDED PLATFORMS:</span> <span>${data.suggested_satellites.join(', ')}</span></div>
                <div style="margin-top:8px; font-size:11px; color:var(--text-dim);">${data.explanation}</div>
                <button class="btn btn-primary w-full mt-1" onclick="window.deployNlpPlan(${data.latitude}, ${data.longitude}, '${data.parsed_target_name}')">EXECUTE MISSION PLAN</button>
            </div>
        `;
    } catch (e) {
        output.innerHTML = '<div class="empty-state text-alert">Failed to parse task instruction.</div>';
    }
}

window.deployNlpPlan = function(lat, lon, name) {
    const taskTab = document.querySelector('.nav-tab[data-view="view-tasking"]');
    if (taskTab) taskTab.click();
    targets = [{ id: `t_nlp_${Date.now()}`, name: name, lat: lat, lon: lon, weight: 10, disaster_type: 'Flood' }];
    renderTargets();
    computeSchedule();
};

// -------------------------------------------------------------
// ALERTS & WATCHLISTS
// -------------------------------------------------------------
async function fetchAlerts() {
    try {
        const res = await fetch(`${API_BASE}/alerts`);
        const alerts = await res.json();
        const list = document.getElementById('alerts-stream-list');
        list.innerHTML = '';

        if (alerts.length === 0) {
            list.innerHTML = '<div class="empty-state">No active alerts triggered.</div>';
            return;
        }

        alerts.forEach(a => {
            const div = document.createElement('div');
            div.className = `disaster-feed-item ${a.severity === 'Critical' ? 'critical' : 'severe'}`;
            div.innerHTML = `
                <div class="df-header">
                    <strong>${a.title}</strong>
                    <span class="badge-mini status-alert">${a.severity.toUpperCase()}</span>
                </div>
                <div style="font-size:11px; color:var(--text-dim); margin-top:4px;">${a.message}</div>
                <div style="font-size:9px; color:var(--text-dim); margin-top:4px; font-family:var(--font-mono);">Source: ${a.source} • ${a.created_at.substring(0, 19)}</div>
            `;
            list.appendChild(div);
        });
    } catch (e) {
        console.error(e);
    }
}

async function fetchAlertRules() {
    try {
        const res = await fetch(`${API_BASE}/alerts/rules`);
        const rules = await res.json();
        const list = document.getElementById('rules-list');
        list.innerHTML = '';

        rules.forEach(r => {
            const div = document.createElement('div');
            div.className = 'target-item';
            div.innerHTML = `
                <div>
                    <strong>${r.name}</strong> [${r.disaster_type} • ${r.min_severity}]<br>
                    <span style="font-size:10px; color:var(--text-dim);">Radius: ${r.max_distance_km} km</span>
                </div>
                <button class="del-btn" onclick="window.deleteRule('${r.id}')">×</button>
            `;
            list.appendChild(div);
        });
    } catch (e) {
        console.error(e);
    }
}

async function createAlertRule() {
    const name = document.getElementById('rule-name').value.trim() || 'Custom Rule';
    const type = document.getElementById('rule-type').value;
    const sev = document.getElementById('rule-sev').value;
    const dist = parseFloat(document.getElementById('rule-dist').value) || 500;

    await fetch(`${API_BASE}/alerts/rules`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            id: `rule_${Date.now()}`,
            name: name,
            disaster_type: type,
            min_severity: sev,
            max_distance_km: dist
        })
    });
    fetchAlertRules();
    fetchAlerts();
}

window.deleteRule = async function(ruleId) {
    await fetch(`${API_BASE}/alerts/rules/${ruleId}`, { method: 'DELETE' });
    fetchAlertRules();
};

// -------------------------------------------------------------
// REPORTS & BRIEFINGS
// -------------------------------------------------------------
function populateReportDropdown() {
    const select = document.getElementById('report-disaster-select');
    select.innerHTML = '';
    allDisasters.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.event_id;
        opt.innerText = `${d.name} (${d.severity})`;
        select.appendChild(opt);
    });
}

async function generateSelectedReport() {
    const id = document.getElementById('report-disaster-select').value;
    if (!id) return;

    const container = document.getElementById('report-view-container');
    container.innerHTML = '<div class="empty-state">Synthesizing intelligence report...</div>';

    try {
        const res = await fetch(`${API_BASE}/reports/generate/${id}`, { method: 'POST' });
        const rep = await res.json();
        
        const infra = rep.infrastructure_exposure || {};
        const weather = rep.weather_context || {};

        container.innerHTML = `
            <div class="intel-card" style="padding:20px; line-height:1.6;">
                <div style="border-bottom:2px solid var(--text-accent); padding-bottom:10px; margin-bottom:15px; display:flex; justify-content:space-between;">
                    <div>
                        <h2 style="font-size:16px;">${rep.title}</h2>
                        <div class="text-xs text-muted">REPORT ID: ${rep.report_id} • ${rep.classification}</div>
                    </div>
                    <div class="badge-tag">SKYWINDOW INTEL</div>
                </div>

                <div class="mb-2">
                    <h3 style="color:var(--text-accent);">1. EXECUTIVE SUMMARY</h3>
                    <p style="font-size:12px; color:var(--text-main);">${rep.executive_summary}</p>
                </div>

                <div class="mb-2" style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
                    <div>
                        <h3 style="color:var(--text-accent);">2. METEOROLOGICAL CONTEXT</h3>
                        <div class="info-row"><span>Temperature:</span> <span>${weather.temperature_c || 'N/A'}°C</span></div>
                        <div class="info-row"><span>Cloud Cover:</span> <span>${weather.cloud_cover_pct || 'N/A'}%</span></div>
                        <div class="info-row"><span>Precipitation:</span> <span>${weather.precipitation_mm || '0'} mm</span></div>
                        <div class="info-row"><span>Wind Speed:</span> <span>${weather.wind_speed_kmh || '0'} km/h</span></div>
                    </div>
                    <div>
                        <h3 style="color:var(--text-accent);">3. CRITICAL INFRASTRUCTURE EXPOSURE</h3>
                        <div class="info-row"><span>Hospitals in Zone:</span> <strong class="status-alert">${infra.hospitals || 0}</strong></div>
                        <div class="info-row"><span>Schools:</span> <span>${infra.schools || 0}</span></div>
                        <div class="info-row"><span>Bridges:</span> <span>${infra.bridges || 0}</span></div>
                        <div class="info-row"><span>Airports:</span> <span>${infra.airports || 0}</span></div>
                    </div>
                </div>

                <div class="mb-2">
                    <h3 style="color:var(--text-accent);">4. SATELLITE TASKING RECOMMENDATIONS</h3>
                    <p style="font-size:12px;">Recommended Sensor: <strong>${rep.satellite_tasking_recommendations.recommended_sensor}</strong></p>
                    <p style="font-size:11px; color:var(--text-dim);">${rep.satellite_tasking_recommendations.rationale}</p>
                </div>

                <div class="provenance-badge-box">
                    <strong>DATA PROVENANCE & UNCERTAINTY:</strong><br>
                    ${rep.limitations_and_uncertainty}
                </div>
            </div>
        `;
    } catch (e) {
        container.innerHTML = '<div class="empty-state text-alert">Report generation failed.</div>';
    }
}

// -------------------------------------------------------------
// DATA SOURCES & API HEALTH
// -------------------------------------------------------------
async function fetchHealth() {
    try {
        const res = await fetch(`${API_BASE}/health`);
        const sources = await res.json();
        const grid = document.getElementById('data-sources-grid');
        grid.innerHTML = '';

        sources.forEach(s => {
            const card = document.createElement('div');
            card.className = 'health-card';
            card.innerHTML = `
                <div class="health-card-header">
                    <strong style="font-size:12px; font-weight:600; color:var(--text-primary);">${s.name}</strong>
                    <span class="badge-mini status-ok">● ${s.status}</span>
                </div>
                <div style="font-size:11px; color:var(--text-secondary); line-height:1.6; margin-top:8px;">
                    <div class="info-row"><span class="label">Provider</span> <span class="font-semibold">${s.provider}</span></div>
                    <div class="info-row"><span class="label">Hazard Domain</span> <span>${s.category}</span></div>
                    <div class="info-row"><span class="label">Ping Latency</span> <span class="font-mono">${s.latency_ms} ms</span></div>
                    <div class="info-row"><span class="label">Update Cadence</span> <span>${s.update_frequency}</span></div>
                    <div class="info-row"><span class="label">Licensing</span> <span>${s.license}</span></div>
                    <div style="margin-top:8px; border-top:1px solid var(--border-subtle); padding-top:6px; font-size:10px; color:var(--text-muted);">
                        <strong>Attribution:</strong> ${s.attribution}
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (e) {
        console.error(e);
    }
}

// -------------------------------------------------------------
// SCENARIO SIMULATOR
// -------------------------------------------------------------
function runSimulation() {
    const type = document.getElementById('sim-scenario-type').value;
    const target = document.getElementById('sim-target-name').value || 'Coastal Urban Corridor';
    const intensity = parseFloat(document.getElementById('sim-intensity-slider').value) || 50;

    const container = document.getElementById('sim-results-card');
    
    let baseArea = 142.0;
    let basePop = 84000;
    let sensorPkg = "Sentinel-1A (C-SAR) + Sentinel-2A (MSI Optical)";
    let rationale = "Penetrate monsoon cloud deck via radar and track flood extent propagation.";
    let hospitals = Math.round(8 * (1 + intensity / 100));
    let schools = Math.round(24 * (1 + intensity / 100));
    let bridges = Math.round(6 * (1 + intensity / 100));

    if (type === 'cyclone') {
        baseArea = 320.0;
        basePop = 165000;
        sensorPkg = "Sentinel-1A (SAR) + Terra (MODIS Thermal) + Landsat 9 (OLI-2)";
        rationale = "High sea-surface wind shear & coastal storm surge requires multi-temporal radar differencing.";
    } else if (type === 'earthquake') {
        baseArea = 450.0;
        basePop = 240000;
        sensorPkg = "Sentinel-1A (InSAR Interferometry) + High-Resolution Optical";
        rationale = "Measure sub-centimeter coseismic crustal deformation and identify collapsed transport corridors.";
    }

    let simArea = (baseArea * (1 + intensity / 100)).toFixed(1);
    let simPop = Math.round(basePop * (1 + intensity / 100));

    container.innerHTML = `
        <div class="intel-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <h3 style="font-size:14px; font-weight:700; color:var(--text-primary);">SIMULATED IMPACT MODEL: ${type.toUpperCase()}</h3>
                <span class="badge-mini status-warn">● NUMERICAL SIMULATION</span>
            </div>

            <div class="sim-metric-badge-grid">
                <div class="sim-metric-box">
                    <span style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">Impact Footprint</span>
                    <strong style="font-size:16px; color:#EF4444; font-family:var(--font-mono);">${simArea} km²</strong>
                    <span style="font-size:9px; color:var(--text-muted);">+${intensity}% anomaly</span>
                </div>
                <div class="sim-metric-box">
                    <span style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">Exposed Population</span>
                    <strong style="font-size:16px; color:#F59E0B; font-family:var(--font-mono);">${simPop.toLocaleString()}</strong>
                    <span style="font-size:9px; color:var(--text-muted);">estimated residents</span>
                </div>
                <div class="sim-metric-box">
                    <span style="font-size:10px; color:var(--text-muted); text-transform:uppercase;">Critical Facilities</span>
                    <strong style="font-size:16px; color:#38BDF8; font-family:var(--font-mono);">${hospitals + schools + bridges} Assets</strong>
                    <span style="font-size:9px; color:var(--text-muted);">${hospitals} hosp · ${schools} schl · ${bridges} brg</span>
                </div>
            </div>

            <div class="info-row"><span class="label">Target Corridor:</span> <strong>${target}</strong></div>
            <div class="info-row"><span class="label">Recommended Sensor Package:</span> <strong class="text-accent">${sensorPkg}</strong></div>
            <div class="info-row"><span class="label">Reconnaissance Rationale:</span> <span>${rationale}</span></div>

            <div style="margin-top:14px; display:flex; gap:8px;">
                <button class="btn btn-primary btn-small" onclick="document.querySelector('[data-view=view-tasking]').click();">
                    Launch SGP4 Satellite Tasking for this Target
                </button>
            </div>

            <div style="margin-top:12px; font-size:10px; color:var(--text-muted); border-top:1px solid var(--border-subtle); padding-top:8px;">
                <strong>SIMULATION NOTE:</strong> Hydrodynamic and seismic parameters are computed for operational table-top readiness and satellite duty-cycle stress testing.
            </div>
        </div>
    `;
}
