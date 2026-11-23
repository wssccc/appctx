"""Tests for actionable resolution errors and add() validation."""

import functools
import sys

import pytest

from appctx import ApplicationContext, BeanResolutionError, bean


class Missing:
    pass


class NeedsMissing:
    def __init__(self, missing: Missing):
        self.missing = missing


def test_missing_bean_message():
    ctx = ApplicationContext()
    ctx.add(NeedsMissing)

    with pytest.raises(BeanResolutionError) as exc_info:
        ctx.refresh()

    message = str(exc_info.value)
    assert "Could not instantiate 1 bean def(s):" in message
    assert "- NeedsMissing:" in message
    assert "argument 'missing'" in message
    assert "type Missing" in message
    assert "none found" in message


def test_multiple_beans_message():
    class Engine:
        pass

    @bean
    def engine_a() -> Engine:
        return Engine()

    @bean
    def engine_b() -> Engine:
        return Engine()

    @bean
    def consumer(engine: Engine):
        return engine

    ctx = ApplicationContext()
    ctx.add(engine_a).add(engine_b).add(consumer)

    with pytest.raises(BeanResolutionError) as exc_info:
        ctx.refresh()

    message = str(exc_info.value)
    assert "argument 'engine' has 2 candidates" in message
    assert "engine_a (Engine)" in message
    assert "engine_b (Engine)" in message


def test_kwonly_unresolvable_message():
    @bean
    def service(*, required):
        return required

    ctx = ApplicationContext()
    ctx.add(service)

    with pytest.raises(BeanResolutionError) as exc_info:
        ctx.refresh()

    message = str(exc_info.value)
    assert "keyword-only argument 'required' cannot be resolved" in message
    assert "no bean named 'required'" in message


def test_missing_annotation_message():
    @bean
    def service(value):
        return value

    ctx = ApplicationContext()
    ctx.add(service)

    with pytest.raises(BeanResolutionError) as exc_info:
        ctx.refresh()

    assert "argument 'value' has no type annotation" in str(exc_info.value)


def test_errors_are_aggregated():
    @bean
    def first(missing: Missing):
        return missing

    @bean
    def second(*, required):
        return required

    ctx = ApplicationContext()
    ctx.add(first).add(second)

    with pytest.raises(BeanResolutionError) as exc_info:
        ctx.refresh()

    message = str(exc_info.value)
    assert "Could not instantiate 2 bean def(s):" in message
    assert "- first:" in message
    assert "- second:" in message


def test_bean_resolution_error_is_runtime_error():
    assert issubclass(BeanResolutionError, RuntimeError)


def test_add_rejects_instance():
    ctx = ApplicationContext()

    with pytest.raises(TypeError, match="add\\(\\) accepts a class or function"):
        ctx.add(object())


def test_add_rejects_partial():
    ctx = ApplicationContext()

    with pytest.raises(TypeError):
        ctx.add(functools.partial(lambda value: value, 1))


def test_add_accepts_function_and_class():
    class Service:
        pass

    def factory():
        return Service()

    ctx = ApplicationContext()
    assert ctx.add(factory) is ctx
    assert ctx.add(Service) is ctx
    assert factory in ctx.bean_defs
    assert Service in ctx.bean_defs


def test_add_accepts_lambda():
    ctx = ApplicationContext()
    factory = lambda: "value"  # noqa: E731
    assert ctx.add(factory) is ctx
    assert factory in ctx.bean_defs


def test_add_ignores_modules():
    ctx = ApplicationContext()
    assert ctx.add(sys) is ctx
    assert ctx.bean_defs == []


def test_circular_dependency_is_hinted():
    class A:
        pass

    class B:
        pass

    @bean
    def a(b: B) -> A:
        return A()

    @bean
    def b(a: A) -> B:
        return B()

    ctx = ApplicationContext()
    ctx.add(a).add(b)

    with pytest.raises(BeanResolutionError) as exc_info:
        ctx.refresh()

    message = str(exc_info.value)
    assert "B is provided by the unresolved bean 'b'" in message
    assert "A is provided by the unresolved bean 'a'" in message


def test_signature_extraction_is_cached_per_refresh(monkeypatch):
    calls = []
    original = ApplicationContext._extract_signature

    def counting(self, bean_def):
        calls.append(bean_def)
        return original(self, bean_def)

    monkeypatch.setattr(ApplicationContext, "_extract_signature", counting)

    class Leaf:
        pass

    class Middle:
        pass

    class Top:
        pass

    @bean
    def leaf() -> Leaf:
        return Leaf()

    @bean
    def middle(leaf_bean: Leaf) -> Middle:
        return Middle()

    @bean
    def top(middle_bean: Middle) -> Top:
        return Top()

    ctx = ApplicationContext()
    # Reverse dependency order forces the retry loop to revisit definitions.
    ctx.add(top).add(middle).add(leaf).refresh()

    assert isinstance(ctx.get_bean(Top), Top)
    assert len(calls) == 3
