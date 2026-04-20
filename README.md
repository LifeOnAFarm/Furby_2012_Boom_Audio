# Furby Project

`furby-project` is a Python CLI for working with Furby Boom / 2012 ROM dumps.

It extracts audio and image assets from Furby ROM binaries, converts Furby image records to and from BMP, decodes bundled `.a18` audio to WAV without the old 32-bit DLL dependency, and rebuilds ROMs from edited assets.

There is extracted audio and images for the following Furbys in Furby Exported Files/:

- Dutch 2012  
- English 2012  
- French 2012  
- English Boom  
- French Boom  
- English Crystal *(same as Boom)*  
- Furbacca  

### Furby 2012 Eyes
![Furby 2012 Eyes](https://github.com/LifeOnAFarm/Furby_2012_Boom_Audio/blob/003ba831338548cdba9973b5421e0e20155f2e77/2012-Eyes-Big.gif)

### Furby Boom Eyes
![Furby Boom Eyes](https://github.com/LifeOnAFarm/Furby_2012_Boom_Audio/blob/774c1bd3997c3e95ca514c81067b95e8a9dacb30/Boom-Eyes-Big.gif)

### Furbacca Eyes
![Furbacca Eyes](https://github.com/LifeOnAFarm/Furby_2012_Boom_Audio/blob/774c1bd3997c3e95ca514c81067b95e8a9dacb30/Furbacca-Eyes-Big.gif)

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