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
