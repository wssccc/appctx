"""Tests for the ApplicationContext container."""

import pytest

from appctx.container import ApplicationContext
from appctx.decorators import bean, component


class Service:
    def __init__(self, name: str = "default"):
        self.name = name


class Repository:
    def __init__(self, service: Service):
        self.service = service


class Controller:
    def __init__(self, repository: Repository, service: Service):
        self.repository = repository
        self.service = service


def test_basic_bean_registration():
    """Test basic bean registration and retrieval."""
    ctx = ApplicationContext()

    @bean
    def service():
        return Service("test")

    ctx.add(service)
    ctx.refresh()

    # Get by type
    s = ctx.get_bean(Service)
    assert s.name == "test"

    # Get by name
    s2 = ctx.get_bean("service")
    assert s2.name == "test"
    assert s is s2


def test_dependency_injection():
    """Test dependency injection."""
    ctx = ApplicationContext()

    @bean
    def service():
        return Service("injected")

    @bean
    def repository(service: Service):
        return Repository(service)

    ctx.add(service).add(repository)
    ctx.refresh()

    repo = ctx.get_bean(Repository)
    assert repo.service.name == "injected"
    assert ctx.get_bean(Service) is repo.service


def test_multiple_dependencies():
    """Test multiple dependencies."""
    ctx = ApplicationContext()

    @bean
    def service():
        return Service("shared")

    @bean
    def repository(service: Service):
        return Repository(service)

    @bean
    def controller(repository: Repository, service: Service):
        return Controller(repository, service)

    ctx.add(service).add(repository).add(controller)
    ctx.refresh()

    ctrl = ctx.get_bean(Controller)
    repo = ctx.get_bean(Repository)
    svc = ctx.get_bean(Service)

    assert ctrl.repository is repo
    assert ctrl.service is svc
    assert repo.service is svc
    assert svc.name == "shared"


def test_get_beans_by_type():
    """Test getting multiple beans of the same type."""
    ctx = ApplicationContext()

    @bean
    def service1():
        return Service("service1")

    @bean
    def service2():
        return Service("service2")

    ctx.add(service1).add(service2)
    ctx.refresh()

    services = ctx.get_beans(Service)
    assert len(services) == 2
    names = {s.name for s in services}
    assert names == {"service1", "service2"}


def test_circular_dependency():
    """Test circular dependency detection."""

    class A:
        def __init__(self, b: "B"):
            self.b = b

    class B:
        def __init__(self, a: "A"):
            self.a = a

    ctx = ApplicationContext()

    @bean
    def a(b: "B"):
        return A(b)

    @bean
    def b(a: "A"):
        return B(a)

    ctx.add(a).add(b)

    with pytest.raises(RuntimeError, match="Could not instantiate"):
        ctx.refresh()


def test_kwargs_support():
    """Test bean instantiation with keyword arguments."""
    ctx = ApplicationContext()

    @bean
    def config_value():
        return "test_config"

    @bean
    def service_with_kwargs(config_value: str, *, timeout=30, retries=3):
        return f"Service: {config_value}, timeout={timeout}, retries={retries}"

    @bean
    def service_with_kwargs_only(*, required_param, optional_param="default"):
        return f"Service: {required_param} and {optional_param}"

    @bean
    def required_param():
        return "required"

    ctx.add(config_value).add(service_with_kwargs).add(service_with_kwargs_only).add(
        required_param
    )
    ctx.refresh()

    # Test basic kwargs
    service = ctx.get_bean("service_with_kwargs")
    assert service == "Service: test_config, timeout=30, retries=3"

    # Test kwargs-only parameters
    service2 = ctx.get_bean("service_with_kwargs_only")
    assert service2 == "Service: required and default"


def test_kwargs_with_varkw():
    """Test bean instantiation with **kwargs."""

    class ConfigStr:
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return self.value

    class UrlStr:
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return self.value

    ctx = ApplicationContext()

    @bean
    def config_value() -> ConfigStr:
        return ConfigStr("test_config")

    @bean
    def database_url() -> UrlStr:
        return UrlStr("localhost:5432")

    @bean
    def flexible_service(config_value: ConfigStr, **kwargs):
        extra = ", ".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"Flexible: {config_value}, extras: {extra}"

    ctx.add(config_value).add(database_url).add(flexible_service)
    ctx.refresh()

    service = ctx.get_bean("flexible_service")
    assert "Flexible: test_config" in service
    assert "database_url=localhost:5432" in service


def test_component_registration():
    """Test component (class-based bean) registration."""
    ctx = ApplicationContext()

    @component
    class ConfigurableService:
        def __init__(self, *, max_connections=100, enable_cache=True):
            self.max_connections = max_connections
            self.enable_cache = enable_cache

    ctx.add(ConfigurableService)
    ctx.refresh()

    service = ctx.get_bean("ConfigurableService")
    assert service.max_connections == 100
    assert service.enable_cache is True


def test_component_with_dependency():
    """Test component with dependency injection."""
    ctx = ApplicationContext()

    @bean
    def config_value():
        return "test_config"

    @component
    class ConfigurableService:
        def __init__(self, config_value: str, *, max_connections=100):
            self.config = config_value
            self.max_connections = max_connections

    ctx.add(config_value).add(ConfigurableService)
    ctx.refresh()

    service = ctx.get_bean("ConfigurableService")
    assert service.config == "test_config"
    assert service.max_connections == 100


