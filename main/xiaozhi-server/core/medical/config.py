from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Bed:
    id: str
    label: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class BedConfig:
    revision: int
    updated_at: str
    beds: tuple[Bed, ...]

    def enabled_bed_ids(self) -> set[str]:
        return {bed.id for bed in self.beds if bed.enabled}


def load_bed_config(path: Path) -> BedConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    revision = payload.get("revision")
    updated_at = payload.get("updated_at")
    rows = payload.get("beds")
    if not isinstance(revision, int) or revision < 1:
        raise ValueError("revision must be a positive integer")
    if not isinstance(updated_at, str):
        raise ValueError("updated_at must be an ISO-8601 string")
    datetime.fromisoformat(updated_at)
    if not isinstance(rows, list):
        raise ValueError("beds must be a list")

    beds: list[Bed] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("each bed must be an object")
        bed_id = row.get("id")
        label = row.get("label")
        enabled = row.get("enabled")
        if not isinstance(bed_id, str) or not bed_id:
            raise ValueError("bed id must be a non-empty string")
        if bed_id in seen:
            raise ValueError(f"duplicate bed id: {bed_id}")
        if not isinstance(label, str) or not label:
            raise ValueError(f"bed {bed_id} label must be a non-empty string")
        if not isinstance(enabled, bool):
            raise ValueError(f"bed {bed_id} enabled must be boolean")
        seen.add(bed_id)
        beds.append(Bed(id=bed_id, label=label, enabled=enabled))
    return BedConfig(revision=revision, updated_at=updated_at, beds=tuple(beds))
