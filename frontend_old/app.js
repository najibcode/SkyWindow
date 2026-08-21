const API_BASE = '/api';

let map;
let trackLayer;
let targetMarkers = {};
let targets = [];
let currentSchedule = null;
let satelliteDataList = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initClock();
    initMap();
    fetchSatellites();
    
    document.getElementById('btn-add-target').addEventListener('click', addTarget);
    document.getElementById('btn-compute').addEventListener('click', computeSchedule);
    document.getElementById('sat-select').addEventListener('change', handleSatChange);
    document.getElementById('btn-close-modal').addEventListener('click', () => {
        document.getElementById('modal-explain').classList.add('hidden');
    });
    document.getElementById('btn-export').addEventListener('click', exportCSV);
    
    // Search location
    document.getElementById('btn-search-loc').addEventListener('click', searchLocation);
    document.getElementById('target-search').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchLocation();
    });
});

function initClock() {
    setInterval(() => {
        const now = new Date();
        document.getElementById('clock').innerText = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
    }, 1000);
}

function initMap() {
    map = L.map('map', {
        zoomControl: true,
        attributionControl: false
    }).setView([20, 0], 2);
    
    // Esri World Imagery (Realistic Satellite View)
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 17
    }).addTo(map);
    
    // RainViewer Live Radar (Clouds/Precipitation overlay)
    L.tileLayer('https://tilecache.rainviewer.com/v2/radar/past_0/256/{z}/{x}/{y}/2/1_1.png', {
        maxZoom: 17,
        opacity: 0.6
    }).addTo(map);
    
    // Click on map to populate lat/lon
    map.on('click', function(e) {
        document.getElementById('target-lat').value = e.latlng.lat.toFixed(4);
        document.getElementById('target-lon').value = e.latlng.lng.toFixed(4);
    });
}

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
            
            // Auto-fill name if empty
            if (!document.getElementById('target-name').value) {
                const shortName = data[0].display_name.split(',')[0].toUpperCase();
                document.getElementById('target-name').value = shortName;
            }
            
            map.setView([lat, lon], 5);
        } else {
            alert('LOCATION NOT FOUND');
        }
    } catch(e) {
        alert('GEOCODING ERROR');
    } finally {
        btn.innerText = 'FIND';
        btn.disabled = false;
    }
}

async function fetchSatellites() {
    try {
        const res = await fetch(`${API_BASE}/satellites`);
        satelliteDataList = await res.json();
        const select = document.getElementById('sat-select');
        
        satelliteDataList.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.innerText = `${s.name} (NORAD: ${s.id})`;
            select.appendChild(opt);
        });
        handleSatChange();
    } catch (e) {
        showError('FAILED TO LOAD SATELLITE DIRECTORY');
    }
}

function handleSatChange() {
    const satId = document.getElementById('sat-select').value;
    const sat = satelliteDataList.find(s => s.id == satId);
    
    if (sat) {
        document.getElementById('sat-info-box').classList.remove('hidden');
        document.getElementById('sat-type').innerText = sat.type || '--';
        document.getElementById('sat-revisit').innerText = sat.revisit || '--';
        document.getElementById('sat-desc').innerText = sat.desc || '--';
        
        if (sat.recommended_capacity) {
            document.getElementById('capacity-limit').value = sat.recommended_capacity;
        }
    }
    
    updateTrack();
}

function addTarget() {
    const nameInput = document.getElementById('target-name');
    const latInput = document.getElementById('target-lat');
    const lonInput = document.getElementById('target-lon');
    const weightInput = document.getElementById('target-weight');
    const searchInput = document.getElementById('target-search');
    
    const name = nameInput.value.trim().toUpperCase() || `TGT-${targets.length + 1}`;
    const lat = parseFloat(latInput.value);
    const lon = parseFloat(lonInput.value);
    const weight = parseFloat(weightInput.value);
    
    if (isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
        alert('INVALID COORDINATES. Click on the map or use search.');
        return;
    }
    
    const id = `t_${Date.now()}`;
    targets.push({id, name, lat, lon, weight});
    
    // Create cinematic marker
    const icon = L.divIcon({
        className: 'custom-div-icon',
        html: `<div style="background:var(--text-accent);width:12px;height:12px;border-radius:50%;border:2px solid #000;box-shadow: 0 0 10px var(--text-accent);"></div><div style="color:#fff;font-size:11px;font-family:var(--font-mono);font-weight:700;margin-top:4px;white-space:nowrap;text-shadow:1px 1px 2px #000, -1px -1px 2px #000, 1px -1px 2px #000, -1px 1px 2px #000;">${name}</div>`,
        iconSize: [30, 42],
        iconAnchor: [6, 6]
    });
    const marker = L.marker([lat, lon], {icon}).addTo(map);
    targetMarkers[id] = marker;
    
    renderTargets();
    
    nameInput.value = '';
    latInput.value = '';
    lonInput.value = '';
    searchInput.value = '';
}

