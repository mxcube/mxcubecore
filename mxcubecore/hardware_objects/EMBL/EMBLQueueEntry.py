#
#  Project: MXCuBE
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

"""
Module contains EMBL specific queue entries
"""

import logging

from mxcubecore.dispatcher import dispatcher
from mxcubecore.hardware_objects.base_queue_entry import (
    BaseQueueEntry,
    QueueExecutionException,
    QUEUE_ENTRY_STATUS,
)
from mxcubecore import HardwareRepository as HWR


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "queue"


class XrayImagingQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None, view_set_queue_entry=True):
        BaseQueueEntry.__init__(self, view, data_model, view_set_queue_entry)

    def execute(self):
        BaseQueueEntry.execute(self)
        HWR.beamline.imaging.execute(self.get_data_model())

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)

        queue_controller = self.get_queue_controller()
        queue_controller.connect(
            HWR.beamline.imaging, "collectImageTaken", self.image_taken
        )
        queue_controller.connect(
            HWR.beamline.imaging, "collectFailed", self.collect_failed
        )

        data_model = self.get_data_model()

        if data_model.get_parent():
            gid = data_model.get_parent().lims_group_id
            data_model.lims_group_id = gid

        HWR.beamline.imaging.pre_execute(self.get_data_model())

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        HWR.beamline.imaging.post_execute(self.get_data_model())

        queue_controller = self.get_queue_controller()
        queue_controller.disconnect(
            HWR.beamline.imaging, "collectImageTaken", self.image_taken
        )
        queue_controller.disconnect(
            HWR.beamline.imaging, "collectFailed", self.collect_failed
        )

    def stop(self):
        BaseQueueEntry.stop(self)
        HWR.beamline.imaging.stop_collect()

    def collect_failed(self, message):
        # this is to work around the remote access problem
        dispatcher.send("collect_finished")
        self.get_view().setText(1, "Failed")
        self.status = QUEUE_ENTRY_STATUS.FAILED
        logging.getLogger("queue_exec").error(message.replace("\n", " "))
        raise QueueExecutionException(message.replace("\n", " "), self)

    def image_taken(self, image_number):
        if image_number > 0:
            num_images = (
                self.get_data_model().acquisitions[0].acquisition_parameters.num_images
            )
            self.get_view().setText(1, str(image_number) + "/" + str(num_images))
