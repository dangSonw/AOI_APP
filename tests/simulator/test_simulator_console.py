from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONSOLE_ROOT = PROJECT_ROOT / 'simulator' / 'console'


def test_simulator_console_contains_camera_and_motion_controls() -> None:
    page = (CONSOLE_ROOT / 'index.html').read_text(encoding='utf-8')

    assert 'Virtual camera' in page
    assert 'Choose image folder' in page
    assert 'Use Windows camera' in page
    assert 'Virtual motion controller' in page
    assert 'Home all axes' in page
    assert 'Emergency stop' in page
    assert 'SIMULATION' in page


def test_simulator_console_uses_responsive_assets_without_external_runtime_dependencies() -> None:
    page = (CONSOLE_ROOT / 'index.html').read_text(encoding='utf-8')
    stylesheet = (CONSOLE_ROOT / 'simulator-console.css').read_text(encoding='utf-8')
    script = (CONSOLE_ROOT / 'simulator-console.js').read_text(encoding='utf-8')

    assert 'simulator-console.css' in page
    assert 'simulator-console.js' in page
    assert 'rel="icon"' in page
    assert '@media' in stylesheet
    assert 'getUserMedia' in script
    assert 'http://127.0.0.1:9101' in script
    assert 'http://127.0.0.1:9102' in script
    assert "'/configuration'" in script
    assert 'refreshCommonConfiguration' in script
    assert 'cameraConfigurationDirty' in script
    assert 'motionConfigurationDirty' in script


def test_simulator_console_preserves_adapter_source_state_on_reload() -> None:
    script = (CONSOLE_ROOT / 'simulator-console.js').read_text(encoding='utf-8')
    initialize_body = script.split('async function initialize() {', 1)[1].split('\n}', 1)[0]

    assert 'refreshSimulationConfiguration' in initialize_body
    assert 'configureCamera()' not in initialize_body
    assert "element('source-label').textContent" in script


def test_windows_camera_selection_feeds_a_frame_to_the_adapter() -> None:
    script = (CONSOLE_ROOT / 'simulator-console.js').read_text(encoding='utf-8')
    start_camera_body = script.split('async function startWindowsCamera() {', 1)[1].split('\n}', 1)[0]

    assert 'await useWebcamFrame()' in start_camera_body