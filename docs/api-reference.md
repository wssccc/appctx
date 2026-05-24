# API Reference

## Decorators

Decorators are pure markers — they set attributes on the target but do **not** register anything with a container. Registration happens via `ApplicationContext.scan()` or `add()`.

### `@bean`

Mark a **function** as a bean factory. The container will call this function to produce the bean instance.

```python
from appctx.decorators import bean

# No-arg form — bean name defaults to function name
@bean
def my_service():
    return MyService()

# With custom name
@bean(name="custom_svc")
def my_service():
    return MyService()
```

**Behavior:**
- Sets `_is_bean = True` on the function
- Sets `_bean_name = name` (or `None` if no name given)
- Raises `TypeError` if applied to a class — use `@component` for classes

### `@component`

Mark a **class** as a component. The container will instantiate it with resolved dependencies.

```python
from appctx.decorators import component

# No-arg form — bean name defaults to class name
@component
class MyComponent:
    def __init__(self, dependency: SomeType):
        self.dependency = dependency

# With custom name
@component(name="my_comp")
class MyComponent:
    pass
```

**Behavior:**
- Sets `_is_component = True` on the class
- Sets `_bean_name = name` (or `None` if no name given)
- Raises `TypeError` if applied to a function — use `@bean` for functions

### `@post_construct`

Mark a method to be called after the bean is constructed and all beans are instantiated.

```python
from appctx.decorators import post_construct

class DatabaseService:
    @post_construct
    def init(self):
        self.connection = create_connection()
```

**Notes:**
- Only non-private methods (not starting with `_`) are considered
- Multiple methods can be annotated in the same class
- If a `@post_construct` method raises, the bean is removed from the container
- Methods run **after all beans are created**, similar to Spring's `@PostConstruct`

## ApplicationContext

The DI container. Create an instance, scan for beans, refresh to instantiate.

```python
from appctx import ApplicationContext

ctx = ApplicationContext()
ctx.scan("myapp", exclude=["myapp.tests"]).refresh()
```

### `__init__()`

```python
ctx = ApplicationContext()
```

Creates a new empty container.

### `scan(package_name=None, exclude=None)`

Scan a package or module for `@bean` / `@component` annotated objects and register them.

**Parameters:**
- `package_name` (`str`, optional) — Package or module name to scan. If `None`, auto-detects the caller's package.
- `exclude` (`list[str]`, optional) — Patterns to exclude. Supports fnmatch glob matching and prefix matching (e.g., `"myapp.tests"` excludes `myapp.tests` and all sub-modules).

**Returns:** `self` for method chaining.

```python
# Scan entire package recursively
ctx.scan("myapp")

# Scan single module
ctx.scan("myapp.services")

# Auto-detect caller's package
ctx.scan()

# With exclude patterns
ctx.scan("myapp", exclude=["myapp.tests", "myapp.internal_*"])

# Method chaining
ctx.scan("myapp").refresh()
```

**Scan behavior:**
- Recursive: walks all sub-packages and modules in a package
- Import filtering: only registers objects whose `__module__` matches the scanned module (prevents cross-import duplication)
- Deduplication: calling `scan()` multiple times won't register the same object twice
- Auto-detection: uses `inspect.currentframe()` to find the caller's `__package__`

### `add(target)`

Manually register a callable or class with the container. Returns `self` for chaining.

```python
@bean
def my_service():
    return MyService()

ctx.add(my_service)
```

This is useful for registering objects that aren't discovered by `scan()`, such as test fixtures or dynamically created beans.

### `refresh()`

Initialize the container and instantiate all registered beans in dependency order.

```python
ctx.refresh()
```

Resolves dependencies iteratively. If any bean definitions can't be instantiated (missing dependencies, circular deps), raises `RuntimeError`. After all beans are created, calls `@post_construct` methods.

### `get_bean(key)`

Retrieve a bean by type or name.

```python
# By type
service = ctx.get_bean(MyService)

# By name (function/class name, or custom name from @bean(name=...))
service = ctx.get_bean("my_service")
```

Raises `KeyError` if not found, `RuntimeError` if multiple beans match a type query.

### `get_beans(type)`

Retrieve all beans of a specific type. Returns a list.

```python
services = ctx.get_beans(MyService)
```

## Dependency Resolution

| Parameter Kind | Resolution Strategy |
|---|---|
| **Positional arguments** | Resolved by type annotation only |
| **Keyword-only arguments** (`*`, `arg`) | Resolved by parameter name, falls back to default |
| **`**kwargs`** | Receives all remaining beans not used by other parameters |

### Positional — type annotation resolution

```python
@component
class UserService:
    def __init__(self, db_config: DbConfig):  # Resolved by DbConfig type
        self.db_config = db_config
```

### Keyword-only — name resolution

```python
@bean
def service(*, db_config, timeout=30):  # db_config resolved by name
    return f"Service: {db_config}, timeout={timeout}"
```

### **kwargs — all remaining beans

```python
@bean
def flexible_service(**kwargs):  # Gets all registered beans
    return kwargs
```

## Custom Bean Names

Both `@bean` and `@component` support a `name` parameter to override the default bean name:

```python
@bean(name="my_config")
def application_config():
    return {"key": "value"}

@component(name="primary_db")
class Database:
    pass

# Access by custom name
ctx.get_bean("my_config")
ctx.get_bean("primary_db")
```

When a custom name is set, the original function/class name is **not** registered — only the custom name works for `get_bean("name")` lookups.

## Error Handling

| Error | When |
|---|---|
| `KeyError` | Requested bean not found in container |
| `RuntimeError` | Bean instantiation failure (including circular dependencies) |
| `RuntimeError` | Ambiguous type match — multiple beans of same type via `get_bean(Type)` |
| `TypeError` | `@bean` on a class or `@component` on a function |
| `ValueError` | `scan()` auto-detection from `__main__` or unknown caller |
