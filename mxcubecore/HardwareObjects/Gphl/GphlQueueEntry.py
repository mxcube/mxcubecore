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
from HardwareRepository.BaseHardwareObjects import HardwareObjectState
from HardwareRepository.HardwareObjects.base_queue_entry import (
    BaseQueueEntry,
    QueueAbortedException,
)
from HardwareRepository import HardwareRepository as HWR


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "queue"


class GphlWorkflowQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)

    def execute(self):
        BaseQueueEntry.execute(self)

        state = HWR.beamline.gphl_workflow.get_state()
        logging.getLogger("queue_exec").info(
            "GphlWorkflowQueueEntry.execute, WF_hwobj state is %s" % state
        )

        # Start execution of a new workflow
        if state != HardwareObjectState.READY:
            # TODO Add handling of potential conflicts.
            # NBNB GPhL workflow cannot have multiple users
            # unless they use separate persistence layers
            raise RuntimeError(
                "Cannot execute workflow - GphlWorkflow HardwareObject is not idle"
            )

        msg = "Starting workflow (%s), please wait." % (self.get_data_model()._type)
        logging.getLogger("user_level_log").info(msg)
        # TODO add parameter and data transfer.
        # workflow_params = self.get_data_model().params_list
        # Add the current node id to workflow parameters
        # group_node_id = self._parent_container._data_model._node_id
        # workflow_params.append("group_node_id")
        # workflow_params.append("%d" % group_node_id)
        HWR.beamline.gphl_workflow.execute()

    def parameter_query(self, field_list, return_parameters):
        msg = "Workflow waiting for input, verify parameters and press continue."
        logging.getLogger("user_level_log").warning(msg)
        self.get_queue_controller().show_workflow_tab()

    def pre_execute(self):
        state = HWR.beamline.gphl_workflow.get_state()
        if state in (HardwareObjectState.OFF, HardwareObjectState.READY):
            BaseQueueEntry.pre_execute(self)
            queue_controller = self.get_queue_controller()

            queue_controller.connect(
                HWR.beamline.gphl_workflow, "gphlParametersNeeded", self.parameter_query
            )

            HWR.beamline.gphl_workflow.pre_execute(self)

            logging.getLogger("HWR").debug("Done GphlWorkflowQueueEntry.pre_execute")
        else:
            raise ValueError(
                "Cannot start GPhL Worlkflow queue, Workflow state was: %s"
                % state.name
            )

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        queue_controller = self.get_queue_controller()
        msg = "Finishing workflow %s" % (self.get_data_model()._type)
        logging.getLogger("user_level_log").info(msg)
        HWR.beamline.gphl_workflow.workflow_end()
        queue_controller.disconnect(
            HWR.beamline.gphl_workflow, "gphlParametersNeeded", self.parameter_query
        )

    def stop(self):
        BaseQueueEntry.stop(self)
        logging.getLogger("queue_exec").debug("In GphlWorkflowQueueEntry.stop")
        HWR.beamline.gphl_workflow.abort()
        self.get_view().setText(1, "Stopped")
        raise QueueAbortedException("Queue stopped", self)
