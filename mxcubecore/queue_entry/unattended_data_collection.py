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
from mxcubecore.queue_entry.base_queue_entry import QueueSkipEntryException
from mxcubecore.queue_entry.data_collection import DataCollectionQueueEntry

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class UnattendedDataCollectionQueueEntry(DataCollectionQueueEntry):
    """The data collection of an unattended collect.

    A standard data collection, at the position found by the tasks before it.
    """

    QMO = queue_model_objects.UnattendedDataCollection

    def pre_execute(self):
        model = self.get_data_model()
        context = model.get_parent().context

        if not context.get("found_spots"):
            msg = f"{model.label} skipped, no spots found"
            raise QueueSkipEntryException(msg, self)

        acq_params = model.acquisitions[0].acquisition_parameters
        acq_params.centred_position = queue_model_objects.CentredPosition(
            context.get("centred_position")
        )
        super().pre_execute()

    def get_type_str(self):
        return self.get_data_model().label
