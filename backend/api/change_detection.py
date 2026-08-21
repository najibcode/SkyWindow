from fastapi import APIRouter, HTTPException
from models.schemas import ChangeDetectionRequest, ChangeDetectionResult
from intelligence.change_detection import change_detection_engine

router = APIRouter(prefix="/api/change-detection", tags=["Change Detection"])

@router.post("", response_model=ChangeDetectionResult)
async def compute_change(req: ChangeDetectionRequest):
    """Computes multi-temporal Earth Observation delta and surface expansion metrics."""
    try:
        return await change_detection_engine.compute_temporal_change(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Change detection error: {str(e)}")
