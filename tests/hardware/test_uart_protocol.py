import os

import pytest

from hardware.mcu.uart_protocol import (
    MAX_PAYLOAD_BYTES,
    FrameType,
    UartFrame,
    UartProtocolError,
    decode_frame,
    encode_frame,
)
from hardware.mcu.uart_transport import UartTransport, UartTransportError


def test_uart_frame_round_trips_version_sequence_type_payload_and_crc() -> None:
    frame = UartFrame(sequence=42, frame_type=FrameType.MOVE_ABSOLUTE, payload=b'bounded-payload')

    encoded = encode_frame(frame)

    assert decode_frame(encoded) == frame


@pytest.mark.parametrize('mutator', (
    lambda value: value[:-1],
    lambda value: value[:8] + bytes([value[8] ^ 1]) + value[9:],
    lambda value: b'NOPE' + value[4:],
))
def test_uart_frame_rejects_truncated_corrupt_or_wrong_magic(mutator) -> None:
    encoded = encode_frame(UartFrame(sequence=1, frame_type=FrameType.HOME, payload=b''))

    with pytest.raises(UartProtocolError):
        decode_frame(mutator(encoded))


def test_uart_frame_rejects_oversized_payload() -> None:
    with pytest.raises(UartProtocolError, match='payload'):
        encode_frame(UartFrame(
            sequence=1, frame_type=FrameType.MOVE_ABSOLUTE,
            payload=b'x' * (MAX_PAYLOAD_BYTES + 1),
        ))


def test_uart_transport_is_lazy_and_times_out_without_complete_response(monkeypatch) -> None:
    opened: list[str] = []
    read_fd, write_fd = os.pipe()

    def opener(path: str, _: int) -> int:
        opened.append(path)
        return read_fd

    transport = UartTransport('/dev/aoi-test', opener=opener, timeout_seconds=0.01)
    assert opened == []
    with pytest.raises(UartTransportError, match='timed out'):
        transport.read_frame()
    assert opened == ['/dev/aoi-test']
    transport.close()
    os.close(write_fd)