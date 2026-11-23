"""Tests for scan(include=...) filtering."""

from appctx import ApplicationContext


def test_scan_include_filters_modules():
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures", include=["tests.fixtures.config"])

    from tests.fixtures.config import application_config, db_config
    from tests.fixtures.services.order_service import OrderService

    assert db_config in ctx.bean_defs
    assert application_config in ctx.bean_defs
    assert OrderService not in ctx.bean_defs


def test_scan_include_package_prefix():
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures", include=["tests.fixtures.services.user_service"])

    from tests.fixtures.config import db_config
    from tests.fixtures.services.user_service import UserService

    assert UserService in ctx.bean_defs
    assert db_config not in ctx.bean_defs

    ctx.add(db_config).refresh()
    assert ctx.get_bean(UserService) is not None


def test_scan_include_glob():
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures", include=["tests.fixtures.services.*_service"])

    from tests.fixtures.services.order_service import OrderService
    from tests.fixtures.services.user_service import UserService

    assert UserService in ctx.bean_defs
    assert OrderService in ctx.bean_defs


def test_scan_include_and_exclude_exclude_wins():
    ctx = ApplicationContext()
    ctx.scan(
        "tests.fixtures",
        include=["tests.fixtures.services"],
        exclude=["tests.fixtures.services.order_service"],
    )

    from tests.fixtures.config import db_config
    from tests.fixtures.services.order_service import OrderService
    from tests.fixtures.services.user_service import UserService

    assert UserService in ctx.bean_defs
    assert OrderService not in ctx.bean_defs

    ctx.add(db_config).refresh()
    assert ctx.get_bean(UserService) is not None


def test_scan_include_root_module_filtered():
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures.config", include=["tests.fixtures.services"])

    assert ctx.bean_defs == []


def test_scan_empty_include_means_no_filter():
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures", include=[])
    ctx.refresh()

    from tests.fixtures.config import DbConfig

    assert ctx.get_bean(DbConfig) is not None


def test_scan_include_is_case_sensitive():
    # Module names are case-sensitive; patterns must be too on every platform.
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures", include=["TESTS.fixtures.config"])

    assert ctx.bean_defs == []
