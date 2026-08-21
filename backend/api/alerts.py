from fastapi import APIRouter, HTTPException
from typing import List
from models.schemas import AlertRule, AlertItem
from services.alert_service import alert_service

router = APIRouter(prefix="/api/alerts", tags=["Alerts & Notifications"])

@router.get("", response_model=List[AlertItem])
async def list_active_alerts():
    """Returns dynamic alerts evaluated against live disaster thresholds."""
    return await alert_service.evaluate_alerts()

@router.get("/rules", response_model=List[AlertRule])
def list_alert_rules():
    """Returns configured alert rules."""
    return alert_service.get_all_rules()

@router.post("/rules", response_model=AlertRule)
def create_alert_rule(rule: AlertRule):
    """Creates a new automated alert monitoring rule."""
    return alert_service.create_rule(rule)

@router.delete("/rules/{rule_id}")
def delete_alert_rule(rule_id: str):
    """Deletes an alert monitoring rule."""
    alert_service.delete_rule(rule_id)
    return {"status": "ok", "deleted_rule_id": rule_id}
