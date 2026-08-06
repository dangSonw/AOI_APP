from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_simulator_launcher_starts_only_virtual_devices_and_console() -> None:
    launcher = (PROJECT_ROOT / 'scripts' / 'run_simulator.sh').read_text(encoding='utf-8')

    assert 'simulator.camera.app:app' in launcher
    assert 'simulator.mcu.app:app' in launcher
    assert '--port 9101' in launcher
    assert '--port 9102' in launcher
    assert 'http.server 9200' in launcher
    assert 'hardware.camera' not in launcher
    assert 'hardware.mcu' not in launcher


def test_simulator_launcher_supports_lifecycle_and_opens_the_windows_browser() -> None:
    launcher = (PROJECT_ROOT / 'scripts' / 'run_simulator.sh').read_text(encoding='utf-8')

    assert '[start|stop|status]' in launcher
    assert 'powershell.exe' in launcher
    assert 'http://127.0.0.1:9200/' in launcher
    assert 'trap' in launcher
    assert 'kill -TERM' in launcher
    assert 'AOI_SIMULATOR_NO_BROWSER' in launcher