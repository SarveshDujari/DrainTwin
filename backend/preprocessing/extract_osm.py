"""Distance (m) from each grid cell to the nearest mapped drain / waterway, via the free Overpass API."""
import json
import time
import numpy as np
import requests
from scipy.spatial import cKDTree
from common import S, W, N_, E, RAW, UA, cell_centres

MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter"]            # public servers; they come and go
QUERY = '[out:json][timeout:60];way["waterway"~"^(drain|ditch|canal|stream|river)$"](%s,%s,%s,%s);out geom;'
KX, KY = 111_320 * np.cos(np.radians((S + N_) / 2)), 110_540      # degrees -> metres
CACHE = RAW / "osm_ways.json"

def _quadrants(k=2):
    """Four small requests are much friendlier to busy public servers than one big one."""
    la, lo = np.linspace(S, N_, k + 1), np.linspace(W, E, k + 1)
    return [(la[i], lo[j], la[i + 1], lo[j + 1]) for i in range(k) for j in range(k)]

def _query(bbox, rounds=3):
    for attempt in range(rounds):
        for url in MIRRORS:
            try:
                r = requests.post(url, data={"data": QUERY % bbox}, headers=UA, timeout=90)
                r.raise_for_status()
                return [w["geometry"] for w in r.json()["elements"] if "geometry" in w]
            except Exception as e:
                print(f"    {url.split('/')[2]} failed: {str(e)[:70]}")
        wait = 10 * (attempt + 1)
        print(f"    all servers busy, retrying in {wait}s ...")
        time.sleep(wait)
    raise RuntimeError("Overpass unavailable")

def fetch_ways():
    if CACHE.exists():
        print("    using cached OSM data (delete data/raw/osm_ways.json to refresh)")
        return json.loads(CACHE.read_text())
    ways = []
    for i, box in enumerate(_quadrants(), 1):
        print(f"    OSM part {i}/4 ...")
        ways += _query(box)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(ways))
    return ways

def densify(line, step=40):
    """Points every ~40 m along a way, so 'nearest vertex' ~ 'nearest drain'."""
    pts = np.array([(p["lon"] * KX, p["lat"] * KY) for p in line])
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        k = max(1, int(np.hypot(*(b - a)) // step))
        out.extend(a + (b - a) * t for t in np.linspace(0, 1, k, endpoint=False))
    out.append(pts[-1])
    return out

def drain_distance(ways=None):
    ways = fetch_ways() if ways is None else ways
    if not ways:
        raise SystemExit("No drains/waterways found in OSM for this area.")
    pts = np.array([p for w in ways for p in densify(w)])
    lat, lng = cell_centres()
    d, _ = cKDTree(pts).query(np.c_[lng.ravel() * KX, lat.ravel() * KY])
    return d.reshape(lat.shape)

if __name__ == "__main__":
    d = drain_distance()
    print("drain distance m: median", int(np.median(d)), "max", int(d.max()))
