# Roadmap

## Phase 1: Consolidation

- create a reusable ROM parser
- move image decode/encode logic into one module
- wrap audio decode using the Python `A1800` decoder
- define ROM record types and validation

## Phase 2: CLI

- add `inspect`
- add `extract`
- add `build`
- add image/audio import-export commands

## Phase 3: Validation

- test extraction against known sample ROMs
- test image round-trips
- test `.a18 -> .wav` against the sample files
- test ROM rebuild structure and offsets

## Phase 4: GUI

- build a small ROM browser/editor
- image preview and replacement
- audio export and preview
- ROM rebuild from edited assets

## Phase 5: Audio Encode Upgrade

- replace DLL-based `.wav -> .a18` encoding if possible
- otherwise isolate legacy encoding behind an optional adapter
