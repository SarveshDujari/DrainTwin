"""Urban Flood Risk Index v2 (UFRI): transparent scoring, no trained model.

    risk = 100 * hazard^GAMMA * (0.25 + 0.75 * susceptibility)

hazard          rain-driven: SCS Curve Number runoff depth (exactly 0 for light rain on permeable ground)
susceptibility  static: runoff convergence, local depression, flatness, distance to drains

Hotspot "sites" are fixed local maxima of the maximum-rain map, so their IDs and positions never change
with the slider; a site is *active* (shown) when its current score passes ACTIVE.
"""
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.ndimage import label, maximum_filter, uniform_filter

from .interventions import INTERVENTIONS, recommend

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_real = DATA_DIR / "delhi_grid.npz"
DATA_SOURCE = "real" if _real.exists() else "demo"          # falls back to the synthetic demo grid
_D = np.load(_real if _real.exists() else DATA_DIR / "delhi_grid_demo.npz")

BOUNDS = [float(v) for v in _D["bounds"]]                    # S, W, N, E
ROWS, COLS = _D["elevation"].shape
MAX_RAIN = 250                                               # mm / 24 h (slider maximum)
LEVELS = (25, 45, 65)                                        # moderate / high / critical cut-offs
ACTIVE = LEVELS[1]                                           # score at which a site counts as a hotspot
W = dict(flow=.35, elev=.30, slope=.20, drain=.15)           # susceptibility weights
GAMMA = .6
CN_BASE, CN_SPAN = 61, 37                                    # curve number: open ground 61 -> fully paved 98 (assumption)

def _norm(a):
    lo, hi = np.percentile(a, [2, 98])                       # robust min-max, outliers can't squash the scale
    return np.clip((a - lo) / (hi - lo + 1e-9), 0, 1)

WATER = _D["water"].astype(bool) if "water" in _D.files else np.zeros((ROWS, COLS), bool)
IMPERV = _D["imperviousness"]
ACC, SLOPE, DIST = _D["flow_acc"], _D["slope"], _D["drain_dist"]
RELIEF = uniform_filter(_D["elevation"], 7, mode="nearest") - _D["elevation"]   # metres below the ~1.7 km neighbourhood
T = dict(flow=_norm(np.log1p(ACC)), elev=_norm(RELIEF), slope=1 - _norm(SLOPE), drain=_norm(DIST))
MED = {k: float(np.median(v)) for k, v in T.items()}
MED_IMP = float(np.median(IMPERV))
CELL_M = (BOUNDS[2] - BOUNDS[0]) * 111_000 / ROWS

def runoff_depth(rain, imp, dcn=0.0):
    """SCS-CN: Q = (P - Ia)^2 / (P + 0.8 S) for P > Ia = 0.2 S, otherwise 0."""
    cn = np.clip(CN_BASE + CN_SPAN * imp + dcn, 30, 98)
    s = 25400 / cn - 254
    ia = 0.2 * s
    return np.where(rain > ia, (rain - ia) ** 2 / (rain + 0.8 * s), 0.0)

REF_RAIN = 175                                               # storm at which a fully paved cell reaches hazard 1.0
Q_REF = float(runoff_depth(REF_RAIN, 1.0))

def compute(rain, mask=None, iv=None, w=None, dcn=0.0, gamma=GAMMA):
    """Return (risk 0-100, runoff depth mm) grids. `iv` applies an intervention inside `mask`."""
    w, imp, t, retain = w or W, IMPERV, T, 1.0
    if iv:
        e = iv["effects"]
        grow = lambda base, m: np.where(mask, base * m, base)
        imp = grow(IMPERV, e.get("imperv", 1))
        t = {k: grow(v, e.get(k, 1)) for k, v in T.items()}
        retain = grow(np.ones_like(IMPERV), e.get("retain", 1))
    q = runoff_depth(rain, imp, dcn) * retain
    susc = sum(w[k] * t[k] for k in w)
    risk = np.clip(100 * np.maximum(q / Q_REF, 0) ** gamma * (0.25 + 0.75 * susc), 0, 100)
    return np.where(WATER, 0.0, risk), q

def severity(score):
    return "low" if score < LEVELS[0] else "moderate" if score < LEVELS[1] else "high" if score < LEVELS[2] else "critical"

def latlng(r, c):
    s, w, n, e = BOUNDS
    return n - (r + .5) * (n - s) / ROWS, w + (c + .5) * (e - w) / COLS

# ---- stable hotspot sites -------------------------------------------------------------------------------------
def _build_sites():
    risk, _ = compute(REF_RAIN)                              # mid-range storm: avoids the flat 100-cap of extreme rain
    peaks = (risk >= ACTIVE) & (risk >= maximum_filter(risk, size=7, mode="constant"))   # one peak per ~1.7 km
    lab, n = label(peaks, structure=np.ones((3, 3)))                                      # merge exact ties
    sites = []
    for i in range(1, n + 1):
        r, c = np.argwhere(lab == i)[0]
        sites.append(dict(r=int(r), c=int(c), peak=float(risk[r, c])))
    sites.sort(key=lambda s: (-s["peak"], s["r"], s["c"]))
    for i, s in enumerate(sites, 1):
        s["id"] = i
    return sites

SITES = _build_sites()
SR = np.array([s["r"] for s in SITES], int)
SC = np.array([s["c"] for s in SITES], int)

