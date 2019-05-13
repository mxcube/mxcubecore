import logging

from HardwareRepository.HardwareObjects.queue_model_enumerables import States
from HardwareRepository.HardwareObjects.base_queue_entry import BaseQueueEntry, QueueAbortedException



class GphlWorkflowQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.workflow_hwobj = None
        self.workflow_running = False

    def execute(self):
        BaseQueueEntry.execute(self)

        state = self.workflow_hwobj.get_state()
        logging.getLogger("queue_exec").info(
            "GphlWorkflowQueueEntry.execute, WF_hwobj state is %s" % state
        )

        # Start execution of a new workflow
        if state != States.ON:
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
        self.workflow_hwobj.execute()

    def workflow_state_handler(self, state):
        if isinstance(state, tuple):
            state = str(state[0])
        else:
            state = str(state)

        if state == "ON":
            self.workflow_running = False
        elif state == "RUNNING":
            self.workflow_running = True
        elif state == "OPEN":
            msg = "Workflow waiting for input, verify parameters and press continue."
            logging.getLogger("user_level_log").warning(msg)
            self.get_queue_controller().show_workflow_tab()

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        queue_controller = self.get_queue_controller()
        self.workflow_hwobj = self.beamline_setup.getObjectByRole("gphl_workflow")

        queue_controller.connect(self.workflow_hwobj, "stateChanged", self.workflow_state_handler)

        self.workflow_hwobj.pre_execute(self)

        logging.getLogger("HWR").debug("Done GphlWorkflowQueueEntry.pre_execute")

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        queue_controller = self.get_queue_controller()
        msg = "Finishing workflow %s" % (self.get_data_model()._type)
        logging.getLogger("user_level_log").info(msg)
        self.workflow_hwobj.workflow_end()
        queue_controller.disconnect(self.workflow_hwobj, "stateChanged", self.workflow_state_handler)

    def stop(self):
        BaseQueueEntry.stop(self)
        logging.getLogger("queue_exec").debug("In GphlWorkflowQueueEntry.stop")
        self.workflow_hwobj.abort()
        self.get_view().setText(1, "Stopped")
        raise QueueAbortedException("Queue stopped", self)
