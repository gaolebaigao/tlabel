# Contributing to TouchLabel AI 🦞

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
# Clone
git clone https://github.com/liesliy/tlabel.git
cd tlabel

# Install in dev mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## How to Contribute

### 1. Fork & Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Follow existing code style (we're not strict, just be consistent)
- Add tests for new functionality
- Update README.md if you change user-facing behavior

### 3. Submit PR

- Write a clear title and description
- Link any related issues
- Make sure tests pass: `pytest tests/ -v`

## Adding a New Sensor Adapter

This is one of the most valuable contributions! Here's the pattern:

1. Create `tlabel/adapters/your_sensor.py`
2. Inherit from `BaseAdapter` and implement:
   - `detect(path) → bool` — can you handle this file?
   - `load(path) → TLabelData` — parse into TLabel Format v2
3. Register in `tlabel/adapters/__init__.py`
4. Add optional dependencies in `pyproject.toml`
5. Add tests in `tests/test_tlabel.py`

See existing adapters (`gelsight.py`, `paxini.py`, `daimon.py`) for reference.

## Reporting Issues

- **Bug reports**: Include Python version, OS, tlabel version, and a minimal repro
- **Feature requests**: Describe the use case, not just the solution

## Code of Conduct

Be respectful. We're all here to make tactile data tooling better.
