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

"""The whitelist bypass - see IPC_FORMAT.md section 7.

Unlike mxcubecore.ipc.whitelist, NOTHING here is validated. Any role path
that resolves and any callable can be called with the arguments the caller
sends.

This is for exploring/debugging ONLY, not meant as a production API.

IPCServer only ever routes uses this logic when `allow_debug_calls` config
is explicitly set to true (false by default).

Enabling it on anything but a local, trusted session means any authenticated
client can invoke *any* method on *any* loaded HardwareObject with *any* arguments.
"""

import inspect
import typing
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from pydantic import BaseModel

from mxcubecore.ipc.jsonable import to_jsonable
from mxcubecore.ipc.whitelist import build_request_model, resolve_role_path


def _resolve(beamline: Any, role: str) -> Any:
    target = beamline if not role else resolve_role_path(beamline, role)
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
    return sorted(names)


def list_roles(beamline: Any, role: str = "") -> Dict[str, Any]:
    """The direct sub-roles of `role` (or of `beamline` itself if `role`
    is empty/omitted).
    """
    target = _resolve(beamline, role)
    get_roles = getattr(target, "get_roles", None)
    roles = get_roles() if callable(get_roles) else []
    return {"role": role, "class": type(target).__name__, "roles": sorted(roles)}


def describe_role(beamline: Any, role: str = "") -> Dict[str, Any]:
    """One role's class, its own sub-roles, and its public (non-underscore)
    callable attributes - each with its signature (best-effort string) and,
    when buildable, a JSON schema for its arguments (the same
    `pydantic.create_model()` mechanism `mxcubecore.ipc.whitelist` uses for
    the whitelist. See `build_request_model()`).
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

        schema = None
        try:
            # Both steps can fail on a parameter type pydantic can't
            # handle - build_request_model() itself for one it can't even
            # build a core schema for (e.g. a bare HardwareObject-typed
            # parameter), model_json_schema() for one it can validate but
            # not describe (e.g. connect/disconnect's Callable-typed
            # `slot`). Either way, best-effort: fall back to no schema
            # rather than failing the whole describe_role() call over one
            # method.
            request_model = build_request_model(attr)
            if request_model is not None:
                schema = request_model.model_json_schema()
        except Exception:  # noqa: BLE001
            schema = None

        methods[name] = {"signature": signature, "schema": schema}

    return {
        "role": role,
        "class": type(target).__name__,
        "roles": sub_roles,
        "methods": methods,
    }


def _coerce_pydantic_args(
    func: Any, args: List[Any], kwargs: Dict[str, Any]
) -> Tuple[List[Any], Dict[str, Any]]:
    """Best-effort: for any parameter type-hinted as a pydantic.BaseModel
    subclass, create a plain dict argument into that model via
    model_validate().

    Deliberately does not swallow a validation failure - letting it
    propagate gives the caller a real pydantic error (e.g. "field
    required: node_id") instead of a confusing AttributeError once the
    unconverted dict reaches the method body.
    """
    try:
        hints = typing.get_type_hints(func)
    except (NameError, TypeError):
        return args, kwargs
    hints.pop("return", None)

    try:
        parameter_names = list(inspect.signature(func).parameters)
    except (TypeError, ValueError):
        return args, kwargs

    def coerce(name: Optional[str], value: Any) -> Any:
        param_type = hints.get(name) if name else None
        if (
            isinstance(value, dict)
            and isinstance(param_type, type)
            and issubclass(param_type, BaseModel)
        ):
            return param_type.model_validate(value)
        return value

    coerced_args = [
        coerce(parameter_names[i] if i < len(parameter_names) else None, value)
        for i, value in enumerate(args)
    ]
    coerced_kwargs = {name: coerce(name, value) for name, value in kwargs.items()}
    return coerced_args, coerced_kwargs


def debug_call(
    beamline: Any,
    role: str,
    method: str,
    args: Optional[List[Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
) -> Any:
    """Call ANY method on ANY resolvable role, with raw arguments - no
    whitelist check, no pydantic validation beyond the best-effort
    single-request-model coercion in _coerce_pydantic_args(). See module
    docstring.
    """
    if args is not None and not isinstance(args, list):
        raise TypeError(f"debug_call: args must be a JSON array, got {args!r}")
    if kwargs is not None and not isinstance(kwargs, dict):
        raise TypeError(f"debug_call: kwargs must be a JSON object, got {kwargs!r}")

    target = _resolve(beamline, role)

    func = getattr(target, method, None)
    if func is None or not callable(func):
        raise ValueError(f"{role or '<beamline>'!r} has no callable method {method!r}")

    coerced_args, coerced_kwargs = _coerce_pydantic_args(func, args or [], kwargs or {})
    result = func(*coerced_args, **coerced_kwargs)
    return to_jsonable(result)