function renderTargets() {
    const list = document.getElementById('targets-list');
    list.innerHTML = '';
    targets.forEach(t => {
        const div = document.createElement('div');
        div.className = 'target-item';
        div.innerHTML = `
            <div>
                <strong style="color:var(--text-main); font-family:var(--font-mono); font-size:13px;">${t.name}</strong> 
                <span style="color:var(--text-dim); font-size:11px;">[PRI: ${t.weight}]</span><br>
                <span style="font-size:11px;color:var(--text-dim);font-family:var(--font-mono)">LAT: ${t.lat.toFixed(4)} &nbsp; LON: ${t.lon.toFixed(4)}</span>
            </div>
            <button class="del-btn" onclick="removeTarget('${t.id}')">×</button>
        `;
        list.appendChild(div);
    });
}

window.removeTarget = function(id) {
    targets = targets.filter(t => t.id !== id);
    if (targetMarkers[id]) {
        map.removeLayer(targetMarkers[id]);
        delete targetMarkers[id];
    }
    renderTargets();
}

async function updateTrack() {
    const satId = document.getElementById('sat-select').value;
    if (!satId) return;
    
    try {
        const res = await fetch(`${API_BASE}/track?satellite_id=${satId}`);
        const data = await res.json();
        
        if (trackLayer) map.removeLayer(trackLayer);
        
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
        
        // Red orbital track for contrast against satellite base
        trackLayer = L.polyline(lines, {color: 'rgba(248, 113, 113, 0.8)', weight: 2, dashArray: '5,5'}).addTo(map);
        
        const currentPos = latlngs[0];
        L.circleMarker(currentPos, {
            radius: 5,
            color: '#fff',
            weight: 2,
            fillColor: 'var(--text-alert)',
            fillOpacity: 1
        }).addTo(trackLayer);
        
    } catch (e) {
        console.error('Failed to load track', e);
    }
}

