from __future__ import annotations

from pathlib import Path

from ._a1800.decoder import decode_a18_bytes, decode_file, write_wav
from .rom import RomFile


def decode_a18_to_wav(input_path: str | Path, output_path: str | Path, sample_rate: int = 16000) -> None:
    decode_file(input_path, output_path, sample_rate=sample_rate)


def export_rom_audio_as_wav(
    rom: RomFile,
    output_dir: str | Path,
    sample_rate: int = 16000,
) -> int:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    count = 0
    for record in rom.audio_records:
        count += 1
        output_path = root / f"audio{count:04d}.wav"
        _, samples = decode_a18_bytes(record.data)
        write_wav(output_path, samples, sample_rate=sample_rate)
    return count
