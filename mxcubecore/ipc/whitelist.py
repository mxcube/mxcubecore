# encoding: utf-8
#
#  Project name: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Global whitelist of HardwareObject methods callable over IPC.

Design (see IPC_FORMAT.md and mxcubecore/ipc's design notes for the
rationale): this is a single, centrally-configured whitelist (a flat list of
"role.method" strings on the IPCServer HardwareObject's own config), not a
whitelist scattered across every object's own configuration -- so an
operator can see everything a beamline exposes over IPC in one place. The
last dot-separated segment is always the method name; everything before it
is a role *path* (see `resolve_role_path()`) -- "diffractometer.omega.foo"
resolves beamline's "diffractometer" role, then that object's own "omega"
sub-role, then calls "foo" on it, without "omega" needing to also be one of
beamline's own top-level roles.

Every whitelisted method's own parameters *are* the wire format - no
separate request/response wrapper method needed::

    def method(self, value: float, timeout: Optional[float] = None) -> float: ...

`params` in an `IPCRequest` is validated against a pydantic model built
from these parameters' own type hints and defaults (via
`pydantic.create_model()`), then the method is called with those validated
fields unpacked as keyword arguments - `method(**validated.model_dump())`,
never `method(validated)`. A method qualifies for the whitelist if either:

- every parameter (besides self) has a type hint pydantic can build a
  field from (no bare `*args`/`**kwargs`) - no decorator required; or
- it is decorated with `@ipc_method(request_model=...)`, explicitly
  supplying a model whose fields are unpacked into the call the same way -
  needed when the signature itself isn't annotated precisely enough (e.g.
  untyped parameters, or wanting stricter validation than the raw hints
  give).

The return value works the same way in reverse: if the method's return
type hint (or an explicit `@ipc_method(response_model=...)`) is a
pydantic.BaseModel subclass, the method must return an instance of it
(validated with `isinstance`, then `.model_dump(mode="json")`-ed for the
wire) - unchanged from before. Otherwise the bare return value (a float,
None, a dict, ...) is used directly as the JSON result, best-effort
(`mxcubecore.ipc.jsonable.to_jsonable`) - no wrapper class required just to
return a plain value.

