"""Manually review one historical landmark coordinate; never auto-mark as verified.

Usage:
  python preprocessing/review_coordinate.py --id DL001 --lat 28.634 --lon 77.226 \
      --source 'https://...' --notes 'Manually checked against map and source' --verify
Without --verify, status remains provisional. Back up CSV before editing.
"""
import argparse
import csv
from pathlib import Path

CSV = Path(__file__).resolve().parents[1] / 'data' / 'validation' / 'ground_truth.csv'

def update(path, identifier, lat, lon, source, notes, verify=False):
    if not 28.3 <= lat <= 29.0 or not 76.8 <= lon <= 77.6:
        raise ValueError('Coordinate outside broad Delhi review region')
    if verify and (not source.startswith(('http://', 'https://')) or len(notes.strip()) < 15):
        raise ValueError('Verification requires a source URL and substantive review notes')
    with path.open(encoding='utf-8', newline='') as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames
        rows = list(reader)
    matching = [r for r in rows if r['id'] == identifier]
    if len(matching) != 1:
        raise ValueError(f'Expected exactly one row for {identifier}')
    row = matching[0]
    row.update(latitude=str(lat), longitude=str(lon), verification_status='verified' if verify else 'provisional',
               coordinate_source=source, review_notes=notes)
    tmp = path.with_suffix('.tmp')
    with tmp.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    tmp.replace(path)

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--id', required=True)
    p.add_argument('--lat', required=True, type=float)
    p.add_argument('--lon', required=True, type=float)
    p.add_argument('--source', required=True)
    p.add_argument('--notes', required=True)
    p.add_argument('--verify', action='store_true')
    a = p.parse_args()
    update(CSV, a.id, a.lat, a.lon, a.source, a.notes, a.verify)
    print(f'Updated {a.id}; status: {"verified" if a.verify else "provisional"}. Review CSV before publishing.')
