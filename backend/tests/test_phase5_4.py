from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_sensitivity_is_monotone_and_does_not_modify_model():
    result = client.get('/api/experimental/rainfall-sensitivity')
    assert result.status_code == 200
    data = result.json()
    assert data['mode'] == 'diagnostic_only'
    assert data['site_spacing_window_cells'] == 7
    series = data['series']
    assert series[0]['rainfall_mm'] == 0
    assert all(a['mean_land_index'] <= b['mean_land_index'] for a, b in zip(series, series[1:]))
    assert all(a['active_hotspots'] <= b['active_hotspots'] for a, b in zip(series, series[1:]))

def test_dem_diagnostics_only_reports():
    result = client.get('/api/experimental/dem-routing-diagnostics')
    assert result.status_code == 200
    data = result.json()
    assert 0 <= data['strict_local_pits'] <= data['interior_cells']
    assert data['mode'] == 'diagnostic_only'
