from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .images import decode_image_record
from .rom import RomFile


@dataclass(frozen=True)
class ExtractResult:
    audio_count: int
    image_count: int


def export_rom_images(
    rom: RomFile,
    output_dir: str | Path,
    image_format: str = "bmp",
) -> int:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    image_count = 0
    for record in rom.image_records:
        image_count += 1
        if image_format == "bin":
            (root / f"img_{image_count:04d}.bin").write_bytes(record.data)
            continue

        try:
            image = decode_image_record(record.data)
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "BMP image export requires Pillow. Install the 'pillow' package "
                "or use --format bin."
            ) from exc
        image.save(root / f"img_{image_count:04d}.bmp")

    return image_count


def extract_rom_assets(
    rom: RomFile,
    output_dir: str | Path,
    extract_audio: bool = True,
    extract_images: bool = True,
) -> ExtractResult:
    root = Path(output_dir)
    audio_dir = root / "a18_files"
    image_dir = root / "imgs"

    audio_count = 0
    image_count = 0

    if extract_audio:
        audio_dir.mkdir(parents=True, exist_ok=True)
        for record in rom.audio_records:
            audio_count += 1
            (audio_dir / f"audio{audio_count:04d}.a18").write_bytes(record.data)

    if extract_images:
        image_dir.mkdir(parents=True, exist_ok=True)
        image_count = export_rom_images(rom, image_dir, image_format="bmp")

    return ExtractResult(audio_count=audio_count, image_count=image_count)
