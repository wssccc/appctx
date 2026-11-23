"""Tests for PEP 563 (from __future__ import annotations) support."""

from __future__ import annotations

import pytest

from appctx import ApplicationContext, BeanResolutionError, bean, component


class Settings:
    def __init__(self, host: str = "localhost", port: int = 5432):
        self.host = host
        self.port = port


@bean
def settings() -> Settings:
    return Settings()


@component
class Engine:
    def __init__(self, settings: Settings):
        self.settings = settings


@bean
def session(engine: Engine, *, settings: Settings, timeout: int = 30):
    return {
        "engine": engine,
        "settings": settings,
        "timeout": timeout,
    }


@bean
def later_engine(engine: Engine) -> Engine:
    return engine


@component
class ForwardConsumer:
    def __init__(self, target: ForwardTarget):
        self.target = target


class ForwardTarget:
    pass


@bean
def forward_target() -> ForwardTarget:
    return ForwardTarget()


def test_pep563_component_injection():
    ctx = ApplicationContext()
    ctx.add(settings).add(Engine).add(session).refresh()

    engine = ctx.get_bean(Engine)
    settings_bean = ctx.get_bean(Settings)
    assert engine.settings is settings_bean

    session_bean = ctx.get_bean("session")
    assert session_bean["engine"] is engine
    assert session_bean["settings"] is settings_bean
    assert session_bean["timeout"] == 30


def test_pep563_bean_factory_dependency():
    ctx = ApplicationContext()
    ctx.add(settings).add(Engine).add(later_engine).refresh()

    assert ctx.get_bean("later_engine") is ctx.get_bean(Engine)


def test_pep563_forward_reference():
    ctx = ApplicationContext()
    ctx.add(forward_target).add(ForwardConsumer).refresh()

    consumer = ctx.get_bean(ForwardConsumer)
    assert consumer.target is ctx.get_bean(ForwardTarget)


def test_pep563_unresolvable_annotation_falls_back():
    class LocalOnly:
        pass

    @bean
    def needs_local(value: LocalOnly):
        return value

    ctx = ApplicationContext()
    ctx.add(needs_local)

    with pytest.raises(BeanResolutionError) as exc_info:
        ctx.refresh()

    message = str(exc_info.value)
    assert "needs_local" in message
    assert "argument 'value' has an annotation that could not be evaluated" in message
    assert "'LocalOnly'" in message


def test_pep563_unresolvable_annotation_does_not_poison_evaluable_ones():
    class LocalOnly:
        pass

    @component
    class Consumer:
        def __init__(self, settings: Settings, local: LocalOnly):
            self.settings = settings
            self.local = local

    ctx = ApplicationContext()
    ctx.add(settings).add(Consumer)

    with pytest.raises(BeanResolutionError) as exc_info:
        ctx.refresh()

    # 'settings' still evaluates to the module-level Settings class; only
    # the genuinely unresolvable 'local' annotation is reported.
    message = str(exc_info.value)
    assert "argument 'local' has an annotation that could not be evaluated" in message
    assert "argument 'settings'" not in message


def test_pep563_unresolvable_return_annotation_does_not_block_injection():
    class LocalResult:
        pass

    @bean
    def local_factory(settings: Settings) -> LocalResult:
        return LocalResult()

    ctx = ApplicationContext()
    ctx.add(settings).add(local_factory)
    ctx.refresh()

    result = ctx.get_bean("local_factory")
    assert isinstance(result, LocalResult)
    assert ctx.get_bean(LocalResult) is result


def test_pep563_class_without_init():
    @component
    class Marker:
        pass

    @bean
    def settings_bean() -> Settings:
        return Settings(host="marker")

    ctx = ApplicationContext()
    ctx.add(settings_bean).add(Marker).refresh()

    marker = ctx.get_bean(Marker)
    assert isinstance(marker, Marker)
