import pytest
from app.services import weather
from app.agents.planner import valid_explanation, fallback_brief, build_evidence
from app.engine import risk as R

@pytest.mark.parametrize('bad', [None, float('nan'), float('inf'), -1, '0', True])
def test_incomplete_weather_is_not_dry_weather(monkeypatch, bad):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'hourly': {'precipitation': [0]*23+[bad], 'time': ['2026-10-11T00:00']*24}}
    monkeypatch.setattr(weather.requests, 'get', lambda *a, **k: Response())
    weather._fetch.cache_clear()
    with pytest.raises(ValueError): weather.forecast_rain_mm()

def test_forecast_preserves_period_and_fetch_time(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'hourly': {'precipitation': [1]*24, 'time': [f'2026-10-11T{h:02d}:00' for h in range(24)]}}
    monkeypatch.setattr(weather.requests, 'get', lambda *a, **k: Response())
    weather._fetch.cache_clear()
    result = weather.forecast_rain_mm()
    assert result['rainfall_mm'] == 24
    assert result['period_start'] == '2026-10-11T00:00'
    assert result['period_end'] == '2026-10-11T23:00'
    assert result['fetched_at'] and result['timezone'] == 'Asia/Kolkata'
    weather._fetch.cache_clear()

def test_ai_safety_claim_is_rejected_and_grid_is_described_correctly():
    assert not valid_explanation('This road is guaranteed to remain safe and the drainage system will prevent flooding during every storm.')
    assert not valid_explanation('The drainage works well and the surface is dry throughout this entire location.')
    text = fallback_brief(build_evidence(R.SITES[0]['id'],100))['summary']
    assert 'analysis cells' in text and '30 m-scale' not in text
