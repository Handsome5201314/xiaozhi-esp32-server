from dataclasses import dataclass
import struct


MAGIC = b"MRA1"
VERSION = 1
HEADER = struct.Struct(">4sBBHII")


class FrameDecodeError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AudioFrame:
    sequence: int
    timestamp_ms: int
    flags: int
    payload: bytes


def encode_frame(frame: AudioFrame) -> bytes:
    if not 0 <= frame.sequence <= 0xFFFFFFFF:
        raise ValueError("sequence is outside uint32")
    if not 0 <= frame.timestamp_ms <= 0xFFFFFFFF:
        raise ValueError("timestamp_ms is outside uint32")
    if not 0 <= frame.flags <= 0xFF:
        raise ValueError("flags is outside uint8")
    if len(frame.payload) > 0xFFFF:
        raise ValueError("payload is too large")
    return HEADER.pack(MAGIC, VERSION, frame.flags, len(frame.payload), frame.sequence, frame.timestamp_ms) + frame.payload


def decode_frame(data: bytes) -> AudioFrame:
    if len(data) < HEADER.size:
        raise FrameDecodeError("frame header is truncated")
    magic, version, flags, payload_length, sequence, timestamp_ms = HEADER.unpack_from(data)
    if magic != MAGIC:
        raise FrameDecodeError("invalid frame magic")
    if version != VERSION:
        raise FrameDecodeError(f"unsupported frame version: {version}")
    payload = data[HEADER.size:]
    if len(payload) != payload_length:
        raise FrameDecodeError("payload length does not match header")
    return AudioFrame(sequence=sequence, timestamp_ms=timestamp_ms, flags=flags, payload=payload)

