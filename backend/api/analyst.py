from fastapi import APIRouter, HTTPException
from models.schemas import AnalystQueryRequest, AnalystResponse
from intelligence.ai_analyst import ai_analyst

router = APIRouter(prefix="/api/analyst", tags=["AI Analyst"])

@router.post("/query", response_model=AnalystResponse)
async def query_analyst(req: AnalystQueryRequest):
    """Processes natural language questions against live telemetry and provides verified evidence."""
    try:
        return await ai_analyst.answer_query(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Analyst error: {str(e)}")
