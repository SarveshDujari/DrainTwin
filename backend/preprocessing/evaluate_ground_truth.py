"""Reproducible Phase 2 evaluation; verified-only by default."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.validation import report

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--rainfall',type=float,default=150)
    p.add_argument('--top-n',type=int,default=12)
    p.add_argument('--radius',type=int,default=300)
    p.add_argument('--include-provisional',action='store_true',help='DIAGNOSTICS ONLY; not a validation result')
    p.add_argument('--output',default='data/validation/evaluation_report.json')
    a=p.parse_args()
    d=report(a.rainfall,a.top_n,a.radius,a.include_provisional)
    print(f"Candidates: {d['candidates']} | verified inside study area: {d['verified_inside']} | awaiting review: {d['pending_review']}")
    print(f"Evaluated coordinates: {d['result']['evaluated']} | status: {d['status']}")
    if d['result']['hit_rate'] is None:
        print('No verified, in-bounds points yet. No accuracy claim can be made.')
    else:
        for key in ('result','terrain_only'):
            r=d[key];print(f"{key}: {r['captured']}/{r['evaluated']} captured at {r['radius_m']}m; hit rate {r['hit_rate']:.1%}; area baseline {r['area_coverage_baseline']:.1%}; lift {r['lift_vs_area_coverage']}")
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(d,indent=2),encoding='utf-8')
    print('Saved:',out)
if __name__=='__main__':main()
