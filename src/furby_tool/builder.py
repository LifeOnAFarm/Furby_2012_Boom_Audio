from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct

from ._a1800.encoder import encode_wav_to_a18_bytes
from .images import IMAGE_RECORD_SIZE
from .rom import A18_MARKER


@dataclass(frozen=True)
class BuildAsset:
    source_path: Path
    kind: str
    data: bytes

    @property
    def size(self) -> int:
        return len(self.data)


@dataclass(frozen=True)
class BuildResult:
    output_path: Path
    record_count: int
    audio_count: int
    image_count: int
    wav_audio_count: int
    a18_audio_count: int
    header_size: int
    padding_size: int
    total_size: int


def validate_a18_file(path: str | Path) -> bool:
    data = Path(path).read_bytes()[:6]
    return len(data) >= 6 and data[4:6] == A18_MARKER


def validate_bin_file(path: str | Path) -> bool:
    return Path(path).stat().st_size == IMAGE_RECORD_SIZE


def collect_audio_files(folder: str | Path) -> list[Path]:
    root = Path(folder)
    return sorted(
        path for path in root.iterdir()
        if path.is_file() and path.suffix.lower() == ".a18" and validate_a18_file(path)
    )


def collect_wav_files(folder: str | Path) -> list[Path]:
    root = Path(folder)
    return sorted(
        path for path in root.iterdir()
        if path.is_file() and path.suffix.lower() == ".wav"
    )


def collect_image_files(folder: str | Path) -> list[Path]:
    root = Path(folder)
    return sorted(
        path for path in root.iterdir()
        if path.is_file() and path.suffix.lower() == ".bin" and validate_bin_file(path)
    )


def build_rom(
    image_folder: str | Path,
    audio_folder: str | Path,
    output_path: str | Path,
    padding_size: int = 0,
    audio_bitrate: int = 16000,
) -> BuildResult:
    output = Path(output_path)
    audio_root = Path(audio_folder)
    audio_files = collect_audio_files(audio_root) if audio_root.exists() else []
    wav_files = collect_wav_files(audio_root) if audio_root.exists() else []
    image_files = collect_image_files(image_folder) if Path(image_folder).exists() else []
    audio_assets = [
        BuildAsset(source_path=path, kind="audio", data=path.read_bytes())
        for path in audio_files
    ]
    wav_audio_assets = [
        BuildAsset(
            source_path=path,
            kind="audio",
            data=encode_wav_to_a18_bytes(path, bitrate=audio_bitrate),
        )
        for path in wav_files
    ]
    image_assets = [
        BuildAsset(source_path=path, kind="image", data=path.read_bytes())
        for path in image_files
    ]

    all_audio_assets = audio_assets + wav_audio_assets
    all_assets = all_audio_assets + image_assets

    if not all_assets:
        raise ValueError(
            "No valid audio or image files were found to build a ROM "
            f"(audio folder: {Path(audio_folder)}, image folder: {Path(image_folder)})"
        )

    record_count = len(all_assets)
    header_size = 4 + (record_count * 4)
    current_offset = header_size + padding_size
    offsets: list[int] = []

    for asset in all_assets:
        offsets.append(current_offset)
        current_offset += asset.size

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as rom_file:
        rom_file.write(struct.pack("<I", record_count))
        for offset in offsets:
            rom_file.write(struct.pack("<I", offset))
        if padding_size:
            rom_file.write(b"\x00" * padding_size)
        for asset in all_assets:
            rom_file.write(asset.data)

    return BuildResult(
        output_path=output,
        record_count=record_count,
        audio_count=len(all_audio_assets),
        image_count=len(image_files),
        wav_audio_count=len(wav_audio_assets),
        a18_audio_count=len(audio_files),
        header_size=header_size,
        padding_size=padding_size,
        total_size=output.stat().st_size,
    )
