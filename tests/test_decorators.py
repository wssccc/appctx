"""Tests for the decorators module."""

import pytest

from appctx.decorators import bean, component, post_construct


def test_bean_marker_attribute():
    """Test that @bean sets _is_bean attribute."""

    @bean
    def my_func():
        return "result"

    assert hasattr(my_func, "_is_bean")
    assert my_func._is_bean is True


def test_bean_default_name():
    """Test that @bean without name sets _bean_name to None."""

    @bean
    def my_func():
        return "result"

    assert hasattr(my_func, "_bean_name")
    assert my_func._bean_name is None


def test_bean_custom_name():
    """Test that @bean(name=...) sets _bean_name to the custom name."""

    @bean(name="custom_name")
    def my_func():
        return "result"

    assert hasattr(my_func, "_bean_name")
    assert my_func._bean_name == "custom_name"


def test_bean_on_class_raises_type_error():
    """Test that @bean on a class raises TypeError."""
    with pytest.raises(TypeError, match="@bean can only be used on functions"):

        @bean
        class MyClass:
            pass


def test_bean_with_name_on_class_raises_type_error():
    """Test that @bean(name=...) on a class raises TypeError."""
    with pytest.raises(TypeError, match="@bean can only be used on functions"):

        @bean(name="custom")
        class MyClass:
            pass


def test_bean_returns_original_function():
    """Test that @bean returns the original function unchanged (except attributes)."""

    def my_func():
        return "result"

    original = my_func
    decorated = bean(my_func)

    assert decorated is original
    assert decorated.__name__ == "my_func"
    assert decorated() == "result"


def test_bean_empty_parentheses():
    """Test that @bean() (empty parentheses) works like @bean."""

    @bean()
    def my_func():
        return "result"

    assert my_func._is_bean is True
    assert my_func._bean_name is None
    assert my_func() == "result"


def test_component_marker_attribute():
    """Test that @component sets _is_component attribute."""

    @component
    class MyClass:
        pass

    assert hasattr(MyClass, "_is_component")
    assert MyClass._is_component is True


def test_component_default_name():
    """Test that @component without name sets _bean_name to None."""

    @component
    class MyClass:
        pass

    assert hasattr(MyClass, "_bean_name")
    assert MyClass._bean_name is None


def test_component_custom_name():
    """Test that @component(name=...) sets _bean_name to the custom name."""

    @component(name="custom_name")
    class MyClass:
        pass

    assert hasattr(MyClass, "_bean_name")
    assert MyClass._bean_name == "custom_name"


def test_component_on_function_raises_type_error():
    """Test that @component on a function raises TypeError."""
    with pytest.raises(TypeError, match="@component can only be used on classes"):

        @component
        def my_func():
            pass


def test_component_with_name_on_function_raises_type_error():
    """Test that @component(name=...) on a function raises TypeError."""
    with pytest.raises(TypeError, match="@component can only be used on classes"):

        @component(name="custom")
        def my_func():
            pass


def test_component_returns_original_class():
    """Test that @component returns the original class unchanged (except attributes)."""

    class MyClass:
        pass

    original = MyClass
    decorated = component(MyClass)

    assert decorated is original
    assert decorated.__name__ == "MyClass"


def test_component_empty_parentheses():
    """Test that @component() (empty parentheses) works like @component."""

    @component()
    class MyClass:
        pass

    assert MyClass._is_component is True
    assert MyClass._bean_name is None


def test_post_construct_marker_attribute():
    """Test that @post_construct sets _is_post_construct attribute."""

    @post_construct
    def my_method(self):
        pass

    assert hasattr(my_method, "_is_post_construct")
    assert my_method._is_post_construct is True


def test_post_construct_returns_original_function():
    """Test that @post_construct returns original function."""

    def my_method(self):
        pass

    original = my_method
    decorated = post_construct(my_method)

    assert decorated is original
    assert decorated.__name__ == "my_method"


def test_bean_empty_name_raises_value_error():
    """Test that @bean(name="") raises ValueError."""
    with pytest.raises(ValueError, match="@bean name cannot be an empty string"):

        @bean(name="")
        def my_func():
            pass


def test_component_empty_name_raises_value_error():
    """Test that @component(name="") raises ValueError."""
    with pytest.raises(ValueError, match="@component name cannot be an empty string"):

        @component(name="")
        class MyClass:
            pass
