"""Tests for component shape edge cases and container isolation."""

import pytest

from appctx import ApplicationContext, bean, component


class Settings:
    pass


@bean
def settings() -> Settings:
    return Settings()


@component
class Marker:
    pass


@component
class Collector:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class BaseService:
    def __init__(self, settings: Settings):
        self.settings = settings


@component
class InheritedService(BaseService):
    pass


class NoInitBase:
    pass


@component
class InheritsObjectInit(NoInitBase):
    pass


def test_component_without_init_is_zero_arg():
    ctx = ApplicationContext()
    ctx.add(settings).add(Marker).refresh()

    marker = ctx.get_bean(Marker)
    assert isinstance(marker, Marker)
    assert ctx.get_bean(Settings) is not None


def test_component_with_explicit_kwargs_receives_remaining_beans():
    ctx = ApplicationContext()
    ctx.add(settings).add(Collector).refresh()

    collector = ctx.get_bean(Collector)
    assert collector.kwargs["settings"] is ctx.get_bean(Settings)


def test_component_inherits_custom_init():
    ctx = ApplicationContext()
    ctx.add(settings).add(InheritedService).refresh()

    service = ctx.get_bean(InheritedService)
    assert service.settings is ctx.get_bean(Settings)


def test_component_inheriting_object_init_is_zero_arg():
    ctx = ApplicationContext()
    ctx.add(settings).add(InheritsObjectInit).refresh()

    instance = ctx.get_bean(InheritsObjectInit)
    assert isinstance(instance, InheritsObjectInit)


def test_multiple_contexts_are_isolated():
    @bean
    def first():
        return "first"

    @bean
    def second():
        return "second"

    ctx1 = ApplicationContext()
    ctx2 = ApplicationContext()
    ctx1.add(first).refresh()
    ctx2.add(second).refresh()

    assert ctx1.get_bean("first") == "first"
    assert ctx2.get_bean("second") == "second"
    with pytest.raises(KeyError):
        ctx1.get_bean("second")
    with pytest.raises(KeyError):
        ctx2.get_bean("first")
