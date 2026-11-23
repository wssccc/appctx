"""
AppCtx - Spring style dependency injection for Python.

This package provides a lightweight dependency injection container
inspired by the Spring Framework for Java.
"""

__version__ = "0.6.0"
__author__ = "wssccc"
__email__ = "wssccc@qq.com"

from appctx.container import ApplicationContext, BeanResolutionError
from appctx.decorators import bean, component, post_construct

__all__ = [
    "ApplicationContext",
    "BeanResolutionError",
    "bean",
    "component",
    "post_construct",
]
