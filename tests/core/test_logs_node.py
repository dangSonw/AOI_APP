import logging

from core.nodes import get_node_runtime


def test_logs_node_returns_popup_event() -> None:
    runtime = get_node_runtime('logs')

    assert runtime is not None
    assert runtime.execute({}, {
        'destination': 'popup',
        'level': 'warning',
        'message': 'Alignment requires review.',
    }) == {
        '__log__': {
            'destination': 'popup',
            'level': 'warning',
            'message': 'Alignment requires review.',
        },
    }


def test_logs_node_writes_terminal_at_selected_level(caplog) -> None:
    runtime = get_node_runtime('logs')
    assert runtime is not None

    with caplog.at_level(logging.INFO, logger='aoi.workflow.logs'):
        outputs = runtime.execute({}, {
            'destination': 'terminal',
            'level': 'info',
            'message': 'Inspection reached alignment.',
        })

    assert outputs == {}
    assert 'Inspection reached alignment.' in caplog.text


def test_logs_node_returns_file_event_without_writing_terminal(caplog) -> None:
    runtime = get_node_runtime('logs')
    assert runtime is not None

    with caplog.at_level(logging.INFO, logger='aoi.workflow.logs'):
        outputs = runtime.execute({}, {
            'destination': 'file',
            'level': 'error',
            'message': 'Inspection result was rejected.',
        })

    assert outputs['__log__']['destination'] == 'file'
    assert caplog.text == ''