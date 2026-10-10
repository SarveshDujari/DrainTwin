import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.engine import risk as R
from app.engine.phase3 import comparison, spatial_layers

client = TestClient(app)

def test_spatial_layers_native_resolution_and_water_mask():
    data = spatial_layers(100)
    assert data['rows'] == R.ROWS and data['cols'] == R.COLS
    for name, layer in data['layers'].items():
        assert np.asarray(layer).shape == (R.ROWS, R.COLS), name
    assert np.asarray(data['layers']['experimental_proxy'])[R.WATER].max(initial=0) == 0

def test_comparison_does_not_change_live_baseline():
    before = R.run(150)
    result = comparison(150)
    assert result['baseline_active'] == len(before['hotspots'])
    assert result['validation_status'] == 'insufficient_verified_points'
    assert result['baseline_evaluation'] is None
    assert R.run(150) == before

def test_endpoints_and_validation():
    assert client.get('/api/phase3/compare').status_code == 200
    assert client.get('/api/phase3/layers?rainfall_mm=50').status_code == 200
    assert client.get('/api/phase3/compare?top_n=0').status_code == 422
    assert client.get('/api/phase3/layers?rainfall_mm=251').status_code == 422
