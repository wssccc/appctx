"""Tests for the scan functionality."""

import pytest

from appctx.container import ApplicationContext


def test_scan_package():
    """Test scanning a package recursively finds all annotated objects."""
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures")
    ctx.refresh()

    # Should find beans from config.py
    from tests.fixtures.config import DbConfig

    db = ctx.get_bean(DbConfig)
    assert db.host == "localhost"
    assert db.port == 5432

    # Should find beans from services/user_service.py
    from tests.fixtures.services.user_service import UserService

    user_svc = ctx.get_bean(UserService)
    assert user_svc.db_config is db

    # Should find beans from services/order_service.py
    from tests.fixtures.services.order_service import OrderService

    order_svc = ctx.get_bean(OrderService)
    assert order_svc.db_config is db


def test_scan_single_module():
    """Test scanning a single module only finds objects in that module."""
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures.config")
    ctx.refresh()

    from tests.fixtures.config import DbConfig

    db = ctx.get_bean(DbConfig)
    assert db.host == "localhost"

    # Custom name bean should be accessible
    app = ctx.get_bean("app_config")
    assert app.name == "my_app"

    # Should NOT find beans from other modules
    from tests.fixtures.services.user_service import UserService

    with pytest.raises(KeyError):
        ctx.get_bean(UserService)


def test_scan_with_exclude():
    """Test scanning with exclude patterns filters out specified packages."""
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures", exclude=["tests.fixtures.excluded"])
    ctx.refresh()

    # Should find beans from config and services
    from tests.fixtures.config import DbConfig

    db = ctx.get_bean(DbConfig)
    assert db is not None

    # Should NOT find beans from excluded package
    from tests.fixtures.excluded.internal import InternalService

    with pytest.raises(KeyError):
        ctx.get_bean(InternalService)


def test_scan_with_glob_exclude():
    """Test scanning with fnmatch glob pattern exclude."""
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures", exclude=["tests.fixtures.excl*"])
    ctx.refresh()

    # Should NOT find beans from excluded package (glob match)
    from tests.fixtures.excluded.internal import InternalService

    with pytest.raises(KeyError):
        ctx.get_bean(InternalService)


def test_scan_custom_bean_name():
    """Test that custom bean names work after scan."""
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures")
    ctx.refresh()

    # Custom name for @bean should work
    app = ctx.get_bean("app_config")
    assert app.name == "my_app"

    # Custom name for @component should work
    from tests.fixtures.services.order_service import PremiumOrderService

    premium = ctx.get_bean("premium_order_service")
    assert isinstance(premium, PremiumOrderService)


def test_scan_cross_module_import_filtering():
    """Test that scan doesn't register imported objects from other modules."""
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures.services.user_service")

    # UserService should be in bean_defs (defined in user_service module)
    from tests.fixtures.config import DbConfig
    from tests.fixtures.services.user_service import UserService

    # UserService should be in bean_defs
    assert UserService in ctx.bean_defs

    # DbConfig should NOT be in bean_defs (it's imported, not defined here)
    assert DbConfig not in ctx.bean_defs


def test_scan_multiple_times():
    """Test that scanning multiple packages accumulates bean definitions."""
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures.config")
    ctx.scan("tests.fixtures.services.user_service")
    ctx.refresh()

    from tests.fixtures.config import DbConfig
    from tests.fixtures.services.user_service import UserService

    db = ctx.get_bean(DbConfig)
    user_svc = ctx.get_bean(UserService)
    assert user_svc.db_config is db


def test_scan_returns_self():
    """Test that scan() returns self for method chaining."""
    ctx = ApplicationContext()
    result = ctx.scan("tests.fixtures.config")
    assert result is ctx


def test_scan_method_chaining():
    """Test scan().refresh() method chaining."""
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures.config").refresh()

    from tests.fixtures.config import DbConfig

    db = ctx.get_bean(DbConfig)
    assert db.host == "localhost"


def test_scan_duplicate_prevention():
    """Test that scanning the same package twice doesn't register duplicates."""
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures.config")
    ctx.scan("tests.fixtures.config")  # Scan again
    ctx.refresh()

    from tests.fixtures.config import DbConfig

    services = ctx.get_beans(DbConfig)
    assert len(services) == 1  # Only one DbConfig bean, not two


def test_scan_exclude_prefix_match():
    """Test that exclude patterns also match module prefixes (package tree)."""
    ctx = ApplicationContext()
    ctx.scan("tests.fixtures", exclude=["tests.fixtures.services"])
    ctx.refresh()

    # Should find beans from config
    from tests.fixtures.config import DbConfig

    db = ctx.get_bean(DbConfig)
    assert db is not None

    # Should NOT find beans from services (prefix match)
    from tests.fixtures.services.user_service import UserService

    with pytest.raises(KeyError):
        ctx.get_bean(UserService)


def test_scan_auto_detect():
    """Test that scan() without arguments auto-detects caller's package."""
    ctx = ApplicationContext()
    # Auto-detect should find the caller's package
    ctx.scan()
    ctx.refresh()

    # Should find beans from the fixtures sub-package
    from tests.fixtures.config import DbConfig

    db = ctx.get_bean(DbConfig)
    assert db.host == "localhost"


def test_scan_auto_detect_from_main_raises():
    """Test that auto-scanning from __main__ raises ValueError."""
    import types
    from unittest.mock import patch

    ctx = ApplicationContext()
    main_module = types.ModuleType("__main__")
    main_module.__name__ = "__main__"
    main_module.__package__ = None

    with patch("appctx.container.inspect.getmodule", return_value=main_module):
        with pytest.raises(ValueError, match="Auto-scanning from __main__"):
            ctx.scan()


def test_scan_auto_detect_currentframe_none():
    """Test that auto-scanning raises ValueError when currentframe() returns None."""
    from unittest.mock import patch

    ctx = ApplicationContext()

    with patch("appctx.container.inspect.currentframe", return_value=None):
        with pytest.raises(ValueError, match="Cannot determine caller's frame"):
            ctx.scan()
