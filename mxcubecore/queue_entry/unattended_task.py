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
import logging

from mxcubecore import HardwareRepository as HWR
from mxcubecore.model import queue_model_objects
from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
    QueueAbortedException,
    QueueSkipEntryException,
)

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class UnattendedTaskQueueEntry(BaseQueueEntry):
    """One step of an unattended collect.

    Calls the method of HWR.beamline.unattended_collect named by the model,
    passing the context shared by the tasks of the parent task group.
    """

    QMO = queue_model_objects.UnattendedTask

    def execute(self):
        super().execute()
        model = self.get_data_model()
        context = model.get_parent().context
        kwargs = dict(model.kwargs)

        if model.needs_spots and not context.get("found_spots"):
            msg = f"{model.label} skipped, no spots found"
            raise QueueSkipEntryException(msg, self)

        if model.method == "unmount":
            kwargs["unload"] = self._is_last_sample()

        try:
            done = getattr(HWR.beamline.unattended_collect, model.method)(
                context, **kwargs
            )
        except Exception as ex:
            logging.getLogger("HWR").exception("%s failed", model.label)
            context["found_spots"] = False
            cls = (
                QueueAbortedException
                if getattr(ex, "abort_queue", False)
                else QueueSkipEntryException
            )
            raise cls(f"{model.label} failed: {ex}", self) from ex

        if done is False:
            context["found_spots"] = False
            raise QueueSkipEntryException(f"{model.label} found nothing", self)

    def _is_last_sample(self):
        """True when no other sample will be mounted after this one."""
        manager = self.get_queue_controller()

        # A single entry run executes nothing else
        if manager is None or manager.run_root_entry is not None:
            return True

        entry = self
        while isinstance(entry.get_container(), BaseQueueEntry):
            entry = entry.get_container()

        top = manager.get_queue_entry_list()

        if entry not in top:
            return True

        return not any(
            later.is_enabled()
            and any(child.is_enabled() for child in later.get_queue_entry_list())
            for later in top[top.index(entry) + 1 :]
        )

    def get_type_str(self):
        return self.get_data_model().label
