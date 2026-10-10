from app.agents.planner import build_evidence, fallback_brief
from app.engine import risk as R

def test_grounded_evidence():
    assert R.SITES
    e = build_evidence(R.SITES[0]['id'], 150)
    assert e['hotspot_id'] == R.SITES[0]['id']
    assert len(e['options']) == 3
    assert all(0 <= x['after'] <= 100 for x in e['options'])
    assert 'guarantees' in e['limitations'][0]

def test_unknown_site():
    assert build_evidence(9999999, 150) is None

def test_fallback():
    e = build_evidence(R.SITES[0]['id'], 100)
    result = fallback_brief(e)
    assert result['mode'] == 'deterministic_fallback'
    assert result['evidence'] == e

from app.agents.planner import valid_explanation, configured_providers

def test_rejects_numeric_hallucinations_and_instruction_acknowledgement():
    assert not valid_explanation('Okay, I understand. I will adhere to the prompt and the rules.')
    assert not valid_explanation('The flood probability is 82% and the score is 56.')
    assert valid_explanation('The terrain is lower than nearby surroundings, and converging flow contributes to modelled susceptibility, not observed flooding.')

def test_provider_priority(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    monkeypatch.setenv('AI_PROVIDER', 'auto')
    assert configured_providers() == ['gemini', 'ollama']
    monkeypatch.setenv('AI_PROVIDER', 'ollama')
    assert configured_providers() == ['ollama', 'gemini']
    monkeypatch.delenv('GEMINI_API_KEY')
    assert configured_providers() == ['ollama']
