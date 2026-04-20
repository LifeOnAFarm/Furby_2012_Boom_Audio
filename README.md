# Furby Project

`furby-project` is a Python CLI for working with Furby Boom / 2012 ROM dumps.

It extracts audio and image assets from Furby ROM binaries, converts Furby image records to and from BMP, decodes bundled `.a18` audio to WAV without the old 32-bit DLL dependency, and rebuilds ROMs from edited assets.

<<<<<<< HEAD
## Current Features

- Inspect a ROM and summarize its records
- Extract `.a18` audio records from a ROM
- Export image records as `.bmp` or raw `.bin`
- Convert BMP files back into Furby image-record `.bin` files
- Decode a single `.a18` file or every audio record in a ROM to WAV
- Rebuild a ROM from image and audio asset folders
=======
There is extracted audio and images for the following Furbys in Furby Exported Files/:
>>>>>>> 841f8f50de2609e6d4b0563977fbca8c9cfbef4f

## Install

<<<<<<< HEAD
```bash
pip install -e .
```

Image commands require `Pillow`, which is included in the default dependencies.

## CLI Usage

Inspect a ROM:

```bash
furby inspect path/to/combined_rom.bin --limit 10
```

Extract assets:

```bash
furby extract path/to/combined_rom.bin --out extracted_assets
```
=======
### Furby 2012 Eyes
![Furby 2012 Eyes](https://github.com/LifeOnAFarm/Furby_2012_Boom_Audio/blob/003ba831338548cdba9973b5421e0e20155f2e77/2012-Eyes-Big.gif)
>>>>>>> 841f8f50de2609e6d4b0563977fbca8c9cfbef4f

Export images as BMP:

```bash
furby export-images path/to/combined_rom.bin --out images --format bmp
```

<<<<<<< HEAD
Decode audio to WAV:

=======
## Current Features

- Inspect a ROM and summarize its records
- Extract `.a18` audio records from a ROM
- Export image records as `.bmp` or raw `.bin`
- Convert BMP files back into Furby image-record `.bin` files
- Decode a single `.a18` file or every audio record in a ROM to WAV
- Rebuild a ROM from image and audio asset folders

## Install

```bash
pip install -e .
```

Image commands require `Pillow`, which is included in the default dependencies.

## CLI Usage

Inspect a ROM:

```bash
furby inspect path/to/combined_rom.bin --limit 10
```

Extract assets:

```bash
furby extract path/to/combined_rom.bin --out extracted_assets
```

Export images as BMP:

```bash
furby export-images path/to/combined_rom.bin --out images --format bmp
```

Decode audio to WAV:

>>>>>>> 841f8f50de2609e6d4b0563977fbca8c9cfbef4f
```bash
furby export-audio-wav path/to/audio0001.a18 --out audio0001.wav
furby export-audio-wav path/to/combined_rom.bin --out exported_wavs
```

Build a ROM:

```bash
furby build --images converted_bins --audio converted_a18 --out rebuilt.bin --padding-mode 4k
```

## Project Layout

- `src/furby_tool/`: reusable library and CLI code
- `src/furby_tool/_a1800/`: bundled pure-Python A1800 decoder
- `tests/`: small smoke tests for ROM parsing and ROM building
- `ARCHITECTURE.md`: notes on how the prototype scripts map into the package
- `ROADMAP.md`: next milestones for the project
<<<<<<< HEAD

## Development

Install dev extras and run tests:

```bash
pip install -e .[dev]
pytest
```

## Contributing

See [CONTRIBUTING.md](D:\Codex FurbyDumper\furby_project\CONTRIBUTING.md:1) for the lightweight development workflow.

## License

This project is licensed under the [MIT License](D:\Codex FurbyDumper\furby_project\LICENSE:1).

## Notes

- The bundled A1800 decoder removes the old 32-bit Python requirement for decoding `.a18` audio.
- Encoding WAV back to `.a18` is still a future task for this package.
- The original workspace still contains older prototype scripts and experiments; this folder is the cleaned CLI-focused package.
=======
>>>>>>> 841f8f50de2609e6d4b0563977fbca8c9cfbef4f