# ---- Monte Carlo: how robust is each hotspot to our own modelling assumptions? ----------------------------------
def _perturbations(n=100):
    rng = np.random.default_rng(7)                           # fixed seed -> repeatable results
    out = []
    for _ in range(n):
        w = {k: v * rng.uniform(.75, 1.25) for k, v in W.items()}
        tot = sum(w.values())
        out.append(({k: v / tot for k, v in w.items()}, rng.uniform(-4, 4), rng.uniform(.5, .7)))
    return out

PERT = _perturbations()

@lru_cache(maxsize=256)
def _mc(rain):
    stack = np.array([compute(rain, w=w, dcn=d, gamma=g)[0][SR, SC] for w, d, g in PERT])
    return (stack >= ACTIVE).mean(0) * 100, np.percentile(stack, 10, axis=0), np.percentile(stack, 90, axis=0)

# ---- explanations: only what is *unusual* about this spot --------------------------------------------------------
_TEXT = {
    "flow": lambda r, c: f"Approximate upstream contributing area: {float(ACC[r, c]) * CELL_M * CELL_M / 1e6:.2f} km² (unconditioned DEM routing; approximate)",
    "elev": lambda r, c: f"Sits {RELIEF[r, c]:.1f} m lower than its surroundings (~1.7 km), so water collects here",
    "slope": lambda r, c: f"Very flat ground ({SLOPE[r, c]:.2f}° vs area median {np.median(SLOPE):.2f}°), so water drains slowly",
    "drain": lambda r, c: f"Nearest mapped drain or waterway is ~{DIST[r, c]:.0f} m away (area median {np.median(DIST):.0f} m)",
    "imperv": lambda r, c: f"{IMPERV[r, c]:.0%} of the surface is built-up (area median {MED_IMP:.0%}), so little rain soaks in",
}

def explain(r, c):
    ex = {k: float(T[k][r, c] - MED[k]) for k in T}
    ex["imperv"] = float(IMPERV[r, c] - MED_IMP)
    wt = {**W, "imperv": .30}
    order = sorted(ex, key=lambda k: -wt[k] * ex[k])
    keys = [k for k in order if k != "slope" and ex[k] >= .15][:3] or [next(k for k in order if k != "slope")]
    return {k: k in keys for k in ex}, [_TEXT[k](r, c) for k in keys]

# ---- public API used by the routes ---------------------------------------------------------------------------------
def run(rain):
    risk, q = compute(rain)
    scores = risk[SR, SC]
    spots = []
    if SITES:
        conf, lo, hi = _mc(round(float(rain), 1))
        for rank, i in enumerate([i for i in sorted(range(len(scores)), key=lambda j: (-float(scores[j]), SITES[j]["id"])) if scores[i] >= ACTIVE], 1):
            s = SITES[i]
            flags, reasons = explain(s["r"], s["c"])
            lat, lng = latlng(s["r"], s["c"])
            spots.append(dict(
                id=s["id"], rank=rank, lat=lat, lng=lng, risk_score=round(float(scores[i])),
                severity=severity(scores[i]), score_range=[round(float(lo[i])), round(float(hi[i]))],
                confidence=round(float(conf[i])), stability_percent=round(float(conf[i])), stability_note="Fraction of tested parameter variations above the hotspot threshold; DEM elevation uncertainty not included.", built_up_percent=round(float(IMPERV[s["r"], s["c"]]) * 100),
                factors=flags, reasons=reasons,
                recommendations=[dict(type=t, label=INTERVENTIONS[t]["label"]) for t in recommend(flags)]))
    top = float(risk.max())
    area_fraction = float(np.mean(risk[~WATER] >= ACTIVE))
    # Study-area summary reflects affected area rather than the single worst raster cell.
    area_level = ('CRITICAL' if area_fraction >= .25 else 'HIGH' if area_fraction >= .10
                  else 'MODERATE' if area_fraction >= .01 else 'LOW')
    return {
        "risk_level": area_level, "risk_score": round(top), "data_source": DATA_SOURCE,
        "overall_level_note": "Heuristic area-coverage category (LOW <1%, MODERATE 1–10%, HIGH 10–25%, CRITICAL >=25% of non-water cells at index 45+); not a flood forecast.",
        "max_cell_susceptibility_index": round(top), "area_summary_basis": "share_of_study_area_at_index_45_or_above",
        "hotspots": spots, "total_hotspots": len(spots),
        "stats": {"area_at_risk_percent": round(float(np.mean(risk[~WATER] >= ACTIVE) * 100), 1),
                  "runoff_percent": round(float(q.mean() / rain * 100)) if rain > 0 else 0},
        "grid": {"bounds": BOUNDS, "rows": ROWS, "cols": COLS, "scores": np.rint(risk).astype(int).tolist()},
    }

def apply_intervention(site_id, kind, rain, radius=2):
    site = next((s for s in SITES if s["id"] == site_id), None)
    iv = INTERVENTIONS.get(kind)
    if not site or not iv:
        return None
    r, c = site["r"], site["c"]
    yy, xx = np.ogrid[:ROWS, :COLS]
    mask = (yy - r) ** 2 + (xx - c) ** 2 <= radius ** 2         # treat a ~500 m radius around the hotspot
    before = float(compute(rain)[0][r, c])
    after = float(compute(rain, mask, iv)[0][r, c])
    return {"before": round(before), "after": round(after), "label": iv["label"],
            "reduction_percent": round((before - after) / before * 100) if before > 0 else 0,
            "radius_m": int(round(radius * CELL_M, -1)),
            "note": "Estimated relative reduction, not an engineering guarantee."}
