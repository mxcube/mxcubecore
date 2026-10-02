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
"""The unattended collect pipeline: one task group, its tasks executed in order."""

import gevent
import pytest

from mxcubecore import queue_entry as qe
from mxcubecore.model import queue_model_objects as qmo
from mxcubecore.queue_entry.base_queue_entry import QUEUE_ENTRY_STATUS
from mxcubecore.queuelib import (
    WARNING,
    QueueBuilder,
    QueueSerializer,
)

METHODS = [task[1] for task in qmo.UNATTENDED_TASKS]
# The methods of the unattended_collect object, "collect" is a data collection
HWOBJ_METHODS = [method for method in METHODS if method != "collect"]
DEFAULTS = {"first_image": 1, "num_images": 10, "osc_range": 0.1, "exp_time": 0.04}
PARAMETERS = {"osc_range": 0.5, "exp_time": 0.02, "num_images": 7}


@pytest.fixture
def queue(beamline):
    model, manager = beamline.queue_model, beamline.queue_manager
    model.connect(model, "child_added", model.queue_model_child_added)
    beamline.unattended_collect.task_time = 0
    # The test beamline.yaml has no "configuration" section, so no defaults
    beamline.config.default_acquisition_parameters = {"default": DEFAULTS}

    serializer = QueueSerializer(QueueBuilder())
    serializer.queue_add_item(
        [
            {
                "type": "Sample",
                "sampleID": "1:01",
                "location": "1:01",
                "sampleName": "sample",
                "tasks": [
                    {
                        "type": "UnattendedCollect",
                        "sampleID": "1:01",
                        "parameters": {},
                    }
                ],
            }
        ]
    )
    yield serializer
    model.disconnect(model, "child_added", model.queue_model_child_added)
    manager.clear()


def _group(beamline):
    sample = beamline.queue_model.get_model_root().get_children()[0]
    return sample.get_children()[0]


def _run(beamline, calls):
    """Execute the task group, recording what is called and the group context."""
    hwobj = beamline.unattended_collect
    group = _group(beamline)

    def record(name):
        method = getattr(type(hwobj), name)

        def wrapper(context, **kwargs):
            calls.append((name, dict(context)))
            if name == "unmount":
                return None
            return method(hwobj, context, **kwargs)

        return wrapper

    def collect(owner, param_list):
        calls.append(("collect", dict(group.context)))
        return gevent.spawn(lambda: None)

    for name in set(HWOBJ_METHODS):
        setattr(hwobj, name, record(name))

    beamline.collect.collect = collect
    entry = beamline.queue_manager.get_entry_with_model(group)
    beamline.queue_manager.execute(entry)

    with gevent.Timeout(20):
        while beamline.queue_manager.is_executing():
            gevent.sleep(0.05)

    return [
        beamline.queue_manager.get_entry_with_model(p) for p in group.get_children()
    ]


def test_one_group_with_the_tasks_in_order(beamline, queue):
    group = _group(beamline)
    children = group.get_children()
    manager = beamline.queue_manager

    assert isinstance(group, qmo.UnattendedCollect)
    assert isinstance(manager.get_entry_with_model(group), qe.TaskGroupQueueEntry)
    assert [task.method for task in children] == METHODS
    assert [type(task) for task in children] == [
        qmo.UnattendedDataCollection if method == "collect" else qmo.UnattendedTask
        for method in METHODS
    ]
    assert isinstance(
        manager.get_entry_with_model(group.get_data_collection()),
        qe.DataCollectionQueueEntry,
    )

    rows = queue.queue_to_dict()["1:01"]["tasks"]

    assert [row["parameters"]["method"] for row in rows] == METHODS
    assert [row["taskIndex"] for row in rows] == list(range(len(METHODS)))
    assert {row["groupID"] for row in rows} == {group._node_id}


def test_parameters_are_those_of_the_data_collection(beamline, queue):
    rows = queue.queue_to_dict()["1:01"]["tasks"]
    # Any row of the group can be sent back, the group is what is returned
    updated = queue.builder.queue_update_item(
        rows[3]["sampleQueueID"],
        rows[3]["queueID"],
        {**rows[3], "parameters": {**rows[3]["parameters"], **PARAMETERS}},
    )

    assert updated is _group(beamline)
    assert queue.node_to_dict(updated)["queueID"] == rows[0]["queueID"]

    acq = _group(beamline).get_data_collection().acquisitions[0]
    rows = queue.queue_to_dict()["1:01"]["tasks"]

    for key, value in PARAMETERS.items():
        assert getattr(acq.acquisition_parameters, key) == value
        assert all(row["parameters"][key] == value for row in rows)

    assert acq.path_template.num_files == PARAMETERS["num_images"]


def test_tasks_run_in_order_and_pass_on_their_results(beamline, queue):
    calls = []
    entries = _run(beamline, calls)
    seen = dict(calls)
    acq = _group(beamline).get_data_collection().acquisitions[0]

    assert [name for name, _ in calls] == METHODS
    assert "grid_id" not in seen["grid_scan"]
    assert seen["line_scan"]["found_spots"]
    assert seen["line_scan"]["grid_id"] in beamline.sample_view.shapes
    assert "point_id" in seen["collect"]
    assert (
        acq.acquisition_parameters.centred_position.as_dict()
        == qmo.CentredPosition(seen["collect"]["centred_position"]).as_dict()
    )
    assert all(e.status == QUEUE_ENTRY_STATUS.SUCCESS for e in entries)
    assert all(e.started_at <= e.ended_at for e in entries)


def test_no_spots_skips_to_unmount(beamline, queue):
    beamline.unattended_collect.found_spots = False
    calls = []
    entries = _run(beamline, calls)

    assert [name for name, _ in calls] == [*METHODS[:3], "unmount"]
    assert [e.status for e in entries[2:7]] == [QUEUE_ENTRY_STATUS.SKIPPED] * 5
    assert entries[7].status == QUEUE_ENTRY_STATUS.SUCCESS

    rows = queue.queue_to_dict()["1:01"]["tasks"]

    assert all(row["state"] == WARNING for row in rows[2:7])


def test_failed_add_leaves_no_group_behind(beamline, queue, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError

    monkeypatch.setattr(queue.builder, "set_dc_params", fail)

    with pytest.raises(RuntimeError):
        queue.add_task(
            "1:01",
            {"type": "UnattendedCollect", "sampleID": "1:01", "parameters": {}},
        )

    assert len(queue.queue_to_dict()["1:01"]["tasks"]) == len(METHODS)


def test_delete_and_restore(beamline, queue):
    saved = queue.queue_to_dict()["1:01"]
    beamline.queue_manager.delete_entry_at([["1:01", 4]])

    assert queue.queue_to_dict()["1:01"]["tasks"] == []

    # Every row is sent back, the first one rebuilds the group
    for row in saved["tasks"]:
        queue.add_task("1:01", row)

    rows = queue.queue_to_dict()["1:01"]["tasks"]

    assert [row["parameters"]["method"] for row in rows] == METHODS
    assert len({row["groupID"] for row in rows}) == 1
