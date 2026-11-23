# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-11-23

### Added
- PEP 563 support — stringized annotations (`from __future__ import annotations`) are resolved with `typing.get_type_hints` for constructor injection, factory arguments, and keyword-only arguments
- MRO-aware type matching — positional arguments and type queries use an exact match first, then a unique assignable type (ABC or runtime-checkable Protocol); `object` is excluded from assignability matching
- `@bean` return annotation type registration — when the declared return type is a class, the bean is registered under both the declared type and its concrete type
- `scan(include=...)` — fnmatch glob and package-prefix filtering; `include` and `exclude` intersect, with `exclude` taking precedence
- Async `@post_construct` hooks via `ApplicationContext.refresh_async()`
- `BeanResolutionError` — a `RuntimeError` subclass with per-bean resolution reasons (missing type, ambiguous candidates, unresolved keyword-only argument, annotation that cannot be evaluated); it also flags missing types that are produced by another unresolved bean, which usually indicates a circular dependency
- CI coverage for Python 3.10–3.13 on `ubuntu-latest` and a separate mypy typecheck job; Python 3.9 remains the minimum supported version but cannot be installed on the current `ubuntu-latest` image
- `make typecheck` target; `make lint` now also checks formatting (`ruff format --check`), matching CI

### Fixed
- `@component` classes without a custom `__init__` are now constructed with no arguments instead of receiving every bean through `**kwargs`
- `refresh()` now reports the specific failing argument, missing type, or candidate list for each bean instead of a generic message
- `get_bean(Type)` now raises `RuntimeError` when multiple beans match, matching the documented behavior
- `add()` now rejects pre-built instances immediately with `TypeError` instead of failing later during `refresh()`
- When a PEP 563 signature cannot be evaluated as a whole, annotations are resolved individually so one unresolvable name no longer breaks the other parameters; the error names the annotation that could not be evaluated instead of reporting a missing bean
- `scan()` include/exclude patterns are matched case-sensitively on every platform (`fnmatchcase`)
- Signature extraction is cached for the duration of a `refresh()`, removing repeated `typing.get_type_hints` calls from the retry loop

### Changed
- **Breaking**: Dropped Python 3.8 support; the minimum supported version is now Python 3.9
- **Breaking**: `get_beans(Type)` now includes beans assignable to the requested type, deduplicated by object identity
- `@bean` factories must return an instance of their declared return type; a mismatch raises `TypeError` and the bean is not registered (non-runtime-checkable Protocols are trusted)
- `refresh()` rejects async `@post_construct` hooks; use `await refresh_async()` instead
- `add()` accepts only classes and functions; modules remain no-ops
- Type checking is installed through the new `typecheck` extra (`pip install -e .[typecheck]`)
- Added Python 3.12 / 3.13 classifiers; `requires-python` is now `>=3.9`
- Version bumped to 0.6.0

## [0.5] - 2026-05-23

### Added
- `@bean` decorator as pure marker for functions (bean factories) — supports `@bean(name="custom")`
- `@component` decorator as pure marker for classes (components) — supports `@component(name="custom")`
- `ApplicationContext.scan(package_name, exclude)` — recursive package/module scanning with fnmatch exclude patterns
- `scan()` auto-detection — call without arguments to auto-detect caller's package
- Cross-module import filtering — scan only registers objects defined in the target module
- Duplicate registration prevention — multiple scans won't register the same object twice

### Changed
- **Breaking**: `@bean` and `@component` are now pure markers, no longer register to a default context
- **Breaking**: `@bean` only accepts functions, `@component` only accepts classes (TypeErrors on misuse)
- **Breaking**: Removed global default context and module-level convenience functions (`add`, `get_bean`, `get_beans`, `refresh`)
- **Breaking**: Removed `ApplicationContext.bean()` instance method — use `scan()` or `add()` instead
- `ApplicationContext.add()` docstring updated to clarify manual registration purpose
- `_instantiate()` now respects `_bean_name` attribute for custom bean names

### Removed
- `_default_context` global singleton
- Module-level `bean`, `component`, `add`, `get_bean`, `get_beans`, `refresh` convenience functions
- `ApplicationContext.bean()` instance method

## [0.3] - 2026-05-23

### Changed
- Bump version to 0.3

## [0.2.2] - 2026-05-23

### Fixed
- Fix falsy bean misjudgment in `_instantiate` by using `bool` return type check

## [0.2.0] - 2025-06-17

### Added
- `@post_construct` decorator for bean initialization hooks
- `**kwargs` dependency injection support
- Type overloads for `ApplicationContext.get_bean` method

### Changed
- Reorganize documentation structure and refine content
- Replace `singledispatchmethod` with simple type checking
- Standardize string quotes and formatting for PEP 8 compliance

## [0.1.2] - 2025-06-17

### Changed
- Support Python 3.8+ version requirement

## [0.1.1] - 2025-06-17

### Changed
- Updated version references in documentation

## [0.1.0] - Initial Release

### Added
- Initial dependency injection container implementation
- Bean registration with @bean decorator
- Dependency resolution through type annotations
- Global context instance for convenience
- Support for circular dependency detection
- Multiple beans of same type support via get_beans(Type)
