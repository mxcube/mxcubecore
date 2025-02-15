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
Module contains Gphl specific queue entries
"""

import logging

from mxcubecore import HardwareRepository as HWR
from mxcubecore.queue_entry.base_queue_entry import BaseQueueEntry

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "queue"


class GphlWorkflowQueueEntry(BaseQueueEntry):
    def execute(self):
        BaseQueueEntry.execute(self)

        msg = "Starting GΦL workflow (%s), please wait." % (
            self.get_data_model().strategy_name
        )
        logging.getLogger("user_level_log").info(msg)
        HWR.beamline.gphl_workflow.execute()

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        if not HWR.beamline.gphl_workflow.is_ready():
            logging.getLogger("user_level_log").warning(
                "WARNING: GΦL workflow was not ready - cleaning up"
            )
            HWR.beamline.gphl_workflow.post_execute()
        HWR.beamline.gphl_workflow.pre_execute(self)
        logging.getLogger("HWR").debug("Done GphlWorkflowQueueEntry.pre_execute")

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        msg = "Finishing GΦL workflow (%s)" % (self.get_data_model().strategy_name)
        logging.getLogger("user_level_log").info(msg)
        HWR.beamline.gphl_workflow.post_execute()

    def stop(self):
        HWR.beamline.gphl_workflow.workflow_aborted("Dummy", "Dummy")
        BaseQueueEntry.stop(self)
        logging.getLogger("HWR").info("MXCuBE aborting current GΦL workflow")
        self.get_view().setText(1, "Stopped")
