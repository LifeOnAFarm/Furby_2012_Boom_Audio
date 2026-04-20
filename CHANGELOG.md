# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-04-20

### Added

- Initial packaged CLI for Furby ROM workflows
- ROM inspection, extraction, image export, image import, audio decode, and ROM build commands
- Bundled pure-Python A1800 decoder, removing the old 32-bit decode requirement
- Basic smoke tests for ROM parsing and ROM building
- GitHub-ready project metadata and ignore rules

### Notes

- WAV to A18 encoding is not yet included in this package
- Some generated test/export folders may still exist locally but are ignored by Git
