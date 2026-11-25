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

"""Whitelist of HardwareObject methods callable over IPC.

See IPC_FORMAT.md, section 4, for the eligibility rules.
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
    Type,
)

from pydantic import BaseModel, TypeAdapter, create_model
from pydantic_core import to_jsonable_python

from mxcubecore.log import ipc_log


class IPCWhitelistError(Exception):
    """Invalid whitelist configuration or call to a non-whitelisted method."""


def ipc_method(
    request_model: Optional[Type[BaseModel]] = None,
    response_model: Optional[Type[BaseModel]] = None,
) -> Callable[[Callable], Callable]:
    """Mark a method as IPC-eligible with explicit request/response models.

    Only needed when the models can't be inferred from the method signature.
    """

    def decorator(func: Callable) -> Callable:
        func.__ipc_request_model__ = request_model
        func.__ipc_response_model__ = response_model
        return func

    return decorator


@dataclass(frozen=True)
class WhitelistEntry:
    """A resolved and validated whitelist entry."""

    method_path: str
    role: str
    method_name: str
    request_model: Type[BaseModel]
    response_type: Any


def _pascal_case(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


def _is_model(type_: Any) -> bool:
    return isinstance(type_, type) and issubclass(type_, BaseModel)


def build_request_model(func: Callable) -> Type[BaseModel]:
    """Build a pydantic request model from the parameters of `func`.

    Raises:
        IPCWhitelistError: when a parameter is untyped, is `*args`/`**kwargs`,
            or has a type pydantic can't handle.
    """
    try:
        signature = inspect.signature(func)
        hints = typing.get_type_hints(func)
    except (NameError, TypeError, ValueError) as exc:
        raise IPCWhitelistError(f"can't introspect signature: {exc}") from exc

    fields: Dict[str, Any] = {}
    for name, param in signature.parameters.items():
        if name == "self":
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            raise IPCWhitelistError(f"*args/**kwargs parameter {name!r}")
        if name not in hints:
            raise IPCWhitelistError(f"parameter {name!r} has no type hint")
        default = ... if param.default is param.empty else param.default
        fields[name] = (hints[name], default)

    try:
        return create_model(f"{_pascal_case(func.__name__)}Request", **fields)
    except Exception as exc:
        raise IPCWhitelistError(f"can't build request model: {exc}") from exc


def validate_params(
    request_model: Type[BaseModel], params: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate `params` and return them as keyword arguments.

    Nested models stay model instances (unlike with `model_dump()`).

    Raises:
        pydantic.ValidationError: when `params` don't validate.
    """
    validated = request_model.model_validate(params)
    return {name: getattr(validated, name) for name in type(validated).model_fields}


def _return_type(func: Callable) -> Any:
    try:
        return typing.get_type_hints(func).get("return", Any)
    except (NameError, TypeError):
        return Any


def _resolve_entry(beamline: Any, method_path: str) -> WhitelistEntry:
    try:
        role, method_name = method_path.rsplit(".", 1)
    except ValueError:
        raise IPCWhitelistError(
            f"Invalid whitelist entry {method_path!r}: expected 'role.method'"
        ) from None

    target = beamline.get_by_id(role)
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
        try:
            request_model = build_request_model(func)
        except IPCWhitelistError as exc:
            raise IPCWhitelistError(
                f"Whitelist entry {method_path!r}: {method_name!r} is not "
                f"IPC-eligible ({exc}) - type-hint every parameter, or use "
                "@ipc_method(request_model=...)"
            ) from exc

    response_type = getattr(func, "__ipc_response_model__", None)
    if response_type is None:
        response_type = _return_type(func)

    ipc_log.info(
        "IPC whitelist: %s -> %s.%s(%s) -> %s",
        method_path,
        role,
        method_name,
        request_model.__name__,
        getattr(response_type, "__name__", response_type),
    )

    return WhitelistEntry(
        method_path=method_path,
        role=role,
        method_name=method_name,
        request_model=request_model,
        response_type=response_type,
    )


def build_whitelist(
    beamline: Any, allowed_methods: List[str]
) -> Dict[str, WhitelistEntry]:
    """Build the whitelist from the configured "role.method" entries.

    Raises:
        IPCWhitelistError: when a role or method could not be resolved, or
            a method is not IPC-eligible.
    """
    ipc_log.info(
        "Building IPC whitelist from %d configured method(s)", len(allowed_methods)
    )
    registry = {path: _resolve_entry(beamline, path) for path in allowed_methods}
    ipc_log.info("IPC whitelist ready: %s", sorted(registry))
    return registry


def describe(registry: Dict[str, WhitelistEntry]) -> Dict[str, Dict[str, Any]]:
    """Implementation of the `_describe` reserved IPC method.

    Returns request and response schemas for each whitelisted method.
    """
    return {
        path: {
            "request_schema": entry.request_model.model_json_schema(),
            "response_schema": TypeAdapter(entry.response_type).json_schema(),
        }
        for path, entry in registry.items()
    }


def dispatch(
    beamline: Any,
    registry: Dict[str, WhitelistEntry],
    method_path: str,
    params: Dict[str, Any],
) -> Any:
    """Validate `params`, call a whitelisted method and return a JSON-safe result.

    Raises:
        IPCWhitelistError: when `method_path` is not whitelisted.
        pydantic.ValidationError: when `params` don't validate.
        TypeError: when the method returns something other than its
            declared pydantic response model.
    """
    entry = registry.get(method_path)
    if entry is None:
        ipc_log.warning("IPC call to non-whitelisted method: %r", method_path)
        raise IPCWhitelistError(f"Method not whitelisted: {method_path!r}")

    ipc_log.info("IPC call: %s(%s)", method_path, params)

    func = getattr(beamline.get_by_id(entry.role), entry.method_name)

    try:
        result = func(**validate_params(entry.request_model, params))
        if _is_model(entry.response_type) and not isinstance(
            result, entry.response_type
        ):
            raise TypeError(
                f"{method_path!r} returned {type(result).__name__!r}, expected "
                f"{entry.response_type.__name__!r}"
            )
        result_json = to_jsonable_python(result)
    except Exception:
        ipc_log.exception("IPC call failed: %s(%s)", method_path, params)
        raise

    ipc_log.info("IPC call %s -> %s", method_path, result_json)
    return result_json
