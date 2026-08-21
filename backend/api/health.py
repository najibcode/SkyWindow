from fastapi import APIRouter
from typing import List
from models.schemas import DataSourceHealth
from services.health_service import health_service

router = APIRouter(prefix="/api", tags=["Health & Data Sources"])

@router.get("/health")
@router.get("/data-sources", response_model=List[DataSourceHealth])
async def check_data_sources():
    """Returns real-time health checks, latencies, update frequencies, and license attributions for all data providers."""
    return await health_service.check_all_sources()
