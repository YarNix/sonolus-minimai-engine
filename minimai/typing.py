from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from sonolus.script.internal.constant import ConstantValue
from sonolus.script.internal.meta_fn import meta_fn
from sonolus.script.internal.visitor import compile_and_call

MAX_ARITY = 4


def override_archetype(override_match: Callable[[Any], bool] | None = None):
    """Decorate a method or property that overrides one in a parent archetype.

    ``override_match(self) -> bool`` tells whether ``self`` (typed as the parent) is an entity
    of the child archetype; defaults to ``ChildArchetype.is_at(self.index)``. Pass a named
    function: sonolus.py resolves a lambda on a decorator line to the decorated function.
    """

    def decorator(member):
        return _PendingOverride(member, override_match)

    return decorator


class _PendingOverride:
    """Placeholder in the class body; resolved once the owning class exists."""

    def __init__(self, member, override_match):
        self.member = member
        self.override_match = override_match

    def __call__(self, *args, **kwargs):
        raise TypeError("@override_archetype must be placed above @property")

    def __set_name__(self, owner: type, name: str):
        setattr(owner, name, self.member)
        parent = next((cls for cls in owner.__mro__[1:] if name in cls.__dict__), None)
        if parent is None:
            raise TypeError(f"{owner.__name__}.{name} overrides nothing")
        parent_member = parent.__dict__[name]
        _check_signature(owner, name, parent_member, self.member)
        match = self.override_match or _default_match(owner)
        if isinstance(parent_member, property):
            dispatch = _make_dispatcher(owner, name, parent_member.fget, match, is_property=True)
            setattr(parent, name, property(dispatch))
        else:
            setattr(parent, name, _make_dispatcher(owner, name, parent_member, match, is_property=False))


def _fn_of(member) -> Callable:
    return member.fget if isinstance(member, property) else member


def _check_signature(owner: type, name: str, parent_member, child_member):
    if isinstance(parent_member, property) != isinstance(child_member, property):
        raise TypeError(f"{owner.__name__}.{name}: property / method mismatch with the parent")
    parent_fn = getattr(_fn_of(parent_member), "_override_original_", _fn_of(parent_member))
    parent_sig = inspect.signature(parent_fn)
    child_sig = inspect.signature(_fn_of(child_member))
    if parent_sig != child_sig:
        raise TypeError(f"{owner.__name__}.{name}{child_sig} doesn't match the parent's {parent_sig}")


def _default_match(child_cls: type) -> Callable[[Any], bool]:
    return lambda self: child_cls.is_at(self.index)


def _make_dispatcher(child_cls: type, name: str, original: Callable, match: Callable, *, is_property: bool):
    signature = inspect.signature(getattr(original, "_override_original_", original))
    runtime_cache: dict[int, Callable] = {}

    @meta_fn
    def dispatch(self, *args, **kwargs):
        if isinstance(self, ConstantValue):
            self = self._as_py_()
        bound = signature.bind(self, *args, **kwargs)
        bound.apply_defaults()
        positional = bound.args[1:]
        # Decided at compile time when the static type already settles it.
        if isinstance(self, child_cls) or not issubclass(child_cls, type(self)):
            return compile_and_call(original, self, *positional)
        arity = len(positional)
        if arity not in runtime_cache:
            child_member = getattr(child_cls, name)
            child_fn = child_member.fget if is_property else child_member
            runtime_cache[arity] = _make_runtime_dispatch(arity, child_cls, child_fn, original, match)
        return compile_and_call(runtime_cache[arity], self, *positional)

    dispatch._override_original_ = getattr(original, "_override_original_", original)
    return dispatch


def _make_runtime_dispatch(arity: int, child_cls: type, child_fn: Callable, original: Callable, match: Callable):
    # Fixed arities: compiled functions need real source.
    if arity == 0:

        def dispatch_0(self):
            if match(self):
                return child_fn(child_cls.at(self.index, check=False))
            return original(self)

        return dispatch_0
    if arity == 1:

        def dispatch_1(self, a):
            if match(self):
                return child_fn(child_cls.at(self.index, check=False), a)
            return original(self, a)

        return dispatch_1
    if arity == 2:

        def dispatch_2(self, a, b):
            if match(self):
                return child_fn(child_cls.at(self.index, check=False), a, b)
            return original(self, a, b)

        return dispatch_2
    if arity == 3:

        def dispatch_3(self, a, b, c):
            if match(self):
                return child_fn(child_cls.at(self.index, check=False), a, b, c)
            return original(self, a, b, c)

        return dispatch_3
    if arity == 4:

        def dispatch_4(self, a, b, c, d):
            if match(self):
                return child_fn(child_cls.at(self.index, check=False), a, b, c, d)
            return original(self, a, b, c, d)

        return dispatch_4
    raise TypeError(f"override_archetype supports at most {MAX_ARITY} arguments")
