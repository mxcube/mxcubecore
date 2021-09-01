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
from mxcubecore.HardwareObjects.base_queue_entry import  BaseQueueEntry
from mxcubecore import HardwareRepository as HWR


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "queue"


class GphlWorkflowQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        if data_model is None:
            raise ValueError("GphlWorkflowQueueEntry,data_model cannot be None")
        BaseQueueEntry.__init__(self, view, data_model)
        data_model.init_from_sample()

    def execute(self):
        BaseQueueEntry.execute(self)

        msg = "Starting workflow (%s), please wait." % (self.get_data_model()._type)
        logging.getLogger("user_level_log").info(msg)
        # TODO add parameter and data transfer.
        # workflow_params = self.get_data_model().params_list
        # Add the current node id to workflow parameters
        #group_node_id = self._parent_container._data_model._node_id
        #workflow_params.append("group_node_id")
        #workflow_params.append("%d" % group_node_id)
        HWR.beamline.gphl_workflow.execute()

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        HWR.beamline.gphl_workflow.pre_execute(self)
        logging.getLogger('HWR').debug(
            "Done GphlWorkflowQueueEntry.pre_execute"
        )

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        msg = "Finishing workflow %s" % (self.get_data_model()._type)
        logging.getLogger("user_level_log").info(msg)
        HWR.beamline.gphl_workflow.post_execute()

    def stop(self):
        BaseQueueEntry.stop(self)
        logging.getLogger("HWR").info("MXCuBE aborting current GPhL workflow")
        self.get_view().setText(1, 'Stopped')
