from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct

from .images import IMAGE_RECORD_SIZE


A18_MARKER = b"\x80\x3E"


@dataclass(frozen=True)
class RomRecord:
    index: int
    offset: int
    size: int
    kind: str
    data: bytes


@dataclass(frozen=True)
class RomFile:
    path: Path
    record_count: int
    offsets: list[int]
    records: list[RomRecord]

    @property
    def audio_records(self) -> list[RomRecord]:
        return [record for record in self.records if record.kind == "audio"]

    @property
    def image_records(self) -> list[RomRecord]:
        return [record for record in self.records if record.kind == "image"]


def classify_record(data: bytes, size: int) -> str:
    if len(data) >= 6 and data[4:6] == A18_MARKER:
        return "audio"
    if size == IMAGE_RECORD_SIZE:
        return "image"
    return "unknown"


def parse_rom(path: str | Path) -> RomFile:
    rom_path = Path(path)
    data = rom_path.read_bytes()
    if len(data) < 4:
        raise ValueError(f"{rom_path} is too small to contain a ROM header")

    record_count = struct.unpack_from("<I", data, 0)[0]
    header_size = 4 + (record_count * 4)
    if len(data) < header_size:
        raise ValueError(f"{rom_path} is truncated: header requires {header_size} bytes")

    offsets = [
        struct.unpack_from("<I", data, 4 + (index * 4))[0]
        for index in range(record_count)
    ]

    records: list[RomRecord] = []
    for index, offset in enumerate(offsets):
        end = offsets[index + 1] if index < record_count - 1 else len(data)
        size = end - offset
        record_data = data[offset:end]
        records.append(
            RomRecord(
                index=index,
                offset=offset,
                size=size,
                kind=classify_record(record_data, size),
                data=record_data,
            )
        )

    return RomFile(
        path=rom_path,
        record_count=record_count,
        offsets=offsets,
        records=records,
    )
