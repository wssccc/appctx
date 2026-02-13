# AppCtx

Spring-style dependency injection for Python

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/wssccc/appctx/blob/main/LICENSE)
[![PyPI Version](https://img.shields.io/pypi/v/appctx.svg)](https://pypi.org/project/appctx/)

## Overview

AppCtx is a lightweight dependency injection container inspired by the Spring Framework, providing a clean and elegant dependency management solution for Python applications. It makes it easy to manage dependencies and create maintainable, testable code.

**Python Requirements**: 3.8+  
**License**: MIT

### Features

- 🚀 **Easy to Use** - Register and inject dependencies with simple decorators
- 🔄 **Auto-wiring** - Automatic dependency resolution based on type annotations
- 🏗️ **Flexible Configuration** - Support for both function and class bean definitions
- 📦 **Lightweight** - Minimal dependencies, focused on core functionality
- 🐍 **Pythonic** - API design that follows Python conventions
- 🔧 **Python 3.8+** - Compatible with Python 3.8, 3.9, 3.10, and 3.11
- 🎯 **Decorator-based bean registration** - Simple `@bean` decorator for registration
- 🔍 **Circular dependency detection** - Detects and reports circular dependencies

## Installation

```bash
pip install appctx
```

### Development Installation

For development, clone the repository and install with development dependencies:

```bash
git clone https://github.com/wssccc/appctx.git
cd appctx
pip install -e .[dev]
```

This will install the following development tools:
- `pytest>=7.0` - Testing framework
- `pytest-cov>=4.0` - Coverage reporting
- `black>=22.0` - Code formatting
- `flake8>=5.0` - Linting
- `mypy>=1.0` - Type checking
- `isort>=5.0` - Import sorting

## Basic Concepts

AppCtx provides a simple way to manage dependencies in your Python applications:

- **Beans**: Objects managed by the container
- **Container**: The `ApplicationContext` that manages beans
- **Dependency Injection**: Automatic wiring of dependencies based on type annotations

## Quick Start

### Basic Usage

```python
from appctx import bean, get_bean, refresh

# Define service classes
class DatabaseService:
    def __init__(self, connection_string: str = "sqlite:///default.db"):
        self.connection_string = connection_string
    
    def connect(self):
        return f"Connected to {self.connection_string}"

class UserService:
    def __init__(self, db: DatabaseService):
        self.db = db
    
    def get_user(self, user_id: int):
        connection = self.db.connect()
        return f"User {user_id} from {connection}"

# Register beans using decorators
@bean
def database_service():
    return DatabaseService("postgresql://localhost/myapp")

@bean
def user_service(db: DatabaseService):  # Auto-inject DatabaseService
    return UserService(db)

# Initialize the container
refresh()

# Get and use beans
user_svc = get_bean(UserService)
print(user_svc.get_user(123))
```

### Class Decorator Usage

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

notification_svc = get_bean(NotificationService)
print(notification_svc.notify("user@example.com", "Hello World!"))
```

### How It Works

1. **Bean Registration**: Use the `@bean` decorator to register functions that create beans
2. **Type Annotations**: Use type annotations to declare dependencies
3. **Container Initialization**: Call `refresh()` to initialize the container and resolve dependencies
4. **Bean Retrieval**: Use `get_bean()` to retrieve beans by type or name

### Advanced Usage

#### Custom Application Context

```python
from appctx import ApplicationContext

# Create custom context
ctx = ApplicationContext()

@ctx.bean
def my_service():
    return MyService()

ctx.refresh()
service = ctx.get_bean(MyService)
```

#### Multiple Beans of Same Type

```python
@bean
def primary_db():
    return DatabaseService("primary://db")

@bean
def secondary_db():
    return DatabaseService("secondary://db")

refresh()

# Get all database services
dbs = get_beans(DatabaseService)
print(f"Found {len(dbs)} database services")

# Get all beans of a specific type
databases = get_beans(DatabaseService)
print(len(databases))  # 2
```

#### Named Bean Retrieval

```python
@bean
def database_service():
    return DatabaseService("app.db")

refresh()

# Get bean by name (function name)
db = get_bean("database_service")
```

#### Post-Construct Initialization

Use the `@post_construct` decorator to execute initialization logic after bean construction:

```python
class EmailService:
    def __init__(self, server: str):
        self.server = server
        self.connected = False

    @post_construct
    def connect(self):
        # Automatically called after construction
        self.connection = f"Connected to {self.server}"
        self.connected = True

    @post_construct
    def verify_connection(self):
        # Multiple post_construct methods are supported
        assert self.connected

@bean
def config_service():
    return ConfigService("smtp.example.com")

@bean
def email_service(config: ConfigService):
    # Config is injected before post_construct runs
    return EmailService(config.smtp_server)

refresh()

email = get_bean(EmailService)
print(email.connection)  # "Connected to smtp.example.com"
```

## API Reference

### Core Decorators

#### `@bean`

Register a function or class as a bean.

```python
@bean
def my_service():
    return MyService()

@bean
class MyComponent:
    def __init__(self, dependency: SomeDependency):
        self.dependency = dependency
```

#### `@post_construct`

Mark a method to be called automatically after the bean has been constructed and all dependencies have been injected. The method should only accept `self` as a parameter and should not return any value. If the method raises an exception, the bean will not be registered in the container.

```python
class DatabaseService:
    def __init__(self):
        self.connection = None

    @post_construct
    def init(self):
        # Initialize the database connection
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

### Container Operations

#### `refresh()`

Initialize the container and instantiate all beans. Must be called before getting beans.

```python
refresh()
```

#### `get_bean(key)`

Get a bean by type or name.

```python
# Get by type
service = get_bean(MyService)

# Get by name
service = get_bean("my_service")
```

#### `get_beans(type)`

Get all beans of a specific type.

```python
services = get_beans(MyService)
```

## Dependency Resolution

AppCtx uses a sophisticated dependency resolution strategy that handles different parameter types:

1. **Positional Arguments** - Resolved by type annotations only. Must have type annotations to be resolved.
2. **Keyword-only Arguments** - Resolved by parameter name first, then use default values if available.
3. **Variable Keyword Arguments (**kwargs)** - Injects all remaining beans that haven't been used as other parameters.
4. **Auto-wiring** - Container automatically resolves and injects dependencies based on the above rules.
5. **Circular Dependency Detection** - Detects and reports circular dependency issues.

### Parameter Resolution Examples

```python
@bean
def config_service():
    return "config_value"

@bean
def database_service():
    return "database_url"

# Positional args - resolved by type annotations
@bean
def service_with_positional(config_service: str):
    return f"Service: {config_service}"

# Keyword-only args - resolved by name
@bean
def service_with_keyword_only(*, config_service, timeout=30):
    return f"Service: {config_service}, timeout={timeout}"

# **kwargs - gets all remaining beans
@bean
def flexible_service(**kwargs):
    return f"Flexible: {kwargs}"
```

## Error Handling

### Common Errors

```python
# Bean not found
try:
    service = get_bean(UnknownService)
except KeyError as e:
    print(f"Bean not found: {e}")

# Multiple beans of same type conflict
try:
    refresh()
except RuntimeError as e:
    print(f"Bean instantiation failed: {e}")

# Circular dependency
try:
    refresh()
except RuntimeError as e:
    print(f"Circular dependency detected: {e}")
```

## Best Practices

1. **Use Type Annotations** - Specify dependency types clearly for better code readability
2. **Single Responsibility** - Each bean should have a clear responsibility
3. **Interface Abstraction** - Use abstract base classes to define service interfaces
4. **Configuration Separation** - Centralize bean configuration management
5. **Test-Friendly** - Design beans that are easy to test

## Development

### Requirements

- Python 3.8 or higher
- pip

### Running Tests

```bash
pytest tests/
```

### Running Tests with Coverage

```bash
pytest --cov=src/appctx tests/
```

### Code Formatting

Format code with Black (line length: 88):

```bash
black src/ tests/
```

### Import Sorting

Sort imports with isort (Black profile):

```bash
isort src/ tests/
```

### Linting

Check code quality with flake8:

```bash
flake8 src/ tests/
```

### Type Checking

Run type checking with mypy:

```bash
mypy src/
```

### Run All Quality Checks

```bash
# Format code
black src/ tests/
isort src/ tests/

# Run linting and type checking
flake8 src/ tests/
mypy src/

# Run tests with coverage
pytest --cov=src/appctx tests/
```

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/wssccc/appctx/blob/main/LICENSE) file for details.

## Contributing

We welcome contributions! Please see our contributing guidelines below.

### Development Setup

1. Fork the project
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=appctx

# Run linting
black --check src/ tests/
flake8 src/ tests/
mypy src/
```

### Release Process

For maintainers, see [RELEASE.md](RELEASE.md) for detailed release instructions.

## Links

- **Homepage**: [https://github.com/wssccc/appctx](https://github.com/wssccc/appctx)
- **Repository**: [https://github.com/wssccc/appctx](https://github.com/wssccc/appctx)
- **PyPI**: [https://pypi.org/project/appctx/](https://pypi.org/project/appctx/)
- **Issues**: [https://github.com/wssccc/appctx/issues](https://github.com/wssccc/appctx/issues)

## Changelog

### v0.1.0

- Initial release
- Basic dependency injection functionality
- Decorator API
- Auto-wiring support
- Python 3.8+ support
