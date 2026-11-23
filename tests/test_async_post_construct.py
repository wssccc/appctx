"""Tests for async @post_construct support."""

import asyncio

import pytest

from appctx import ApplicationContext, bean, component, post_construct


class AsyncService:
    def __init__(self):
        self.initialized = False

    @post_construct
    async def init(self):
        self.initialized = True


class AsyncComponent(AsyncService):
    pass


def test_refresh_rejects_async_hooks():
    ctx = ApplicationContext()
    ctx.add(AsyncComponent)

    with pytest.raises(RuntimeError) as exc_info:
        ctx.refresh()

    message = str(exc_info.value)
    assert "async hooks found: AsyncComponent.init" in message
    assert "refresh_async" in message
    assert ctx.get_bean(AsyncComponent).initialized is False


def test_refresh_async_runs_async_hook():
    ctx = ApplicationContext()
    ctx.add(AsyncComponent)

    asyncio.run(ctx.refresh_async())

    assert ctx.get_bean(AsyncComponent).initialized is True


def test_refresh_async_preserves_hook_order():
    class MixedService:
        def __init__(self):
            self.calls = []

        @post_construct
        def a_sync(self):
            self.calls.append("sync")

        @post_construct
        async def b_async(self):
            self.calls.append("async")

    @component
    class MixedComponent(MixedService):
        pass

    ctx = ApplicationContext()
    ctx.add(MixedComponent)

    asyncio.run(ctx.refresh_async())

    assert ctx.get_bean(MixedComponent).calls == ["sync", "async"]


def test_async_hook_failure_unregisters_bean():
    class FailingService:
        def __init__(self):
            self.failed = False

        @post_construct
        async def init(self):
            self.failed = True
            raise ValueError("async init failed")

    @component
    class FailingComponent(FailingService):
        pass

    ctx = ApplicationContext()
    ctx.add(FailingComponent)

    with pytest.raises(ValueError, match="async init failed"):
        asyncio.run(ctx.refresh_async())

    with pytest.raises(KeyError):
        ctx.get_bean("FailingComponent")
    assert ctx.bean_types_map.get(FailingComponent) is None


def test_async_hook_failure_removes_dual_registration_keys():
    class Base:
        pass

    class Impl(Base):
        def __init__(self):
            pass

        @post_construct
        async def init(self):
            raise ValueError("boom")

    @bean
    def factory() -> Base:
        return Impl()

    ctx = ApplicationContext()
    ctx.add(factory)

    with pytest.raises(ValueError, match="boom"):
        asyncio.run(ctx.refresh_async())

    assert ctx.bean_types_map.get(Base) is None
    assert ctx.bean_types_map.get(Impl) is None


def test_refresh_async_works_with_only_sync_hooks():
    @bean
    def service():
        return "value"

    ctx = ApplicationContext()
    ctx.add(service)

    asyncio.run(ctx.refresh_async())

    assert ctx.get_bean("service") == "value"
