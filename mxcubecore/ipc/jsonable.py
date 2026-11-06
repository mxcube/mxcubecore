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

"""Shared by mxcubecore.ipc.debug and mxcubecore.ipc.whitelist: turning an
arbitrary Python return value into something JSON-safe to put on the wire.
"""

import json
from typing import Any

from pydantic import BaseModel


def to_jsonable(value: Any) -> Any:
    """Best-effort JSON-safe representation of an arbitrary return value -
    falling back to repr() for anything that can't be serialized directly
    is preferable to erroring out.
    """
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    try:
        json.dumps(value)
    except TypeError:
        return repr(value)
    return value
