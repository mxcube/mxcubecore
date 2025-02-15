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

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.queue_entry.base_queue_entry import BaseQueueEntry

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class AdvancedConnectorQueueEntry(BaseQueueEntry):
    """Controls different steps"""

    def __init__(self, view=None, data_model=None, view_set_queue_entry=True):
        BaseQueueEntry.__init__(self, view, data_model, view_set_queue_entry)
        self.first_qe = None
        self.second_qe = None

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)

    def execute(self):
        BaseQueueEntry.execute(self)
        first_qe_data_model = self.first_qe.get_data_model()

        if first_qe_data_model.run_online_processing == "XrayCentering":
            best_positions = first_qe_data_model.online_processing_results[
                "aligned"
            ].get("best_positions", [])

            if len(best_positions) > 0:
                best_cpos = best_positions[0]["cpos"]
                helical_model = self.second_qe.get_data_model()

                # logging.getLogger("user_level_log").info(\
                #    "Moving to the best position")
                # HWR.beamline.diffractometer.move_motors(best_cpos)
                # gevent.sleep(2)

                logging.getLogger("user_level_log").info("Rotating 90 degrees")
                HWR.beamline.diffractometer.move_omega_relative(90)
                logging.getLogger("user_level_log").info("Creating a helical line")

                gevent.sleep(2)
                (
                    auto_line,
                    cpos_one,
                    cpos_two,
                ) = HWR.beamline.sample_view.create_auto_line()
                helical_model.acquisitions[
                    0
                ].acquisition_parameters.osc_start = cpos_one.phi
                helical_model.acquisitions[
                    0
                ].acquisition_parameters.centred_position = cpos_one
                helical_model.acquisitions[
                    1
                ].acquisition_parameters.centred_position = cpos_two

                self.second_qe.set_enabled(True)
            else:
                logging.getLogger("user_level_log").warning(
                    "No diffraction found. Cancelling Xray centering"
                )
                self.second_qe.set_enabled(False)
