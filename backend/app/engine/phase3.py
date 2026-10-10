"""Phase 3 experimental spatial signals, OFF by default until ground-truth validation.

All calculations use the existing 64x64 DEM grid; interpolating to 128x128 would
NOT add physical resolution. OSM data are waterways, not a verified storm-drain network.
"""
from functools import lru_cache
import numpy as np
from scipy.ndimage import distance_transform_edt, maximum_filter
from . import risk as R

@lru_cache(maxsize=1)
def diagnostics():
    elevation = np.asarray(R._D["elevation"], dtype=float)
    # Approximate vertical difference to nearest mapped waterway using existing distance grid.
    # This is NOT true HAND (height above nearest hydrologically connected drainage).
    distance = np.asarray(R.DIST, dtype=float)
    cell_m = float(R.CELL_M)
    close = distance <= max(250, cell_m)
    if close.any():
        from scipy.ndimage import distance_transform_edt
        _, indices = distance_transform_edt(~close, return_indices=True)
        reference = elevation[tuple(indices)]
        relative = elevation - reference
    else:
        relative = np.zeros_like(elevation)
    # Terrain-driven local runoff-convergence potential (not a flow-routing simulation).
    convergence = np.log1p(np.maximum(R.ACC, 0))
    convergence = R._norm(convergence)
    near_drain = np.exp(-distance / 500.0)
    low_lying = np.clip(-relative / 3.0, 0, 1)
    proxy = np.clip(.45 * convergence + .35 * low_lying + .20 * near_drain, 0, 1)
    proxy = np.where(R.WATER, 0, proxy)
    return {"relative_height_m": relative, "convergence": convergence,
            "near_waterway": near_drain, "experimental_proxy": proxy}

def summary(rain=150):
    if not 0 <= rain <= R.MAX_RAIN:
        raise ValueError("Rainfall outside allowed range")
    d = diagnostics()
    risk, runoff_mm = R.compute(rain)
    # Runoff is local SCS-CN runoff depth, not accumulated discharge or flood depth.
    valid = ~R.WATER
    cell_area_m2 = (R.CELL_M * ((R.BOUNDS[3] - R.BOUNDS[1]) * 111_000 * np.cos(np.deg2rad(np.mean([R.BOUNDS[0], R.BOUNDS[2]]))) / R.COLS))
    total_m3 = float(np.sum(runoff_mm[valid]) * cell_area_m2 / 1000.0)
    return {"phase": 3, "mode": "experimental_diagnostics_only", "rainfall_mm": rain,
            "grid_shape": [R.ROWS, R.COLS], "grid_resolution_note": "Native 64x64 DEM grid; no fabricated 128x128 detail",
            "runoff_volume_m3_approx": round(total_m3),
            "runoff_volume_note": "Sum of cell runoff depths x approximate cell areas; not routed, calibrated or observed volume",
            "proxy_min": round(float(d["experimental_proxy"].min()), 3),
            "proxy_max": round(float(d["experimental_proxy"].max()), 3),
            "proxy_mean": round(float(d["experimental_proxy"].mean()), 3),
            "risk_max": round(float(risk.max()), 2),
            "caveats": ["Not validated against historical waterlogging", "OSM waterway proximity is not drainage capacity", "Relative elevation is not hydrologically connected HAND", "Not an underpass detector or hydraulic routing model"]}

def replay(storms=(25, 50, 100, 150, 200)):
    """Scenario sweep, NOT a replay of a historical storm event."""
    return {"type": "hypothetical_rainfall_sweep", "historical": False,
            "scenarios": [{"rainfall_mm": float(r), "active_hotspots": len(R.run(float(r))["hotspots"]),
                           "approx_runoff_volume_m3": summary(float(r))["runoff_volume_m3_approx"]} for r in storms]}


