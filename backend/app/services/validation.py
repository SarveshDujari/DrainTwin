"""Phase 2: source-traceable evaluation. Pending/provisional coordinates NEVER count as validation."""
import csv
from functools import lru_cache
from pathlib import Path
import numpy as np
from ..engine import risk as R

CSV_PATH = Path(__file__).resolve().parents[2] / 'data' / 'validation' / 'ground_truth.csv'
EARTH_M = 6371000.0

def distance_m(a_lat, a_lon, b_lat, b_lon):
    a, b, c, d = map(np.radians, np.broadcast_arrays(a_lat, a_lon, b_lat, b_lon))
    da, db = c-a, d-b
    h = np.sin(da/2)**2 + np.cos(a)*np.cos(c)*np.sin(db/2)**2
    return 2*EARTH_M*np.arcsin(np.sqrt(np.clip(h,0,1)))

def read_points(path=None, include_provisional=False):
    path = CSV_PATH if path is None else path
    with open(path, encoding='utf-8', newline='') as f:
        rows=list(csv.DictReader(f))
    usable=[]
    for x in rows:
        status=x['verification_status'].strip().lower()
        if status!='verified' and not (include_provisional and status=='provisional'):
            continue
        try: lat,lon=float(x['latitude']),float(x['longitude'])
        except (TypeError,ValueError): continue
        if not (-90<=lat<=90 and -180<=lon<=180): continue
        usable.append({**x,'latitude':lat,'longitude':lon})
    return rows,usable

def within_bounds(lat,lon,bounds=R.BOUNDS):
    s,w,n,e=bounds
    return s<=lat<=n and w<=lon<=e

def evaluate_sites(points, sites, bounds, radius_m=300, top_n=12, seed=42, samples=25000):
    """Coverage lift uses a uniformly sampled *study-area* null, not an invented expected hit count.

    This is a spatial area-coverage baseline, NOT a calibrated random-site statistical test.
    """
    if radius_m<=0 or top_n<0: raise ValueError('radius_m must be positive; top_n nonnegative')
    valid=[x for x in points if within_bounds(x['latitude'],x['longitude'],bounds)]
    selected=sites[:top_n]
    hits=[]
    for p in valid:
        d=min((float(distance_m(p['latitude'],p['longitude'],h['lat'],h['lng'])) for h in selected),default=float('inf'))
        hits.append({'id':p['id'],'name':p['name'],'distance_m':round(d,1) if np.isfinite(d) else None,
                     'captured':bool(d<=radius_m)})
    s,w,n,e=bounds
    rng=np.random.default_rng(seed)
    # Equal-area latitude sampling (sin(lat) uniform); longitude uniform.
    lat=np.degrees(np.arcsin(rng.uniform(np.sin(np.radians(s)),np.sin(np.radians(n)),samples)))
    lon=rng.uniform(w,e,samples)
    covered=np.zeros(samples,dtype=bool)
    for h in selected:
        covered |= distance_m(lat,lon,h['lat'],h['lng'])<=radius_m
    chance=float(covered.mean())
    rate=sum(h['captured'] for h in hits)/len(hits) if hits else None
    return {'evaluated':len(valid),'captured':sum(h['captured'] for h in hits),
            'hit_rate':round(rate,4) if rate is not None else None,
            'area_coverage_baseline':round(chance,4),
            'lift_vs_area_coverage':round(rate/chance,3) if rate is not None and chance else None,
            'radius_m':radius_m,'top_n':top_n,'matches':hits,
            'baseline_note':'Area coverage of 300 m buffers around predicted sites; not a random-site significance test.'}

def _hotspots(rain, terrain_only=False):
    if not terrain_only:
        return R.run(rain)['hotspots']
    # Ablation keeps the SAME fixed candidate sites, and removes the drainage factor.
    w={k:v for k,v in R.W.items() if k!='drain'}
    tot=sum(w.values()); w={k:v/tot for k,v in w.items()}
    risk,_=R.compute(rain,w=w)
    sites=[]
    for site in R.SITES:
        score=float(risk[site['r'],site['c']])
        if score>=R.ACTIVE:
            lat,lng=R.latlng(site['r'],site['c'])
            sites.append({'id':site['id'],'lat':lat,'lng':lng,'risk_score':round(score,2)})
    return sorted(sites,key=lambda x:-x['risk_score'])

def report(rain=150, top_n=12, radius_m=300, include_provisional=False):
    return _cached_report(rain, top_n, radius_m, include_provisional, CSV_PATH.stat().st_mtime_ns)

@lru_cache(maxsize=32)
def _cached_report(rain, top_n, radius_m, include_provisional, _csv_mtime):
    if not 0<=rain<=R.MAX_RAIN: raise ValueError('rain out of range')
    if not 1<=top_n<=500: raise ValueError('top_n out of range')
    if not 50<=radius_m<=2000: raise ValueError('radius out of range')
    all_rows, usable=read_points(include_provisional=include_provisional)
    inside=[p for p in usable if within_bounds(p['latitude'],p['longitude'])]
    normal=_hotspots(rain)
    baseline=_hotspots(rain,terrain_only=True)
    result=evaluate_sites(inside,normal,R.BOUNDS,radius_m,top_n)
    terrain=evaluate_sites(inside,baseline,R.BOUNDS,radius_m,top_n)
    curve=[{'top_n':k,'hit_rate':evaluate_sites(inside,normal,R.BOUNDS,radius_m,k,samples=3000)['hit_rate']}
           for k in sorted(set([1,3,5,8,12,20,30,min(len(normal),50)])) if k>0]
    return {'status':'evaluated' if len(inside) >= 10 and not include_provisional else ('provisional' if inside else 'awaiting_verified_coordinates'),
            'study_area':'Central Delhi', 'rainfall_mm':rain,'data_source':R.DATA_SOURCE,
            'candidates':len(all_rows),'verified_total':sum(p['verification_status']=='verified' for p in all_rows),
            'verified_inside':len([p for p in inside if p['verification_status']=='verified']),
            'excluded_outside':len(usable)-len(inside),
            'pending_review':sum(p['verification_status']!='verified' for p in all_rows),
            'metrics_display_allowed':len(inside)>=10 and not include_provisional,
            'evaluation_protocol':'Fixed reference: 150 mm rainfall, top 12 sites, 300 m radius; no rainfall-event matching.',
            'result':result,'terrain_only':terrain,'no_drain':terrain,'capture_curve':curve,
            'points':[{'id':p['id'],'name':p['name'],'lat':p['latitude'],'lng':p['longitude'],
                       'status':p['verification_status'],'source_url':p['source_url']} for p in inside],
            'caveats':['Historical reports are not synchronized to the rainfall scenario.',
                       'Official watchlist entries are not all observed flood events.',
                       'Coordinates require human landmark verification before use.',
                       'Fixed hotspot candidates make the terrain-only comparison an ablation, not an independent baseline.',
                       'Nearby reported points may not be independent observations.',
                       'With fewer than 10 verified in-area points, quantitative performance claims are withheld.']}
