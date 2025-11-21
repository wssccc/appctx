"""Tests for the ApplicationContext container."""

import pytest

from appctx.container import ApplicationContext


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

    @ctx.bean
    def service():
        return Service("test")

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

    @ctx.bean
    def service():
        return Service("injected")

    @ctx.bean
    def repository(service: Service):
        return Repository(service)

    ctx.refresh()

    repo = ctx.get_bean(Repository)
    assert repo.service.name == "injected"
    assert ctx.get_bean(Service) is repo.service


def test_multiple_dependencies():
    """Test multiple dependencies."""
    ctx = ApplicationContext()

    @ctx.bean
    def service():
        return Service("shared")

    @ctx.bean
    def repository(service: Service):
        return Repository(service)

    @ctx.bean
    def controller(repository: Repository, service: Service):
        return Controller(repository, service)

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

    @ctx.bean
    def service1():
        return Service("service1")

    @ctx.bean
    def service2():
        return Service("service2")

    ctx.refresh()

    services = ctx.get_beans(Service)
    assert len(services) == 2
    names = {s.name for s in services}
    assert names == {"service1", "service2"}


def test_circular_dependency():
    """Test circular dependency detection."""
    ctx = ApplicationContext()

    @ctx.bean
    def a(b: "B"):
        return A(b)

    @ctx.bean
    def b(a: "A"):
        return B(a)

    with pytest.raises(RuntimeError, match="Could not instantiate"):
        ctx.refresh()


class A:
    def __init__(self, b: "B"):
        self.b = b


class B:
    def __init__(self, a: "A"):
        self.a = a


def test_kwargs_support():
    """Test bean instantiation with keyword arguments."""
    ctx = ApplicationContext()

    @ctx.bean
    def config_value():
        return "test_config"

    @ctx.bean
    def service_with_kwargs(config_value: str, *, timeout=30, retries=3):
        return f"Service: {config_value}, timeout={timeout}, retries={retries}"

    @ctx.bean
    def service_with_kwargs_only(*, required_param, optional_param="default"):
        return f"Service: {required_param} and {optional_param}"

    @ctx.bean
    def required_param():
        return "required"

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

    @ctx.bean
    def config_value() -> ConfigStr:
        return ConfigStr("test_config")

    @ctx.bean
    def database_url() -> UrlStr:
        return UrlStr("localhost:5432")

    @ctx.bean
    def flexible_service(config_value: ConfigStr, **kwargs):
        extra = ", ".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"Flexible: {config_value}, extras: {extra}"

    ctx.refresh()

    service = ctx.get_bean("flexible_service")
    assert "Flexible: test_config" in service
    assert "database_url=localhost:5432" in service


def test_class_with_kwargs():
    """Test class bean instantiation with kwargs in __init__."""
    ctx = ApplicationContext()

    @ctx.bean
    def config_value():
        return "test_config"

    @ctx.bean
    class ConfigurableService:
        def __init__(
            self, config_value: str, *, max_connections=100, enable_cache=True
        ):
            self.config = config_value
            self.max_connections = max_connections
            self.enable_cache = enable_cache

        def __str__(self):
            return (
                f"ConfigurableService(config={self.config}, "
                f"max_conn={self.max_connections}, cache={self.enable_cache})"
            )

    ctx.refresh()

    service = ctx.get_bean("ConfigurableService")
    assert (
        str(service)
        == "ConfigurableService(config=test_config, max_conn=100, cache=True)"
    )
    assert service.config == "test_config"
    assert service.max_connections == 100
    assert service.enable_cache is True


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

    @ctx.bean
    def config_value() -> ConfigStr:
        return ConfigStr("test_config")

    @ctx.bean
    def database_url() -> UrlStr:
        return UrlStr("localhost:5432")

    @ctx.bean
    def full_service(
        config_value: ConfigStr, database_url: UrlStr, *, debug=False, timeout=30
    ):
        return (
            f"Full: {config_value}, db={database_url}, debug={debug}, timeout={timeout}"
        )

    ctx.refresh()

    service = ctx.get_bean("full_service")
    assert service == "Full: test_config, db=localhost:5432, debug=False, timeout=30"


def test_kwargs_dependency_resolution():
    """Test that kwargs are resolved only by parameter names."""
    ctx = ApplicationContext()

    @ctx.bean
    def string_config():
        return "string_value"

    @ctx.bean
    def int_config():
        return 42

    @ctx.bean
    def service_by_name(string_config: str):
        return f"By type: {string_config}"

    @ctx.bean
    def service_with_kwargs_only(*, string_config):
        return f"By kwargs name: {string_config}"

    ctx.refresh()

    service1 = ctx.get_bean("service_by_name")
    assert service1 == "By type: string_value"

    service2 = ctx.get_bean("service_with_kwargs_only")
    assert service2 == "By kwargs name: string_value"


def test_positional_args_type_resolution():
    """Test that positional arguments are resolved by type annotations."""
    ctx = ApplicationContext()

    @ctx.bean
    def string_config():
        return "string_value"

    @ctx.bean
    def int_config():
        return 42

    @ctx.bean
    def service_with_typed_args(string_config: str, int_config: int):
        return f"Typed: {string_config}, {int_config}"

    ctx.refresh()

    service = ctx.get_bean("service_with_typed_args")
    assert service == "Typed: string_value, 42"
