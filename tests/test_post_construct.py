"""Tests for the post_construct decorator."""

import pytest

from appctx.container import ApplicationContext
from appctx.decorators import bean, component, post_construct


class ServiceWithPostConstruct:
    def __init__(self, name: str = "default"):
        self.name = name
        self.initialized = False

    @post_construct
    def init(self):
        """Method to be called after construction."""
        self.initialized = True
        self.name = f"initialized_{self.name}"


class ServiceWithMultiplePostConstruct:
    def __init__(self):
        self.init1_called = False
        self.init2_called = False

    @post_construct
    def init_method_1(self):
        self.init1_called = True

    @post_construct
    def init_method_2(self):
        self.init2_called = True


def test_post_construct_decorator():
    """Test that post_construct methods are called after bean creation."""
    ctx = ApplicationContext()

    @bean
    def service():
        return ServiceWithPostConstruct("test")

    ctx.add(service)
    ctx.refresh()

    service_instance = ctx.get_bean("service")
    assert service_instance.initialized is True
    assert service_instance.name == "initialized_test"


def test_multiple_post_construct_methods():
    """Test that multiple post_construct methods are all called."""
    ctx = ApplicationContext()

    @bean
    def service():
        return ServiceWithMultiplePostConstruct()

    ctx.add(service)
    ctx.refresh()

    service_instance = ctx.get_bean("service")
    assert service_instance.init1_called is True
    assert service_instance.init2_called is True


def test_post_construct_with_dependencies():
    """Test post_construct with dependency injection."""

    class ConfigService:
        def __init__(self):
            self.config = {"key": "value"}

    class ClientService:
        def __init__(self, config: ConfigService):
            self.config = config
            self.connected = False

        @post_construct
        def connect(self):
            self.connected = True

    ctx = ApplicationContext()

    @bean
    def config_service():
        return ConfigService()

    @bean
    def client_service(config: ConfigService):
        return ClientService(config)

    ctx.add(config_service).add(client_service)
    ctx.refresh()

    client = ctx.get_bean(ClientService)
    assert client.connected is True
    assert client.config is not None
    assert client.config.config["key"] == "value"


def test_post_construct_on_component():
    """Test post_construct on a @component class."""

    @component
    class ServiceWithInit:
        def __init__(self):
            self.initialized = False

        @post_construct
        def initialize(self):
            self.initialized = True

    ctx = ApplicationContext()
    ctx.add(ServiceWithInit)
    ctx.refresh()

    service = ctx.get_bean(ServiceWithInit)
    assert service.initialized is True


def test_post_construct_failure_prevents_registration():
    """Test that a failed post_construct prevents bean registration."""

    class FailingService:
        def __init__(self):
            self.initialized = False

        @post_construct
        def init(self):
            self.initialized = True
            raise ValueError("Initialization failed!")

    ctx = ApplicationContext()

    @bean
    def failing_service():
        return FailingService()

    ctx.add(failing_service)

    # Refresh should fail
    with pytest.raises(ValueError, match="Initialization failed!"):
        ctx.refresh()

    # Bean should not be registered
    with pytest.raises(KeyError):
        ctx.get_bean("failing_service")


def test_post_construct_failure_with_dependencies():
    """Test that post_construct failure doesn't affect other beans."""

    class HealthyService:
        def __init__(self):
            self.ready = True

        @post_construct
        def init(self):
            pass

    class FailingService:
        def __init__(self):
            self.initialized = False

        @post_construct
        def init(self):
            raise RuntimeError("Failed to init")

    ctx = ApplicationContext()

    @bean
    def healthy_service():
        return HealthyService()

    @bean
    def failing_service():
        return FailingService()

    ctx.add(healthy_service).add(failing_service)

    # Refresh should fail due to failing_service
    with pytest.raises(RuntimeError, match="Failed to init"):
        ctx.refresh()

    # But healthy_service should be registered
    ctx.get_bean("healthy_service")


def test_post_construct_multiple_methods_one_fails():
    """Test that if one post_construct fails, bean is not registered."""

    class MultiInitService:
        def __init__(self):
            self.init1_called = False

        @post_construct
        def init1(self):
            self.init1_called = True

        @post_construct
        def init2(self):
            raise ValueError("Second init failed!")

    ctx = ApplicationContext()

    @bean
    def multi_init_service():
        return MultiInitService()

    ctx.add(multi_init_service)

    # Refresh should fail
    with pytest.raises(ValueError, match="Second init failed!"):
        ctx.refresh()

    # Bean should not be registered even though first init succeeded
    with pytest.raises(KeyError):
        ctx.get_bean("multi_init_service")
