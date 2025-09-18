"""Tests for the decorators module."""

from appctx.container import ApplicationContext


class MockService:
    def __init__(self, name: str = "test"):
        self.name = name


def test_bean_decorator():
    """Test the bean decorator with independent context."""
    ctx = ApplicationContext()

    @ctx.bean
    def test_service():
        return MockService("decorated")

    ctx.refresh()

    service = ctx.get_bean(MockService)
    assert service.name == "decorated"
    assert service is ctx.get_bean("test_service")


def test_component_decorator():
    """Test the component decorator alias."""
    ctx = ApplicationContext()

    def another_service():
        return MockService("component")

    ctx.add(another_service)
    ctx.refresh()

    service = ctx.get_bean(MockService)
    assert service.name == "component"


def test_bean_with_dependencies():
    """Test bean decorator with dependencies."""
    ctx = ApplicationContext()

    @ctx.bean
    def base_service():
        return MockService("base")

    @ctx.bean
    def dependent_service(base_service: MockService):
        return MockService(f"dependent_on_{base_service.name}")

    ctx.refresh()

    base = ctx.get_bean("base_service")
    dependent = ctx.get_bean("dependent_service")

    assert base.name == "base"
    assert dependent.name == "dependent_on_base"
