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


class SampleCentringQueueEntry(BaseQueueEntry):
    """
    Entry for centring a sample
    """

    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)

    def __setstate__(self, d):
        self.__dict__.update(d)

    def __getstate__(self):
        d = dict(self.__dict__)
        d["move_kappa_phi_task"] = None
        return d

    def execute(self):
        BaseQueueEntry.execute(self)

        self.get_view().setText(1, "Waiting for input")
        log = logging.getLogger("user_level_log")

        data_model = self.get_data_model()

        kappa = data_model.get_kappa()
        kappa_phi = data_model.get_kappa_phi()

        # kappa and kappa_phi settings are applied first, and assume that the
        # beamline does have axes with exactly these names
        #
        # Other motor_positions are applied afterwards, but in random order.
        # motor_positions override kappa and kappa_phi if both are set
        #
        # Since setting one motor can change the position of another
        # (on ESRF ID30B setting kappa and kappa_phi changes the translation motors)
        # the order is important.
        dd0 = {}
        if kappa is not None:
            dd0["kappa"] = kappa
        if kappa_phi is not None:
            dd0["kappa_phi"] = kappa_phi
        if dd0:
            if (
                not hasattr(HWR.beamline.diffractometer, "in_kappa_mode")
                or HWR.beamline.diffractometer.in_kappa_mode()
            ):
                HWR.beamline.diffractometer.move_motors(dd0)

        motor_positions = dict(
            tt0
            for tt0 in data_model.get_other_motor_positions().items()
            if tt0[1] is not None
        )
        if motor_positions:
            HWR.beamline.diffractometer.move_motors(motor_positions)

        log.warning(
            "Please center a new or select an existing point and press continue."
        )
        self.get_queue_controller().pause(True)

        shapes = list(HWR.beamline.sample_view.get_selected_shapes())

        if shapes:
            pos = shapes[0]
            if hasattr(pos, "get_centred_position"):
                cpos = pos.get_centred_position()
            else:
                cpos = pos.get_centred_positions()[0]
        else:
            msg = "No centred position selected, using current position."
            log.info(msg)

            # Create a centred positions of the current position
            pos_dict = HWR.beamline.diffractometer.get_positions()
            cpos = queue_model_objects.CentredPosition(pos_dict)

        self._data_model.set_centring_result(cpos)

        self.get_view().setText(1, "Input accepted")

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)

    def post_execute(self):
        # If centring is executed once then we dont have to execute it again
        self.get_view().set_checkable(False)
        BaseQueueEntry.post_execute(self)

    def get_type_str(self):
        return "Sample centering"
