from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_backend_launcher_exposes_project_root_and_backend_packages() -> None:
    launcher = (PROJECT_ROOT / 'scripts' / 'run_dev.sh').read_text(encoding='utf-8')

    assert 'PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/backend"' in launcher
    assert 'python -m uvicorn app.main:app' in launcher