def test_mixed_args_and_kwargs():
    """Test bean instantiation with both positional and keyword arguments."""

    class ConfigStr:
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return self.value

    class UrlStr:
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return self.value

    ctx = ApplicationContext()

    @bean
    def config_value() -> ConfigStr:
        return ConfigStr("test_config")

    @bean
    def database_url() -> UrlStr:
        return UrlStr("localhost:5432")

    @bean
    def full_service(
        config_value: ConfigStr, database_url: UrlStr, *, debug=False, timeout=30
    ):
        return (
            f"Full: {config_value}, db={database_url}, debug={debug}, timeout={timeout}"
        )

    ctx.add(config_value).add(database_url).add(full_service)
    ctx.refresh()

    service = ctx.get_bean("full_service")
    assert service == "Full: test_config, db=localhost:5432, debug=False, timeout=30"


def test_kwargs_dependency_resolution():
    """Test that kwargs are resolved only by parameter names."""
    ctx = ApplicationContext()

    @bean
    def string_config():
        return "string_value"

    @bean
    def int_config():
        return 42

    @bean
    def service_by_name(string_config: str):
        return f"By type: {string_config}"

    @bean
    def service_with_kwargs_only(*, string_config):
        return f"By kwargs name: {string_config}"

    ctx.add(string_config).add(int_config).add(service_by_name).add(
        service_with_kwargs_only
    )
    ctx.refresh()

    service1 = ctx.get_bean("service_by_name")
    assert service1 == "By type: string_value"

    service2 = ctx.get_bean("service_with_kwargs_only")
    assert service2 == "By kwargs name: string_value"


def test_falsy_bean_values():
    """Test that beans returning falsy values are correctly instantiated."""
    ctx = ApplicationContext()

    @bean
    def zero_bean():
        return 0

    @bean
    def false_bean():
        return False

    @bean
    def empty_str_bean():
        return ""

    @bean
    def empty_list_bean():
        return []

    @bean
    def none_bean():
        return None

    ctx.add(zero_bean).add(false_bean).add(empty_str_bean).add(empty_list_bean).add(
        none_bean
    )
    ctx.refresh()

    assert ctx.get_bean("zero_bean") == 0
    assert ctx.get_bean("false_bean") is False
    assert ctx.get_bean("empty_str_bean") == ""
    assert ctx.get_bean("empty_list_bean") == []
    assert ctx.get_bean("none_bean") is None


def test_falsy_bean_with_dependency():
    """Test that a bean returning a falsy value can still be used as dependency."""
    ctx = ApplicationContext()

    @bean
    def config():
        return 0

    @bean
    def service(config: int):
        return f"value={config}"

    ctx.add(config).add(service)
    ctx.refresh()

    assert ctx.get_bean("config") == 0
    assert ctx.get_bean("service") == "value=0"


def test_positional_args_type_resolution():
    """Test that positional arguments are resolved by type annotations."""
    ctx = ApplicationContext()

    @bean
    def string_config():
        return "string_value"

    @bean
    def int_config():
        return 42

    @bean
    def service_with_typed_args(string_config: str, int_config: int):
        return f"Typed: {string_config}, {int_config}"

    ctx.add(string_config).add(int_config).add(service_with_typed_args)
    ctx.refresh()

    service = ctx.get_bean("service_with_typed_args")
    assert service == "Typed: string_value, 42"


def test_custom_bean_name():
    """Test that custom bean names via @bean(name=...) work correctly."""
    ctx = ApplicationContext()

    @bean(name="my_service")
    def service():
        return Service("custom_name")

    ctx.add(service)
    ctx.refresh()

    # Get by custom name
    s = ctx.get_bean("my_service")
    assert s.name == "custom_name"

    # Get by type
    s2 = ctx.get_bean(Service)
    assert s2 is s

    # Original function name should not work
    with pytest.raises(KeyError):
        ctx.get_bean("service")


def test_custom_component_name():
    """Test that custom bean names via @component(name=...) work correctly."""
    ctx = ApplicationContext()

    @component(name="my_component")
    class MyComponent:
        pass

    ctx.add(MyComponent)
    ctx.refresh()

    # Get by custom name
    c = ctx.get_bean("my_component")
    assert isinstance(c, MyComponent)

    # Get by type
    c2 = ctx.get_bean(MyComponent)
    assert c2 is c

    # Original class name should not work
    with pytest.raises(KeyError):
        ctx.get_bean("MyComponent")


def test_add_returns_self():
    """Test that add() returns self for method chaining."""
    ctx = ApplicationContext()

    @bean
    def service():
        return Service("test")

    result = ctx.add(service)
    assert result is ctx


def test_kwonlyargs_bean_name_overrides_default():
    """Test that keyword-only args resolve by bean name first,
    then fall back to default.

    This verifies the documented contract:
    "resolved by parameter name, falls back to default".
    When a bean with the same name as a kwonlyarg exists,
    it should be injected instead of using the default value.
    """
    ctx = ApplicationContext()

    @bean
    def timeout():
        return 60

    @bean
    def service(*, timeout=30):
        return f"timeout={timeout}"

    ctx.add(timeout).add(service)
    ctx.refresh()

    # Bean named "timeout" should override the default value of 30
    result = ctx.get_bean("service")
    assert result == "timeout=60"


def test_kwonlyargs_falls_back_to_default_when_no_bean():
    """Test that keyword-only args use default value when no matching bean exists."""
    ctx = ApplicationContext()

    @bean
    def service(*, timeout=30, retries=3):
        return f"timeout={timeout}, retries={retries}"

    ctx.add(service)
    ctx.refresh()

    result = ctx.get_bean("service")
    assert result == "timeout=30, retries=3"
