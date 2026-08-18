from types import SimpleNamespace

from app.services.inspection_runtime_service import _append_workflow_log_line
from core.pipeline import WorkflowExecutionRecord


def _record() -> WorkflowExecutionRecord:
    return WorkflowExecutionRecord(
        node_instance_id='node-1', algorithm_id='logs', status='completed',
        parameters={}, inputs={}, outputs={}, duration_ms=3,
        log_event={'destination': 'file', 'level': 'warning', 'message': 'Alignment requires review.'},
    )


def test_file_destination_appends_durable_lines(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / 'logs' / 'workflow-log.txt'
    monkeypatch.setattr(
        'app.services.inspection_runtime_service.get_settings',
        lambda: SimpleNamespace(workflow_log_path=log_path),
    )

    _append_workflow_log_line('run-1', _record())
    _append_workflow_log_line('run-1', _record())

    lines = log_path.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 2
    for line in lines:
        assert line.endswith('[WARNING] run=run-1 node=node-1 algorithm=logs: Alignment requires review.')
        assert len(line.split(' ', 1)[0]) > 0


def test_file_destination_swallows_os_errors_without_raising(tmp_path, monkeypatch, caplog) -> None:
    import logging

    monkeypatch.setattr(
        'app.services.inspection_runtime_service.get_settings',
        lambda: SimpleNamespace(workflow_log_path=tmp_path),
    )

    with caplog.at_level(logging.ERROR, logger='app.services.inspection_runtime_service'):
        _append_workflow_log_line('run-1', _record())

    assert 'workflow log file' in caplog.text