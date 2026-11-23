"""Tests for MRO-aware type matching, dual registration, and queries."""

from abc import ABC
from typing import Protocol, runtime_checkable

import pytest

from appctx import ApplicationContext, BeanResolutionError, bean, component


class Notifier(ABC):
    pass


@component
class EmailNotifier(Notifier):
    pass


@component
class ConsoleNotifier(Notifier):
    pass


class NotificationService:
    def __init__(self, notifier: Notifier):
        self.notifier = notifier


def test_abc_dependency_gets_unique_subclass():
    ctx = ApplicationContext()
    ctx.add(EmailNotifier).add(NotificationService).refresh()

    service = ctx.get_bean(NotificationService)
    assert isinstance(service.notifier, EmailNotifier)
    assert ctx.get_bean(Notifier) is service.notifier


def test_abc_dependency_ambiguous():
    ctx = ApplicationContext()
    ctx.add(EmailNotifier).add(ConsoleNotifier).add(NotificationService)

    with pytest.raises(BeanResolutionError) as exc_info:
        ctx.refresh()

    message = str(exc_info.value)
    assert "notifier" in message
    assert "2 candidates" in message
    assert "EmailNotifier" in message
    assert "ConsoleNotifier" in message


def test_get_beans_includes_assignable_subclasses():
    ctx = ApplicationContext()
    ctx.add(EmailNotifier).add(ConsoleNotifier).refresh()

    beans = ctx.get_beans(Notifier)
    assert len(beans) == 2
    assert {type(bean).__name__ for bean in beans} == {
        "EmailNotifier",
        "ConsoleNotifier",
    }


def test_get_bean_multiple_assignable_raises():
    ctx = ApplicationContext()
    ctx.add(EmailNotifier).add(ConsoleNotifier).refresh()

    with pytest.raises(RuntimeError, match="Multiple beans match type Notifier"):
        ctx.get_bean(Notifier)


def test_exact_concrete_type_still_wins():
    ctx = ApplicationContext()
    ctx.add(EmailNotifier).add(ConsoleNotifier).refresh()

    email = ctx.get_bean(EmailNotifier)
    assert isinstance(email, EmailNotifier)
    assert len(ctx.get_beans(EmailNotifier)) == 1


def test_dual_registration_from_return_annotation():
    class Store:
        def save(self):
            pass

    class SqlStore(Store):
        def save(self):
            pass

    @bean
    def store() -> Store:
        return SqlStore()

    ctx = ApplicationContext()
    ctx.add(store).refresh()

    stored = ctx.get_bean(Store)
    assert isinstance(stored, SqlStore)
    assert ctx.get_bean(SqlStore) is stored
    assert ctx.get_beans(Store) == [stored]
    assert ctx.get_beans(SqlStore) == [stored]


def test_dual_registration_is_deduplicated_for_assignable_queries():
    class Root:
        pass

    class Base(Root):
        pass

    class Impl(Base):
        pass

    @bean
    def base_factory() -> Base:
        return Impl()

    ctx = ApplicationContext()
    ctx.add(base_factory).refresh()

    beans = ctx.get_beans(Root)
    assert len(beans) == 1
    assert ctx.get_bean(Root) is ctx.get_bean(Impl)


def test_object_is_not_used_for_assignable_matching():
    class Thing:
        pass

    @component
    class NeedsObject:
        def __init__(self, value: object):
            self.value = value

    @bean
    def thing() -> Thing:
        return Thing()

    ctx = ApplicationContext()
    ctx.add(thing).add(NeedsObject)

    with pytest.raises(BeanResolutionError) as exc_info:
        ctx.refresh()

    assert "needs a bean of type object" in str(exc_info.value)
    assert ctx.get_beans(object) == []


def test_bool_satisfies_int_via_python_issubclass_semantics():
    @bean
    def flag() -> bool:
        return True

    @bean
    def needs_int(value: int):
        return value

    ctx = ApplicationContext()
    ctx.add(flag).add(needs_int).refresh()

    assert ctx.get_bean("needs_int") is True


def test_runtime_checkable_protocol_matches_structurally():
    @runtime_checkable
    class Greeter(Protocol):
        def greet(self) -> str: ...

    @component
    class FriendlyGreeter:
        def greet(self) -> str:
            return "hi"

    @component
    class GreetingService:
        def __init__(self, greeter: Greeter):
            self.greeter = greeter

    ctx = ApplicationContext()
    ctx.add(FriendlyGreeter).add(GreetingService).refresh()

    assert ctx.get_bean(GreetingService).greeter is ctx.get_bean(FriendlyGreeter)


def test_non_runtime_protocol_is_skipped():
    class Greeter(Protocol):
        def greet(self) -> str: ...

    @component
    class FriendlyGreeter:
        def greet(self) -> str:
            return "hi"

    @component
    class GreetingService:
        def __init__(self, greeter: Greeter):
            self.greeter = greeter

    ctx = ApplicationContext()
    ctx.add(FriendlyGreeter).add(GreetingService)

    with pytest.raises(BeanResolutionError) as exc_info:
        ctx.refresh()

    assert "Greeter" in str(exc_info.value)


def test_get_bean_multiple_exact_types_raises():
    @bean
    def first() -> int:
        return 1

    @bean
    def second() -> int:
        return 2

    ctx = ApplicationContext()
    ctx.add(first).add(second).refresh()

    with pytest.raises(RuntimeError, match="Multiple beans match type int"):
        ctx.get_bean(int)


def test_exact_match_beats_assignable_match():
    class Base:
        pass

    class Impl(Base):
        pass

    @bean
    def base() -> Base:
        return Base()

    @bean
    def impl() -> Impl:
        return Impl()

    @bean
    def consumer(value: Base):
        return value

    ctx = ApplicationContext()
    ctx.add(base).add(impl).add(consumer).refresh()

    assert type(ctx.get_bean("consumer")) is Base
    assert type(ctx.get_bean(Base)) is Base


def test_declared_return_type_mismatch_raises():
    class Base:
        pass

    class Unrelated:
        pass

    @bean
    def wrong() -> Base:
        return Unrelated()

    ctx = ApplicationContext()
    ctx.add(wrong)

    with pytest.raises(
        TypeError, match="declared to return Base but produced Unrelated"
    ):
        ctx.refresh()

    assert ctx.bean_names_map == {}
    assert dict(ctx.bean_types_map) == {}


def test_non_runtime_protocol_return_type_is_trusted():
    class Greeter(Protocol):
        def greet(self) -> str: ...

    class Impl:
        def greet(self) -> str:
            return "hi"

    @bean
    def greeter() -> Greeter:
        return Impl()

    ctx = ApplicationContext()
    ctx.add(greeter).refresh()

    assert ctx.get_bean(Greeter) is ctx.get_bean(Impl)
