import fnmatch
import importlib
import inspect
import pkgutil
import types
import typing
from collections import defaultdict
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

T = TypeVar("T")

_EMPTY_SPEC = inspect.FullArgSpec(
    args=[],
    varargs=None,
    varkw=None,
    defaults=None,
    kwonlyargs=[],
    kwonlydefaults=None,
    annotations={},
)

_Resolution = Tuple[List[Any], Dict[str, Any]]

_Signature = Tuple[inspect.FullArgSpec, Dict[str, Any], Optional[type]]


class BeanResolutionError(RuntimeError):
    """Raised when one or more bean definitions cannot be instantiated."""


def _kind_name(obj: Any) -> str:
    """Return a readable type name for an arbitrary object."""
    name = getattr(obj, "__name__", None)
    if isinstance(name, str):
        return name
    return type(obj).__name__


def _bean_display_name(bean_def: Any) -> str:
    """Return the name used for a bean definition in error messages."""
    name = getattr(bean_def, "_bean_name", None)
    if isinstance(name, str) and name:
        return name
    return _kind_name(bean_def)


def _display_type(value: Any) -> str:
    """Return a readable name for a type annotation."""
    name = getattr(value, "__name__", None)
    return name if isinstance(name, str) else str(value)


def _dedupe_by_identity(beans: Iterable[Any]) -> List[Any]:
    """Deduplicate beans by object identity while preserving order."""
    seen = set()
    result: List[Any] = []
    for bean in beans:
        key = id(bean)
        if key in seen:
            continue
        seen.add(key)
        result.append(bean)
    return result


def _can_use_mro(wanted: Any) -> bool:
    """Whether a type is eligible for assignability-based matching."""
    return wanted is not object and isinstance(wanted, type)


def _safe_issubclass(candidate: Any, wanted: Any) -> bool:
    """Check assignability, skipping non-class and non-runtime-checkable types."""
    if not _can_use_mro(wanted) or not isinstance(candidate, type):
        return False
    try:
        return issubclass(candidate, wanted)
    except TypeError:
        return False


