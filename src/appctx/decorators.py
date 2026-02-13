from typing import Any, Callable


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
