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
"""Start and end time of the queue entries, and their place in the queue JSON."""

from unittest.mock import Mock

import gevent
import pytest

from mxcubecore.model import queue_model_objects as qmo
from mxcubecore.queue_entry.base_queue_entry import (
    QUEUE_ENTRY_STATUS,
    BaseQueueEntry,
    QueueSkipEntryException,
)
from mxcubecore.queuelib import QueueBuilder, QueueSerializer


class ProbeQueueEntry(BaseQueueEntry):
    """Records its own state while it runs, can be made to be skipped."""

    def __init__(self, view, data_model, skip=False):
        super().__init__(view, data_model)
        self.skip = skip
        self.seen = []

    def execute(self):
        self.seen.append((self.status, self.started_at, self.ended_at))
        if self.skip:
            raise QueueSkipEntryException("skipped", self)


@pytest.fixture
def manager(beamline):
    yield beamline.queue_manager
    beamline.queue_manager.clear()


def _run(manager, *entries):
    group = ProbeQueueEntry(Mock(), qmo.TaskGroup())
    for entry in (group, *entries):
        entry.set_enabled(True)
    for entry in entries:
        group.enqueue(entry)
    manager.enqueue(group)

    started = []
    manager.connect(
        "queue_entry_execute_started",
        lambda entry: started.append((entry, entry.status, entry.started_at)),
    )
    manager.execute(group)

    with gevent.Timeout(10):
        while manager.is_executing():
            gevent.sleep(0.01)

    return started


def test_entries_are_timed(manager):
    done = ProbeQueueEntry(Mock(), qmo.TaskNode())
    skipped = ProbeQueueEntry(Mock(), qmo.TaskNode(), skip=True)

    _run(manager, done, skipped)

    for entry in (done, skipped):
        status, started_at, ended_at = entry.seen[0]
        assert status == QUEUE_ENTRY_STATUS.RUNNING
        assert started_at is not None and ended_at is None
        assert entry.started_at <= entry.ended_at

    assert done.status == QUEUE_ENTRY_STATUS.SUCCESS
    assert skipped.status == QUEUE_ENTRY_STATUS.SKIPPED
    assert done.ended_at <= skipped.started_at


def test_running_and_timed_when_announced(manager):
    probe = ProbeQueueEntry(Mock(), qmo.TaskNode())

    started = _run(manager, probe)
    announced = {entry: (status, at) for entry, status, at in started}

    assert announced[probe] == (QUEUE_ENTRY_STATUS.RUNNING, probe.started_at)


def test_times_in_the_queue_json(beamline, manager):
    model = beamline.queue_model
    model.connect(model, "child_added", model.queue_model_child_added)
    # The test beamline.yaml has no "configuration" section, so no defaults
    beamline.config.default_acquisition_parameters = {
        "default": {
            "first_image": 1,
            "num_images": 1,
            "osc_range": 0.1,
            "exp_time": 0.1,
        }
    }
    serializer = QueueSerializer(QueueBuilder())

    try:
        serializer.queue_add_item(
            [
                {
                    "type": "Sample",
                    "sampleID": "1:01",
                    "location": "1:01",
                    "sampleName": "sample",
                    "tasks": [
                        {
                            "type": "DataCollection",
                            "sampleID": "1:01",
                            "parameters": {"subdir": "timing"},
                        }
                    ],
                }
            ]
        )
        row = serializer.queue_to_dict()["1:01"]["tasks"][0]

        assert (row["startedAt"], row["endedAt"]) == (None, None)

        _, entry = manager.get_entry(row["queueID"])
        entry.started_at, entry.ended_at = 10.0, 12.5
        row = serializer.queue_to_dict()["1:01"]["tasks"][0]

        assert (row["startedAt"], row["endedAt"]) == (10.0, 12.5)
    finally:
        model.disconnect(model, "child_added", model.queue_model_child_added)
