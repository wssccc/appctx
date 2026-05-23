# AppCtx - AI Coding Instructions

## Project Overview

AppCtx is a lightweight dependency injection container for Python inspired by the Spring Framework. It provides decorator-based bean registration and auto-wiring capabilities using type annotations.

## Core Architecture

### Key Components

- **ApplicationContext** (`src/appctx/container.py`): Main DI container that manages bean lifecycle
- **Decorators** (`src/appctx/decorators.py`): `@post_construct` decorator for lifecycle hooks
- **Bean Registration**: Uses `@bean` / `@component` decorator to register functions/classes as beans
- **Dependency Resolution**: Auto-wires dependencies based on type annotations or parameter names
- **Default Context**: Global context instance exposed through `__init__.py` for convenience

### Public API (from `__init__.py`)

`bean`, `component`, `add`, `get_bean`, `get_beans`, `refresh`, `post_construct`, `ApplicationContext`

### Data Flow

1. Bean definitions are registered using `@bean` / `@component` decorator
2. `refresh()` initializes container and instantiates beans in dependency order
3. Dependencies are resolved through type annotations (primary) or parameter names (fallback)
4. Beans are stored in `bean_names_map` (by name) and `bean_types_map` (by type)

## Development Workflow

> Use `make` targets when available. Run `make help` to list all commands.

### Testing
```bash
make test           # Run all tests
make test-cov       # Run tests with coverage report
```

### Code Quality
```bash
make format         # Format code with black + isort
make lint           # Check formatting, flake8, and mypy
```

### Build and Release
```bash
make build          # Build package (python -m build)
make check-build    # Build and validate with twine
make publish-test   # Publish to Test PyPI
make publish        # Publish to PyPI
```

### Version Bumping

Version is defined in `src/appctx/__init__.py` as `__version__`. To bump:
1. Edit `__version__` in `src/appctx/__init__.py`
2. Add a new entry in `CHANGELOG.md` following the existing format
3. Commit with message like `chore: Bump version to x.y.z`

### Full Quality Pipeline
```bash
make format && make lint && make test
```

## Key Patterns

### Bean Registration
```python
# Function-based bean
@bean
def service():
    return Service("config")

# Class-based bean (Spring-style)
@component
class Component:
    def __init__(self, dependency: Service):
        self.dependency = dependency
```

### Post-Construct Hook
```python
class DatabaseService:
    @post_construct
    def init(self):
        self.connection = create_connection()
```

### Dependency Injection
- Positional arguments are resolved by type annotations only
- Keyword-only arguments are resolved by parameter name first, then use defaults
- `**kwargs` injects all remaining beans not already used as parameters
- Circular dependencies detected and reported as RuntimeError
- Multiple beans of same type supported via `get_beans(Type)`

### Error Handling
- `KeyError` for missing beans
- `RuntimeError` for instantiation failures (including circular dependencies)
- `RuntimeError` for ambiguous type matches (multiple beans of same type)

## Project Structure

- `src/appctx/`: Main package code
- `tests/`: Comprehensive test suite covering all scenarios
- `docs/`: API reference and development guide
- `.github/workflows/`: CI (`ci.yml`) and publishing (`publish.yml`) pipelines

## Configuration

- Python 3.8+ support required
- Type hints enforced via mypy
- Black formatting (88 char line length)
- Test coverage reporting configured
- PyPI publishing via GitHub Actions (trusted publishing)

## Critical Implementation Details

- Bean instantiation uses iterative resolution (not recursive) to handle complex dependency graphs
- Simple type checking used for type-based bean retrieval (replaced singledispatchmethod for broader Python compatibility)
- `defaultdict` for type-based bean storage to support multiple beans per type
- Post-construction lifecycle hooks available via `@post_construct` decorator (called after all beans are created)
- `_instantiate` returns `bool` to avoid falsy bean misjudgment
