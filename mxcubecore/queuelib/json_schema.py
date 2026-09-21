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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.
"""Generates the JSON Schema for the queue JSON format.

See JSON_FORMAT.md in this package for the format documentation. The schema
returned by get_json_schema() is generated directly from the PyDantic
models in models.py (via model_json_schema()).
"""

from mxcubecore.queuelib.constants import QUEUE_FORMAT_VERSION
from mxcubecore.queuelib.models import SampleNode

SCHEMA_ID = (
    "https://github.com/mxcube/mxcubecore/blob/develop/"
    "mxcubecore/queuelib/queue.schema.json"
)


def get_json_schema() -> dict:
    """Return the JSON Schema for queue_to_dict()'s root ("get the whole
    queue") response.

    :returns: a JSON Schema (draft 2020-12) dict.
    """
    sample_node_schema = SampleNode.model_json_schema()
    defs = sample_node_schema.pop("$defs", {})
    defs["SampleNode"] = sample_node_schema

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_ID,
        "title": "MXCuBE queue client format",
        "formatVersion": QUEUE_FORMAT_VERSION,
        "description": (
            "The whole queue: a dict keyed by sample ID, each value a "
            "SampleNode, plus the synthetic 'sample_order' and "
            "'format_version' keys sharing that same top-level namespace. "
            "See JSON_FORMAT.md's 'Known issues' #2 for why this differs "
            "from the shape returned when queue_to_dict() is called on a "
            "specific node."
        ),
        "type": "object",
        "properties": {
            "sample_order": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Sample IDs in queue order. Absent (not empty) when the "
                    "queue has zero samples."
                ),
            },
            "format_version": {
                "const": QUEUE_FORMAT_VERSION,
                "description": "Always present, even for an empty queue.",
            },
        },
        "additionalProperties": {"$ref": "#/$defs/SampleNode"},
        "$defs": defs,
    }
