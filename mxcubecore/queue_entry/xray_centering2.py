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
import logging

from mxcubecore import HardwareRepository as HWR
from mxcubecore.model import queue_model_objects

from mxcubecore.queue_entry.base_queue_entry import BaseQueueEntry

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class XrayCentering2QueueEntry(BaseQueueEntry):
    """
    Entry for X-ray centring (2022 version)
    """

    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)

    def execute(self):
        BaseQueueEntry.execute(self)
        HWR.beamline.xray_centring.execute()

    def pre_execute(self):
        """Pre-execute. Set to new motor position, if any"""
        BaseQueueEntry.pre_execute(self)
        logging.getLogger("user_level_log").info("Starting Xray centring, please wait.")

        data_model = self.get_data_model()

        motor_positions = dict(
            item
            for item in data_model.get_motor_positions().items()
            if item[1] is not None
        )
        pos_dict = {}
        for tag in ("kappa", "kappa_phi"):
            if tag in motor_positions:
                pos_dict[tag] = motor_positions.pop(tag)
        if pos_dict:
            # Some beamlines move centering motors while moving kappa, kappa_phi
            # Hence we need to move kappa, kappa_phi first.
            HWR.beamline.diffractometer.move_motors(pos_dict)
        if motor_positions:
            # Move the rest of the motors, if needed
            HWR.beamline.diffractometer.move_motors(motor_positions)

        HWR.beamline.xray_centring.pre_execute(self)

    def post_execute(self):
        """Post-execute. Store centring result in data model"""
        BaseQueueEntry.post_execute(self)

        # Create a centred position object of the current position
        # and put it in the data model for future access.
        pos_dict = HWR.beamline.diffractometer.get_positions()
        cpos = queue_model_objects.CentredPosition(pos_dict)
        self._data_model.set_centring_result(cpos)

        logging.getLogger("user_level_log").info("Finishing Xray centring")

        HWR.beamline.xray_centring.post_execute()

    def get_type_str(self):
        return "X-ray centring"
