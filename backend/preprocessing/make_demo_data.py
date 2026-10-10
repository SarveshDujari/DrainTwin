"""Builds data/delhi_grid.npz: a 64x64 feature grid over central Delhi.

Synthetic stand-in so the whole stack runs offline. Replace with real
SRTM / WorldCover / OSM features (same keys) -- see README "Next steps".
"""
import numpy as np
from pathlib import Path
from scipy.ndimage import gaussian_filter

N = 64
BOUNDS = (28.56, 77.15, 28.70, 77.30)  # south, west, north, east
rng = np.random.default_rng(42)
y, x = np.mgrid[0:N, 0:N] / N

elev = 217 - 8 * x + gaussian_filter(rng.normal(0, 1, (N, N)), 6) * 25
elev -= 6 * np.exp(-((x - .75) ** 2 + (y - .40) ** 2) / .02)   # Yamuna-side basin
elev -= 4 * np.exp(-((x - .30) ** 2 + (y - .70) ** 2) / .01)   # underpass-like sink

river = np.abs(x - (.92 + .02 * np.sin(7 * y))) < .016          # Yamuna-like strip
elev[river] -= 4

cell_m = (BOUNDS[2] - BOUNDS[0]) * 111_000 / N
gy, gx = np.gradient(elev, cell_m)
slope = np.degrees(np.arctan(np.hypot(gy, gx)))

imperv = np.clip(.55 + gaussian_filter(rng.normal(0, 1, (N, N)), 5) * 3.5, .05, .95)
drain_dist = np.clip(250 + gaussian_filter(rng.normal(0, 1, (N, N)), 4) * 900, 20, 800)

# D8 flow accumulation: push each cell's water to its lowest lower neighbour
acc = np.ones((N, N))
for i in np.argsort(-elev.ravel()):
    r, c = divmod(i, N)
    best, bv = None, elev[r, c]
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            rr, cc = r + dr, c + dc
            if (dr or dc) and 0 <= rr < N and 0 <= cc < N and elev[rr, cc] < bv:
                best, bv = (rr, cc), elev[rr, cc]
    if best:
        acc[best] += acc[r, c]

out = Path(__file__).resolve().parents[1] / "data" / "delhi_grid_demo.npz"
np.savez_compressed(out, elevation=elev, slope=slope, imperviousness=imperv,
                    drain_dist=drain_dist, flow_acc=acc, water=river, bounds=np.array(BOUNDS))
print("saved", out)
