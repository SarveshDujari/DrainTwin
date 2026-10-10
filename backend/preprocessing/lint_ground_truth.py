"""Audit the ground-truth CSV without inventing or changing coordinates.

Run from backend: python preprocessing/lint_ground_truth.py
"""
import csv
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / 'data' / 'validation' / 'ground_truth.csv'
VALID = {'pending', 'provisional', 'verified', 'rejected'}

def audit(path=CSV):
    with open(path, encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    problems = []
    seen = set()
    for index, row in enumerate(rows, start=2):
        identity = row.get('id', '').strip()
        if not identity or identity in seen:
            problems.append(f'row {index}: missing/duplicate id')
        seen.add(identity)
        status = row.get('verification_status', '').strip().lower()
        if status not in VALID:
            problems.append(f'row {index}: invalid verification_status {status!r}')
        lat, lon = row.get('latitude', '').strip(), row.get('longitude', '').strip()
        if bool(lat) != bool(lon):
            problems.append(f'row {index}: latitude/longitude must both be present')
        if lat and lon:
            try:
                y, x = float(lat), float(lon)
                if not (28.3 <= y <= 29.0 and 76.8 <= x <= 77.6):
                    problems.append(f'row {index}: coordinates outside broad Delhi review region')
            except ValueError:
                problems.append(f'row {index}: nonnumeric coordinates')
        if status == 'verified' and not (lat and lon):
            problems.append(f'row {index}: verified point missing coordinates')
        if status == 'verified' and not row.get('source_url', '').strip():
            problems.append(f'row {index}: verified point missing source_url')
    return len(rows), problems

if __name__ == '__main__':
    count, errors = audit()
    print(f'Checked {count} records: {len(errors)} issue(s)')
    for error in errors:
        print('-', error)
    raise SystemExit(1 if errors else 0)
