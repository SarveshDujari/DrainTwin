"""Optional AWS Strands Agent planner, with safe deterministic offline fallback."""
import os
import importlib.util
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..agents.planner import build_evidence, fallback_brief, strands_brief

router = APIRouter()

class BriefRequest(BaseModel):
    hotspot_id: int = Field(ge=1)
    rainfall_mm: float = Field(default=150, ge=0, le=250)
    use_agent: bool = False

@router.get('/agent/status')
def status():
    enabled = os.getenv('STRANDS_ENABLED') == '1'
    installed = importlib.util.find_spec('strands') is not None
    providers = []
    if enabled and installed:
        if os.getenv('GEMINI_API_KEY'):
            providers.append('gemini')
        providers.append('ollama')
    return {'strands_enabled': enabled and installed, 'providers': providers,
            'preferred_provider': os.getenv('AI_PROVIDER', 'auto'),
            'default_mode': 'deterministic_fallback',
            'caveat': 'Provider configuration is not a connectivity guarantee; failures fall back.'}

@router.post('/agent/brief')
def brief(body: BriefRequest):
    evidence = build_evidence(body.hotspot_id, body.rainfall_mm)
    if evidence is None:
        raise HTTPException(status_code=404, detail='Unknown hotspot ID')
    if body.use_agent:
        return strands_brief(evidence)
    return fallback_brief(evidence)
