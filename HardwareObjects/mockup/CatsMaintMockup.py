"""
CATS maintenance mockup.
"""
import logging

from mx3core.TaskUtils import task
from mx3core.BaseHardwareObjects import Equipment

import gevent
import time


__author__ = "Mikel Eguiraun"
__credits__ = ["The MxCuBE collaboration"]


TOOL_FLANGE, TOOL_UNIPUCK, TOOL_SPINE, TOOL_PLATE, TOOL_LASER, TOOL_DOUBLE_GRIPPER = (
    0,
    1,
    2,
    3,
    4,
    5,
)

TOOL_TO_STR = {
    "Flange": TOOL_FLANGE,
    "Unipuck": TOOL_UNIPUCK,
    "Rotat": TOOL_SPINE,
    "Plate": TOOL_PLATE,
    "Laser": TOOL_LASER,
    "Double": TOOL_DOUBLE_GRIPPER,
}


class CatsMaintMockup(Equipment):

    __TYPE__ = "CATS"
    NO_OF_LIDS = 3

    """
    Actual implementation of the CATS Sample Changer, MAINTENANCE COMMANDS ONLY
    BESSY BL14.1 installation with 3 lids
    """

    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)

        self._state = "READY"
        self._running = 0
        self._powered = 0
        self._toolopen = 0
        self._message = "Nothing to report"
        self._regulating = 0
        self._lid1state = 0
        self._lid2state = 0
        self._lid3state = 0
        self._charging = 0
        self._currenttool = 1

    def init(self):

        try:
            self.cats_model = self.cats_device.read_attribute("CatsModel").value
        except Exception:
            self.cats_model = "CATS"

    def get_current_tool(self):
        return self._currenttool

    ################################################################################
    def _do_abort(self):
        """
        Launch the "abort" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        pass

    def _do_reset(self):
        """
        Launch the "reset" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        pass

    def _do_dry_gripper(self):
        """
        Launch the "dry" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        pass

    def _do_set_on_diff(self, sample):
        """
        Launch the "setondiff" command on the CATS Tango DS, an example of sample value is 2:05

        :returns: None
        :rtype: None
        """

        if sample is None:
            raise Exception("No sample selected")
        else:
            str_tmp = str(sample)
            sample_tmp = str_tmp.split(":")
            # calculate CATS specific lid/sample number
            lid = (int(sample_tmp[0]) - 1) / 3 + 1
            puc_pos = ((int(sample_tmp[0]) - 1) % 3) * 10 + int(sample_tmp[1])
            argin = [str(lid), str(puc_pos), "0"]
            logging.getLogger().info("to SetOnDiff %s", argin)
            # self._execute_server_task(self._cmdSetOnDiff,argin)

    def _do_power_state(self, state=False):
        """
        Switch on CATS power if >state< == True, power off otherwise

        :returns: None
        :rtype: None
        """
        self._powered = state
        self._update_powered_state(state)

    def _do_enable_regulation(self):
        """
        Switch on CATS regulation

        :returns: None
        :rtype: None
        """
        self._regulating = True
        self._update_regulation_state(True)

    def _do_disable_regulation(self):
        """
        Switch off CATS regulation

        :returns: None
        :rtype: None
        """
        self._regulating = False
        self._update_regulation_state(False)

    def _do_lid1_state(self, state=True):
        """
        Opens lid 1 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        self._lid1state = state
        self._update_lid1_state(state)

    def _do_lid2_state(self, state=True):
        """
        Opens lid 2 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        self._lid2state = state
        self._update_lid2_state(state)

    def _do_lid3_state(self, state=True):
        """
        Opens lid 3 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        self._lid3state = state
        self._update_lid3_state(state)

    #########################          PROTECTED          #########################

    def _execute_task(self, wait, method, *args):
        ret = self._run(method, *args)
        if wait:
            return ret.get()
        else:
            return ret

    @task
    def _run(self, method, *args):
        exception = None
        ret = None
        try:
            ret = method(*args)
        except Exception as ex:
            exception = ex
        if exception is not None:
            raise exception  # pylint: disable-msg=E0702
        return ret

    #########################           PRIVATE           #########################

    def _update_running_state(self, value):
        self._running = value
        self.emit("runningStateChanged", (value,))
        self._update_global_state()

    def _update_powered_state(self, value):
        self._powered = value
        self.emit("powerStateChanged", (value,))
        self._update_global_state()

    def _update_tool_state(self, value):
        self._toolopen = value
        self.emit("toolStateChanged", (value,))
        self._update_global_state()

    def _update_message(self, value):
        self._message = value
        self.emit("messageChanged", (value,))
        self._update_global_state()

    def _update_regulation_state(self, value):
        self._regulating = value
        self.emit("regulationStateChanged", (value,))
        self._update_global_state()

    def _update_state(self, value):
        self._state = value
        self._update_global_state()

    def _update_lid1_state(self, value):
        self._lid1state = value
        self.emit("lid1StateChanged", (value,))
        self._update_global_state()

    def _update_lid2_state(self, value):
        self._lid2state = value
        self.emit("lid2StateChanged", (value,))
        self._update_global_state()

    def _update_lid3_state(self, value):
        self._lid3state = value
        self.emit("lid3StateChanged", (value,))
        self._update_global_state()

    def _update_operation_mode(self, value):
        self._charging = not value

    def _update_global_state(self):
        state_dict, cmd_state, message = self.get_global_state()
        self.emit("globalStateChanged", (state_dict, cmd_state, message))

    def get_global_state(self):
        """
           Update clients with a global state that
           contains different:

           - first param (state_dict):
               collection of state bits

           - second param (cmd_state):
               list of command identifiers and the
               status of each of them True/False
               representing whether the command is
               currently available or not

           - message
               a message describing current state information
               as a string
        """
        _ready = str(self._state) in ("READY", "ON")

        if self._running:
            state_str = "MOVING"
        elif not (self._powered) and _ready:
            state_str = "DISABLED"
        elif _ready:
            state_str = "READY"
        else:
            state_str = str(self._state)

        state_dict = {
            "toolopen": self._toolopen,
            "powered": self._powered,
            "running": self._running,
            "regulating": self._regulating,
            "lid1": self._lid1state,
            "lid2": self._lid2state,
            "lid3": self._lid3state,
            "state": state_str,
        }

        cmd_state = {
            "powerOn": (not self._powered) and _ready,
            "powerOff": (self._powered) and _ready,
            "regulon": (not self._regulating) and _ready,
            "openlid1": (not self._lid1state) and self._powered and _ready,
            "closelid1": self._lid1state and self._powered and _ready,
            "dry": (not self._running) and self._powered and _ready,
            "soak": (not self._running) and self._powered and _ready,
            "home": (not self._running) and self._powered and _ready,
            "back": (not self._running) and self._powered and _ready,
            "safe": (not self._running) and self._powered and _ready,
            "clear_memory": True,
            "reset": True,
            "abort": self._running,
        }

        message = self._message

        return state_dict, cmd_state, message

    def get_cmd_info(self):
        """ return information about existing commands for this object
           the information is organized as a list
           with each element contains
           [ cmd_name,  display_name, category ]
        """
        """ [cmd_id, cmd_display_name, nb_args, cmd_category, description ] """
        cmd_list = [
            [
                "Power",
                [
                    ["powerOn", "PowerOn", "Switch Power On"],
                    ["powerOff", "PowerOff", "Switch Power Off"],
                    ["regulon", "Regulation On", "Swich LN2 Regulation On"],
                ],
            ],
            [
                "Lid",
                [
                    ["openlid1", "Open Lid", "Open Lid"],
                    ["closelid1", "Close Lid", "Close Lid"],
                ],
            ],
            [
                "Actions",
                [
                    ["home", "Home", "Actions", "Home (trajectory)"],
                    ["dry", "Dry", "Actions", "Dry (trajectory)"],
                    ["soak", "Soak", "Actions", "Soak (trajectory)"],
                ],
            ],
            [
                "Recovery",
                [
                    [
                        "clear_memory",
                        "Clear Memory",
                        "Clear Info in Robot Memory "
                        " (includes info about sample on Diffr)",
                    ],
                    ["reset", "Reset Message", "Reset Cats State"],
                    ["back", "Back", "Reset Cats State"],
                    ["safe", "Safe", "Reset Cats State"],
                ],
            ],
            ["Abort", [["abort", "Abort", "Abort Execution of Command"]]],
        ]
        return cmd_list

    def _execute_server_task(self, method, *args):
        task_id = method(*args)
        ret = None
        # introduced wait because it takes some time before the attribute PathRunning is set
        # after launching a transfer
        # after setting refresh in the Tango DS to 0.1 s a wait of 1s is enough
        time.sleep(1.0)
        while str(self._chnPathRunning.get_value()).lower() == "true":
            gevent.sleep(0.1)
        ret = True
        return ret

    def send_command(self, cmd_name, args=None):

        #
        lid = 1
        toolcal = 0
        tool = self.get_current_tool()

        if cmd_name in ["dry", "safe", "home"]:
            if tool is not None:
                args = [tool]
            else:
                raise Exception("Cannot detect type of TOOL in Cats. Command ignored")

        if cmd_name == "soak":
            if tool in [TOOL_DOUBLE_GRIPPER, TOOL_UNIPUCK]:
                args = [str(tool), str(lid)]
            else:
                raise Exception("Can SOAK only when UNIPUCK tool is mounted")

        if cmd_name == "back":
            if tool is not None:
                args = [tool, toolcal]
            else:
                raise Exception("Cannot detect type of TOOL in Cats. Command ignored")

        if cmd_name == "powerOn":
            self._do_power_state(True)
        if cmd_name == "powerOff":
            self._do_power_state(False)

        if cmd_name == "regulon":
            self._do_enable_regulation()
        if cmd_name == "reguloff":
            self._do_disable_regulation()
        if cmd_name == "openlid1":
            self._do_lid1_state(True)
        if cmd_name == "closelid1":
            self._do_lid1_state(False)
        return True


def test_hwo(hwo):
    print((hwo.get_current_tool()))
