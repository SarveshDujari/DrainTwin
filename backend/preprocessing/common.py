"""Shared constants/helpers for the real-data pipeline. Row 0 of every grid is the NORTH edge."""
import numpy as np
from pathlib import Path

S, W, N_, E = 28.56, 77.15, 28.70, 77.30      # study area (must match the backend bounds)
N = 64                                          # output grid is N x N cells (~245 m each)
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
UA = {"User-Agent": "DrainTwin-hackathon/0.1"}

def block_mean(a, n=N):
    """Average a fine raster down to an n x n grid."""
    r = np.linspace(0, a.shape[0], n + 1).astype(int)
    c = np.linspace(0, a.shape[1], n + 1).astype(int)
    return np.array([[a[r[i]:r[i + 1], c[j]:c[j + 1]].mean() for j in range(n)] for i in range(n)])

def cell_centres(n=N):
    lat = N_ - (np.arange(n) + .5) * (N_ - S) / n
    lng = W + (np.arange(n) + .5) * (E - W) / n
    return np.meshgrid(lat, lng, indexing="ij")

def d8_flow_acc(elev):
    """Each cell sends its accumulated water to its lowest strictly-lower neighbour (D8)."""
    n, m = elev.shape
    acc = np.ones_like(elev)
    for i in np.argsort(-elev.ravel()):
        r, c = divmod(i, m)
        best, bv = None, elev[r, c]
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = r + dr, c + dc
                if (dr or dc) and 0 <= rr < n and 0 <= cc < m and elev[rr, cc] < bv:
                    best, bv = (rr, cc), elev[rr, cc]
        if best:
            acc[best] += acc[r, c]
    return acc
