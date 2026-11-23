# Development Guide

## Requirements

- Python 3.9 or higher
- pip
- make (optional; the `Makefile` wraps the commands below)

## Development Setup

```bash
git clone https://github.com/wssccc/appctx.git
cd appctx
pip install -e ".[dev,typecheck]"
```

This installs the following development tools:
- `pytest>=7.0` — Testing framework
- `pytest-cov>=4.0` — Coverage reporting
- `ruff>=0.4.0` — Formatting and linting (the project uses ruff, not black/isort/flake8)
- `mypy>=1.0,<2.0` — Type checking (pinned below 2.0 while Python 3.9 is supported)

`requirements-dev.txt` lists the same packages if you prefer `pip install -r requirements-dev.txt`.

## Running Tests

```bash
# Run all tests
make test            # or: pytest tests/ -q

# Run with coverage
make test-cov
```

## Code Quality

```bash
# Format code (line length: 88)
make format          # ruff format src/ tests/

# Lint (ruff check + ruff format --check)
make lint

# Type check
make typecheck       # mypy src/
```

### Run All Quality Checks

```bash
make format && make lint && make typecheck && make test
```

Or manually:

```bash
ruff format src/ tests/
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/
pytest tests/ -q
```

The minimum supported interpreter is Python 3.9: avoid syntax or APIs that require a newer version, and keep the ruff and mypy targets at `py39`.

## Project Structure

```
src/appctx/          # Main package code
    __init__.py      # Public API exports and __version__
    container.py     # ApplicationContext and BeanResolutionError
    decorators.py    # @bean, @component and @post_construct decorators
    py.typed
tests/               # Test suite and fixtures
docs/                # API reference and development guide
```

## Contributing

We welcome contributions!

1. Fork the project
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

### Before Submitting

- Ensure all tests pass: `pytest tests/ -q`
- Ensure code is formatted: `ruff format --check src/ tests/`
- Ensure linting passes: `ruff check src/ tests/`
- Ensure type checking passes: `mypy src/`

## Release Process

For maintainers, see [RELEASE.md](../RELEASE.md) for detailed release instructions.