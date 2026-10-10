from fastapi import APIRouter
from ..engine import risk as R
from ..models.schemas import SimulateIn

router = APIRouter()

@router.get("/area")
def area():
    s, w, n, e = R.BOUNDS
    return {"name": "Central Delhi (study area)", "bounds": R.BOUNDS, "center": [(s + n) / 2, (w + e) / 2],
            "max_rain_mm": R.MAX_RAIN, "levels": R.LEVELS, "data_source": R.DATA_SOURCE}

@router.post("/simulate")
def simulate(body: SimulateIn):
    return R.run(body.rainfall_mm)
