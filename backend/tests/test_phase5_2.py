import csv
from pathlib import Path
import pytest
from app.engine import risk as R
from app.services import validation
from preprocessing.review_coordinate import update


def test_stable_tie_break_and_explanations():
    a = R.run(150)['hotspots']
    b = R.run(150)['hotspots']
    assert [(h['id'], h['rank']) for h in a] == [(h['id'], h['rank']) for h in b]
    assert all(not h['factors']['slope'] for h in a)
    assert 'overall_level_note' in R.run(100)


def test_coordinate_review_requires_evidence(tmp_path):
    path = tmp_path / 'points.csv'
    with path.open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['id', 'latitude', 'longitude', 'verification_status', 'coordinate_source', 'review_notes'])
        w.writeheader()
        w.writerow(dict(id='DL001', latitude='', longitude='', verification_status='pending', coordinate_source='', review_notes=''))
    with pytest.raises(ValueError):
        update(path, 'DL001', 28.63, 77.22, 'guess', 'too short', True)
    update(path, 'DL001', 28.63, 77.22, 'manual', 'Needs map verification', False)
    assert 'provisional' in path.read_text()
    update(path, 'DL001', 28.63, 77.22, 'https://example.org/source', 'Reviewed against documented landmark', True)
    assert 'verified' in path.read_text()


def test_report_cache_refreshes_on_csv_edit(monkeypatch, tmp_path):
    path = tmp_path / 'ground_truth.csv'
    path.write_text('id,name,verification_status,latitude,longitude,source_url\n', encoding='utf-8')
    monkeypatch.setattr(validation, 'CSV_PATH', path)
    # The public report reads current file mtime rather than a stale cached result.
    assert validation.report(150)['candidates'] == 0
    path.write_text('id,name,verification_status,latitude,longitude,source_url\nDLX,Test,pending,,,https://example.org\n', encoding='utf-8')
    assert validation.report(150)['candidates'] == 1
