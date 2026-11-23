# AppCtx

Spring-style dependency injection for Python

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/wssccc/appctx/blob/main/LICENSE)
[![PyPI Version](https://img.shields.io/pypi/v/appctx.svg)](https://pypi.org/project/appctx/)

## Overview

AppCtx is a lightweight dependency injection (DI) container for Python, inspired by the Spring Framework. It uses decorator-based bean registration with package scanning and auto-wiring via type annotations to manage dependencies in a clean, testable way.

**Python Requirements**: 3.9+ | **License**: MIT

### Features

- 🏷️ **Pure marker decorators** — `@bean` for functions, `@component` for classes — no coupling to container instances
- 🔍 **Package scanning** — `ApplicationContext.scan()` auto-discovers annotated objects, with include/exclude filtering
- 🔄 **Auto-wiring** — Dependencies resolved from type annotations, including `from __future__ import annotations` (PEP 563)
- 🧩 **Interface-first injection** — Depend on an ABC or runtime-checkable Protocol; the container finds a unique implementation
- 🔗 **Circular dependency detection** — Caught at startup, not runtime
- ⚡ **Async lifecycle** — `@post_construct` can be async; use `await ctx.refresh_async()`
- 🧭 **Actionable errors** — `BeanResolutionError` reports the missing type or ambiguous candidates per bean
- 📦 **Lightweight** — Zero mandatory dependencies beyond stdlib
- 🐍 **Pythonic API** — Feels natural in Python, not a Java port
- 🏗️ **Multiple contexts** — Isolated containers for different scopes
- ✨ **Custom bean names** — `@bean(name="custom")` / `@component(name="custom")`

## Installation

```bash
pip install appctx
```

## Quick Start

### 1. Define beans and components

Use `@bean` on functions (factories) and `@component` on classes:

```python
# myapp/config.py
from appctx.decorators import bean

@bean
def db_config():
    return {"host": "localhost", "port": 5432}

@bean(name="app_config")  # Custom bean name
def application_config():
    return {"name": "my_app", "debug": False}
```

```python
# myapp/services.py
from appctx.decorators import component

@component
class UserService:
    def __init__(self, db_config: dict):
        self.db_config = db_config

    def get_user(self, user_id: int):
        return f"User {user_id} from {self.db_config['host']}"

@component(name="notification_svc")
class NotificationService:
    def __init__(self, db_config: dict, app_config: dict):
        self.db_config = db_config
        self.app_config = app_config
```

### 2. Scan, refresh, and use

```python
# main.py
from appctx import ApplicationContext

ctx = ApplicationContext()
ctx.scan("myapp").refresh()

# Entry point — the only place you should call get_bean
user_svc = ctx.get_bean(UserService)
print(user_svc.get_user(123))
```

> **Note:** `get_bean()` is only needed at the **entry point** to bootstrap your application. All other dependencies are injected automatically via constructor or function parameters — just like Spring.

> **PEP 563:** AppCtx works with `from __future__ import annotations`; stringized annotations are resolved when the container refreshes.

### Post-construct lifecycle

Use `@post_construct` to run initialization logic after all beans are created:

```python
from appctx.decorators import component, post_construct

@component
class DatabaseService:
    def __init__(self):
        self.connection = None

    @post_construct
    def init(self):
        self.connection = create_connection()  # Called after all beans are created
```

Async hooks are supported through the async refresh API:

```python
@component
class AsyncDatabaseService:
    def __init__(self):
        self.connection = None

    @post_construct
    async def init(self):
        self.connection = await create_connection()
```

Call `await ctx.refresh_async()` from an async application. `ctx.refresh()` only runs synchronous hooks and raises a clear `RuntimeError` if async hooks are present.

## Core Concepts

| Concept | Description |
|---|---|
| **Bean** | An object managed by the container |
| **ApplicationContext** | The DI container that holds and wires beans |
| **`@bean`** | Pure marker decorator for functions (bean factories) |
| **`@component`** | Pure marker decorator for classes (components) |
| **`scan()`** | Discovers `@bean`/`@component` annotated objects in packages |
| **`refresh()`** | Instantiates all beans and runs synchronous lifecycle hooks |
| **`refresh_async()`** | Async variant that also runs async `@post_construct` hooks |
| **`add()`** | Manually register a class or function bean definition |

### Dependency Resolution Rules

1. **Positional arguments** → resolved by exact type first, then by a unique assignable type (ABC or runtime-checkable Protocol)
2. **Keyword-only arguments** (`*, name`) → resolved by parameter name, falls back to default
3. **`**kwargs`** → receives all remaining beans not consumed by other parameters
4. **Ambiguity** → multiple candidates or a missing dependency raise `BeanResolutionError` with the argument and candidate details at `refresh()`

> PEP 563 string annotations are supported. `object` is not used for assignability matching, so a dependency on `object` only matches an explicitly registered `object` bean.

## Scanning

### Package scanning

Scan an entire package recursively:

```python
ctx = ApplicationContext()
ctx.scan("myapp").refresh()
```

### Module scanning

Scan a single module:

```python
ctx = ApplicationContext()
ctx.scan("myapp.services").refresh()
```

### Auto-detection

Call `scan()` without arguments to auto-detect the caller's package:

```python
# Called from within myapp/main.py
ctx = ApplicationContext()
ctx.scan().refresh()  # Auto-detects "myapp" package
```

### Exclude patterns

Exclude packages or modules using fnmatch glob patterns:

```python
ctx = ApplicationContext()
ctx.scan("myapp", exclude=["myapp.tests", "myapp.internal_*"]).refresh()
```

### Include patterns

Restrict scanning to selected packages or modules:

```python
ctx = ApplicationContext()
ctx.scan("myapp", include=["myapp.services", "myapp.config"]).refresh()
```

`include` supports the same fnmatch glob and package-prefix matching as `exclude`. When both are provided, a module must match `include` and must not match `exclude`.

## Decorators

### `@bean` — Function bean factories

```python
from appctx.decorators import bean

@bean
def my_service():
    return MyService()

@bean(name="custom_service")
def another_service():
    return MyService()
```

- Only accepts **functions** — raises `TypeError` on classes
- Sets `_is_bean = True` and `_bean_name` attributes
- The declared return type (when it is a class) is registered in addition to the concrete return type; useful for factories declared to return an ABC/Protocol. The produced object must be an instance of the declared type, otherwise `refresh()` raises `TypeError`
- Use `@component` for classes

### `@component` — Class components

```python
from appctx.decorators import component

@component
class MyComponent:
    def __init__(self, dependency: SomeDependency):
        self.dependency = dependency

@component(name="my_comp")
class AnotherComponent:
    pass
```

- Only accepts **classes** — raises `TypeError` on functions
- Sets `_is_component = True` and `_bean_name` attributes
- A class without a custom `__init__` is constructed with no arguments; explicit `**kwargs` still receives the remaining beans
- Use `@bean` for functions

### `@post_construct` — Lifecycle hooks

```python
from appctx.decorators import post_construct

class MyService:
    @post_construct
    def init(self):
        self.connection = create_connection()
```

## Organizing Beans Across Modules

Define beans in separate modules, scan to discover them:

```python
# myapp/__init__.py — empty or minimal

# myapp/config.py
from appctx.decorators import bean
@bean
def db_config():
    return {"host": "localhost"}

# myapp/services.py
from appctx.decorators import component
@component
class UserService:
    def __init__(self, db_config: dict):
        self.db_config = db_config

# main.py
from appctx import ApplicationContext
ctx = ApplicationContext()
ctx.scan("myapp").refresh()
```

You can also manually register bean definitions with `add()`:

```python
ctx = ApplicationContext()
ctx.add(my_factory_func).add(MyComponentClass)
ctx.refresh()
```

`add()` accepts classes and functions only. Modules are ignored; pre-built instances raise `TypeError` — wrap them in a `@bean` factory instead.

## Best Practices

1. **Rely on auto-wiring, avoid `get_bean`** — Let the container inject dependencies via parameters.
2. **Use type annotations** — They are the primary mechanism for dependency resolution.
3. **Use `@bean` for functions, `@component` for classes** — Semantic separation like Spring.
4. **Prefer `scan()` over `add()`** — Let the container discover beans automatically.
5. **Use `@post_construct` for initialization** — Not `__init__` side-effects.
6. **Separate configuration from logic** — Use dedicated config beans.
7. **Design for testability** — Beans that accept dependencies via constructor are trivially mockable.

## Error Handling

- `BeanResolutionError` (subclass of `RuntimeError`) — one or more bean definitions could not be instantiated; the message lists each bean with its reason (missing type, ambiguous candidates, or an annotation that cannot be evaluated) and flags likely circular dependencies.
- `KeyError` — `get_bean` could not find a bean.
- `RuntimeError` — `get_bean(Type)` matched multiple beans, or `refresh()` found an async `@post_construct` hook.
- `TypeError` — `add()` received a pre-built instance, or a `@bean` factory returned an object that is not an instance of its declared return type.

## Documentation

- **[API Reference](docs/api-reference.md)** — Full API: decorators, container ops, dependency resolution
- **[Development Guide](docs/development.md)** — Setup, testing, code quality, contributing
- **[Release Guide](RELEASE.md)** — Release process for maintainers
- **[Changelog](CHANGELOG.md)** — Version history

## License

MIT — see [LICENSE](https://github.com/wssccc/appctx/blob/main/LICENSE).

## Links

- **Repository**: [github.com/wssccc/appctx](https://github.com/wssccc/appctx)
- **PyPI**: [pypi.org/project/appctx](https://pypi.org/project/appctx/)
- **Issues**: [github.com/wssccc/appctx/issues](https://github.com/wssccc/appctx/issues)
