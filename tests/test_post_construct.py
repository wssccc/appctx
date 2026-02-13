"""Tests for the post_construct decorator."""

import pytest

from appctx import ApplicationContext, bean, post_construct


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

    @ctx.bean
    def service():
        return ServiceWithPostConstruct("test")

    ctx.refresh()

    service_instance = ctx.get_bean("service")
    assert service_instance.initialized is True
    assert service_instance.name == "initialized_test"


def test_multiple_post_construct_methods():
    """Test that multiple post_construct methods are all called."""
    ctx = ApplicationContext()

    @ctx.bean
    def service():
        return ServiceWithMultiplePostConstruct()

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

    @ctx.bean
    def config_service():
        return ConfigService()

    @ctx.bean
    def client_service(config: ConfigService):
        return ClientService(config)

    ctx.refresh()

    client = ctx.get_bean(ClientService)
    assert client.connected is True
    assert client.config is not None
    assert client.config.config["key"] == "value"


def test_post_construct_with_global_decorator():
    """Test post_construct with the global bean decorator."""
    from appctx import post_construct, refresh, get_bean

    class GlobalService:
        def __init__(self):
            self.initialized = False

        @post_construct
        def initialize(self):
            self.initialized = True

    @bean
    def global_service():
        return GlobalService()

    refresh()

    service = get_bean(GlobalService)
    assert service.initialized is True


def test_post_construct_failure_prevents_registration():
    """Test that a failed post_construct prevents bean registration."""
    from appctx import ApplicationContext

    class FailingService:
        def __init__(self):
            self.initialized = False

        @post_construct
        def init(self):
            self.initialized = True
            raise ValueError("Initialization failed!")

    ctx = ApplicationContext()

    @ctx.bean
    def failing_service():
        return FailingService()

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

    @ctx.bean
    def healthy_service():
        return HealthyService()

    @ctx.bean
    def failing_service():
        return FailingService()

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

    @ctx.bean
    def multi_init_service():
        return MultiInitService()

    # Refresh should fail
    with pytest.raises(ValueError, match="Second init failed!"):
        ctx.refresh()

    # Bean should not be registered even though first init succeeded
    with pytest.raises(KeyError):
        ctx.get_bean("multi_init_service")
