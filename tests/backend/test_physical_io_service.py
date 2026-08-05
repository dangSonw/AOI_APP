import json
from pathlib import Path

from app.schemas.physical_io import PhysicalOutputState
from app.services.physical_io_service import read_output_state, write_output_state


def test_output_state_is_written_and_read_atomically(tmp_path: Path) -> None:
    output_path = tmp_path / 'output.json'
    state = PhysicalOutputState(
        revision=2,
        updatedAt='2026-08-04T00:00:00Z',
        signals={'cameraTrigger': True},
    )

    write_output_state(output_path, state)
    restored_state = read_output_state(tmp_path)

    assert restored_state.revision == 2
    assert restored_state.signals['cameraTrigger'] is True
    assert json.loads(output_path.read_text(encoding='utf-8'))['revision'] == 2