def comparison(rain=150, top_n=12, radius_m=300, include_provisional=False):
    """Exploratory ranking ablation using fixed candidate sites; never changes live scores.

    The experimental proxy is static. Blending it with rain-driven baseline scores
    is a *ranking experiment*, not a calibrated flood probability.
    """
    from ..services.validation import read_points, within_bounds, evaluate_sites
    if not 0 <= rain <= R.MAX_RAIN or not 1 <= top_n <= 500 or not 50 <= radius_m <= 2000:
        raise ValueError('Invalid comparison parameters')
    grid, _ = R.compute(rain)
    proxy = diagnostics()['experimental_proxy']
    # Fixed sites and fixed 20% proxy blend, declared before reviewing validation.
    baseline = grid[R.SR, R.SC]
    experimental = np.clip(0.8 * baseline + 0.2 * (100 * proxy[R.SR, R.SC]), 0, 100)
    def ranked(scores):
        result = []
        for i in np.argsort(-scores):
            if scores[i] < R.ACTIVE:
                continue
            lat, lng = R.latlng(int(R.SR[i]), int(R.SC[i]))
            result.append({'id': R.SITES[int(i)]['id'], 'lat': lat, 'lng': lng,
                           'risk_score': round(float(scores[i]), 2)})
        return result
    a, b = ranked(baseline), ranked(experimental)
    all_rows, usable = read_points(include_provisional=include_provisional)
    inside = [p for p in usable if within_bounds(p['latitude'], p['longitude'])]
    result = {
        'phase': 3, 'mode': 'experimental_ranking_ablation', 'rainfall_mm': rain,
        'blend': {'baseline_weight': 0.8, 'experimental_proxy_weight': 0.2},
        'top_n': top_n, 'radius_m': radius_m,
        'candidate_sites': len(R.SITES), 'baseline_active': len(a), 'experimental_active': len(b),
        'baseline_top': a[:top_n], 'experimental_top': b[:top_n],
        'verified_inside': sum(p['verification_status'] == 'verified' for p in inside),
        'provisional_inside': sum(p['verification_status'] == 'provisional' for p in inside),
        'validation_status': ('provisional_debug_only' if include_provisional else 'verified_only') if inside else 'insufficient_verified_points',
        'limitations': ['Fixed candidate sites: no new underpasses discovered',
                        'Experimental proxy is uncalibrated and is not a flood probability',
                        'Rainfall amount represents an assumed 24-hour total',
                        'Do not select blend weights based on evaluation locations'],
    }
    if inside:
        result['baseline_evaluation'] = evaluate_sites(inside, a, R.BOUNDS, radius_m, top_n)
        result['experimental_evaluation'] = evaluate_sites(inside, b, R.BOUNDS, radius_m, top_n)
    else:
        result['baseline_evaluation'] = None
        result['experimental_evaluation'] = None
    return result


def spatial_layers(rain=150):
    """Return real native-resolution arrays for inspection, not interpolated 128x128 data."""
    if not 0 <= rain <= R.MAX_RAIN:
        raise ValueError('Rainfall outside allowed range')
    risk, runoff = R.compute(rain)
    d = diagnostics()
    return {'phase': 3, 'mode': 'experimental_spatial_layers', 'bounds': R.BOUNDS,
            'rows': R.ROWS, 'cols': R.COLS, 'rainfall_mm': rain,
            'layers': {'baseline_risk': np.round(risk, 1).tolist(),
                       'runoff_mm': np.round(np.where(R.WATER, 0, runoff), 1).tolist(),
                       'terrain_convergence': np.round(d['convergence'], 3).tolist(),
                       'relative_height_m': np.round(d['relative_height_m'], 2).tolist(),
                       'waterway_proximity': np.round(d['near_waterway'], 3).tolist(),
                       'experimental_proxy': np.round(d['experimental_proxy'], 3).tolist()},
            'note': 'Native 64x64 diagnostic layers. Not flood depth, hydraulic routing, or observed inundation.'}


def rainfall_sensitivity(rainfalls=(0, 25, 50, 75, 100, 125, 150, 175, 200, 225, 250)):
    """Uncalibrated diagnostic: continuous risk coverage vs thresholded hotspot count.

    Does not change production site detection, scoring, or interventions.
    """
    output = []
    for rain in rainfalls:
        if not 0 <= rain <= R.MAX_RAIN:
            raise ValueError('Rainfall outside allowed range')
        grid, _ = R.compute(rain)
        land = grid[~R.WATER]
        site_scores = grid[R.SR, R.SC]
        output.append({
            'rainfall_mm': float(rain),
            'active_hotspots': int(np.count_nonzero(site_scores >= R.ACTIVE)),
            'area_above_25_percent': round(float(np.mean(land >= 25) * 100), 2),
            'area_above_45_percent': round(float(np.mean(land >= 45) * 100), 2),
            'area_above_65_percent': round(float(np.mean(land >= 65) * 100), 2),
            'mean_land_index': round(float(np.mean(land)), 2),
            'p90_land_index': round(float(np.percentile(land, 90)), 2),
        })
    return {
        'mode': 'diagnostic_only', 'threshold_index': R.ACTIVE,
        'site_spacing_window_cells': 7, 'stable_candidate_sites': len(R.SITES),
        'series': output,
        'limitations': [
            'Hotspot count is a thresholded local-maximum statistic and may change abruptly.',
            'Continuous coverage and percentile indices provide context but are not flood probabilities.',
            'No observed flood data or hydraulic calibration is used.',
        ],
    }


def dem_routing_diagnostics():
    """Inspect sinks in the existing DEM without filling or rerouting them."""
    from scipy.ndimage import minimum_filter
    elev = np.asarray(R._D['elevation'], dtype=float)
    interior = elev[1:-1, 1:-1]
    neighbors = np.stack([
        elev[1 + dr: elev.shape[0] - 1 + dr, 1 + dc: elev.shape[1] - 1 + dc]
        for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)
    ])
    pits = np.all(interior < neighbors, axis=0)
    return {
        'mode': 'diagnostic_only', 'interior_cells': int(interior.size),
        'strict_local_pits': int(pits.sum()),
        'pit_fraction_percent': round(float(pits.mean() * 100), 2),
        'notes': [
            'Strict 8-neighbor pits in the source elevation grid; flat areas are not counted.',
            'Pits may be DEM artefacts or real depressions. No automatic filling was performed.',
            'The existing flow accumulation grid is not recomputed by this endpoint.',
        ],
    }
