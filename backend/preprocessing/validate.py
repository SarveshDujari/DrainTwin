"""Sanity check: do well-known Delhi waterlogging spots rank high? (coordinates approximate, verify them)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from app.engine import risk as R

SPOTS = {"Minto Bridge": (28.6340, 77.2260), "ITO": (28.6280, 77.2410), "Moolchand underpass": (28.5690, 77.2335)}
grid, _ = R.compute(100)
s, w, n, e = R.BOUNDS
for name, (la, lo) in SPOTS.items():
    r, c = int((n - la) / (n - s) * R.ROWS), int((lo - w) / (e - w) * R.COLS)
    print(f"{name:22s} risk {grid[r, c]:5.1f} | higher than {(grid < grid[r, c]).mean():.0%} of the area")
