"""Multi-query, cache-first Nominatim suggestions. Never marks a location verified.

Run: python preprocessing/geocode_ground_truth.py --limit 10 --user-agent "DrainTwinResearch/0.2 (contact@example.com)"
--limit counts NETWORK requests, not candidate rows. Existing cache is reused.
"""
import argparse
import csv
import json
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "data/validation/ground_truth.csv"
CACHE = ROOT / "data/validation/geocode_cache.json"
ALIASES = {"MB Road": "Mehrauli Badarpur Road", "MG Road": "Mehrauli Gurgaon Road", "MM Road": "Mahatma Gandhi Road"}
NAMES = {"Andheria Mor": "Andheria Mod", "11 Murti": "Gyarah Murti", "Delhi Zoo": "National Zoological Park"}

def queries(row):
    name, road = row["name"].strip(), row["road"].strip()
    expanded = ALIASES.get(road, road)
    candidates = [f"{name}, {road}, Delhi, India", f"{name}, {expanded}, Delhi, India",
                  f"{name}, New Delhi, India", f"{name}, Delhi, India"]
    if name in NAMES:
        candidates.append(f"{NAMES[name]}, New Delhi, India")
    if "Underpass" in name:
        candidates.append(f"{name.replace('Underpass','').strip()}, Delhi, India")
    return list(dict.fromkeys(candidates))

def plausible(item):
    try:
        lat, lon = float(item["lat"]), float(item["lon"])
    except (TypeError, KeyError, ValueError):
        return False
    # Broad Delhi NCR plausibility filter, NOT exact-site verification.
    return 28.3 <= lat <= 28.9 and 76.8 <= lon <= 77.5

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--user-agent", required=True)
    args = parser.parse_args()
    if "@" not in args.user_agent or args.limit < 0:
        parser.error("Provide an identifiable contact email in --user-agent and nonnegative --limit")
    with CSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    requests_made = 0
    matched = 0
    for row in rows:
        if row["verification_status"].strip().lower() in ("verified", "provisional") or row.get("latitude", "").strip():
            continue
        for key in queries(row):
            if key not in cache:
                if requests_made >= args.limit:
                    break
                try:
                    response = requests.get("https://nominatim.openstreetmap.org/search",
                        params={"q": key, "format": "json", "limit": 3, "countrycodes": "in"},
                        headers={"User-Agent": args.user_agent}, timeout=25)
                    response.raise_for_status()
                    cache[key] = response.json()
                    requests_made += 1
                    CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
                    time.sleep(1.2)
                except requests.RequestException as exc:
                    print(f"Network error on {key}: {exc}; stopping safely")
                    break
            value = cache[key]
            options = value if isinstance(value, list) else ([value] if value else [])
            candidate = next((item for item in options if plausible(item)), None)
            if candidate:
                row["latitude"], row["longitude"] = candidate["lat"], candidate["lon"]
                row["verification_status"] = "provisional"
                row["coordinate_source"] = "Nominatim candidate (not verified)"
                row["review_notes"] = f"Matched query: {key}; map label: {candidate.get('display_name','')[:150]}. Verify exact road point."
                matched += 1
                break
    if rows:
        with CSV.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader(); writer.writerows(rows)
    print(f"Network requests: {requests_made}; new provisional matches: {matched}; pending: {sum(r['verification_status']=='pending' for r in rows)}")
    print("Provisional coordinates are NOT verified ground truth. Review each pin manually.")

if __name__ == "__main__":
    main()
