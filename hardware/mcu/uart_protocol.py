from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from enum import IntEnum


MAGIC = b'AOI1'
PROTOCOL_VERSION = 1
MAX_PAYLOAD_BYTES = 4096
HEADER = struct.Struct('>4sBI BH')
CRC = struct.Struct('>I')


class UartProtocolError(ValueError):
    pass


class FrameType(IntEnum):
    HEARTBEAT = 1
    HOME = 2
    MOVE_ABSOLUTE = 3
    STOP = 4
    CLEAR_FAULT = 5
    STATE = 6
    ACK = 7
    ERROR = 8


@dataclass(frozen=True)
class UartFrame:
    sequence: int
    frame_type: FrameType
    payload: bytes


def encode_frame(frame: UartFrame) -> bytes:
    if frame.sequence < 0 or frame.sequence > 0xFFFFFFFF:
        raise UartProtocolError('UART sequence is outside uint32 range.')
    if len(frame.payload) > MAX_PAYLOAD_BYTES:
        raise UartProtocolError('UART payload exceeds maximum size.')
    header = HEADER.pack(MAGIC, PROTOCOL_VERSION, frame.sequence, int(frame.frame_type), len(frame.payload))
    body = header + frame.payload
    return body + CRC.pack(zlib.crc32(body) & 0xFFFFFFFF)


def decode_frame(value: bytes) -> UartFrame:
    minimum = HEADER.size + CRC.size
    if len(value) < minimum:
        raise UartProtocolError('UART frame is truncated.')
    magic, version, sequence, raw_type, payload_length = HEADER.unpack(value[:HEADER.size])
    if magic != MAGIC or version != PROTOCOL_VERSION:
        raise UartProtocolError('UART frame magic or version is invalid.')
    if payload_length > MAX_PAYLOAD_BYTES or len(value) != minimum + payload_length:
        raise UartProtocolError('UART frame payload length is invalid.')
    expected_crc = CRC.unpack(value[-CRC.size:])[0]
    if zlib.crc32(value[:-CRC.size]) & 0xFFFFFFFF != expected_crc:
        raise UartProtocolError('UART frame CRC is invalid.')
    try:
        frame_type = FrameType(raw_type)
    except ValueError as error:
        raise UartProtocolError('UART frame type is unsupported.') from error
    return UartFrame(sequence=sequence, frame_type=frame_type, payload=value[HEADER.size:-CRC.size])