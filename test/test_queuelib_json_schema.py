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
"""Keeps queue.schema.json (the published, checked-in JSON Schema) in sync
with what get_json_schema() actually generates from the live Pydantic
models - if a model change isn't matched by regenerating the checked-in
file, this test catches the drift instead of a third-party client."""

import json
from pathlib import Path

from mxcubecore.queuelib.constants import QUEUE_FORMAT_VERSION
from mxcubecore.queuelib.json_schema import get_json_schema

SCHEMA_PATH = (
    Path(__file__).parent.parent / "mxcubecore" / "queuelib" / "queue.schema.json"
)


def test_checked_in_schema_matches_generated_schema():
    checked_in = json.loads(SCHEMA_PATH.read_text())
    generated = get_json_schema()

    assert checked_in == generated, (
        "queue.schema.json is out of date - regenerate it with "
        "get_json_schema() (see json_schema.py's docstring)"
    )


def test_schema_reports_current_format_version():
    schema = get_json_schema()

    assert schema["formatVersion"] == QUEUE_FORMAT_VERSION


def test_schema_covers_every_task_node_type():
    schema = get_json_schema()
    defs = schema["$defs"]

    assert "SampleNode" in defs
    for task_model in (
        "DataCollectionNodeModel",
        "CharacterisationNodeModel",
        "XRFNodeModel",
        "EnergyScanNodeModel",
        "WorkflowNodeModel",
    ):
        assert task_model in defs
