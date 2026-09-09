from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

from .frame import AudioFrame, decode_frame, encode_frame
from .ogg import OggOpusWriter


@dataclass(frozen=True, slots=True)
class SessionCreate:
    device_id: str
    mode: str
    bed_id: str | None
    session_id: str | None = None


@dataclass(frozen=True, slots=True)
class SessionRecord:
    session_id: str
    device_id: str
    mode: str
    bed_id: str | None
    started_at: str


@dataclass(frozen=True, slots=True)
class FinishResult:
    status: str
    missing: list[list[int]]


class SessionStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, request: SessionCreate) -> SessionRecord:
        if request.mode not in {"bed", "general"}:
            raise ValueError("mode must be bed or general")
        if request.mode == "bed" and not request.bed_id:
            raise ValueError("bed mode requires bed_id")
        if request.mode == "general" and request.bed_id is not None:
            raise ValueError("general mode must not include bed_id")
        if not request.device_id:
            raise ValueError("device_id is required")

        session_id = str(UUID(request.session_id)) if request.session_id else str(uuid4())
        directory = self._session_dir(session_id)
        if (directory / "session.json").exists():
            existing = SessionRecord(**json.loads((directory / "session.json").read_text(encoding="utf-8")))
            if (existing.device_id, existing.mode, existing.bed_id) != (request.device_id, request.mode, request.bed_id):
                raise ValueError("session_id already exists with different metadata")
            return existing

        record = SessionRecord(
            session_id=session_id,
            device_id=request.device_id,
            mode=request.mode,
            bed_id=request.bed_id,
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        (directory / "frames").mkdir(parents=True)
        self._atomic_write(directory / "session.json", json.dumps(asdict(record), ensure_ascii=False, indent=2).encode())
        return record

    def get(self, session_id: str) -> SessionRecord:
        path = self._session_dir(session_id) / "session.json"
        return SessionRecord(**json.loads(path.read_text(encoding="utf-8")))

    def append_frame(self, session_id: str, frame: AudioFrame) -> int:
        frame_path = self._session_dir(session_id) / "frames" / f"{frame.sequence:010d}.bin"
        encoded = encode_frame(frame)
        if frame_path.exists():
            existing = decode_frame(frame_path.read_bytes())
            if existing != frame:
                raise ValueError(f"sequence {frame.sequence} already exists with different data")
            return self.highest_contiguous_sequence(session_id)
        self._atomic_write(frame_path, encoded)
        return self.highest_contiguous_sequence(session_id)

    def frame_sequences(self, session_id: str) -> list[int]:
        frames = self._session_dir(session_id) / "frames"
        return sorted(int(path.stem) for path in frames.glob("*.bin"))

    def highest_contiguous_sequence(self, session_id: str) -> int:
        expected = 0
        for sequence in self.frame_sequences(session_id):
            if sequence != expected:
                break
            expected += 1
        return expected - 1

    def finish(self, session_id: str, last_sequence: int) -> FinishResult:
        if last_sequence < -1:
            raise ValueError("last_sequence must be >= -1")
        sequences = set(self.frame_sequences(session_id))
        missing_values = [sequence for sequence in range(last_sequence + 1) if sequence not in sequences]
        missing = self._ranges(missing_values)
        status = "completed" if not missing else "incomplete"
        result = FinishResult(status=status, missing=missing)
        if status == "completed":
            self._write_ogg(session_id)
        self._atomic_write(
            self._session_dir(session_id) / "finish.json",
            json.dumps(asdict(result), ensure_ascii=False, indent=2).encode(),
        )
        return result

    def _write_ogg(self, session_id: str) -> None:
        directory = self._session_dir(session_id)
        temporary = directory / "recording.ogg.tmp"
        output = directory / "recording.ogg"
        serial = UUID(session_id).int & 0xFFFFFFFF
        with OggOpusWriter(temporary, serial=serial) as writer:
            for sequence in self.frame_sequences(session_id):
                frame = decode_frame((directory / "frames" / f"{sequence:010d}.bin").read_bytes())
                writer.write_packet(frame.payload)
        os.replace(temporary, output)

    def _session_dir(self, session_id: str) -> Path:
        try:
            normalized = str(UUID(session_id))
        except ValueError as exc:
            raise ValueError("invalid session_id") from exc
        directory = (self.root / normalized).resolve()
        if directory.parent != self.root:
            raise ValueError("session path escapes storage root")
        if not directory.exists() and (self.root / normalized).parent == self.root:
            return directory
        if not (directory / "session.json").exists():
            raise KeyError(f"unknown session: {session_id}")
        return directory

    @staticmethod
    def _ranges(values: list[int]) -> list[list[int]]:
        if not values:
            return []
        ranges: list[list[int]] = []
        start = previous = values[0]
        for value in values[1:]:
            if value != previous + 1:
                ranges.append([start, previous])
                start = value
            previous = value
        ranges.append([start, previous])
        return ranges

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
