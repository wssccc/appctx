# AppCtx - Agent Instructions

Universal guidance for AI coding agents working in this repository. `AGENTS.md` is the canonical instruction file; tool-specific instruction files should not duplicate it.

## Project Overview

AppCtx is a lightweight, Spring-inspired dependency injection container for Python. It uses pure marker decorators (`@bean` for functions, `@component` for classes) that do not depend on a container instance. `ApplicationContext.scan()` discovers marked objects in packages.

- Package: `src/appctx/`
- Tests: `tests/`
- Docs: `docs/`
- Python support: **3.9–3.13** (`requires-python >=3.9`)

## Public API

From `appctx/__init__.py`:

- `ApplicationContext`
- `BeanResolutionError` (subclass of `RuntimeError`)
- `bean`
- `component`
- `post_construct`

`ApplicationContext` methods: `scan`, `add`, `refresh`, `refresh_async`, `get_bean`, `get_beans`.

## Core Architecture

- `src/appctx/container.py`: `ApplicationContext`, `BeanResolutionError`, and the resolution/registration helpers.
- `src/appctx/decorators.py`: pure marker decorators. Marker attributes are set with `setattr`.
- Bean definitions live in `bean_defs`; instantiated beans live in `bean_names_map` (name to instance) and `bean_types_map` (type to list of instances).
- `refresh()` / `refresh_async()` instantiate definitions iteratively until no progress remains, then raise an aggregated `BeanResolutionError` for anything left.
- `scan()` uses `pkgutil.walk_packages`; `_scan_module` only registers objects whose `__module__` matches the scanned module.

## Development Workflow

Use the `make` targets. Run `make help` for the full list.

### Testing

```bash
make test
make test-cov
pytest tests/ -q
```

The minimum supported interpreter is Python 3.9. CI runs 3.10–3.13 on `ubuntu-latest`; Python 3.9 is not exercised in CI because `actions/setup-python` has no 3.9 build for the current `ubuntu-latest` image (26.04). Keep 3.9 compatibility in mind when choosing syntax and APIs.

### Code Quality

The project uses **ruff**, not black/flake8/isort:

```bash
make format          # ruff format src/ tests/
make lint            # ruff check + ruff format --check src/ tests/
make typecheck       # mypy src/ (requires: pip install -e .[typecheck])
```

`pyproject.toml` configures ruff (`target-version = "py39"`) and strict mypy (`python_version = "3.9"`). mypy is pinned to `>=1.0,<2.0` because mypy 2.x requires `--python-version >=3.10`.

Full quality pipeline:

```bash
make format && make lint && make typecheck && make test
```

### Build and Release

```bash
make build
make check-build
make publish-test
make publish
```

Do not publish unless explicitly asked. The version lives in `src/appctx/__init__.py` (`__version__`); `pyproject.toml` reads it dynamically. When bumping: update `__version__`, add a `CHANGELOG.md` entry, and commit with `chore: Bump version to x.y.z`.

## Dependency Resolution

1. **Positional arguments**: exact registered type first. If none, use a unique type assignable via `issubclass` (ABC or runtime-checkable Protocol). `object` is excluded from assignability matching. Multiple candidates or none raise `BeanResolutionError`.
2. **Keyword-only arguments**: bean name first, then the default; otherwise an error.
3. **`**kwargs`**: all remaining beans not consumed by other parameters.
4. Exact matches always win over assignable matches. If multiple *exact* beans exist, that is an error and MRO fallback is not attempted.
5. Parameterized generics (`List[X]`), `Any`, and non-runtime-checkable Protocols do not participate in MRO matching.

PEP 563 (`from __future__ import annotations`) is supported. Annotations are resolved with `typing.get_type_hints` (for classes, on `__init__`). If the signature cannot be evaluated as a whole, each string annotation is evaluated on its own (`_resolve_annotations`), so one unresolvable name does not turn the other annotations into strings. Annotations that still cannot be evaluated stay strings and are reported by name in a `BeanResolutionError`, never as a `NameError`.

`@bean` factories: if the declared return annotation is a class, the bean is registered under both the declared type and its concrete type. The produced object must be an instance of the declared type (`_check_declared_type` uses `issubclass`; non-runtime-checkable Protocols are trusted). A mismatch raises `TypeError` and the bean is not registered.

### Queries

- `get_bean(Type)`: exact first, then a unique assignable type; multiple matches raise `RuntimeError` with candidate names; no match raises `KeyError`. `object` is not used for assignability.
- `get_beans(Type)`: exact plus assignable beans, deduplicated by object identity, with exact matches first.

## Bean Registration

```python
from appctx import ApplicationContext, bean, component

@bean
def service():
    return Service("config")

@bean(name="my_service")
def named_service():
    return Service("config")

@component
class Component:
    def __init__(self, dependency: Service):
        self.dependency = dependency

ctx = ApplicationContext()
ctx.scan("myapp").refresh()
```

