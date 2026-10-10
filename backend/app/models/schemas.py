from pydantic import BaseModel, Field

class SimulateIn(BaseModel):
    rainfall_mm: float = Field(100, ge=0, le=250)

class InterventionIn(BaseModel):
    hotspot_id: int
    type: str
    rainfall_mm: float = Field(100, ge=0, le=250)
