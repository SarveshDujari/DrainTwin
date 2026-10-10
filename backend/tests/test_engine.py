import numpy as np
from fastapi.testclient import TestClient
from app.engine import risk as R
from app.main import app

client = TestClient(app)
RAINS = range(0, 251, 10)

def test_risk_never_decreases_with_rain():
    prev = None
    for mm in RAINS:
        g, _ = R.compute(mm)
        if prev is not None:
            assert (g >= prev - 1e-9).all()
        prev = g

def test_light_rain_has_no_hotspots_and_no_colour():
    d = R.run(10)
    assert d["hotspots"] == [] and np.array(d["grid"]["scores"]).max() < R.LEVELS[0]

def test_hotspots_only_appear_never_vanish_as_rain_rises():
    seen = set()
    for mm in RAINS:
        ids = {h["id"] for h in R.run(mm)["hotspots"]}
        assert seen <= ids
        seen = ids

def test_ids_keep_their_location():
    pos = {}
    for mm in (100, 150, 200, 250):
        for h in R.run(mm)["hotspots"]:
            assert pos.setdefault(h["id"], (h["lat"], h["lng"])) == (h["lat"], h["lng"])

def test_hotspots_ranked_by_score_and_never_on_water():
    hs = R.run(200)["hotspots"]
    assert [h["risk_score"] for h in hs] == sorted((h["risk_score"] for h in hs), reverse=True)
    assert not R.WATER[R.SR, R.SC].any()

def test_confidence_and_range_are_sane():
    for h in R.run(150)["hotspots"]:
        assert 0 <= h["confidence"] <= 100 and h["score_range"][0] <= h["score_range"][1]
        assert h["reasons"]

def test_interventions_reduce_risk_and_unknown_ids_404():
    h = R.run(200)["hotspots"][0]
    for kind in ("drainage", "permeable_surface", "retention_basin"):
        r = client.post("/api/intervention", json={"hotspot_id": h["id"], "type": kind, "rainfall_mm": 200}).json()
        assert r["after"] < r["before"]
    assert client.post("/api/intervention", json={"hotspot_id": 9999, "type": "drainage"}).status_code == 404

def test_simulate_endpoint_shape():
    d = client.post("/api/simulate", json={"rainfall_mm": 120}).json()
    assert d["total_hotspots"] == len(d["hotspots"]) and len(d["grid"]["scores"]) == R.ROWS
