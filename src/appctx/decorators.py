from typing import Any, Callable

from .container import ApplicationContext

# Default application context instance
_default_context = ApplicationContext()


def bean(func_or_class: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to register a function or class as a bean in the default
    application context.

    Args:
        func_or_class: The function or class to register as a bean

    Returns:
        The original function or class
    """
    return _default_context.bean(func_or_class)


def component(func_or_class: Callable[..., Any]) -> Callable[..., Any]:
    """
    Alias for bean decorator.

    Args:
        func_or_class: The function or class to register as a bean

    Returns:
        The original function or class
    """
    return bean(func_or_class)

def post_construct(func: Callable[[Any], None]) -> Callable[[Any], None]:
    """
    Decorator to mark a method to be called after the bean has been
    constructed.

    The method should only accept self as a parameter and should not return any value.

    Args:
        func: The method to mark

    Returns:
        The original method
    """
    func._is_post_construct = True  # type: ignore[attr-defined]
    return func