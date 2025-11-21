"""
AppCtx - Spring style dependency injection for Python.

This package provides a lightweight dependency injection container
inspired by the Spring Framework for Java.
"""

__version__ = "0.1.1"
__author__ = "wssccc"
__email__ = "wssccc@qq.com"

# Import main API for convenience
from .container import ApplicationContext
from .decorators import post_construct

# Create default application context
_default_context = ApplicationContext()

# Export main API functions
bean = _default_context.bean
add = _default_context.add
get_bean = _default_context.get_bean
get_beans = _default_context.get_beans
refresh = _default_context.refresh

__all__ = [
    "ApplicationContext",
    "bean",
    "add",
    "get_bean",
    "get_beans",
    "refresh",
    "post_construct",
]
