from __future__ import annotations

import os
import select
import termios
import time
from collections.abc import Callable

from hardware.mcu.uart_protocol import CRC, HEADER, MAX_PAYLOAD_BYTES, UartFrame, decode_frame, encode_frame


class UartTransportError(RuntimeError):
    pass


def _open_serial(path: str, baud_rate: int) -> int:
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    attributes = termios.tcgetattr(fd)
    speed = getattr(termios, f'B{baud_rate}', None)
    if speed is None:
        os.close(fd)
        raise UartTransportError('Configured UART baud rate is unsupported.')
    attributes[4] = speed
    attributes[5] = speed
    attributes[2] = termios.CS8 | termios.CLOCAL | termios.CREAD
    attributes[3] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attributes)
    return fd


class UartTransport:
    def __init__(
        self, path: str, *, baud_rate: int = 115200, timeout_seconds: float = 1.0,
        opener: Callable[[str, int], int] = _open_serial,
    ) -> None:
        self.path = path
        self.baud_rate = baud_rate
        self.timeout_seconds = timeout_seconds
        self.opener = opener
        self._fd: int | None = None

    def _descriptor(self) -> int:
        if self._fd is None:
            try:
                self._fd = self.opener(self.path, self.baud_rate)
            except OSError as error:
                raise UartTransportError('MCU UART device could not be opened.') from error
        return self._fd

    def close(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def write_frame(self, frame: UartFrame) -> None:
        payload = encode_frame(frame)
        fd = self._descriptor()
        written = 0
        deadline = time.monotonic() + self.timeout_seconds
        while written < len(payload):
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
                raise UartTransportError('MCU UART write timed out.')
            written += os.write(fd, payload[written:])

    def read_frame(self) -> UartFrame:
        header = self._read_exact(HEADER.size)
        payload_length = HEADER.unpack(header)[4]
        if payload_length > MAX_PAYLOAD_BYTES:
            raise UartTransportError('MCU UART payload length is invalid.')
        return decode_frame(header + self._read_exact(payload_length + CRC.size))

    def _read_exact(self, length: int) -> bytes:
        fd = self._descriptor()
        value = bytearray()
        deadline = time.monotonic() + self.timeout_seconds
        while len(value) < length:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
                raise UartTransportError('MCU UART read timed out.')
            chunk = os.read(fd, length - len(value))
            if not chunk:
                raise UartTransportError('MCU UART closed before a complete frame arrived.')
            value.extend(chunk)
        return bytes(value)