class ApplicationContext:
    """Spring-style dependency injection container."""

    def __init__(self) -> None:
        self.bean_defs: List[Any] = []
        self.bean_names_map: Dict[str, Any] = {}
        self.bean_types_map: Dict[Type, List[Any]] = defaultdict(list)
        # Memoized _extract_signature() results, cleared on every refresh.
        self._signature_cache: Dict[Any, _Signature] = {}

    @overload
    def get_bean(self, k: str) -> Any: ...

    @overload
    def get_bean(self, k: Type[T]) -> T: ...

    def get_bean(self, k: Union[str, Type[T]]) -> Union[Any, T]:
        """Get a bean by name or type.

        Type lookups prefer an exact registered type. If none exists, a
        unique bean assignable to the requested type is returned. Multiple
        candidates raise RuntimeError; no candidates raise KeyError.
        """
        if isinstance(k, str):
            return self.bean_names_map[k]
        if not isinstance(k, type):
            raise NotImplementedError(f"Cannot get bean for key type: {type(k)}")

        exact = self._exact_beans(k)
        if exact:
            if len(exact) > 1:
                raise RuntimeError(self._multiple_beans_message(k, exact))
            return exact[0]

        assignable = self._assignable_beans(k)
        if not assignable:
            raise KeyError(f"No bean of type {k} found")
        if len(assignable) > 1:
            raise RuntimeError(self._multiple_beans_message(k, assignable))
        return assignable[0]

    def get_beans(self, _type: Type[T]) -> List[T]:
        """Get all beans of a specific type.

        Includes beans assignable to the requested type, with exact matches
        first. Results are deduplicated by object identity.
        """
        beans = self._exact_beans(_type)
        beans.extend(self._assignable_beans(_type))
        return cast(List[T], _dedupe_by_identity(beans))

    def _exact_beans(self, wanted: Any) -> List[Any]:
        try:
            return list(self.bean_types_map.get(wanted, []))
        except TypeError:
            return []

    def _assignable_beans(self, wanted: Any) -> List[Any]:
        if not _can_use_mro(wanted):
            return []
        matches: List[Any] = []
        for candidate_type, beans in list(self.bean_types_map.items()):
            if _safe_issubclass(candidate_type, wanted):
                matches.extend(beans)
        return _dedupe_by_identity(matches)

    def _multiple_beans_message(self, wanted: Any, beans: List[Any]) -> str:
        type_name = _display_type(wanted)
        candidates = ", ".join(self._bean_label(bean) for bean in beans)
        return (
            f"Multiple beans match type {type_name}: {candidates}; "
            f"use get_beans({type_name}) or get_bean('name')"
        )

    def _bean_label(self, bean: Any) -> str:
        for name, candidate in self.bean_names_map.items():
            if candidate is bean:
                return f"{name} ({type(bean).__name__})"
        return type(bean).__name__

    def scan(
        self,
        package_name: Optional[str] = None,
        exclude: Optional[List[str]] = None,
        include: Optional[List[str]] = None,
    ) -> "ApplicationContext":
        """Scan a package for annotated beans and components.

        Recursively imports modules within the specified package and
        registers any objects marked with @bean or @component.

        Args:
            package_name: Package or module name to scan. If None,
                auto-detects the caller's package.
            exclude: List of module/package name patterns to exclude.
                Supports fnmatch glob patterns (e.g., "my_pkg.test_*").
            include: List of module/package name patterns to include.
                When provided and non-empty, only matching modules are
                scanned. Uses the same fnmatch glob and package-prefix
                matching as ``exclude``. When both are provided, a module
                must match ``include`` and must not match ``exclude``.

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

        # Preserve the 0.5 behaviour: excluding the root package stops the scan.
        if exclude and self._matches_any(module.__name__, exclude):
            return self
        if self._should_scan(module.__name__, exclude, include):
            self._scan_module(module)

        # If it's a package, recursively scan sub-modules
        if hasattr(module, "__path__"):
            for _importer, modname, _ispkg in pkgutil.walk_packages(
                module.__path__, module.__name__ + "."
            ):
                if not self._should_scan(modname, exclude, include):
                    continue
                sub_module = importlib.import_module(modname)
                self._scan_module(sub_module)

        return self

    def _matches_any(self, module_name: str, patterns: List[str]) -> bool:
        """Check whether a module matches any glob or package-prefix pattern.

        Matching is case-sensitive on every platform because module names are.
        """
        for pattern in patterns:
            if fnmatch.fnmatchcase(module_name, pattern):
                return True
            # Prefix match: include/exclude an entire package tree
            if module_name.startswith(pattern + "."):
                return True
        return False

    def _should_scan(
        self,
        module_name: str,
        exclude: Optional[List[str]],
        include: Optional[List[str]],
    ) -> bool:
        """Apply include/exclude filters to a module name."""
        if exclude and self._matches_any(module_name, exclude):
            return False
        if include and not self._matches_any(module_name, include):
            return False
        return True

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

    def _get_type_hints(self, target: Any) -> Optional[Dict[str, Any]]:
        """Resolve type hints, returning None when annotations are not evaluable."""
        try:
            return dict(typing.get_type_hints(target))
        except Exception:
            return None

    def _eval_annotation(self, raw: str, globalns: Dict[str, Any]) -> Any:
        """Evaluate one string annotation, returning the raw string on failure."""
        holder = types.SimpleNamespace(__annotations__={"value": raw})
        try:
            return typing.get_type_hints(holder, globalns=globalns)["value"]
        except Exception:
            return raw

    def _resolve_annotations(
        self, target: Any, spec: inspect.FullArgSpec
    ) -> Dict[str, Any]:
        """Return the annotations of ``target`` with strings resolved.

        When ``typing.get_type_hints`` cannot evaluate the signature as a
        whole, each string annotation is evaluated on its own so that one
        unresolvable name does not turn every other annotation into a string.
        Annotations that still cannot be evaluated are left as strings.
        """
        hints = self._get_type_hints(target)
        if hints is not None:
            return hints
        globalns = getattr(target, "__globals__", {})
        return {
            name: self._eval_annotation(raw, globalns) if isinstance(raw, str) else raw
            for name, raw in spec.annotations.items()
        }

    def _annotations_without_return(
        self, annotations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Drop the ``return`` key from a resolved annotation map."""
        return {
            name: annotation
            for name, annotation in annotations.items()
            if name != "return"
        }

    def _cached_signature(self, bean_def: Any) -> _Signature:
        """Memoize :meth:`_extract_signature` for the current refresh."""
        try:
            cached = self._signature_cache.get(bean_def)
        except TypeError:
            return self._extract_signature(bean_def)
        if cached is None:
            cached = self._extract_signature(bean_def)
            self._signature_cache[bean_def] = cached
        return cached

    def _extract_signature(self, bean_def: Any) -> _Signature:
        """Extract the call signature and resolved parameter annotations.

        For classes, annotations come from ``__init__`` (PEP 563 compatible).
        For functions, the declared return type is returned when it is a class.
        """
        if inspect.isclass(bean_def):
            init = bean_def.__init__
            if init is object.__init__:
                # No custom constructor: treat as a zero-argument component.
                return _EMPTY_SPEC, {}, None

            spec = inspect.getfullargspec(init)
            args = list(spec.args)
            if args:
                args.pop(0)  # Remove the instance parameter by position
            spec = spec._replace(args=args)
            annotations = self._resolve_annotations(init, spec)
            return spec, self._annotations_without_return(annotations), None

        spec = inspect.getfullargspec(bean_def)
        hints = self._resolve_annotations(bean_def, spec)
        annotations = self._annotations_without_return(hints)
        return_type: Optional[type] = None
        candidate = hints.get("return")
        if inspect.isclass(candidate):
            return_type = candidate
        return spec, annotations, return_type

    def _resolve_dependencies(
        self,
        spec: inspect.FullArgSpec,
        annotations: Dict[str, Any],
    ) -> Tuple[Optional[_Resolution], Optional[str]]:
        """Convert a signature into arguments and keyword arguments.

        Returns ``((args, kwargs), None)`` on success and ``(None, reason)``
        when a dependency cannot be resolved.

        Resolution strategy:
        - Positional args: exact type first, then unique assignable type
        - Keyword-only args: resolved by name first, then use defaults
        - **kwargs: all remaining beans not already used
        """
        args: List[Any] = []
        kwargs: Dict[str, Any] = {}

        for arg_name in spec.args:
            if arg_name not in annotations:
                return None, f"argument '{arg_name}' has no type annotation"

            arg_type = annotations[arg_name]
            if isinstance(arg_type, str):
                return (
                    None,
                    f"argument '{arg_name}' has an annotation that could not be "
                    f"evaluated at runtime: '{arg_type}' (a name that is not "
                    f"importable when the container refreshes, such as a "
                    f"function-local class or a TYPE_CHECKING-only import)",
                )
            candidates = self._exact_beans(arg_type)
            if not candidates:
                candidates = self._assignable_beans(arg_type)

            if not candidates:
                return (
                    None,
                    f"argument '{arg_name}' needs a bean of type "
                    f"{_display_type(arg_type)} (none found)",
                )
            if len(candidates) > 1:
                labels = ", ".join(self._bean_label(bean) for bean in candidates)
                return (
                    None,
                    f"argument '{arg_name}' has {len(candidates)} candidates "
                    f"({labels})",
                )
            args.append(candidates[0])

        for arg_name in spec.kwonlyargs:
            if arg_name in self.bean_names_map:
                kwargs[arg_name] = self.bean_names_map[arg_name]
            elif spec.kwonlydefaults and arg_name in spec.kwonlydefaults:
                kwargs[arg_name] = spec.kwonlydefaults[arg_name]
            else:
                return (
                    None,
                    f"keyword-only argument '{arg_name}' cannot be resolved "
                    f"(no bean named '{arg_name}' and no default)",
                )

        if spec.varkw:
            used_param_names = set(spec.args + spec.kwonlyargs)
            for bean_name, bean_instance in self.bean_names_map.items():
                if bean_name not in used_param_names:
                    kwargs[bean_name] = bean_instance

        return (args, kwargs), None

    def _instantiate(self, bean_def: Any) -> bool:
        """Instantiate a bean definition.

        Returns True on success, False if dependencies are not ready.
        """
        try:
            spec, annotations, return_type = self._cached_signature(bean_def)
            deps, _reason = self._resolve_dependencies(spec, annotations)
        except Exception:
            # Signature inspection failures are reported by _describe_failure().
            return False

        if deps is None:
            return False

        args, kwargs = deps
        obj = bean_def(*args, **kwargs)

        bean_name = _bean_display_name(bean_def)
        type_keys: List[type] = [type(obj)]
        if return_type is not None and return_type is not type(obj):
            self._check_declared_type(bean_name, obj, return_type)
            type_keys.append(return_type)
        self.bean_names_map[bean_name] = obj
        self._register_bean(obj, type_keys)

        return True

    def _check_declared_type(self, bean_name: str, obj: Any, declared: type) -> None:
        """Verify that a factory result matches its declared return type."""
        try:
            satisfied = issubclass(type(obj), declared)
        except TypeError:
            # Non-runtime-checkable protocols cannot be verified; trust them.
            return
        if not satisfied:
            raise TypeError(
                f"Bean '{bean_name}' is declared to return "
                f"{_display_type(declared)} but produced "
                f"{_display_type(type(obj))}"
            )

    def _register_bean(self, obj: Any, type_keys: Iterable[type]) -> None:
        """Register a bean instance under each of its type keys."""
        for type_key in type_keys:
            beans = self.bean_types_map[type_key]
            if not any(existing is obj for existing in beans):
                beans.append(obj)

    def _unregister(self, bean_name: str, obj: Any) -> None:
        """Remove a bean from the name and all type maps."""
        self.bean_names_map.pop(bean_name, None)
        for type_key, beans in list(self.bean_types_map.items()):
            remaining = [bean for bean in beans if bean is not obj]
            if len(remaining) == len(beans):
                continue
            if remaining:
                self.bean_types_map[type_key] = remaining
            else:
                del self.bean_types_map[type_key]

    def _describe_failure(self, bean_def: Any) -> str:
        """Return an actionable reason why a bean definition cannot be built."""
        try:
            spec, annotations, _return_type = self._cached_signature(bean_def)
            deps, reason = self._resolve_dependencies(spec, annotations)
        except Exception as exc:
            return f"could not inspect signature: {exc}"
        if deps is not None:
            return "dependencies were satisfied but instantiation failed"
        return reason or "unknown resolution failure"

    def _instantiate_all(self) -> None:
        """Instantiate all possible beans and raise an aggregated error."""
        self._signature_cache.clear()
        while self._refresh():
            pass
        if not self.bean_defs:
            return

        providers = self._providers(self.bean_defs)
        details = []
        for bean_def in self.bean_defs:
            reason = self._describe_failure(bean_def)
            hint = self._circular_hint(bean_def, providers)
            details.append(f"- {_bean_display_name(bean_def)}: {reason}{hint}")
        message = (
            f"Could not instantiate {len(self.bean_defs)} bean def(s):\n"
            + "\n".join(details)
        )
        raise BeanResolutionError(message)

    def _providers(self, bean_defs: List[Any]) -> Dict[Any, List[str]]:
        """Map each type produced by unresolved definitions to its bean names."""
        providers: Dict[Any, List[str]] = {}
        for bean_def in bean_defs:
            try:
                _spec, _annotations, return_type = self._cached_signature(bean_def)
            except Exception:
                continue
            if inspect.isclass(bean_def):
                produced = [bean_def]
            else:
                produced = [return_type] if return_type is not None else []
            for type_key in produced:
                names = providers.setdefault(type_key, [])
                names.append(_bean_display_name(bean_def))
        return providers

    def _missing_types(
        self, spec: inspect.FullArgSpec, annotations: Dict[str, Any]
    ) -> List[Any]:
        """Return annotated positional types that currently have no bean."""
        missing: List[Any] = []
        for arg_name in spec.args:
            arg_type = annotations.get(arg_name)
            if not isinstance(arg_type, type):
                continue
            if not self._exact_beans(arg_type) and not self._assignable_beans(arg_type):
                missing.append(arg_type)
        return missing

    def _circular_hint(self, bean_def: Any, providers: Dict[Any, List[str]]) -> str:
        """Suggest a circular dependency when a missing type is still pending."""
        try:
            spec, annotations, _return_type = self._cached_signature(bean_def)
        except Exception:
            return ""
        for missing in self._missing_types(spec, annotations):
            pending = providers.get(missing, [])
            if pending:
                return (
                    f" (possible circular dependency: "
                    f"{_display_type(missing)} is provided by the unresolved "
                    f"bean '{pending[0]}')"
                )
        return ""

    def _iter_post_construct_methods(self, obj: Any) -> Iterator[Tuple[str, Any]]:
        """Yield public @post_construct methods of an object."""
        for name in dir(obj):
            if name.startswith("_"):
                continue
            attr = getattr(obj, name)
            if callable(attr) and hasattr(attr, "_is_post_construct"):
                yield name, attr

    def _find_async_post_constructs(self) -> List[str]:
        """Return ``bean.method`` labels for async post_construct hooks."""
        found: List[str] = []
        for bean_name, obj in self.bean_names_map.items():
            for method_name, attr in self._iter_post_construct_methods(obj):
                if inspect.iscoroutinefunction(attr):
                    found.append(f"{bean_name}.{method_name}")
        return found

    def _call_post_construct_sync(self, obj: Any) -> None:
        for _name, attr in self._iter_post_construct_methods(obj):
            attr()

    async def _call_post_construct_async(self, obj: Any) -> None:
        for _name, attr in self._iter_post_construct_methods(obj):
            if inspect.iscoroutinefunction(attr):
                await attr()
            else:
                attr()

    def _call_post_construct_sync_all(self) -> None:
        """Call synchronous post_construct hooks on all registered beans."""
        for bean_name, obj in list(self.bean_names_map.items()):
            try:
                self._call_post_construct_sync(obj)
            except Exception:
                self._unregister(bean_name, obj)
                raise

    async def _call_post_construct_async_all(self) -> None:
        """Call sync and async post_construct hooks in registration order."""
        for bean_name, obj in list(self.bean_names_map.items()):
            try:
                await self._call_post_construct_async(obj)
            except Exception:
                self._unregister(bean_name, obj)
                raise

    def add(self, target: Any) -> "ApplicationContext":
        """Add a class or function bean definition manually.

        Modules are ignored for backward compatibility. Pre-built instances
        are not supported and raise TypeError.
        """
        if inspect.ismodule(target):
            return self
        if inspect.isclass(target) or inspect.isroutine(target):
            self.bean_defs.append(target)
            return self
        raise TypeError(
            "add() accepts a class or function bean definition, "
            f"got instance of {type(target).__name__}; "
            "register a @bean factory function instead."
        )

    def _refresh(self) -> bool:
        """Refresh a single iteration."""
        for i in range(len(self.bean_defs)):
            b = self.bean_defs[i]
            if self._instantiate(b):
                self.bean_defs.pop(i)
                return True
        return False

    def refresh(self) -> None:
        """Initialize the container and instantiate all beans.

        Raises:
            BeanResolutionError: If one or more bean definitions cannot be
                instantiated.
            RuntimeError: If an async @post_construct hook is present. Use
                ``await refresh_async()`` instead.
        """
        self._instantiate_all()

        async_hooks = self._find_async_post_constructs()
        if async_hooks:
            raise RuntimeError(
                "refresh() only supports synchronous @post_construct hooks; "
                f"async hooks found: {', '.join(async_hooks)}; "
                "use 'await ctx.refresh_async()' instead."
            )

        self._call_post_construct_sync_all()

    async def refresh_async(self) -> None:
        """Initialize the container and run sync and async lifecycle hooks.

        This is the async counterpart of :meth:`refresh`. It executes
        synchronous and asynchronous ``@post_construct`` hooks in the same
        order that ``refresh()`` uses for synchronous hooks.
        """
        self._instantiate_all()
        await self._call_post_construct_async_all()
