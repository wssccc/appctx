import fnmatch
import importlib
import inspect
import pkgutil
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union, overload

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

    def scan(
        self,
        package_name: Optional[str] = None,
        exclude: Optional[List[str]] = None,
    ) -> "ApplicationContext":
        """Scan a package for annotated beans and components.

        Recursively imports modules within the specified package and
        registers any objects marked with @bean or @component.

        Args:
            package_name: Package or module name to scan. If None,
                auto-detects the caller's package.
            exclude: List of module/package name patterns to exclude.
                Supports fnmatch glob patterns (e.g., "my_pkg.test_*").

        Returns:
            self for method chaining (e.g., ctx.scan("pkg").refresh()).

        Raises:
            ValueError: If package_name cannot be determined for auto-scanning.
        """
        if package_name is None:
            caller_frame = inspect.currentframe()
            if caller_frame is None:
                raise ValueError(
                    "Cannot determine caller's frame for auto-scanning. "
                    "Please specify a package name explicitly."
                )
            caller_frame = caller_frame.f_back
            caller_module = inspect.getmodule(caller_frame)
            if caller_module is None:
                raise ValueError("Cannot determine caller's module for auto-scanning")
            package_name = caller_module.__package__
            if package_name is None:
                if caller_module.__name__ == "__main__":
                    raise ValueError(
                        "Auto-scanning from __main__ is not supported. "
                        "Please specify a package name explicitly."
                    )
                package_name = caller_module.__name__

        module = importlib.import_module(package_name)

        # Scan the root module/package itself
        if exclude and self._should_exclude(module.__name__, exclude):
            return self
        self._scan_module(module)

        # If it's a package, recursively scan sub-modules
        if hasattr(module, "__path__"):
            for _importer, modname, _ispkg in pkgutil.walk_packages(
                module.__path__, module.__name__ + "."
            ):
                if exclude and self._should_exclude(modname, exclude):
                    continue
                sub_module = importlib.import_module(modname)
                self._scan_module(sub_module)

        return self

    def _should_exclude(self, module_name: str, exclude: List[str]) -> bool:
        """Check if a module name matches any exclude pattern.

        Supports fnmatch glob patterns and prefix matching for packages.
        """
        for pattern in exclude:
            if fnmatch.fnmatch(module_name, pattern):
                return True
            # Prefix match: exclude entire package tree
            if module_name.startswith(pattern + "."):
                return True
        return False

    def _scan_module(self, module: Any) -> None:
        """Scan a module for annotated beans and components.

        Only registers objects defined in this module (not imported
        from elsewhere) to avoid duplicate registration.
        """
        for name in dir(module):
            if name.startswith("_"):
                continue
            obj = getattr(module, name)
            # Only register objects defined in this module
            if hasattr(obj, "__module__") and obj.__module__ != module.__name__:
                continue
            if hasattr(obj, "_is_bean") or hasattr(obj, "_is_component"):
                if obj not in self.bean_defs:
                    self.bean_defs.append(obj)

    def _instantiate(self, bean_def: Any) -> bool:
        """Instantiate a bean definition.

        Returns True on success, False if dependencies are not ready.
        """
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

            # Use custom bean name if specified, otherwise use __name__
            bean_name = getattr(bean_def, "_bean_name", None) or bean_def.__name__
            self.bean_names_map[bean_name] = obj
            self.bean_types_map[type(obj)].append(obj)

            return True
        return False

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

    def _call_post_construct_on_all_beans(self) -> None:
        """Call post_construct on all registered beans after all beans are created."""
        for bean_name, obj in list(self.bean_names_map.items()):
            try:
                self._call_post_construct(obj)
            except Exception:
                # Remove the bean from container if post_construct fails
                obj_type = type(obj)
                self.bean_names_map.pop(bean_name, None)
                if obj_type in self.bean_types_map:
                    self.bean_types_map[obj_type] = [
                        b for b in self.bean_types_map[obj_type] if b is not obj
                    ]
                    if not self.bean_types_map[obj_type]:
                        del self.bean_types_map[obj_type]
                raise

    def _resolve_dependencies(
        self, spec: inspect.FullArgSpec
    ) -> Optional[Tuple[List[Any], Dict[str, Any]]]:
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

        # Resolve keyword-only arguments by name first, then fall back to defaults
        if spec.kwonlyargs:
            for arg_name in spec.kwonlyargs:
                # Try to resolve by bean name first
                if arg_name in self.bean_names_map:
                    kwargs[arg_name] = self.bean_names_map[arg_name]
                # Fall back to default value
                elif spec.kwonlydefaults and arg_name in spec.kwonlydefaults:
                    kwargs[arg_name] = spec.kwonlydefaults[arg_name]
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

    def add(self, target: Any) -> "ApplicationContext":
        """Add a bean definition manually."""
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

        # Call post_construct methods after all beans are instantiated
        # Following Spring's PostConstruct behavior
        self._call_post_construct_on_all_beans()
