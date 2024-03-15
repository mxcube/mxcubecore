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

import time
import logging

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
    QueueAbortedException,
)

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class GenericWorkflowQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.rpc_server_hwobj = None
        self.workflow_running = False
        self.workflow_started = False

    def execute(self):
        BaseQueueEntry.execute(self)

        workflow_hwobj = HWR.beamline.workflow

        # Start execution of a new workflow
        if str(workflow_hwobj.state.value) != "ON":
            # We are trying to start a new workflow and the Tango server is not idle,
            # therefore first abort any running workflow:
            workflow_hwobj.abort()
            if workflow_hwobj.command_failure():
                msg = (
                    "Workflow abort command failed! Please check workflow Tango server."
                )
                logging.getLogger("user_level_log").error(msg)
            else:
                # Then sleep three seconds for allowing the server to abort a running
                # workflow:
                time.sleep(3)
                # If the Tango server has been restarted the state.value is None.
                # If not wait till the state.value is "ON":
                if workflow_hwobj.state.value is not None:
                    while str(workflow_hwobj.state.value) != "ON":
                        time.sleep(0.5)

        msg = "Starting workflow (%s), please wait." % (self.get_data_model()._type)
        logging.getLogger("user_level_log").info(msg)
        workflow_params = self.get_data_model().params_list
        # Add the current node id to workflow parameters
        # group_node_id = self._parent_container._data_model._node_id
        # workflow_params.append("group_node_id")
        # workflow_params.append("%d" % group_node_id)
        workflow_hwobj.start(workflow_params)
        if workflow_hwobj.command_failure():
            msg = "Workflow start command failed! Please check workflow Tango server."
            logging.getLogger("user_level_log").error(msg)
            self.workflow_running = False
        else:
            self.workflow_running = True
            while workflow_hwobj.state.value == "RUNNING":
                time.sleep(1)

    def workflow_state_handler(self, state):
        if isinstance(state, tuple):
            state = str(state[0])
        else:
            state = str(state)

        if state == "ON":
            self.workflow_running = False
        elif state == "RUNNING":
            self.workflow_started = True
        elif state == "OPEN":
            msg = "Workflow waiting for input, verify parameters and press continue."
            logging.getLogger("user_level_log").warning(msg)
            self.get_queue_controller().show_workflow_tab()

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        qc = self.get_queue_controller()
        workflow_hwobj = HWR.beamline.workflow

        qc.connect(workflow_hwobj, "stateChanged", self.workflow_state_handler)

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        qc = self.get_queue_controller()
        workflow_hwobj = HWR.beamline.workflow
        qc.disconnect(workflow_hwobj, "stateChanged", self.workflow_state_handler)
        # reset state
        self.workflow_started = False
        self.workflow_running = False

        self.get_data_model().set_executed(True)
        self.get_data_model().set_enabled(False)

    def stop(self):
        BaseQueueEntry.stop(self)
        workflow_hwobj = HWR.beamline.workflow
        workflow_hwobj.abort()
        self.get_view().setText(1, "Stopped")
        raise QueueAbortedException("Queue stopped", self)
