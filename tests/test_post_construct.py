"""Tests for the post_construct decorator."""

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

    service = ctx.get_bean("service")
    assert service.initialized is True
    assert service.name == "initialized_test"


def test_multiple_post_construct_methods():
    """Test that multiple post_construct methods are all called."""
    ctx = ApplicationContext()

    @ctx.bean
    def service():
        return ServiceWithMultiplePostConstruct()

    ctx.refresh()

    service = ctx.get_bean("service")
    assert service.init1_called is True
    assert service.init2_called is True


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
