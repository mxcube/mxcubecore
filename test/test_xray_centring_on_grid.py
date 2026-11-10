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
"""An X-ray centring queued on a grid drawn on the sample view."""

import pytest

from mxcubecore import queue_entry as qe
from mxcubecore.model import queue_model_objects as qmo
from mxcubecore.queuelib import QueueBuilder, QueueSerializer


@pytest.fixture
def serializer(beamline):
    model = beamline.queue_model
    model.connect(model, "child_added", model.queue_model_child_added)
    serializer = QueueSerializer(QueueBuilder())
    serializer.queue_add_item(
        [
            {
                "type": "Sample",
                "sampleID": "1:01",
                "location": "1:01",
                "sampleName": "sample",
                "tasks": [],
            }
        ]
    )
    yield serializer
    model.disconnect(model, "child_added", model.queue_model_child_added)
    beamline.queue_manager.clear()


@pytest.fixture
def grid(beamline):
    position = {"omega": 30, "phiz": 0, "phiy": 0, "sampx": 0, "sampy": 0}
    grid = beamline.sample_view.add_shape_from_mpos([position], (0, 0), "G")
    yield grid
    beamline.sample_view.delete_shape(grid.id)


def _add(serializer, grid):
    return serializer.add_task(
        "1:01",
        {
            "type": "XrayCentring",
            "sampleID": "1:01",
            "parameters": {"shape": grid.id, "prefix": "xc", "subdir": "xc"},
        },
    )


def test_queued_on_the_grid(beamline, serializer, grid):
    node_id = _add(serializer, grid)
    model, entry = beamline.queue_manager.get_entry(node_id)

    assert isinstance(model, qmo.XrayCentring2)
    assert isinstance(entry, qe.XrayCentring2QueueEntry)
    assert model.shape == grid.id
    # Back to the omega of the grid before the scan
    assert model.get_motor_positions() == {"omega": 30}
    assert model.path_template.base_prefix == "xc"


def test_row_in_the_queue_json(serializer, grid):
    node_id = _add(serializer, grid)
    row = serializer.queue_to_dict()["1:01"]["tasks"][0]

    assert row["type"] == "XrayCentring"
    assert row["queueID"] == node_id
    assert row["parameters"]["shape"] == grid.id
    assert row["parameters"]["subdir"] == "xc"

    # Sent back as it is, it is queued again
    serializer.add_task("1:01", {**row, "queueID": -1})

    assert len(serializer.queue_to_dict()["1:01"]["tasks"]) == 2


def test_without_a_grid_it_is_not_a_row(beamline, serializer):
    sample = beamline.queue_model.get_model_root().get_children()[0]
    beamline.queue_model.add_child(sample, qmo.XrayCentring2())

    assert serializer.queue_to_dict()["1:01"]["tasks"] == []
