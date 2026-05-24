import inspect
from typing import Any, Callable, Optional, Union


def bean(
    _target: Optional[Callable] = None, *, name: Optional[str] = None
) -> Union[Callable, Any]:
    """
    Decorator to mark a function as a bean factory.

    Can be used with or without arguments:
    - @bean          — marks the function as a bean, uses function name as bean name
    - @bean(name="x") — marks the function as a bean with a custom bean name

    @bean can only be used on functions. Use @component for classes.

    Args:
        name: Custom bean name. Defaults to the function's __name__.
            Must not be an empty string.

    Returns:
        The original function with _is_bean and _bean_name attributes set.
    """

    if name is not None and not name:
        raise ValueError("@bean name cannot be an empty string")

    def decorator(func: Callable) -> Callable:
        if not callable(func):
            raise TypeError(f"@bean target must be callable, got {type(func).__name__}")
        if inspect.isclass(func):
            raise TypeError(
                f"@bean can only be used on functions, not classes. "
                f"Use @component for class '{func.__name__}'."
            )
        func._is_bean = True  # type: ignore[attr-defined]
        func._bean_name = name  # type: ignore[attr-defined]
        return func

    if _target is not None:
        # @bean without parentheses
        return decorator(_target)
    else:
        # @bean() or @bean(name="custom")
        return decorator


def component(
    _target: Optional[type] = None, *, name: Optional[str] = None
) -> Union[type, Any]:
    """
    Decorator to mark a class as a component.

    Can be used with or without arguments:
    - @component          — marks the class as a component, uses class name as bean name
    - @component(name="x") — marks the class as a component with a custom bean name

    @component can only be used on classes. Use @bean for functions.

    Args:
        name: Custom bean name. Defaults to the class's __name__.
            Must not be an empty string.

    Returns:
        The original class with _is_component and _bean_name attributes set.
    """

    if name is not None and not name:
        raise ValueError("@component name cannot be an empty string")

    def decorator(cls: type) -> type:
        if not inspect.isclass(cls):
            raise TypeError(
                f"@component can only be used on classes, got {type(cls).__name__}"
            )
        cls._is_component = True  # type: ignore[attr-defined]
        cls._bean_name = name  # type: ignore[attr-defined]
        return cls

    if _target is not None:
        # @component without parentheses
        return decorator(_target)
    else:
        # @component() or @component(name="custom")
        return decorator


def post_construct(func: Callable[[Any], None]) -> Callable[[Any], None]:
    """
    Decorator to mark a method to be called after the bean has been
    constructed.

    The method should only accept self as a parameter and should not return any value.

    Args:
        func: The method to mark

    Returns:
        The original method with _is_post_construct attribute set.
    """
    func._is_post_construct = True  # type: ignore[attr-defined]
    return func
