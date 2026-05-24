# AppCtx - AI Coding Instructions

## Project Overview

AppCtx is a lightweight dependency injection container for Python inspired by the Spring Framework. It uses pure marker decorators (`@bean` for functions, `@component` for classes) that are decoupled from the container. Bean discovery is done via `ApplicationContext.scan()` which recursively scans Python packages.

## Core Architecture

### Key Components

- **ApplicationContext** (`src/appctx/container.py`): Main DI container with `scan()`, `add()`, `refresh()`, `get_bean()`, `get_beans()` methods
- **Decorators** (`src/appctx/decorators.py`): Pure marker decorators: `@bean` (functions), `@component` (classes), `@post_construct` (lifecycle hooks)
- **Bean Discovery**: `scan(package_name, exclude)` recursively scans packages, `__module__` filtering prevents cross-import duplication
- **Dependency Resolution**: Auto-wires dependencies based on type annotations or parameter names

### Public API (from `__init__.py`)

`ApplicationContext`, `bean`, `component`, `post_construct`

### Data Flow

1. `@bean` / `@component` decorators set marker attributes (`_is_bean`, `_is_component`, `_bean_name`) on objects
2. `scan()` discovers marked objects in packages and adds them to `bean_defs`
3. `refresh()` initializes container and instantiates beans in dependency order
4. Dependencies are resolved through type annotations (primary) or parameter names (fallback)
5. Beans are stored in `bean_names_map` (by name) and `bean_types_map` (by type)

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
from appctx import ApplicationContext
from appctx.decorators import bean, component

# Function-based bean factory
@bean
def service():
    return Service("config")

# Custom bean name
@bean(name="my_service")
def service():
    return Service("config")

# Class-based component (Spring-style)
@component
class Component:
    def __init__(self, dependency: Service):
        self.dependency = dependency

# Scan and refresh
ctx = ApplicationContext()
ctx.scan("myapp").refresh()

# Or manually add
ctx.add(service).refresh()
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

- `@bean` only accepts functions (raises TypeError on classes); `@component` only accepts classes (raises TypeError on functions)
- `@bean`/`@component` support optional `name` parameter for custom bean names via `_bean_name` attribute
- `scan()` uses `pkgutil.walk_packages` for recursive package scanning with `fnmatch` glob exclude support
- `_scan_module` filters by `obj.__module__ == module.__name__` to prevent cross-import duplicate registration
- Bean instantiation uses iterative resolution (not recursive) to handle complex dependency graphs
- `_instantiate` uses `getattr(bean_def, '_bean_name', None) or bean_def.__name__` for bean name resolution
- Simple type checking used for type-based bean retrieval (replaced singledispatchmethod for broader Python compatibility)
- `defaultdict` for type-based bean storage to support multiple beans per type
- Post-construction lifecycle hooks available via `@post_construct` decorator (called after all beans are created)
- `_instantiate` returns `bool` to avoid falsy bean misjudgment
