import uuid
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from models.schemas import AlertRule, AlertItem
from disasters.manager import disaster_manager
from database import get_db

class AlertService:
    """
    Evaluates customizable alert triggers against live disaster telemetry
    and maintains historical alert audit records.
    """
    def create_rule(self, rule: AlertRule) -> AlertRule:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO alert_rules (id, name, disaster_type, min_severity, min_magnitude, max_distance_km, center_lat, center_lon, notify_email, notify_webhook, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            rule.id or str(uuid.uuid4()), rule.name, rule.disaster_type, rule.min_severity,
            rule.min_magnitude, rule.max_distance_km, rule.center_lat, rule.center_lon,
            rule.notify_email, rule.notify_webhook, 1 if rule.is_active else 0,
            datetime.utcnow().isoformat() + "Z"
        ))
        conn.commit()
        conn.close()
        return rule

    def get_all_rules(self) -> List[AlertRule]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM alert_rules')
        rows = cursor.fetchall()
        conn.close()
        return [
            AlertRule(
                id=r['id'], name=r['name'], disaster_type=r['disaster_type'],
                min_severity=r['min_severity'], min_magnitude=r['min_magnitude'],
                max_distance_km=r['max_distance_km'], center_lat=r['center_lat'],
                center_lon=r['center_lon'], notify_email=r['notify_email'],
                notify_webhook=r['notify_webhook'], is_active=bool(r['is_active'])
            ) for r in rows
        ]

    def delete_rule(self, rule_id: str):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM alert_rules WHERE id = ?', (rule_id,))
        conn.commit()
        conn.close()

    async def evaluate_alerts(self) -> List[AlertItem]:
        rules = self.get_all_rules()
        disasters = await disaster_manager.get_all_disasters()
        now_iso = datetime.utcnow().isoformat() + "Z"
        generated_alerts = []

        for d in disasters:
            # Baseline critical alert generation
            if d.severity.value in ["Critical", "Severe"]:
                item = AlertItem(
                    id=f"ALT-{d.event_id[:8]}",
                    rule_id="DEFAULT_CRITICAL",
                    rule_name="Global Severe Event Monitor",
                    disaster_id=d.event_id,
                    disaster_name=d.name,
                    severity=d.severity.value,
                    title=f"🚨 {d.severity.value.upper()} ALERT: {d.name}",
                    message=f"Risk Score {d.risk_score}/100. Delineated {d.affected_area_km2:.1f} km² impact zone. Recommended sensor: {d.recommended_sensor}.",
                    created_at=now_iso,
                    source=d.provenance.provider
                )
                generated_alerts.append(item)

            # Custom rules matching
            for r in rules:
                if not r.is_active:
                    continue
                if r.disaster_type != "ALL" and r.disaster_type.lower() not in d.event_type.value.lower():
                    continue
                if r.min_magnitude and (d.magnitude or 0) < r.min_magnitude:
                    continue
                
                # Check spatial distance if center coordinates given
                if r.center_lat is not None and r.center_lon is not None:
                    dist_km = self._haversine(r.center_lat, r.center_lon, d.latitude, d.longitude)
                    if dist_km > r.max_distance_km:
                        continue

                item = AlertItem(
                    id=f"ALT-RULE-{r.id[:6]}-{d.event_id[:6]}",
                    rule_id=r.id,
                    rule_name=r.name,
                    disaster_id=d.event_id,
                    disaster_name=d.name,
                    severity=d.severity.value,
                    title=f"Rule Triggered [{r.name}]: {d.name}",
                    message=f"Event matched criteria (Severity: {d.severity.value}, Distance: within threshold).",
                    created_at=now_iso,
                    source=d.provenance.provider
                )
                generated_alerts.append(item)

        return generated_alerts

    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c

alert_service = AlertService()
