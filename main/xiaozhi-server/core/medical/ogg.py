from pathlib import Path
import struct


OGG_POLYNOMIAL = 0x04C11DB7
OPUS_GRANULES_PER_60_MS = 2880


def ogg_crc(data: bytes | bytearray) -> int:
    checksum = 0
    for byte in data:
        checksum ^= byte << 24
        for _ in range(8):
            checksum = ((checksum << 1) ^ OGG_POLYNOMIAL) & 0xFFFFFFFF if checksum & 0x80000000 else (checksum << 1) & 0xFFFFFFFF
    return checksum


class OggOpusWriter:
    def __init__(self, path: Path, serial: int):
        self.path = path
        self.serial = serial & 0xFFFFFFFF
        self.page_sequence = 0
        self.granule_position = 0
        self.pending_packet: bytes | None = None
        self.handle = None

    def __enter__(self):
        self.handle = self.path.open("wb")
        opus_head = b"OpusHead" + struct.pack("<BBHIhB", 1, 1, 312, 16000, 0, 0)
        vendor = b"xiaozhi-medical-gateway"
        opus_tags = b"OpusTags" + struct.pack("<I", len(vendor)) + vendor + struct.pack("<I", 0)
        self._write_page(opus_head, header_type=0x02, granule=0)
        self._write_page(opus_tags, header_type=0, granule=0)
        return self

    def write_packet(self, packet: bytes) -> None:
        if not packet:
            raise ValueError("Opus packet must not be empty")
        if self.pending_packet is not None:
            self.granule_position += OPUS_GRANULES_PER_60_MS
            self._write_page(self.pending_packet, header_type=0, granule=self.granule_position)
        self.pending_packet = bytes(packet)

    def __exit__(self, exc_type, exc, traceback):
        try:
            if exc_type is None and self.pending_packet is not None:
                self.granule_position += OPUS_GRANULES_PER_60_MS
                self._write_page(self.pending_packet, header_type=0x04, granule=self.granule_position)
        finally:
            if self.handle is not None:
                self.handle.close()
                self.handle = None

    def _write_page(self, packet: bytes, header_type: int, granule: int) -> None:
        if self.handle is None:
            raise RuntimeError("writer is not open")
        segments = [255] * (len(packet) // 255)
        remainder = len(packet) % 255
        segments.append(remainder)
        if len(segments) > 255:
            raise ValueError("packet is too large for a single Ogg page")

        header = bytearray(
            struct.pack(
                "<4sBBQIIIB",
                b"OggS",
                0,
                header_type,
                granule,
                self.serial,
                self.page_sequence,
                0,
                len(segments),
            )
        )
        page = header + bytes(segments) + packet
        struct.pack_into("<I", page, 22, ogg_crc(page))
        self.handle.write(page)
        self.page_sequence += 1
