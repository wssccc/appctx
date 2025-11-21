import inspect
from collections import defaultdict
from typing import Any, Dict, List, Type, TypeVar, Optional, overload, Union

T = TypeVar("T")


class ApplicationContext:
    """Spring-style dependency injection container."""

    def __init__(self) -> None:
        self.bean_defs: List[Any] = []
        self.bean_names_map: Dict[str, Any] = {}
        self.bean_types_map: Dict[Type, List[Any]] = defaultdict(list)

    @overload
    def get_bean(self, k: str) -> Any: ...

    @overload
    def get_bean(self, k: Type[T]) -> T: ...

    def get_bean(self, k: Union[str, Type[T]]) -> Union[Any, T]:
        """Get a bean by name or type."""
        if isinstance(k, str):
            return self.bean_names_map[k]
        elif isinstance(k, type):
            beans = self.bean_types_map[k]
            if not beans:
                raise KeyError(f"No bean of type {k} found")
            return beans[0]
        else:
            raise NotImplementedError(f"Cannot get bean for key type: {type(k)}")

    def get_beans(self, _type: Type[T]) -> List[T]:
        """Get all beans of a specific type."""
        return self.bean_types_map[_type]

    def _instantiate(self, bean_def: Any) -> Optional[Any]:
        """Instantiate a bean definition."""
        is_class = inspect.isclass(bean_def)
        if is_class:
            spec = inspect.getfullargspec(bean_def.__init__)
            spec.args.pop(0)  # Remove 'self'
        else:
            spec = inspect.getfullargspec(bean_def)

        deps = self._resolve_dependencies(spec)
        if deps is not None:
            args, kwargs = deps
            obj = bean_def(*args, **kwargs)
            # Register bean by name for both function and class beans
            self.bean_names_map[bean_def.__name__] = obj
            self.bean_types_map[type(obj)].append(obj)

            # Call post_construct methods if they exist
            self._call_post_construct(obj)

            return obj
        return None

    def _call_post_construct(self, obj: Any) -> None:
        """Call post_construct methods on the object if they exist."""
        # Get all attributes of the object
        for name in dir(obj):
            # Skip private attributes
            if name.startswith("_"):
                continue

            attr = getattr(obj, name)
            # Check if it's callable and has the _is_post_construct attribute
            if callable(attr) and hasattr(attr, "_is_post_construct"):
                # Call the method
                attr()

    def _resolve_dependencies(
        self, spec: inspect.FullArgSpec
    ) -> Optional[tuple[List[Any], Dict[str, Any]]]:
        """Convert function signature to arguments and keyword arguments.

        Resolution strategy:
        - Positional args: resolved by type annotations only
        - Keyword-only args: resolved by name first, then use defaults
        - **kwargs: all remaining beans not already used
        """
        args = []
        kwargs = {}

        # Resolve positional arguments by type annotations
        for arg_name in spec.args:
            if arg_name not in spec.annotations:
                # Positional args without type annotation cannot be resolved
                return None

            arg_type = spec.annotations[arg_name]
            typed_beans = self.bean_types_map[arg_type]

            if not typed_beans:
                # No beans of required type available
                return None

            if len(typed_beans) > 1:
                raise RuntimeError(
                    f"Multiple beans of type {arg_type} for arg '{arg_name}'"
                )

            args.append(typed_beans[0])

        # Resolve keyword-only arguments by name
        if spec.kwonlyargs:
            for arg_name in spec.kwonlyargs:
                # Check for default value first
                if spec.kwonlydefaults and arg_name in spec.kwonlydefaults:
                    kwargs[arg_name] = spec.kwonlydefaults[arg_name]
                # Then try to resolve by bean name
                elif arg_name in self.bean_names_map:
                    kwargs[arg_name] = self.bean_names_map[arg_name]
                else:
                    # Cannot resolve this keyword-only argument
                    return None

        # Handle **kwargs parameter - inject all remaining beans
        if spec.varkw:
            # Track all parameter names to avoid duplicates
            used_param_names = set(spec.args + (spec.kwonlyargs or []))

            # Add all beans that haven't been used as parameters
            for bean_name, bean_instance in self.bean_names_map.items():
                if bean_name not in used_param_names:
                    kwargs[bean_name] = bean_instance

        return args, kwargs

    def bean(self, target: T) -> T:
        """Decorator to register a bean."""
        self.bean_defs.append(target)
        return target

    def add(self, target: Any) -> "ApplicationContext":
        """Add a bean definition."""
        if inspect.ismodule(target):
            return self
        self.bean_defs.append(target)
        return self

    def _refresh(self) -> bool:
        """Refresh a single iteration."""
        for i in range(len(self.bean_defs)):
            b = self.bean_defs[i]
            if self._instantiate(b):
                self.bean_defs.pop(i)
                return True
        return False

    def refresh(self) -> None:
        """Initialize the container and instantiate all beans."""
        while self._refresh():
            pass
        if self.bean_defs:
            bean_names = ", ".join(f"{d.__name__}: {d}" for d in self.bean_defs)
            raise RuntimeError(f"Could not instantiate bean defs {bean_names}")
