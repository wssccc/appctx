# AppCtx

Spring-style dependency injection for Python

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/wssccc/appctx/blob/main/LICENSE)
[![PyPI Version](https://img.shields.io/pypi/v/appctx.svg)](https://pypi.org/project/appctx/)

## Overview

AppCtx is a lightweight dependency injection (DI) container for Python, inspired by the Spring Framework. It uses decorator-based bean registration and auto-wiring via type annotations to manage dependencies in a clean, testable way.

**Python Requirements**: 3.8+ | **License**: MIT

### Features

- 🚀 **Decorator-based registration** — `@bean` / `@component` to register, `@post_construct` for lifecycle hooks
- 🔄 **Auto-wiring** — Dependencies resolved from type annotations automatically
- 🔍 **Circular dependency detection** — Caught at startup, not runtime
- 📦 **Lightweight** — Zero mandatory dependencies beyond stdlib
- 🐍 **Pythonic API** — Feels natural in Python, not a Java port
- 🏗️ **Multiple contexts** — Isolated containers for different scopes

## Installation

```bash
pip install appctx
```

## Quick Start

### 1. Define and register beans

Use `@bean` on functions that create your objects. Dependencies are declared via type annotations:

```python
from appctx import bean, get_bean, refresh

class DatabaseService:
    def __init__(self, connection_string: str = "sqlite:///default.db"):
        self.connection_string = connection_string

    def connect(self):
        return f"Connected to {self.connection_string}"

class UserService:
    def __init__(self, db: DatabaseService):
        self.db = db

    def get_user(self, user_id: int):
        return f"User {user_id} from {self.db.connect()}"

# Register beans
@bean
def database_service():
    return DatabaseService("postgresql://localhost/myapp")

@bean
def user_service(db: DatabaseService):  # Auto-injected by type
    return UserService(db)
```

### 2. Initialize and use

```python
# Initialize the container — resolves all dependencies
refresh()

# Retrieve the root application object (the only place you should call get_bean)
user_svc = get_bean(UserService)
print(user_svc.get_user(123))
```

> **Note:** `get_bean()` is only needed at the **entry point** to bootstrap your application. All other dependencies are injected automatically via constructor or function parameters — just like Spring.

### Class-style beans

Decorate classes directly — the container instantiates them with resolved dependencies:

```python
from appctx import bean, get_bean, refresh

@bean
class EmailService:
    def __init__(self):
        self.server = "smtp.example.com"
    
    def send_email(self, to: str, subject: str):
        return f"Email sent to {to} via {self.server}"

@bean
class NotificationService:
    def __init__(self, email: EmailService):
        self.email = email
    
    def notify(self, user: str, message: str):
        return self.email.send_email(user, "Notification", message)

refresh()

# Entry point — the only place you should call get_bean
notification_svc = get_bean(NotificationService)
print(notification_svc.notify("user@example.com", "Hello World!"))
```

### Post-construct lifecycle

Use `@post_construct` to run initialization logic after all beans are created:

```python
from appctx import post_construct

class DatabaseService:
    def __init__(self):
        self.connection = None

    @post_construct
    def init(self):
        self.connection = create_connection()  # Called automatically after construction

@bean
def database_service():
    return DatabaseService()
```

> **Note:** `@post_construct` methods run after **all** beans are created, so you can safely reference other beans during initialization.

### How It Works

1. **Bean Registration**: Use the `@bean` decorator to register functions/classes that create beans
2. **Auto-wiring**: Dependencies are resolved from type annotations and injected automatically — no manual `get_bean()` calls needed
3. **Container Initialization**: Call `refresh()` to instantiate all beans in dependency order
4. **Entry Point**: Use `get_bean()` **once** at the application root to retrieve the assembled object graph

## Core Concepts

| Concept | Description |
|---|---|
| **Bean** | An object managed by the container |
| **ApplicationContext** | The DI container that holds and wires beans |
| **`@bean`** | Decorator that registers a function/class as a bean factory (alias: `@component`) |
| **`refresh()`** | Initializes the container, instantiates all beans in dependency order |
| **`get_bean(T)`** | Retrieve a bean by type or name (low-level; prefer auto-wiring) |
| **`get_beans(T)`** | Retrieve all beans of a given type (low-level; prefer auto-wiring) |

### Dependency Resolution Rules

1. **Positional arguments** → resolved by type annotation
2. **Keyword-only arguments** (`*, name`) → resolved by parameter name, falls back to default
3. **`**kwargs`** → receives all remaining beans not consumed by other parameters

## Global Default Context

AppCtx provides a **global default context** for convenience, similar to Spring's application context. The top-level functions (`bean`, `refresh`, `get_bean`, `add`) operate on this shared instance:

```python
from appctx import bean, refresh, get_bean

# These all use the same global ApplicationContext behind the scenes
@bean
def my_service():
    return MyService()

refresh()
app = get_bean(MyService)
```

### Custom Context (Isolation)

For libraries or tests that need isolation, create your own `ApplicationContext`:

```python
from appctx import ApplicationContext

ctx = ApplicationContext()

@ctx.bean
def my_service():
    return MyService()

ctx.refresh()
app = ctx.get_bean(MyService)
```

> **Note:** `@bean` on the global context registers beans immediately when the module is imported. For custom contexts, use `@ctx.bean` to register against that specific instance.

## Organizing Beans Across Modules

AppCtx does **not** perform automatic package scanning. Instead, beans are registered at import time — when Python loads a module, any `@bean` decorators execute and register with the target context.

To wire beans across multiple modules, simply **import** them before calling `refresh()`:

```python
# main.py
from appctx import bean, refresh, get_bean

# Import modules so their @bean decorators fire
import myapp.services.user   # registers UserService
import myapp.services.email   # registers EmailService
import myapp.config           # registers ConfigService

refresh()
app = get_bean(UserService)
```

You can also use `add()` to register a plain function or class (without the `@bean` decorator):

```python
from appctx import add

def some_service():
    return SomeService()

add(some_service)  # Equivalent to @bean on some_service
```

> **Note:** For modules, simply importing them is sufficient — the `@bean` decorators fire at import time. `add(module)` is available as a semantic marker but the import alone triggers registration.

## Best Practices

1. **Rely on auto-wiring, avoid `get_bean`** — Like Spring, let the container inject dependencies via function/constructor parameters. Reserve `get_bean()` only for bootstrapping the root application object.
2. **Use type annotations** — They are the primary mechanism for dependency resolution. Always annotate positional parameters.
3. **Single responsibility per bean** — Each bean should have one clear purpose.
4. **Prefer constructor injection** — Dependencies go in `__init__` parameters, not hidden inside methods.
5. **Keep beans stateless when possible** — Makes testing and reasoning easier.
6. **Use `@post_construct` for initialization** — Not `__init__` side-effects. Post-construct runs after all beans exist, allowing cross-bean setup.
7. **Separate configuration from logic** — Use dedicated config beans instead of hardcoding values.
8. **Design for testability** — Beans that accept dependencies via constructor are trivially mockable in tests.

## Documentation

- **[API Reference](docs/api-reference.md)** — Full API: decorators, container ops, dependency resolution, error handling
- **[Development Guide](docs/development.md)** — Setup, testing, code quality, contributing
- **[Release Guide](RELEASE.md)** — Release process for maintainers
- **[Changelog](CHANGELOG.md)** — Version history

## License

MIT — see [LICENSE](https://github.com/wssccc/appctx/blob/main/LICENSE).

## Links

- **Repository**: [github.com/wssccc/appctx](https://github.com/wssccc/appctx)
- **PyPI**: [pypi.org/project/appctx](https://pypi.org/project/appctx/)
- **Issues**: [github.com/wssccc/appctx/issues](https://github.com/wssccc/appctx/issues)
