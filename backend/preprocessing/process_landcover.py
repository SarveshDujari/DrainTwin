"""Imperviousness per cell from ESA WorldCover 2021 (10 m). Reads only our window from the cloud-hosted file."""
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from common import S, W, N_, E, block_mean

# WorldCover class -> how much rain it sheds (0 = absorbs, 1 = fully paved)
IMPERV = {10: .10, 20: .15, 30: .20, 40: .25, 50: .90, 60: .40, 70: .0, 80: .0, 90: .10, 95: .10, 100: .10}

def tile_url():
    la, lo = int(S // 3 * 3), int(W // 3 * 3)         # tiles are 3 x 3 degrees, named by their SW corner
    return ("https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/"
            f"ESA_WorldCover_10m_2021_v200_N{la:02d}E{lo:03d}_Map.tif")

def landcover_features():
    """Return (imperviousness 0-1, water mask) on the N x N grid."""
    with rasterio.open(tile_url()) as src:
        lc = src.read(1, window=from_bounds(W, S, E, N_, src.transform))
    lut = np.zeros(256)
    for k, v in IMPERV.items():
        lut[k] = v
    return block_mean(lut[lc]), block_mean((lc == 80).astype(float)) > 0.5      # class 80 = permanent water

if __name__ == "__main__":
    i, water = landcover_features()
    print("water cells:", int(water.sum()))
    print("imperviousness mean:", i.mean().round(2), "min/max:", i.min().round(2), i.max().round(2))
