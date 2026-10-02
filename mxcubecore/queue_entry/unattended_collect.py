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
from mxcubecore.model import queue_model_objects
from mxcubecore.queue_entry.base_queue_entry import TaskGroupQueueEntry

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class UnattendedCollectQueueEntry(TaskGroupQueueEntry):
    """Task group of an unattended collect, its tasks are the child entries."""

    QMO = queue_model_objects.UnattendedCollect

    def pre_execute(self):
        super().pre_execute()
        self.get_data_model().reset_context()
