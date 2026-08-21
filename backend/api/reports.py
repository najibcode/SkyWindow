from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
from services.report_service import report_service

router = APIRouter(prefix="/api/reports", tags=["Reports & Briefings"])

@router.post("/generate/{disaster_id}")
async def generate_report(disaster_id: str):
    """Generates an executive disaster intelligence briefing for an incident."""
    try:
        return await report_service.generate_incident_report(disaster_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")

@router.get("")
def list_reports():
    """Lists recent intelligence reports."""
    return report_service.get_saved_reports()
