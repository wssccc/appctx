# API Reference

## Core Decorators

### `@bean` / `@component`

Register a function or class as a bean in the application context. `@component` is a Spring-style alias for `@bean` — they are identical.

```python
from appctx import bean, component

# Function-based bean
@bean
def my_service():
    return MyService()

# Class-based bean (Spring-style)
@component
class MyComponent:
    def __init__(self, dependency: SomeDependency):
        self.dependency = dependency
```

When decorating a class, the class itself is registered as a bean factory. The container will instantiate it with resolved dependencies.

### `@post_construct`

Mark a method to be called automatically after the bean has been constructed and all dependencies have been injected.

```python
from appctx import post_construct

class DatabaseService:
    def __init__(self):
        self.connection = None

    @post_construct
    def init(self):
        self.connection = create_connection()
        self.setup_tables()

@bean
def database_service():
    return DatabaseService()
```

**Important notes:**
- Only non-private methods (not starting with `_`) are considered
- Multiple methods can be annotated with `@post_construct` in the same class
- If a `@post_construct` method raises an exception, the bean is removed from the container
- `@post_construct` methods are called **after all beans are created**, similar to Spring's `@PostConstruct`
- All beans exist in the container during `@post_construct` execution
- Order of `@post_construct` calls depends on bean registration order, not dependency relationships

## Container Operations

### Global Default Context

`from appctx import bean, refresh, get_bean, add` — these all operate on a shared global `ApplicationContext` instance. This is the recommended pattern for most applications.

For isolated contexts (e.g., tests, libraries), create an explicit `ApplicationContext()`:

```python
from appctx import ApplicationContext

ctx = ApplicationContext()

@ctx.bean
def my_service():
    return MyService()

ctx.refresh()
```

### `add(target)`

Register a callable or class with the context — equivalent to using the `@bean` decorator on it. Returns the context for chaining.

```python
from appctx import add

def some_service():
    return SomeService()

# Register without decorator
add(some_service)

# Also accepts classes
add(AnotherService)
```

> **Note:** AppCtx does not scan packages automatically. When you `import` a module, any `@bean` decorators in that module fire and register with the global context. `add()` is for registering individual callables/classes that weren't decorated.

### `refresh()`

Initialize the container and instantiate all beans. Must be called before getting any beans.

```python
from appctx import refresh

refresh()
```

### `get_bean(key)`

Get a bean by type or name.

> ⚠️ **Low-level API.** In normal application code, prefer auto-wiring via constructor/function parameters — just like Spring. Use `get_bean()` only at the application entry point to retrieve the root object, or in rare cases where dynamic bean lookup is unavoidable.

```python
from appctx import get_bean

# Get by type
service = get_bean(MyService)

# Get by name (function/class name used in @bean)
service = get_bean("my_service")
```

Raises `KeyError` if the bean is not found.

### `get_beans(type)`

Get all beans of a specific type. Returns a list.

> ⚠️ **Low-level API.** Same guidance as `get_bean()` — prefer auto-wiring. Useful mainly for plugin-style architectures where you need to discover all implementations of an interface.

```python
from appctx import get_beans

services = get_beans(MyService)
for svc in services:
    print(svc)
```

## Dependency Resolution

AppCtx resolves dependencies based on parameter types and names:

| Parameter Kind | Resolution Strategy |
|---|---|
| **Positional arguments** | Resolved by type annotation only |
| **Keyword-only arguments** (`*`, `arg`) | Resolved by parameter name first, then default value |
| **`**kwargs`** | Receives all remaining beans not used by other parameters |

### Resolution Examples

```python
@bean
def config_service():
    return "config_value"

@bean
def database_service():
    return "database_url"

# Positional args — resolved by type annotations
@bean
def service_with_positional(config_service: str):
    return f"Service: {config_service}"

# Keyword-only args — resolved by name
@bean
def service_with_keyword_only(*, config_service, timeout=30):
    return f"Service: {config_service}, timeout={timeout}"

# **kwargs — gets all remaining beans
@bean
def flexible_service(**kwargs):
    return f"Flexible: {kwargs}"
```

### Circular Dependency Detection

Circular dependencies are detected and reported as `RuntimeError` during `refresh()`.

## Multiple Beans of Same Type

Multiple beans of the same type are supported. Use `get_beans()` to retrieve all of them:

```python
@bean
def primary_db():
    return DatabaseService("primary://db")

@bean
def secondary_db():
    return DatabaseService("secondary://db")

refresh()

# Get all database services
dbs = get_beans(DatabaseService)  # Returns list of both
```

> **Note:** When using `get_bean(Type)` with multiple beans of the same type, a `RuntimeError` is raised due to ambiguity. Use `get_beans(Type)` or `get_bean("name")` instead.

## Error Handling

| Error | When |
|---|---|
| `KeyError` | Requested bean not found in container |
| `RuntimeError` | Bean instantiation failure (including circular dependencies) |
| `RuntimeError` | Ambiguous type match — multiple beans of the same type via `get_bean(Type)` |

```python
try:
    service = get_bean(UnknownService)
except KeyError as e:
    print(f"Bean not found: {e}")

try:
    refresh()
except RuntimeError as e:
    print(f"Instantiation failed: {e}")
```