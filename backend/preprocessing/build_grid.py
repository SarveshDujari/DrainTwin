"""Run all steps and write data/delhi_grid.npz (same keys the backend already reads).

    python preprocessing/build_grid.py            # full build, results of each step are cached in data/raw/
    python preprocessing/build_grid.py --no-osm   # skip the drain step if OpenStreetMap servers are down
"""
import sys
import numpy as np
from common import S, W, N_, E, N, RAW
from process_dem import dem_features
from process_landcover import landcover_features
from extract_osm import drain_distance

def cached(name, fn):
    """Finished steps are saved, so a failure later never costs you the earlier work."""
    f = RAW / f"stage_{name}.npz"
    if f.exists():
        print("    using cached", f.name)
        d = np.load(f)
        return tuple(d[k] for k in d.files)
    out = fn()
    RAW.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(f, *out)
    return out

print("1/3 DEM ...");        elev, slope, acc = cached("dem", dem_features)
print("2/3 Land cover ..."); imp, water = cached("landcover", landcover_features)
print("3/3 OSM drains ...")
if "--no-osm" in sys.argv:
    print("    WARNING: skipping drains. The 'distance to drain' factor is switched off; rerun without --no-osm later.")
    drain = np.full((N, N), 500.0)
else:
    try:
        drain = drain_distance()
    except (RuntimeError, SystemExit):
        sys.exit("\nOpenStreetMap servers are busy. Your DEM and land-cover work is saved.\n"
                 "Retry in 10-15 minutes, or run:  python preprocessing/build_grid.py --no-osm")
out = RAW.parent / "delhi_grid.npz"
np.savez_compressed(out, elevation=elev, slope=slope, imperviousness=imp,
                    drain_dist=drain, flow_acc=acc, water=water, bounds=np.array((S, W, N_, E)))
print("saved", out, "| now restart uvicorn")