async function computeSchedule() {
    const satId = document.getElementById('sat-select').value;
    const capacity = parseInt(document.getElementById('capacity-limit').value);
    const maxCloud = parseFloat(document.getElementById('max-cloud-cover').value) || 100;
    const powerPer = parseFloat(document.getElementById('power-per-pass').value) || 150;
    const storagePer = parseFloat(document.getElementById('storage-per-pass').value) || 12;
    
    if (targets.length === 0) {
        alert('NO TARGETS DEFINED. Please add at least one location.');
        return;
    }
    
    const btn = document.getElementById('btn-compute');
    btn.disabled = true;
    btn.innerText = 'COMPUTING...';
    
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
        
        if (!res.ok) throw new Error('API ERROR');
        
        const data = await res.json();
        currentSchedule = data;
        renderSchedule(data);
        document.getElementById('btn-export').disabled = false;
        
    } catch (e) {
        showError('SCHEDULE COMPUTATION FAILED');
    } finally {
        btn.disabled = false;
        btn.innerText = 'GENERATE SCHEDULE';
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
        container.innerHTML = '<div class="empty-state">NO VISIBILITY IN NEXT 48H</div>';
        return;
    }
    
    const all = [...data.scheduled.map(p => ({...p, status: 'SCHEDULED'})), 
                 ...data.rejected.map(p => ({...p, status: 'REJECTED'}))]
                .sort((a,b) => new Date(a.rise_time) - new Date(b.rise_time));
                
    all.forEach(p => {
        const cc = p.cloud_cover;
        const ccClass = cc < 30 ? 'cc-good' : (cc < 70 ? 'cc-ok' : 'cc-bad');
        const bgClass = cc < 30 ? 'bg-good' : (cc < 70 ? 'bg-ok' : 'bg-bad');
        const ccText = cc !== null ? `${cc}%` : 'N/A';
        
        const isRej = p.status === 'REJECTED';
        
        const el = document.createElement('div');
        el.className = `schedule-item ${isRej ? 'rejected' : ''}`;
        
        el.innerHTML = `
            <div class="sched-header">
                <div class="sched-target">${p.target_name}</div>
                <div class="sched-status ${isRej ? 'status-rej' : 'status-appr'}">${p.status}</div>
            </div>
            <div class="sched-body">
                <div class="sched-row">
                    <span>OVERPASS UTC:</span>
                    <span class="sched-val">${p.culminate_time.replace('T', ' ').substring(0, 16)}</span>
                </div>
                <div class="sched-row">
                    <span>MAX ELEVATION:</span>
                    <span class="sched-val">${p.max_elevation_deg}°</span>
                </div>
                
                <div style="margin-top:8px;">
                    <div style="display:flex; justify-content:space-between;">
                        <span>FORECAST CLOUD COVER:</span>
                        <span class="sched-val ${ccClass}">${ccText}</span>
                    </div>
                    ${cc !== null ? `
                    <div class="weather-bar-container">
                        <div class="weather-bar ${bgClass}" style="width: ${cc}%"></div>
                    </div>` : ''}
                </div>
                
                ${p.reject_reason ? `<div style="margin-top:8px;color:var(--text-alert)">REASON: ${p.reject_reason}</div>` : ''}
            </div>
            <div class="sched-footer">
                <span>PRIORITY: ${p.target_weight}</span>
                <button class="btn btn-small btn-secondary btn-audit">VIEW AUDIT LOG</button>
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
        <div class="audit-row"><span class="audit-label">ORBIT MODEL</span><span>SGP4</span></div>
        <div class="audit-row"><span class="audit-label">TLE SOURCE</span><span>${tleInfo.name}</span></div>
        <div class="audit-row"><span class="audit-label">CULMINATE TIME (UTC)</span><span>${pass.culminate_time.replace('T', ' ')}</span></div>
        <div class="audit-row"><span class="audit-label">MAX ELEVATION</span><span>${pass.max_elevation_deg}°</span></div>
        <div class="audit-row"><span class="audit-label">FORECAST CLOUD COVER</span><span>${pass.cloud_cover !== null ? pass.cloud_cover + '%' : 'UNAVAILABLE'}</span></div>
        <div class="audit-row"><span class="audit-label">COMPUTED SCORE</span><span>${pass.score ? pass.score.toFixed(2) : 'N/A'}</span></div>
        <div class="audit-row"><span class="audit-label">AUDIT TRAIL</span><span style="font-size:10px;text-align:right;">${pass.audit_reason || 'N/A'}</span></div>
        <div class="audit-row"><span class="audit-label">SCHEDULING DECISION</span><span style="color:${pass.reject_reason ? 'var(--text-alert)' : 'var(--text-success)'}">${pass.reject_reason ? 'REJECTED' : 'SCHEDULED'}</span></div>
        ${pass.reject_reason ? `<div class="audit-row"><span class="audit-label">REJECTION REASON</span><span style="color:var(--text-alert)">${pass.reject_reason}</span></div>` : ''}
    `;
    
    modal.classList.remove('hidden');
}

function exportCSV() {
    if (!currentSchedule) return;
    
    let csv = "TARGET,STATUS,RISE_TIME,CULMINATE_TIME,SET_TIME,MAX_ELEV,CLOUD_COVER,SCORE,REASON,AUDIT_TRAIL\n";
    
    const all = [...currentSchedule.scheduled.map(p => ({...p, status: 'SCHEDULED'})), 
                 ...currentSchedule.rejected.map(p => ({...p, status: 'REJECTED'}))]
                .sort((a,b) => new Date(a.rise_time) - new Date(b.rise_time));
                
    all.forEach(p => {
        csv += `${p.target_name},${p.status},${p.rise_time},${p.culminate_time},${p.set_time},${p.max_elevation_deg},${p.cloud_cover},${p.score},"${p.reject_reason || 'Scheduled'}","${p.audit_reason || ''}"\n`;
    });
    
    const blob = new Blob([csv], {type: 'text/csv;charset=utf-8;'});
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = `skywindow_schedule_${Date.now()}.csv`;
    
    document.body.appendChild(a);
    a.click();
    
    setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }, 100);
}

function showError(msg) {
    document.getElementById('conn-status').className = 'status-err';
    document.getElementById('conn-status').innerText = 'SYS ERR: ' + msg;
    setTimeout(() => {
        document.getElementById('conn-status').className = 'status-ok';
        document.getElementById('conn-status').innerText = 'CONN: STABLE';
    }, 3000);
}
