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
- When the declared return type is a class, it is registered in addition to the concrete return type; this lets a factory declared to return an ABC/Protocol be resolved by that declared type
- The factory result must be an instance of the declared type (checked with `issubclass`; non-runtime-checkable Protocols are trusted). A mismatch raises `TypeError` at `refresh()` and the bean is not registered

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
- A class without a custom `__init__` is constructed with no arguments; explicit `**kwargs` still receives all remaining beans

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
- Async methods are supported through `await ctx.refresh_async()`. A synchronous `ctx.refresh()` runs only synchronous hooks and raises `RuntimeError` if any async hook is present.

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

### `scan(package_name=None, exclude=None, include=None)`

Scan a package or module for `@bean` / `@component` annotated objects and register them.

**Parameters:**
- `package_name` (`str`, optional) — Package or module name to scan. If `None`, auto-detects the caller's package.
- `exclude` (`list[str]`, optional) — Patterns to exclude. Supports fnmatch glob matching and prefix matching (e.g., `"myapp.tests"` excludes `myapp.tests` and all sub-modules).
- `include` (`list[str]`, optional) — Patterns to include. When provided and non-empty, only matching modules are scanned. Uses the same fnmatch glob and package-prefix matching as `exclude`. When both are provided, a module must match `include` and must not match `exclude`.

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

# Only scan selected packages/modules
ctx.scan("myapp", include=["myapp.services", "myapp.config"])

# Method chaining
ctx.scan("myapp").refresh()
```

**Scan behavior:**
- Recursive: walks all sub-packages and modules in a package
- Import filtering: only registers objects whose `__module__` matches the scanned module (prevents cross-import duplication)
- Deduplication: calling `scan()` multiple times won't register the same object twice
- Include filtering: the root module is also subject to `include`; scanning still recurses into sub-packages to find matching modules
- Pattern matching is case-sensitive on every platform, because module names are
- Auto-detection: uses `inspect.currentframe()` to find the caller's `__package__`

### `add(target)`

Manually register a class or function bean definition with the container. Returns `self` for chaining.

```python
@bean
def my_service():
    return MyService()

ctx.add(my_service)
```

This is useful for registering definitions that aren't discovered by `scan()`, such as test fixtures or dynamically created beans.

**Rules:**
- Classes and functions (including lambdas and methods) are accepted.
- Modules are ignored (no-op).
- Pre-built instances and other callables (for example `functools.partial`) raise `TypeError`. Wrap an instance in a `@bean` factory instead.

### `refresh()`

Initialize the container and instantiate all registered beans in dependency order.

```python
ctx.refresh()
```

Resolves dependencies iteratively. If any bean definitions can't be instantiated (missing dependencies, ambiguous matches, circular deps), raises `BeanResolutionError` (a `RuntimeError` subclass) whose message lists each failing bean and the specific reason; when a missing type is produced by another unresolved definition, the message flags a possible circular dependency. After all beans are created, calls synchronous `@post_construct` methods.

If any async `@post_construct` method is present, `refresh()` raises `RuntimeError` before calling any hook; use `refresh_async()` instead.

### `refresh_async()`

Async counterpart of `refresh()`.

```python
await ctx.refresh_async()
```

Instantiates all beans, then runs synchronous and asynchronous `@post_construct` methods in the same order used by `refresh()`. Use this from an async application when beans have async lifecycle hooks.

### `get_bean(key)`

Retrieve a bean by type or name.

```python
# By type
service = ctx.get_bean(MyService)

# By name (function/class name, or custom name from @bean(name=...))
service = ctx.get_bean("my_service")
```

Type lookups prefer an exact registered type. If none exists, a unique bean assignable to the requested type (for example, a subclass of an ABC) is returned. Multiple candidates raise `RuntimeError` with the candidate names; no candidates raise `KeyError`. The `object` type is not used for assignability matching.

### `get_beans(type)`

Retrieve all beans assignable to a specific type. Returns a list, with exact matches first and duplicates removed by object identity.

```python
services = ctx.get_beans(MyService)
```

## Dependency Resolution

| Parameter Kind | Resolution Strategy |
|---|---|
| **Positional arguments** | Exact type first, then a unique assignable type (ABC or runtime-checkable Protocol) |
| **Keyword-only arguments** (`*`, `arg`) | Resolved by parameter name, falls back to default |
| **`**kwargs`** | Receives all remaining beans not used by other parameters |

PEP 563 (`from __future__ import annotations`) is supported: stringized annotations are resolved with `typing.get_type_hints` when the container refreshes. If the signature cannot be evaluated as a whole (for example because one annotation names a function-local class or a `TYPE_CHECKING`-only import), each string annotation is evaluated on its own, so the remaining parameters are still injected. The annotation that cannot be evaluated is then reported by name in the `BeanResolutionError` instead of a misleading "missing bean" error.

When multiple beans match a positional argument, the container raises `BeanResolutionError` instead of choosing one arbitrarily. Exact type matches always take precedence over assignable matches. The `object` type is excluded from assignability matching.

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
| `BeanResolutionError` | One or more bean definitions cannot be instantiated (missing dependency, ambiguous match, unresolvable kw-only argument, annotation that cannot be evaluated). Subclass of `RuntimeError` |
| `RuntimeError` | `get_bean(Type)` matched multiple beans, or `refresh()` found an async `@post_construct` hook |
| `TypeError` | `@bean` on a class, `@component` on a function, `add()` received a pre-built instance, or a `@bean` factory produced an object that does not match its declared return type |
| `ValueError` | `scan()` auto-detection from `__main__` or unknown caller |