Being eligible does not, by itself, expose a method: it must also be listed
in the IPCServer's `allowed_methods` configuration.
"""

import inspect
import typing
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
)

from pydantic import BaseModel, TypeAdapter, create_model

from mxcubecore.ipc.constants import logger
from mxcubecore.ipc.jsonable import to_jsonable


class IPCWhitelistError(Exception):
    """Raised for anything wrong with whitelist configuration or dispatch:
    an unresolvable role/method, a non-eligible method, or a call to a
    method that isn't (or is no longer) in the whitelist.
    """


def ipc_method(
    request_model: Optional[Type[BaseModel]] = None,
    response_model: Optional[Type[BaseModel]] = None,
) -> Callable[[Callable], Callable]:
    """Mark a HardwareObject method as IPC-eligible.

    Optional: only needed to supply an explicit request and/or response
    model when it can't be (precisely enough) inferred from the method's
    own signature - see module docstring. `request_model`'s fields are
    unpacked into the call as keyword arguments, exactly like an
    auto-built request model's are.
    """

    def decorator(func: Callable) -> Callable:
        func.__ipc_request_model__ = request_model
        func.__ipc_response_model__ = response_model
        return func

    return decorator


@dataclass(frozen=True)
class WhitelistEntry:
    """One resolved, validated whitelist entry, ready to dispatch calls to.

    response_model is None for a method whose return value isn't a
    pydantic.BaseModel - the bare return value is used as the JSON result
    directly (see dispatch()); response_type is then the raw type hint
    (possibly Any), used only to build a JSON schema for it in describe().
    """

    method_path: str
    role: str
    method_name: str
    request_model: Type[BaseModel]
    response_model: Optional[Type[BaseModel]]
    response_type: Any


def _pascal_case(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_")) or "Method"


def build_request_model(func: Callable) -> Optional[Type[BaseModel]]:
    """Auto-build a pydantic request model from func's own parameters
    (besides self): one field per parameter, named/typed/defaulted exactly
    like the parameter itself.

    Returns None if the signature isn't self-describing enough: it can't be
    introspected at all, has a bare `*args`/`**kwargs`, or any parameter
    (besides self) lacks a type hint.
    """
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return None
    try:
        hints = typing.get_type_hints(func)
    except (NameError, TypeError):
        return None

    fields: Dict[str, Any] = {}
    for name, param in signature.parameters.items():
        if name == "self":
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            return None
        if name not in hints:
            return None
        default = ... if param.default is param.empty else param.default
        fields[name] = (hints[name], default)

    return create_model(f"{_pascal_case(func.__name__)}Request", **fields)


def _response_info(func: Callable) -> Tuple[Optional[Type[BaseModel]], Any]:
    """(response_model, response_type) from func's own return type hint -
    response_model is that hint if it's a pydantic.BaseModel subclass,
    else None (see WhitelistEntry).
    """
    try:
        hints = typing.get_type_hints(func)
    except (NameError, TypeError):
        return None, Any

    return_type = hints.get("return", Any)
    if isinstance(return_type, type) and issubclass(return_type, BaseModel):
        return return_type, return_type
    return None, return_type


def get_role(beamline: Any, role: str) -> Any:
    """Resolve a single, direct role by name off of `beamline`.

    `beamline.get_object_by_role(role)` (from HardwareObjectNode) is tried
    first: it looks the role up in `_hwobj_by_role`, which is how *every*
    configured role is actually registered, regardless of whether `Beamline`
    also happens to declare it as a `@property` (only a fixed subset of
    roles, e.g. `procedure`/`diffractometer`, get that treatment - a plain
    `getattr(beamline, role)` would silently miss any role that isn't one of
    those, even though it loaded and is registered just fine).
    """
    get_by_role = getattr(beamline, "get_object_by_role", None)
    if callable(get_by_role):
        target = get_by_role(role)
        if target is not None:
            return target
    return getattr(beamline, role, None)


def resolve_role_path(beamline: Any, role_path: str) -> Any:
    """Resolve a role path - one or more dot-separated hops, each resolved
    with `get_role()` off of the previous one, starting from `beamline`.

    "diffractometer" resolves `beamline`'s own "diffractometer" role;
    "diffractometer.omega" resolves diffractometer's "omega" role (its
    `motors:` sub-object) without needing "omega" to *also* be registered
    as one of beamline's own top-level roles. Returns None if any hop along
    the path fails to resolve.
    """
    target = beamline
    for segment in role_path.split("."):
        target = get_role(target, segment)
        if target is None:
            return None
    return target


def _resolve_entry(beamline: Any, method_path: str) -> WhitelistEntry:
    """Resolve one "role.method" (or "role.sub_role.method") whitelist
    entry, or raise IPCWhitelistError.
    """
    try:
        role, method_name = method_path.rsplit(".", 1)
    except ValueError:
        raise IPCWhitelistError(
            f"Invalid whitelist entry {method_path!r}: expected 'role.method'"
        ) from None

    target = resolve_role_path(beamline, role)
    if target is None:
        raise IPCWhitelistError(
            f"Whitelist entry {method_path!r}: no such beamline role {role!r}"
        )

    func = getattr(target, method_name, None)
    if func is None or not callable(func):
        raise IPCWhitelistError(
            f"Whitelist entry {method_path!r}: {role!r} has no callable "
            f"method {method_name!r}"
        )

    request_model = getattr(func, "__ipc_request_model__", None)
    if request_model is None:
        request_model = build_request_model(func)

    if request_model is None:
        raise IPCWhitelistError(
            f"Whitelist entry {method_path!r}: {method_name!r} is not "
            "IPC-eligible - every parameter (besides self) needs a type "
            "hint pydantic can build a field from (no bare *args/**kwargs), "
            "or supply @ipc_method(request_model=...) explicitly"
        )

    response_model = getattr(func, "__ipc_response_model__", None)
    response_type: Any = response_model
    if response_model is None:
        response_model, response_type = _response_info(func)

    logger.info(
        "IPC whitelist: %s -> %s.%s(%s) -> %s",
        method_path,
        role,
        method_name,
        request_model.__name__,
        response_model.__name__ if response_model is not None else response_type,
    )

    return WhitelistEntry(
        method_path=method_path,
        role=role,
        method_name=method_name,
        request_model=request_model,
        response_model=response_model,
        response_type=response_type,
    )


def build_whitelist(
    beamline: Any, allowed_methods: List[str]
) -> Dict[str, WhitelistEntry]:
    """Resolve and validate the configured "role.method" list once at
    IPCServer startup. Fails fast: any entry that doesn't resolve to a role,
    doesn't resolve to a method, or isn't IPC-eligible raises
    IPCWhitelistError immediately, rather than failing later on first call.
    """
    logger.info(
        "Building IPC whitelist from %d configured method(s)", len(allowed_methods)
    )
    registry = {path: _resolve_entry(beamline, path) for path in allowed_methods}
    logger.info("IPC whitelist ready: %s", sorted(registry))
    return registry


def describe(registry: Dict[str, WhitelistEntry]) -> Dict[str, Dict[str, Any]]:
    """Self-description of the whitelist for the `_describe` reserved
    method: one request/response JSON schema pair per entry, so a client
    can discover what's callable without hardcoding it - see
    MXCuBEIPCClient (the separate mxcube-ipc-client package) and
    IPC_FORMAT.md section 6.

    response_schema comes from response_model when there is one (a
    pydantic.BaseModel return type), else from a TypeAdapter over the bare
    response_type - either way it's built from the entry's own resolved
    types, so it can never drift from what dispatch() actually enforces.
    """
    return {
        method_path: {
            "request_schema": entry.request_model.model_json_schema(),
            "response_schema": (
                entry.response_model.model_json_schema()
                if entry.response_model is not None
                else TypeAdapter(entry.response_type).json_schema()
            ),
        }
        for method_path, entry in registry.items()
    }


def dispatch(
    beamline: Any,
    registry: Dict[str, WhitelistEntry],
    method_path: str,
    params: Dict[str, Any],
) -> Any:
    """Validate params, invoke one whitelisted call, and return a
    JSON-serializable result. Raises IPCWhitelistError if method_path isn't
    in the registry, or pydantic.ValidationError if params don't validate
    against the method's request model.
    """
    entry = registry.get(method_path)
    if entry is None:
        logger.warning("IPC call to non-whitelisted method: %r", method_path)
        raise IPCWhitelistError(f"Method not whitelisted: {method_path!r}")

    logger.info("IPC call: %s(%s)", method_path, params)

    target = resolve_role_path(beamline, entry.role)
    func = getattr(target, entry.method_name)

    try:
        request_obj = entry.request_model.model_validate(params)
        result = func(**request_obj.model_dump())
    except Exception:
        logger.exception("IPC call failed: %s(%s)", method_path, params)
        raise

    if entry.response_model is not None:
        if not isinstance(result, entry.response_model):
            logger.error(
                "IPC call %s returned %r, expected %r",
                method_path,
                type(result).__name__,
                entry.response_model.__name__,
            )
            raise IPCWhitelistError(
                f"{method_path!r} returned {type(result).__name__!r}, expected "
                f"{entry.response_model.__name__!r}"
            )
        result_json = result.model_dump(mode="json")
    else:
        result_json = to_jsonable(result)

    logger.info("IPC call %s -> %s", method_path, result_json)
    return result_json
