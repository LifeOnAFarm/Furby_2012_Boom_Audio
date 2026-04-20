from __future__ import annotations

import struct

from furby_tool.images import IMAGE_RECORD_SIZE
from furby_tool.rom import A18_MARKER, parse_rom


def test_parse_rom_classifies_audio_and_image(tmp_path):
    audio_data = struct.pack("<I", 6) + A18_MARKER + (b"\x11" * 6)
    image_data = bytes([0xAA]) * IMAGE_RECORD_SIZE

    record_count = 2
    header_size = 4 + record_count * 4
    audio_offset = header_size
    image_offset = audio_offset + len(audio_data)

    rom_path = tmp_path / "sample.bin"
    rom_path.write_bytes(
        b"".join(
            [
                struct.pack("<I", record_count),
                struct.pack("<I", audio_offset),
                struct.pack("<I", image_offset),
                audio_data,
                image_data,
            ]
        )
    )

    rom = parse_rom(rom_path)

    assert rom.record_count == 2
    assert [record.kind for record in rom.records] == ["audio", "image"]
    assert len(rom.audio_records) == 1
    assert len(rom.image_records) == 1
