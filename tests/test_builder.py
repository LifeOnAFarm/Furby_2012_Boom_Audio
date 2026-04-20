from __future__ import annotations

import struct
import wave

from furby_tool.builder import build_rom
from furby_tool.images import IMAGE_RECORD_SIZE
from furby_tool.rom import parse_rom


def test_build_rom_writes_header_padding_and_records(tmp_path):
    audio_dir = tmp_path / "audio"
    image_dir = tmp_path / "images"
    audio_dir.mkdir()
    image_dir.mkdir()

    audio_path = audio_dir / "audio0001.a18"
    image_path = image_dir / "img_0001.bin"
    audio_path.write_bytes(struct.pack("<I", 6) + b"\x80\x3E" + (b"\x22" * 6))
    image_path.write_bytes(bytes([0x55]) * IMAGE_RECORD_SIZE)

    output_path = tmp_path / "rebuilt.bin"
    result = build_rom(image_dir, audio_dir, output_path, padding_size=16)
    rom = parse_rom(output_path)

    assert result.record_count == 2
    assert result.audio_count == 1
    assert result.image_count == 1
    assert result.padding_size == 16
    assert rom.offsets == [12 + 16, 12 + 16 + audio_path.stat().st_size]
    assert [record.kind for record in rom.records] == ["audio", "image"]
    assert result.a18_audio_count == 1
    assert result.wav_audio_count == 0


def test_build_rom_auto_encodes_wav_audio(tmp_path):
    audio_dir = tmp_path / "audio"
    image_dir = tmp_path / "images"
    audio_dir.mkdir()
    image_dir.mkdir()

    wav_path = audio_dir / "audio0001.wav"
    image_path = image_dir / "img_0001.bin"
    image_path.write_bytes(bytes([0x55]) * IMAGE_RECORD_SIZE)

    samples = [0] * 320
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(struct.pack("<" + "h" * len(samples), *samples))

    output_path = tmp_path / "rebuilt_from_wav.bin"
    result = build_rom(image_dir, audio_dir, output_path)
    rom = parse_rom(output_path)

    assert result.record_count == 2
    assert result.audio_count == 1
    assert result.a18_audio_count == 0
    assert result.wav_audio_count == 1
    assert [record.kind for record in rom.records] == ["audio", "image"]
