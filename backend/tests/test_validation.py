import csv
from fastapi.testclient import TestClient
from app.main import app
from app.services.validation import evaluate_sites, read_points, within_bounds

def test_evaluation_hits_and_misses():
    b=[28.56,77.15,28.70,77.30]
    pts=[{'id':'a','name':'a','latitude':28.60,'longitude':77.20},
         {'id':'b','name':'b','latitude':28.69,'longitude':77.29},
         {'id':'outside','name':'outside','latitude':28.9,'longitude':77.2}]
    spots=[{'lat':28.60,'lng':77.20}]
    result=evaluate_sites(pts,spots,b,300,1,samples=1000)
    assert result['evaluated']==2 and result['captured']==1 and result['hit_rate']==0.5
    assert result['area_coverage_baseline']>=0

def test_zero_selected_sites():
    p=[{'id':'a','name':'a','latitude':28.6,'longitude':77.2}]
    r=evaluate_sites(p,[],[28.56,77.15,28.70,77.30],300,0,samples=100)
    assert r['captured']==0 and r['hit_rate']==0

def test_no_unverified_points_counted():
    rows,accepted=read_points()
    assert len(rows)>=30
    assert all(x['verification_status']=='verified' for x in accepted)

def test_endpoint_never_invents_accuracy():
    resp=TestClient(app).get('/api/validation')
    assert resp.status_code==200
    data=resp.json()
    assert data['candidates']>=30
    if data['verified_inside']==0:
        assert data['result']['hit_rate'] is None
