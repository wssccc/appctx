"""
AppCtx - Spring style dependency injection for Python.

This package provides a lightweight dependency injection container
inspired by the Spring Framework for Java.
"""

__version__ = "0.5"
__author__ = "wssccc"
__email__ = "wssccc@qq.com"

from appctx.container import ApplicationContext
from appctx.decorators import bean, component, post_construct

__all__ = [
    "ApplicationContext",
    "bean",
    "component",
    "post_construct",
]
