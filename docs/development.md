# Development Guide

## Requirements

- Python 3.8 or higher
- pip

## Development Setup

```bash
git clone https://github.com/wssccc/appctx.git
cd appctx
pip install -e .[dev]
```

This installs the following development tools:
- `pytest>=7.0` — Testing framework
- `pytest-cov>=4.0` — Coverage reporting
- `black>=22.0` — Code formatting
- `flake8>=5.0` — Linting
- `mypy>=1.0` — Type checking
- `isort>=5.0` — Import sorting

## Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src/appctx tests/
```

## Code Quality

```bash
# Format code (line length: 88)
black src/ tests/

# Sort imports (Black profile)
isort src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/
```

### Run All Quality Checks

```bash
make format && make lint && make test
```

Or manually:

```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
pytest --cov=src/appctx tests/
```

## Project Structure

```
src/appctx/          # Main package code
    __init__.py      # Public API exports, default context
    container.py     # ApplicationContext implementation
    decorators.py    # @bean and @post_construct decorators
tests/               # Test suite
docs/                # Documentation
```

## Contributing

We welcome contributions!

1. Fork the project
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

### Before Submitting

- Ensure all tests pass: `pytest`
- Ensure code is formatted: `black --check src/ tests/`
- Ensure linting passes: `flake8 src/ tests/`
- Ensure type checking passes: `mypy src/`

## Release Process

For maintainers, see [RELEASE.md](../RELEASE.md) for detailed release instructions.