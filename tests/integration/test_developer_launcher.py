from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_backend_launcher_exposes_project_root_and_backend_packages() -> None:
    launcher = (PROJECT_ROOT / 'scripts' / 'run_dev.sh').read_text(encoding='utf-8')

    assert 'PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/backend"' in launcher
    assert 'python -m uvicorn app.main:app' in launcher


def test_launcher_uses_hardware_by_default_and_supports_explicit_simulation() -> None:
    launcher = (PROJECT_ROOT / 'scripts' / 'run_dev.sh').read_text(encoding='utf-8')

    assert 'RUNTIME_MODE="hardware"' in launcher
    assert 'start --mode simulation' in launcher
    assert 'simulator.camera.app:app' in launcher
    assert 'simulator.mcu.app:app' in launcher
    assert 'hardware.camera.app:app' in launcher
    assert 'hardware.mcu.app:app' in launcher
    assert 'python -m http.server 9200' in launcher
    assert 'simulator/console' in launcher
    assert 'CONSOLE_PROCESS_GROUP' in launcher
    assert 'http://127.0.0.1:9200/' in launcher
    assert 'open_windows_browser' in launcher
    assert 'read_runtime_mode' in launcher
    assert 'Simulator console: http://127.0.0.1:9200/' in launcher


def test_launcher_manages_adapter_ports_and_never_declares_a_fallback() -> None:
    launcher = (PROJECT_ROOT / 'scripts' / 'run_dev.sh').read_text(encoding='utf-8')

    assert 'ensure_port_is_available 9101' in launcher
    assert 'ensure_port_is_available 9102' in launcher
    assert 'http://127.0.0.1:9101/health' in launcher
    assert 'http://127.0.0.1:9102/health' in launcher
    assert 'fallback' not in launcher.lower()
    assert 'adapter_is_healthy' in launcher
    assert '[ "$RUNTIME_MODE" = "simulation" ]' in launcher