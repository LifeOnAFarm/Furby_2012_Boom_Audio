from __future__ import annotations

import argparse
from pathlib import Path

from .audio import decode_a18_to_wav, export_rom_audio_as_wav
from .builder import build_rom
from .extract import export_rom_images, extract_rom_assets
from .images import convert_bmp_file_to_record
from .rom import parse_rom


def cmd_inspect(args: argparse.Namespace) -> int:
    rom = parse_rom(args.rom)
    print(f"ROM: {rom.path}")
    print(f"Records: {rom.record_count}")
    print(f"Audio records: {len(rom.audio_records)}")
    print(f"Image records: {len(rom.image_records)}")
    unknown_count = len([record for record in rom.records if record.kind == 'unknown'])
    print(f"Unknown records: {unknown_count}")
    print()
    for record in rom.records[: args.limit]:
        print(
            f"#{record.index:04d} "
            f"offset=0x{record.offset:X} "
            f"size={record.size} "
            f"type={record.kind}"
        )
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    rom = parse_rom(args.rom)
    result = extract_rom_assets(
        rom,
        args.out,
        extract_audio=not args.no_audio,
        extract_images=not args.no_images,
    )
    print(f"Extracted audio files: {result.audio_count}")
    print(f"Extracted image files: {result.image_count}")
    print(f"Output directory: {Path(args.out).resolve()}")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    padding_size = resolve_padding(args.padding_mode, args.padding)
    result = build_rom(
        image_folder=args.images,
        audio_folder=args.audio,
        output_path=args.out,
        padding_size=padding_size,
    )
    print(f"Built ROM: {result.output_path}")
    print(f"Records: {result.record_count}")
    print(f"Audio files: {result.audio_count}")
    print(f"Image files: {result.image_count}")
    print(f"Header size: {result.header_size}")
    print(f"Padding size: {result.padding_size}")
    print(f"Total size: {result.total_size}")
    return 0


def cmd_import_images(args: argparse.Namespace) -> int:
    input_dir = Path(args.input)
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for path in sorted(input_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() != ".bmp":
            continue
        output_path = output_dir / f"{path.stem}.bin"
        convert_bmp_file_to_record(path, output_path)
        count += 1

    print(f"Converted BMP files: {count}")
    print(f"Output directory: {output_dir.resolve()}")
    return 0


def cmd_export_images(args: argparse.Namespace) -> int:
    rom = parse_rom(args.rom)
    count = export_rom_images(rom, args.out, image_format=args.format)
    print(f"Exported image files: {count}")
    print(f"Format: {args.format}")
    print(f"Output directory: {Path(args.out).resolve()}")
    return 0


def cmd_export_audio_wav(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    if input_path.suffix.lower() == ".a18":
        output_path = Path(args.out)
        decode_a18_to_wav(input_path, output_path, sample_rate=args.sample_rate)
        print(f"Decoded WAV: {output_path.resolve()}")
        return 0

    rom = parse_rom(input_path)
    count = export_rom_audio_as_wav(rom, args.out, sample_rate=args.sample_rate)
    print(f"Exported WAV files: {count}")
    print(f"Output directory: {Path(args.out).resolve()}")
    return 0


def resolve_padding(mode: str, explicit_padding: int | None) -> int:
    if explicit_padding is not None:
        return explicit_padding
    if mode == "4k":
        return 4096
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Furby ROM CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect a Furby ROM")
    inspect_parser.add_argument("rom")
    inspect_parser.add_argument("--limit", type=int, default=20)
    inspect_parser.set_defaults(func=cmd_inspect)

    extract_parser = subparsers.add_parser("extract", help="Extract ROM assets")
    extract_parser.add_argument("rom")
    extract_parser.add_argument("--out", required=True)
    extract_parser.add_argument("--no-audio", action="store_true")
    extract_parser.add_argument("--no-images", action="store_true")
    extract_parser.set_defaults(func=cmd_extract)

    build_parser_cmd = subparsers.add_parser("build", help="Build a ROM from asset folders")
    build_parser_cmd.add_argument("--images", required=True)
    build_parser_cmd.add_argument("--audio", required=True)
    build_parser_cmd.add_argument("--out", required=True)
    build_parser_cmd.add_argument("--padding", type=int)
    build_parser_cmd.add_argument(
        "--padding-mode",
        choices=["none", "4k"],
        default="none",
        help="Named padding mode used when --padding is not set",
    )
    build_parser_cmd.set_defaults(func=cmd_build)

    import_images_parser = subparsers.add_parser(
        "import-images",
        help="Convert BMP files into Furby image records",
    )
    import_images_parser.add_argument("input")
    import_images_parser.add_argument("--out", required=True)
    import_images_parser.set_defaults(func=cmd_import_images)

    export_images_parser = subparsers.add_parser(
        "export-images",
        help="Export image records from a ROM as BMP or raw BIN files",
    )
    export_images_parser.add_argument("rom")
    export_images_parser.add_argument("--out", required=True)
    export_images_parser.add_argument(
        "--format",
        choices=["bmp", "bin"],
        default="bmp",
        help="Output format for exported images",
    )
    export_images_parser.set_defaults(func=cmd_export_images)

    export_audio_parser = subparsers.add_parser(
        "export-audio-wav",
        help="Decode ROM audio records or a single A18 file to WAV",
    )
    export_audio_parser.add_argument("input")
    export_audio_parser.add_argument("--out", required=True)
    export_audio_parser.add_argument("--sample-rate", type=int, default=16000)
    export_audio_parser.set_defaults(func=cmd_export_audio_wav)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
