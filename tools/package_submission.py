"""Build a source submission from an allowlist, including untracked implementation files."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'outputs' / 'DrainTwin_Submission.zip'
FILES = ['README.md', 'SUBMISSION_STATUS.md', 'PROJECT_REVIEW.md',
         'frontend/package.json', 'frontend/package-lock.json', 'frontend/vite.config.js',
         'frontend/index.html', 'frontend/.env.example', 'backend/.env.example',
         'backend/pytest.ini', 'backend/data/delhi_grid.npz', 'backend/data/delhi_grid_demo.npz',
         'tools/package_submission.py']
TREES = ['frontend/src', 'backend/app', 'backend/preprocessing', 'backend/tests', 'backend/data/validation']
ALLOWED = {'.py', '.js', '.jsx', '.css', '.md', '.csv', '.json', '.txt'}

def package():
    files = {ROOT / p for p in FILES if (ROOT / p).is_file()}
    files.update((ROOT / 'backend').glob('requirements*.txt'))
    for directory in TREES:
        files.update(p for p in (ROOT / directory).rglob('*') if p.is_file() and p.suffix in ALLOWED
                     and '__pycache__' not in p.parts and not p.name.startswith('.env'))
    manifest = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(files)}
    required = ['frontend/src/services/routing.js', 'frontend/src/components/RoutePlanner.jsx',
                'backend/app/main.py', 'backend/data/delhi_grid.npz']
    assert all(name in manifest for name in required), 'Required submission files are missing'
    OUTPUT.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files): archive.write(path, 'draintwin/' + path.relative_to(ROOT).as_posix())
        archive.writestr('draintwin/SUBMISSION_MANIFEST.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(OUTPUT) as archive:
        assert archive.testzip() is None
        assert not any(Path(name).name == '.env' for name in archive.namelist())
        for name, digest in manifest.items():
            assert hashlib.sha256(archive.read('draintwin/' + name)).hexdigest() == digest
    print(f'Created {OUTPUT} ({len(files)} files; manifest verified)')

if __name__ == '__main__': package()
