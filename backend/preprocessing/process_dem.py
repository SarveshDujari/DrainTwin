"""Elevation, slope, flow accumulation from free AWS terrain tiles (Terrarium PNG, SRTM-derived). No API key."""
import math
import numpy as np
import requests
from PIL import Image
from scipy.ndimage import gaussian_filter
from common import S, W, N_, E, N, RAW, UA, block_mean, d8_flow_acc

Z = 12   # ~33 m/pixel at Delhi
URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

def _px(lat, lon):                               # lat/lon -> global web-mercator pixel
    n = 2 ** Z * 256
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n

def load_dem(s=S, w=W, n=N_, e=E):
    (x0, y0), (x1, y1) = _px(n, w), _px(s, e)
    tx, ty = range(int(x0 // 256), int(x1 // 256) + 1), range(int(y0 // 256), int(y1 // 256) + 1)
    RAW.mkdir(parents=True, exist_ok=True)
    mosaic = np.zeros((len(ty) * 256, len(tx) * 256))
    for j, y in enumerate(ty):
        for i, x in enumerate(tx):
            f = RAW / f"terrarium_{Z}_{x}_{y}.png"          # cached after first download
            if not f.exists():
                r = requests.get(URL.format(z=Z, x=x, y=y), headers=UA, timeout=30)
                r.raise_for_status()
                f.write_bytes(r.content)
            p = np.asarray(Image.open(f).convert("RGB"), float)
            mosaic[j * 256:(j + 1) * 256, i * 256:(i + 1) * 256] = p[..., 0] * 256 + p[..., 1] + p[..., 2] / 256 - 32768
    ox, oy = tx[0] * 256, ty[0] * 256
    return mosaic[int(y0 - oy):int(y1 - oy), int(x0 - ox):int(x1 - ox)]

K = 8   # buffer, in grid cells, added on every side so flow accumulation isn't cut off at the edges

def dem_features():
    dlat, dlng = (N_ - S) / N, (E - W) / N
    dem = load_dem(S - K * dlat, W - K * dlng, N_ + K * dlat, E + K * dlng)
    n = N + 2 * K
    res = 156543.03 * math.cos(math.radians((S + N_) / 2)) / 2 ** Z      # metres per pixel
    gy, gx = np.gradient(gaussian_filter(dem, 2), res)                   # light smoothing kills DEM noise
    slope = block_mean(np.degrees(np.arctan(np.hypot(gy, gx))), n)
    elev = gaussian_filter(block_mean(dem, n), 0.7)
    acc = d8_flow_acc(elev)
    core = (slice(K, -K), slice(K, -K))
    return elev[core], slope[core], acc[core]

if __name__ == "__main__":
    e, s, a = dem_features()
    print("elevation m:", e.min().round(1), "-", e.max().round(1), "| max flow acc:", int(a.max()))
