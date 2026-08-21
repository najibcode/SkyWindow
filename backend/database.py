import sqlite3
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from config import settings

DB_PATH = settings.db_path

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Existing forecast_log table (preserve exact compatibility)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forecast_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_name TEXT,
            lat REAL,
            lon REAL,
            pass_time TEXT,
            predicted_cloud_cover REAL,
            prediction_made_at TEXT,
            actual_cloud_cover REAL,
            actual_recorded_at TEXT
        )
    ''')
    
    # 2. Disaster Events Cache & History
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS disaster_events (
            event_id TEXT PRIMARY KEY,
            name TEXT,
            event_type TEXT,
            category TEXT,
            status TEXT,
            severity TEXT,
            latitude REAL,
            longitude REAL,
            depth_km REAL,
            magnitude REAL,
            wind_speed_kmh REAL,
            affected_area_km2 REAL,
            estimated_population INTEGER,
            risk_score REAL,
            start_time TEXT,
            last_updated TEXT,
            source_provider TEXT,
            raw_geojson TEXT,
            provenance_json TEXT,
            timeline_json TEXT,
            infrastructure_json TEXT,
            recommended_sensor TEXT
        )
    ''')
    
    # 3. Alert Rules
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_rules (
            id TEXT PRIMARY KEY,
            name TEXT,
            disaster_type TEXT,
            min_severity TEXT,
            min_magnitude REAL,
            max_distance_km REAL,
            center_lat REAL,
            center_lon REAL,
            notify_email TEXT,
            notify_webhook TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT
        )
    ''')
    
    # 4. Alert Items History
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_history (
            id TEXT PRIMARY KEY,
            rule_id TEXT,
            rule_name TEXT,
            disaster_id TEXT,
            disaster_name TEXT,
            severity TEXT,
            title TEXT,
            message TEXT,
            created_at TEXT,
            is_read INTEGER DEFAULT 0,
            source TEXT
        )
    ''')
    
    # 5. Monitored Areas / Watchlists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitored_areas (
            id TEXT PRIMARY KEY,
            name TEXT,
            latitude REAL,
            longitude REAL,
            radius_km REAL,
            monitored_types TEXT,
            created_at TEXT,
            notes TEXT
        )
    ''')
    
    # 6. Mission Tasks / Schedules
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mission_tasks (
            id TEXT PRIMARY KEY,
            satellite_id INTEGER,
            satellite_name TEXT,
            disaster_id TEXT,
            task_name TEXT,
            scheduled_passes_json TEXT,
            stats_json TEXT,
            created_at TEXT,
            status TEXT
        )
    ''')
    
    # 7. Intelligence Reports
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intelligence_reports (
            id TEXT PRIMARY KEY,
            title TEXT,
            disaster_id TEXT,
            report_type TEXT,
            summary TEXT,
            content_json TEXT,
            created_at TEXT,
            author TEXT
        )
    ''')
    
    # 8. Data Sources Health Record
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS data_source_status (
            source_id TEXT PRIMARY KEY,
            name TEXT,
            provider TEXT,
            category TEXT,
            endpoint TEXT,
            status TEXT,
            latency_ms INTEGER,
            last_check TEXT,
            last_success TEXT,
            error_detail TEXT
        )
    ''')
    
    # Add indexes for speed
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_disaster_type ON disaster_events(event_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_disaster_time ON disaster_events(last_updated)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_time ON alert_history(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_forecast_time ON forecast_log(pass_time)')
    
    conn.commit()
    conn.close()

# Existing backward-compatible helpers
def log_prediction(target_name: str, lat: float, lon: float, pass_time: str, predicted_cloud_cover: float, prediction_made_at: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO forecast_log (target_name, lat, lon, pass_time, predicted_cloud_cover, prediction_made_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (target_name, lat, lon, pass_time, predicted_cloud_cover, prediction_made_at))
    conn.commit()
    conn.close()

def update_actual_forecast(pass_time: str, lat: float, lon: float, actual_cloud_cover: float, actual_recorded_at: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE forecast_log
        SET actual_cloud_cover = ?, actual_recorded_at = ?
        WHERE pass_time = ? AND lat = ? AND lon = ? AND actual_cloud_cover IS NULL
    ''', (actual_cloud_cover, actual_recorded_at, pass_time, lat, lon))
    conn.commit()
    conn.close()
    
def get_calibration_log() -> List[Dict]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM forecast_log ORDER BY id DESC LIMIT 100
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Save and query disaster events
def upsert_disaster_event(event_dict: Dict[str, Any]):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO disaster_events (
            event_id, name, event_type, category, status, severity,
            latitude, longitude, depth_km, magnitude, wind_speed_kmh,
            affected_area_km2, estimated_population, risk_score,
            start_time, last_updated, source_provider,
            raw_geojson, provenance_json, timeline_json,
            infrastructure_json, recommended_sensor
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_id) DO UPDATE SET
            status=excluded.status,
            severity=excluded.severity,
            last_updated=excluded.last_updated,
            magnitude=excluded.magnitude,
            wind_speed_kmh=excluded.wind_speed_kmh,
            affected_area_km2=excluded.affected_area_km2,
            estimated_population=excluded.estimated_population,
            risk_score=excluded.risk_score,
            raw_geojson=excluded.raw_geojson,
            provenance_json=excluded.provenance_json,
            timeline_json=excluded.timeline_json,
            infrastructure_json=excluded.infrastructure_json
    ''', (
        event_dict['event_id'],
        event_dict['name'],
        event_dict['event_type'],
        event_dict['category'],
        event_dict.get('status', 'Active'),
        event_dict['severity'],
        event_dict['latitude'],
        event_dict['longitude'],
        event_dict.get('depth_km'),
        event_dict.get('magnitude'),
        event_dict.get('wind_speed_kmh'),
        event_dict.get('affected_area_km2'),
        event_dict.get('estimated_population'),
        event_dict.get('risk_score', 50.0),
        event_dict.get('start_time', datetime.utcnow().isoformat()),
        event_dict.get('last_updated', datetime.utcnow().isoformat()),
        event_dict.get('source_provider', 'USGS/Open-Meteo'),
        json.dumps(event_dict.get('geometry')) if event_dict.get('geometry') else None,
        json.dumps(event_dict.get('provenance', {})),
        json.dumps(event_dict.get('timeline', [])),
        json.dumps(event_dict.get('exposed_infrastructure', {})),
        event_dict.get('recommended_sensor', 'SAR')
    ))
    conn.commit()
    conn.close()

def get_all_disasters_db() -> List[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM disaster_events ORDER BY last_updated DESC')
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        d = dict(r)
        if d.get('raw_geojson'):
            d['geometry'] = json.loads(d['raw_geojson'])
        if d.get('provenance_json'):
            d['provenance'] = json.loads(d['provenance_json'])
        if d.get('timeline_json'):
            d['timeline'] = json.loads(d['timeline_json'])
        if d.get('infrastructure_json'):
            d['exposed_infrastructure'] = json.loads(d['infrastructure_json'])
        results.append(d)
    return results

def get_disaster_by_id_db(event_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM disaster_events WHERE event_id = ?', (event_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    if d.get('raw_geojson'):
        d['geometry'] = json.loads(d['raw_geojson'])
    if d.get('provenance_json'):
        d['provenance'] = json.loads(d['provenance_json'])
    if d.get('timeline_json'):
        d['timeline'] = json.loads(d['timeline_json'])
    if d.get('infrastructure_json'):
        d['exposed_infrastructure'] = json.loads(d['infrastructure_json'])
    return d

init_db()