`add()` accepts classes and functions (routines). Modules are ignored. Pre-built instances and other callables (for example `functools.partial`) raise `TypeError`; use a `@bean` factory instead. There is no `add_instance()`.

`@component` classes without a custom `__init__` are constructed with no arguments. An explicit `**kwargs` constructor still receives all remaining beans.

## Scanning

`scan(package_name=None, exclude=None, include=None)`:

- `exclude` and `include` support fnmatch globs and package-prefix matching.
- When both are provided, a module must match `include` and must not match `exclude`; exclude wins.
- The root module is also subject to `include`; scanning still recurses into subpackages.
- Excluding the root module preserves the historical behavior of stopping the scan.
- `include=None` or `include=[]` means no include filter.
- Pattern matching is case-sensitive on every platform (`fnmatch.fnmatchcase`), because module names are.

## Lifecycle

`@post_construct` methods are called after all beans are created, in `dir(obj)` order.

- `refresh()` runs synchronous hooks only. If any async hook exists, it raises `RuntimeError` *before* calling any hook; use `refresh_async()`.
- `refresh_async()` runs synchronous hooks inline and awaits async hooks in the same order. It also works when there are no async hooks.
- If a hook fails, the bean is removed from `bean_names_map` and from every `bean_types_map` key before the exception propagates.

## Error Handling

- `BeanResolutionError` (subclass of `RuntimeError`): one or more bean definitions cannot be instantiated; the message lists each bean and its reason (missing type, ambiguous candidates, unresolved keyword-only argument, annotation that cannot be evaluated).
- `KeyError`: `get_bean` found no bean.
- `RuntimeError`: `get_bean(Type)` matched multiple beans, or `refresh()` found an async hook.
- `TypeError`: decorator misuse, `add()` received a pre-built instance, or a `@bean` factory produced an object that does not match its declared return type.
- `ValueError`: `scan()` auto-detection from `__main__` or an unknown caller.

## Critical Implementation Notes

- `_EMPTY_SPEC` is used for classes whose `__init__ is object.__init__`; this prevents object's `**kwargs` constructor from swallowing all beans.
- `_extract_signature()` returns `(FullArgSpec, parameter_annotations, declared_return_type)`. It removes the instance parameter by position and drops the `return` key from parameter annotations. `_cached_signature()` memoizes it per `bean_def` for one `_instantiate_all()` run (`_signature_cache`), because the retry loop revisits unresolved definitions.
- `_resolve_dependencies()` returns `((args, kwargs), None)` on success or `(None, reason)` on failure; it must not raise for ordinary resolution failures.
- `_instantiate_all()` runs the iterative loop and raises `BeanResolutionError` with one `- name: reason` line per remaining definition. `_describe_failure()` recomputes reasons against the final container state. `_providers()`, `_missing_types()` and `_circular_hint()` append a hint when a missing type is produced by another unresolved definition.
- `_instantiate()` returns `bool`; signature/resolution failures return `False`, while exceptions raised by a factory itself (including a declared-return-type mismatch) propagate.
- Type lookup helpers: `_exact_beans`, `_assignable_beans`, `_safe_issubclass`, `_dedupe_by_identity`. Exact matches take precedence.
- `_register_bean()` registers a bean under `type(obj)` and, for `@bean` factories with a class return annotation, the declared type. It avoids duplicate identity entries per key.
- `_unregister()` removes the bean from the name map and from all type-map lists, deleting empty type keys.
- `bean_types_map` is a `defaultdict(list)`; prefer `.get()` for lookups so failed lookups do not create empty entries.
- `add()` order: modules are a no-op; classes/functions are appended to `bean_defs`; everything else raises `TypeError`.
- Marker attributes are set with `setattr` to remain compatible with newer mypy versions.

## Testing Notes

- `tests/test_pep563.py` starts with `from __future__ import annotations`; referenced classes must be module-level for `typing.get_type_hints` to resolve them.
- `tests/test_scan.py::test_scan_auto_detect` scans the entire `tests` package. Avoid module-level decorated classes with unsatisfiable dependencies or async hooks in test modules; register such classes manually inside the test instead.
- Add regression tests for any behavior change in `tests/`; run `pytest -q` before finishing.
- The project supports Python 3.9+; avoid 3.10+-only syntax (for example `match`) and keep ruff/mypy targets at 3.9.

## Project Structure

```text
src/appctx/
    __init__.py      # public exports and __version__
    container.py     # ApplicationContext, BeanResolutionError
    decorators.py    # @bean, @component, @post_construct
    py.typed
tests/               # pytest suite and fixtures
docs/                # API reference and development guide
.github/workflows/   # CI and publishing
```

## Working Agreements

- Put scratch files in `temp/transient/` and never commit them.
- Do not run `git stash`, `git checkout`, or `git add -A`.
- Do not edit build artifacts (`build/`, `dist/`, `*.egg-info/`, caches); regenerate them with the Makefile.
- Keep code, comments, and documentation in English.
- Prefer minimal, focused changes and run the quality pipeline before reporting completion.
