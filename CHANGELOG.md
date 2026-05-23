# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
