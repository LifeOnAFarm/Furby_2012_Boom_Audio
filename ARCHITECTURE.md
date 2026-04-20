# Architecture Notes

## Existing Functional Areas

The scripts in the root workspace break down into a few clean responsibilities:

### ROM extraction

- read ROM header
- collect record offsets
- detect audio records by `.a18` marker `0x80 0x3E`
- detect image records by `256`-byte size

Current sources:

- `full_split.py`
- `split.py`

### Image decoding and encoding

- Furby image records are 256 bytes
- they decode into 64x32 monochrome bitmaps
- the current code uses fixed `x_offsets` and `y_offsets` lookup arrays

Current sources:

- decode path in `full_split.py` / `split.py`
- encode path in `encode_bmp.py`

### Audio decoding and encoding

- `.a18 -> .wav` is now solved in pure Python via `a1800_decoder/`
- `.wav -> .a18` still uses the old DLL-based encoder

Current sources:

- decode path in `a1800_decoder/`
- encode path in `encode_wav.py`

### ROM building

- write file count
- write record offsets
- append audio records first, then image records
- possibly insert padding between header and data

Current sources:

- `combine.py`
- `Furby Code/combine.py`

### Utility helpers

- duplicate assets for filler/testing
- convert text hex dumps into binary

Current sources:

- `dupe.py`
- `hex_to_bin.py`

## Problems With The Current State

1. Logic is duplicated across scripts.
2. The old GUI mixes UI code and business logic heavily.
3. The old audio path assumes `a1800.dll` for parts of the workflow.
4. There is no single source of truth for ROM layout and validation rules.
5. There are no automated tests protecting rebuild/extract behavior.

## Proposed Package Layout

```text
furby_project/
  README.md
  ARCHITECTURE.md
  ROADMAP.md
  pyproject.toml
  src/
    furby_tool/
      __init__.py
      rom.py
      records.py
      images.py
      audio.py
      builder.py
      cli.py
      gui/
        __init__.py
        app.py
  tests/
    test_rom.py
    test_images.py
    test_audio.py
```

## Core Data Model

### ROM

- `record_count`
- `offsets`
- `records`
- optional `padding_size`

### Record

- `index`
- `offset`
- `size`
- `kind`: `audio`, `image`, or `unknown`
- raw bytes

### Image Asset

- source record bytes
- decoded `PIL.Image`
- encoder back to 256-byte Furby format

### Audio Asset

- source `.a18` bytes
- decoded PCM/WAV export
- optional future encoder back to `.a18`

## Recommended CLI Shape

```text
furby extract rom.bin --out extracted/
furby inspect rom.bin
furby export-images rom.bin --out imgs/
furby export-audio rom.bin --out wavs/
furby import-images assets/ --out converted_bins/
furby import-audio wavs/ --out converted_a18/
furby build --images converted_bins --audio converted_a18 --out combined_rom.bin
```

## GUI Scope

The GUI should sit on top of the library and not own the real logic.

Recommended first GUI:

- open ROM
- show asset counts
- preview images
- list audio clips and play exported WAV previews
- replace image/audio entries
- build ROM

## Important Technical Decisions

1. Use the new Python decoder for `.a18 -> .wav`.
2. Keep encode support modular because `.wav -> .a18` may need a later pure-Python port.
3. Preserve the exact image bit mapping arrays from the prototypes.
4. Treat the padding behavior in `Furby Code/combine.py` as a configurable ROM-build option until verified as universal.
