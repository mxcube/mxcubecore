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

"""The IPCServer's `events:` whitelist: which HardwareObject signals are
forwarded as IPCEvents, and (optionally) the declared types of their
positional arguments.

HardwareObject signals are undeclared - `self.emit("valueChanged", value)`
can pass anything - so unlike a whitelisted method, an event's payload
can't be introspected. Each `events:` entry may therefore declare it
explicitly, one Python type expression per positional signal argument::

    - role: diffractometer.omega
      signal: valueChanged
      method: diffractometer.omega.valueChanged
      args: [float]

`args` is turned into a JSON schema (via pydantic's TypeAdapter, like a
method's response_schema) and published through `_describe`, and every
emission is checked against it - a mismatch is logged as a warning (the
event is still forwarded), so the declaration can't silently drift from
what the HardwareObject actually emits. Entries without `args` are
forwarded unchanged and described with `args_schema: null`.

See IPC_FORMAT.md section 5.
"""

import ast
import importlib
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from pydantic import TypeAdapter, ValidationError

from mxcubecore.ipc.constants import logger
from mxcubecore.ipc.whitelist import IPCWhitelistError, resolve_role_path

# Names an `args` type expression may use without a module path. Anything
# else must be a fully-qualified, importable "package.module.Name".
_TYPE_NAMES: Dict[str, Any] = {
    "Any": Any,
    "None": None,
    "bool": bool,
    "int": int,
    "float": float,
    "str": str,
    "bytes": bytes,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "List": List,
    "Dict": Dict,
    "Tuple": Tuple,
    "Optional": Optional,
    "Union": Union,
}


def _import_dotted(path: str) -> Any:
    """Resolve "package.module.Name" (or "package.module.Class.Inner") by
    importing the longest importable module prefix, then getattr-ing the
    rest.
    """
    parts = path.split(".")
    for split in range(len(parts) - 1, 0, -1):
        try:
            target = importlib.import_module(".".join(parts[:split]))
        except ImportError:
            continue
        for attr in parts[split:]:
            target = getattr(target, attr)
        return target
    raise ValueError(f"cannot import {path!r}")


def _eval_type_node(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant) and node.value is None:
        return None
    if isinstance(node, ast.Name):
        if node.id not in _TYPE_NAMES:
            raise ValueError(
                f"unknown type name {node.id!r} - use one of "
                f"{sorted(_TYPE_NAMES)} or a fully-qualified module path"
            )
        return _TYPE_NAMES[node.id]
    if isinstance(node, ast.Attribute):
        return _import_dotted(ast.unparse(node))
    if isinstance(node, ast.Subscript):
        origin = _eval_type_node(node.value)
        if isinstance(node.slice, ast.Tuple):
            params = tuple(_eval_type_node(elt) for elt in node.slice.elts)
        else:
            params = _eval_type_node(node.slice)
        return origin[params]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return Union[_eval_type_node(node.left), _eval_type_node(node.right)]
    raise ValueError(f"unsupported type expression {ast.unparse(node)!r}")


def parse_type(expression: str) -> Any:
    """Turn a config type expression ("float", "Optional[float]",
    "dict[str, Any]", "int | None", "mxcubecore.model.foo.Bar", ...) into
    the type it names - without eval(): only the names in _TYPE_NAMES and
    fully-qualified importable paths are accepted.
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"invalid type expression {expression!r}: {exc}") from None
    return _eval_type_node(tree.body)


@dataclass(frozen=True)
class EventEntry:
    """One resolved `events:` entry. args_adapter validates a whole
    positional-args tuple; it (and args) are None when the entry doesn't
    declare `args`.
    """

    method: str
    role: str
    signal: str
    sender: Any
    args: Optional[Tuple[str, ...]]
    args_adapter: Optional[TypeAdapter]

    def args_schema(self) -> Optional[Dict[str, Any]]:
        if self.args_adapter is None:
            return None
        return self.args_adapter.json_schema()

    def check_args(self, args: Tuple[Any, ...]) -> None:
        """Log a warning if `args` doesn't match the declared types."""
        if self.args_adapter is None:
            return
        try:
            self.args_adapter.validate_python(tuple(args))
        except ValidationError as exc:
            logger.warning(
                "IPC event %s: %s.%s emitted %r, which doesn't match declared "
                "args %s: %s",
                self.method,
                self.role,
                self.signal,
                args,
                list(self.args),
                exc,
            )


def _resolve_event(beamline: Any, cfg: Dict[str, Any]) -> EventEntry:
    missing = [key for key in ("role", "signal", "method") if not cfg.get(key)]
    if missing:
        raise IPCWhitelistError(f"Event entry {cfg!r}: missing {missing}")

    role, signal, method = cfg["role"], cfg["signal"], cfg["method"]
    sender = resolve_role_path(beamline, role)
    if sender is None:
        raise IPCWhitelistError(f"Event {method!r}: no such beamline role {role!r}")

    args_cfg = cfg.get("args")
    args: Optional[Tuple[str, ...]] = None
    args_adapter: Optional[TypeAdapter] = None
    if args_cfg is not None:
        if isinstance(args_cfg, str) or not isinstance(args_cfg, (list, tuple)):
            raise IPCWhitelistError(
                f"Event {method!r}: 'args' must be a list of type expressions, "
                f"one per positional signal argument, got {args_cfg!r}"
            )
        args = tuple(str(arg) for arg in args_cfg)
        try:
            types = tuple(parse_type(arg) for arg in args)
            args_adapter = TypeAdapter(Tuple[types] if types else Tuple[()])
            args_adapter.json_schema()
        except Exception as exc:
            raise IPCWhitelistError(f"Event {method!r}: invalid 'args': {exc}") from exc

    logger.info(
        "IPC event whitelist: %s.%s -> %s%s",
        role,
        signal,
        method,
        f" args={list(args)}" if args is not None else "",
    )
    return EventEntry(
        method=method,
        role=role,
        signal=signal,
        sender=sender,
        args=args,
        args_adapter=args_adapter,
    )


def build_events(
    beamline: Any, events_cfg: List[Dict[str, Any]]
) -> Dict[str, EventEntry]:
    """Resolve and validate the configured `events:` list once at
    IPCServer startup, failing fast like build_whitelist(): an unresolvable
    role, an invalid `args` declaration, or two entries sharing a `method`
    name raises IPCWhitelistError immediately.
    """
    entries: Dict[str, EventEntry] = {}
    for cfg in events_cfg:
        entry = _resolve_event(beamline, cfg)
        if entry.method in entries:
            raise IPCWhitelistError(
                f"Event {entry.method!r} is configured more than once"
            )
        entries[entry.method] = entry
    return entries


def describe_events(entries: Dict[str, EventEntry]) -> Dict[str, Dict[str, Any]]:
    """The `events` half of `_describe`: per forwarded event, where it
    comes from and the JSON schema of its `params.args` (null if the entry
    doesn't declare `args`).
    """
    return {
        method: {
            "role": entry.role,
            "signal": entry.signal,
            "args": list(entry.args) if entry.args is not None else None,
            "args_schema": entry.args_schema(),
        }
        for method, entry in entries.items()
    }
