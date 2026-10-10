from fastapi import APIRouter, HTTPException
from ..engine import risk as R
from ..models.schemas import InterventionIn
from ..services.weather import forecast_rain_mm

router = APIRouter()

@router.post("/intervention")
def intervention(body: InterventionIn):
    result = R.apply_intervention(body.hotspot_id, body.type, body.rainfall_mm)
    if result is None:
        raise HTTPException(404, "Unknown hotspot or intervention")
    return result

@router.get("/weather")
def weather():
    try:
        return forecast_rain_mm()
    except Exception:
        raise HTTPException(503, "Weather service unavailable")
