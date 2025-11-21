import inspect
from collections import defaultdict
from functools import singledispatchmethod
from typing import Any, Callable, Dict, List, Type, TypeVar, Optional, overload

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

    @singledispatchmethod
    def get_bean(self, k: Any) -> Any:
        """Get a bean by name or type."""
        raise NotImplementedError(f"Cannot get bean for key type: {type(k)}")

    @get_bean.register
    def _(self, k: str) -> Any:
        """Get a bean by name."""
        return self.bean_names_map[k]

    @get_bean.register
    def _(self, k: type) -> Any:
        """Get a bean by type."""
        beans = self.bean_types_map[k]
        if not beans:
            raise KeyError(f"No bean of type {k} found")
        return beans[0]

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

        args = self._to_args(spec)
        if args is not None:
            obj = bean_def(*args)
            if not is_class:
                self.bean_names_map[bean_def.__name__] = obj
            self.bean_types_map[type(obj)].append(obj)
            return obj
        return None

    def _to_args(self, spec: inspect.FullArgSpec) -> Optional[List[Any]]:
        """Convert function signature to arguments."""
        args = []
        for a in spec.args:
            if a in spec.annotations:
                typed_beans = self.bean_types_map[spec.annotations[a]]
                if len(typed_beans) > 1:
                    raise RuntimeError(
                        f"Found multiple beans of type {spec.annotations[a]}"
                    )
                elif not typed_beans:
                    return None
                args.append(typed_beans[0])
            else:
                if a not in self.bean_names_map:
                    return None
                args.append(self.bean_names_map[a])
        return args

    def bean(self, target: Callable) -> Callable:
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
