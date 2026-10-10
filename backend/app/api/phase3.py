from fastapi import APIRouter, Query
from ..engine.phase3 import summary, replay
router = APIRouter()

@router.get("/phase3/diagnostics")
def phase3_diagnostics(rainfall_mm: float = Query(150, ge=0, le=250)):
    return summary(rainfall_mm)

@router.get("/phase3/scenarios")
def phase3_scenarios():
    return replay()

from ..engine.phase3 import comparison, spatial_layers

@router.get('/phase3/compare')
def phase3_compare(rainfall_mm: float = Query(150, ge=0, le=250),
                   top_n: int = Query(12, ge=1, le=500),
                   radius_m: int = Query(300, ge=50, le=2000),
                   include_provisional: bool = False):
    return comparison(rainfall_mm, top_n, radius_m, include_provisional)

@router.get('/phase3/layers')
def phase3_layers(rainfall_mm: float = Query(150, ge=0, le=250)):
    return spatial_layers(rainfall_mm)


from ..engine.phase3 import rainfall_sensitivity, dem_routing_diagnostics

@router.get('/experimental/rainfall-sensitivity')
def experimental_rainfall_sensitivity():
    return rainfall_sensitivity()

@router.get('/experimental/dem-routing-diagnostics')
def experimental_dem_routing_diagnostics():
    return dem_routing_diagnostics()
