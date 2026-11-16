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

"""Whitelist bypass for exploring and debugging - see IPC_FORMAT.md,
"Debug bypass".

Any resolvable role and any callable on it can be called. Arguments are
validated against the method's signature when a request model can be built
from it, and passed through unchanged otherwise.

Only reachable when IPCServer's `allow_debug_calls` is true (false by
default). Never enable it outside a local, trusted session.
"""

import inspect
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from pydantic_core import to_jsonable_python

from mxcubecore.ipc.whitelist import (
    IPCWhitelistError,
    build_request_model,
    validate_params,
)


def _resolve(beamline: Any, role: str) -> Any:
    target = beamline.get_by_id(role) if role else beamline
    if target is None:
        raise ValueError(f"No such role: {role!r}")
    return target


def _public_attr_names(target: Any) -> List[str]:
    names = []
    for name in dir(target):
        if name.startswith("_"):
            continue
        try:
            getattr(target, name)
        except Exception:  # noqa: S112 - exploration tool, expect some to fail
            continue
        names.append(name)
    return names


def list_roles(beamline: Any, role: str = "") -> Dict[str, Any]:
    """The direct sub-roles of `role` (of `beamline` itself if empty)."""
    target = _resolve(beamline, role)
    get_roles = getattr(target, "get_roles", None)
    roles = get_roles() if callable(get_roles) else []
    return {"role": role, "class": type(target).__name__, "roles": sorted(roles)}


def describe_role(beamline: Any, role: str = "") -> Dict[str, Any]:
    """Class, sub-roles and public methods of `role`.

    Each method has its signature and, when one can be built, the JSON
    schema of its arguments.
    """
    target = _resolve(beamline, role)

    get_roles = getattr(target, "get_roles", None)
    sub_roles = sorted(get_roles()) if callable(get_roles) else []

    methods = {}
    for name in _public_attr_names(target):
        attr = getattr(target, name)
        if not callable(attr):
            continue
        try:
            signature = str(inspect.signature(attr))
        except (TypeError, ValueError):
            signature = "(...)"

        try:
            schema = build_request_model(attr).model_json_schema()
        except Exception:  # noqa: BLE001 - e.g. a Callable-typed parameter
            schema = None

        methods[name] = {"signature": signature, "schema": schema}

    return {
        "role": role,
        "class": type(target).__name__,
        "roles": sub_roles,
        "methods": methods,
    }


def debug_call(
    beamline: Any,
    role: str,
    method: str,
    args: Optional[List[Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> Any:
    """Call any method on any resolvable role.

    Raises:
        pydantic.ValidationError: when the arguments don't validate against
            the method's signature.
    """
    if args is not None and not isinstance(args, list):
        raise TypeError(f"debug_call: args must be a JSON array, got {args!r}")
    if kwargs is not None and not isinstance(kwargs, dict):
        raise TypeError(f"debug_call: kwargs must be a JSON object, got {kwargs!r}")
    args, kwargs = args or [], kwargs or {}

    target = _resolve(beamline, role)

    func = getattr(target, method, None)
    if func is None or not callable(func):
        raise ValueError(f"{role or '<beamline>'!r} has no callable method {method!r}")

    try:
        request_model = build_request_model(func)
    except IPCWhitelistError:
        result = func(*args, **kwargs)
    else:
        result = func(**validate_params(request_model, _as_kwargs(func, args, kwargs)))

    return to_jsonable_python(result, fallback=repr)


def _as_kwargs(func: Any, args: List[Any], kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Merge positional `args` into `kwargs` by parameter name."""
    try:
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
    except TypeError as exc:
        raise TypeError(f"debug_call: {exc}") from exc
    return dict(bound.arguments)
