import sqlite3
import os
from typing import List, Dict, Any
from pydantic import BaseModel

DB_PATH = "skywindow.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table for forecast tracking
    # stores past forecasts to compare with actual
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
    conn.commit()
    conn.close()

def log_prediction(target_name: str, lat: float, lon: float, pass_time: str, predicted_cloud_cover: float, prediction_made_at: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO forecast_log (target_name, lat, lon, pass_time, predicted_cloud_cover, prediction_made_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (target_name, lat, lon, pass_time, predicted_cloud_cover, prediction_made_at))
    conn.commit()
    conn.close()

def update_actual_forecast(pass_time: str, lat: float, lon: float, actual_cloud_cover: float, actual_recorded_at: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE forecast_log
        SET actual_cloud_cover = ?, actual_recorded_at = ?
        WHERE pass_time = ? AND lat = ? AND lon = ? AND actual_cloud_cover IS NULL
    ''', (actual_cloud_cover, actual_recorded_at, pass_time, lat, lon))
    conn.commit()
    conn.close()
    
def get_calibration_log() -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM forecast_log ORDER BY id DESC LIMIT 100
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

init_db()
