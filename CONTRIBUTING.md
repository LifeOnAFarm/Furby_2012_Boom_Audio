# Contributing

Thanks for helping with the project.

## Development Setup

```bash
pip install -e .[dev]
```

If you only need the CLI without test tooling:

```bash
pip install -e .
```

## Suggested Workflow

- Keep new logic inside `src/furby_tool/` rather than adding more standalone scripts
- Prefer building reusable library functions first, then exposing them through the CLI
- Add or update tests in `tests/` when changing ROM parsing or build behavior
- Keep generated exports and local experiment files out of commits

## Current Priorities

- WAV to A18 encoding in pure Python
- Better round-trip and fixture coverage
- A cleaner edit-and-rebuild workflow
- A GUI on top of the shared library once the CLI settles down
