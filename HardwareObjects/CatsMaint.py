"""
CATS maintenance commands hardware object.

Functionality in addition to sample-transfer functionality: power control,
lid control, error-recovery commands, ...

Derived from Michael Hellmig's implementation for the BESSY CATS sample changer
 -add more controls, including Regulation Off, Gripper Dry/Open/Close, Reset Memory, Set Sample On Diff
 -add CATS dewar layout

Vicente Rey - add support for ISARA Model

"""
import logging

from HardwareRepository.TaskUtils import task
from HardwareRepository.BaseHardwareObjects import Equipment

import gevent
import time

from PyTango import DeviceProxy

__author__ = "Jie Nan"
__credits__ = ["The MxCuBE collaboration"]

__email__ = "jie.nan@maxlab.lu.se"
__status__ = "Alpha"

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
    "EMBL": TOOL_SPINE,
    "Rotat": TOOL_SPINE,
    "Plate": TOOL_PLATE,
    "Laser": TOOL_LASER,
    "Double": TOOL_DOUBLE_GRIPPER,
}


class CatsMaint(Equipment):

    __TYPE__ = "CATS"
    NO_OF_LIDS = 3

    """
    Actual implementation of the CATS Sample Changer, MAINTENANCE COMMANDS ONLY
    BESSY BL14.1 installation with 3 lids
    """

    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)

        self._state = None
        self._running = None
        self._powered = None
        self._toolopen = None
        self._message = None
        self._regulating = None
        self._lid1state = None
        self._lid2state = None
        self._lid3state = None
        self._charging = None

    def init(self):

        self.cats_device = DeviceProxy(self.tangoname)

        try:
            self.cats_model = self.cats_device.read_attribute("CatsModel").value
        except Exception:
            self.cats_model = "CATS"

        if self.is_isara():
            self.nb_of_lids = 1
        else:
            self.nb_of_lids = 3

        self._chnState = self.add_channel(
            {
                "type": "tango",
                "name": "_chnState",
                "tangoname": self.tangoname,
                "polling": 1000,
            },
            "State",
        )

        self._chnPathRunning = self.add_channel(
            {
                "type": "tango",
                "name": "_chnPathRunning",
                "tangoname": self.tangoname,
                "polling": 1000,
            },
            "PathRunning",
        )
        self._chnPowered = self.add_channel(
            {
                "type": "tango",
                "name": "_chnPowered",
                "tangoname": self.tangoname,
                "polling": 1000,
            },
            "Powered",
        )
        self._chnMessage = self.add_channel(
            {
                "type": "tango",
                "name": "_chnMessage",
                "tangoname": self.tangoname,
                "polling": 1000,
            },
            "Message",
        )
        self._chnToolOpenClose = self.add_channel(
            {
                "type": "tango",
                "name": "_chnToolOpenClose",
                "tangoname": self.tangoname,
                "polling": 1000,
            },
            "di_ToolOpen",
        )
        self._chnLN2Regulation = self.add_channel(
            {
                "type": "tango",
                "name": "_chnLN2Regulation",
                "tangoname": self.tangoname,
                "polling": 1000,
            },
            "LN2Regulating",
        )
        self._chnBarcode = self.add_channel(
            {
                "type": "tango",
                "name": "_chnBarcode",
                "tangoname": self.tangoname,
                "polling": 1000,
            },
            "Barcode",
        )

        self._chnLid1State = self.add_channel(
            {
                "type": "tango",
                "name": "_chnLid1State",
                "tangoname": self.tangoname,
                "polling": 1000,
            },
            "di_Lid1Open",
        )
        self._chnLid1State.connect_signal("update", self._update_lid1_state)

        if self.nb_of_lids > 1:
            self._chnLid2State = self.add_channel(
                {
                    "type": "tango",
                    "name": "_chnLid2State",
                    "tangoname": self.tangoname,
                    "polling": 1000,
                },
                "di_Lid2Open",
            )
            self._chnLid2State.connect_signal("update", self._update_lid2_state)

        if self.nb_of_lids > 2:
            self._chnLid3State = self.add_channel(
                {
                    "type": "tango",
                    "name": "_chnLid3State",
                    "tangoname": self.tangoname,
                    "polling": 1000,
                },
                "di_Lid3Open",
            )
            self._chnLid3State.connect_signal("update", self._update_lid3_state)

        self._chnState.connect_signal("update", self._update_state)
        self._chnPathRunning.connect_signal("update", self._update_running_state)
        self._chnPowered.connect_signal("update", self._update_powered_state)
        self._chnToolOpenClose.connect_signal("update", self._update_tool_state)
        self._chnMessage.connect_signal("update", self._update_message)
        self._chnLN2Regulation.connect_signal("update", self._update_regulation_state)
        self._chnBarcode.connect_signal("update", self._updateBarcode)

        self._chnCurrentTool = self.add_channel(
            {"type": "tango", "name": "_chnCurrentTool", "tangoname": self.tangoname},
            "Tool",
        )
        #
        self._cmdPowerOn = self.add_command(
            {"type": "tango", "name": "_cmdPowerOn", "tangoname": self.tangoname},
            "powerOn",
        )
        self._cmdPowerOff = self.add_command(
            {"type": "tango", "name": "_cmdPowerOff", "tangoname": self.tangoname},
            "powerOff",
        )
        self._cmdOpenTool = self.add_command(
            {"type": "tango", "name": "_cmdOpenTool", "tangoname": self.tangoname},
            "opentool",
        )
        self._cmdCloseTool = self.add_command(
            {"type": "tango", "name": "_cmdCloseTool", "tangoname": self.tangoname},
            "closetool",
        )
        self._cmdMagnetOn = self.add_command(
            {"type": "tango", "name": "_cmdMagnetOn", "tangoname": self.tangoname},
            "magnetOn",
        )
        self._cmdMagnetOff = self.add_command(
            {"type": "tango", "name": "_cmdMagnetOff", "tangoname": self.tangoname},
            "magnetOff",
        )

        # LIDs
        self._cmdOpenLid1 = self.add_command(
            {"type": "tango", "name": "_cmdOpenLid1", "tangoname": self.tangoname},
            "openlid1",
        )
        self._cmdCloseLid1 = self.add_command(
            {"type": "tango", "name": "_cmdCloseLid1", "tangoname": self.tangoname},
            "closelid1",
        )

        if self.nb_of_lids > 1:
            self._cmdOpenLid2 = self.add_command(
                {"type": "tango", "name": "_cmdOpenLid1", "tangoname": self.tangoname},
                "openlid2",
            )
            self._cmdCloseLid2 = self.add_command(
                {"type": "tango", "name": "_cmdCloseLid1", "tangoname": self.tangoname},
                "closelid2",
            )

        if self.nb_of_lids > 2:
            self._cmdOpenLid3 = self.add_command(
                {"type": "tango", "name": "_cmdOpenLid1", "tangoname": self.tangoname},
                "openlid3",
            )
            self._cmdCloseLid3 = self.add_command(
                {"type": "tango", "name": "_cmdCloseLid1", "tangoname": self.tangoname},
                "closelid3",
            )

        self._cmdRegulOn = self.add_command(
            {"type": "tango", "name": "_cmdRegulOn", "tangoname": self.tangoname},
            "regulon",
        )
        self._cmdRegulOff = self.add_command(
            {"type": "tango", "name": "_cmdRegulOff", "tangoname": self.tangoname},
            "reguloff",
        )

        self._cmdToolOpen = self.add_command(
            {"type": "tango", "name": "_cmdToolOpen", "tangoname": self.tangoname},
            "opentool",
        )
        self._cmdToolClose = self.add_command(
            {"type": "tango", "name": "_cmdToolClose", "tangoname": self.tangoname},
            "closetool",
        )

        # Paths
        self._cmdAbort = self.add_command(
            {"type": "tango", "name": "_cmdAbort", "tangoname": self.tangoname}, "abort"
        )
        self._cmdDry = self.add_command(
            {"type": "tango", "name": "_cmdDry", "tangoname": self.tangoname}, "dry"
        )
        self._cmdSafe = self.add_command(
            {"type": "tango", "name": "_cmdSafe", "tangoname": self.tangoname}, "safe"
        )
        self._cmdHome = self.add_command(
            {"type": "tango", "name": "_cmdHome", "tangoname": self.tangoname}, "home"
        )
        self._cmdSoak = self.add_command(
            {"type": "tango", "name": "_cmdSoak", "tangoname": self.tangoname}, "soak"
        )
        self._cmdBack = self.add_command(
            {"type": "tango", "name": "_cmdBack", "tangoname": self.tangoname}, "back"
        )
        self._cmdCalibration = self.add_command(
            {"type": "tango", "name": "_cmdCalibration", "tangoname": self.tangoname},
            "toolcalibration",
        )

        self._cmdClearMemory = self.add_command(
            {"type": "tango", "name": "_cmdClearMemory", "tangoname": self.tangoname},
            "clear_memory",
        )
        self._cmdReset = self.add_command(
            {"type": "tango", "name": "_cmdReset", "tangoname": self.tangoname}, "reset"
        )
        self._cmdResetParameters = self.add_command(
            {
                "type": "tango",
                "name": "_cmdResetParameters",
                "tangoname": self.tangoname,
            },
            "reset_parameters",
        )

        self._cmdRecoverFailure = self.add_command(
            {
                "type": "tango",
                "name": "_cmdRecoverFailure",
                "tangoname": self.tangoname,
            },
            "recoverFailure",
        )

        self._cmdResetMotion = self.add_command(
            {"type": "tango", "name": "_cmdResetMotion", "tangoname": self.tangoname},
            "resetmotion",
        )

        self._cmdSetOnDiff = self.add_command(
            {"type": "tango", "name": "_cmdSetOnDiff", "tangoname": self.tangoname},
            "setondiff",
        )
        self._cmdSetOnTool = self.add_command(
            {"type": "tango", "name": "_cmdSetOnTool", "tangoname": self.tangoname},
            "settool",
        )
        self._cmdSetOnTool2 = self.add_command(
            {"type": "tango", "name": "_cmdSetOnTool2", "tangoname": self.tangoname},
            "settool2",
        )

        self.state_actions = {
            "power": {
                "in_open": self._cmdPowerOn,
                "out_close": self._cmdPowerOff,
                "state": self._chnPowered,
            }
        }

    def is_isara(self):
        return self.cats_model == "ISARA"

    def is_cats(self):
        return self.cats_model != "ISARA"

    def get_current_tool(self):
        current_value = self._chnCurrentTool.get_value()

        tool = TOOL_TO_STR.get(current_value, None)

        return tool

    ################################################################################

    def back_traj(self):
        """
        Moves a sample from the gripper back into the dewar to its logged position.
        """
        return self._execute_task(False, self._do_back)

    def safe_traj(self):
        """
        Safely Moves the robot arm and the gripper to the home position
        """
        return self._execute_task(False, self._do_safe)

    def _do_abort(self):
        """
        Launch the "abort" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdAbort()

    def _do_home(self):
        """
        Launch the "abort" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        tool = self.get_current_tool()
        self._cmdHome(tool)

    def _do_reset(self):
        """
        Launch the "reset" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        logging.getLogger("HWR").debug("CatsMaint. doing reset")
        return
        self._cmdReset()

    def _do_reset_memory(self):
        """
        Launch the "reset memory" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdClearMemory()
        time.sleep(1)
        self._cmdResetParameters()
        time.sleep(1)

    def _do_reset_motion(self):
        """
        Launch the "reset_motion" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdResetMotion()

    def _do_recover_failure(self):
        """
        Launch the "recoverFailure" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdRecoverFailure()

    def _do_calibration(self):
        """
        Launch the "toolcalibration" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        tool = self.get_current_tool()
        self._cmdCalibration(tool)

    def _do_open_tool(self):
        """
        Launch the "opentool" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdOpenTool()

    def _do_close_tool(self):
        """
        Launch the "closetool" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._cmdCloseTool()

    def _do_dry_gripper(self):
        """
        Launch the "dry" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        tool = self.get_current_tool()
        self._cmdDry(tool)

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
            self._execute_server_task(self._cmdSetOnDiff, argin)

    def _do_back(self):
        """
        Launch the "back" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        tool = self.get_current_tool()
        argin = [str(tool), "0"]  # to send string array with two arg...
        self._execute_server_task(self._cmdBack, argin)

    def _do_safe(self):
        """
        Launch the "safe" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        argin = self.get_current_tool()
        self._execute_server_task(self._cmdSafe, argin)

    def _do_power_state(self, state=False):
        """
        Switch on CATS power if >state< == True, power off otherwise

        :returns: None
        :rtype: None
        """
        logging.getLogger("HWR").debug("   running power state command ")
        if state:
            self._cmdPowerOn()
        else:
            self._cmdPowerOff()

        self.do_state_action("power", state)

    def _do_enable_regulation(self):
        """
        Switch on CATS regulation

        :returns: None
        :rtype: None
        """
        self._cmdRegulOn()

    def _do_disable_regulation(self):
        """
        Switch off CATS regulation

        :returns: None
        :rtype: None
        """
        self._cmdRegulOff()

    def _do_lid1_state(self, state=True):
        """
        Opens lid 1 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._execute_server_task(self._cmdOpenLid1)
        else:
            self._execute_server_task(self._cmdCloseLid1)

    def _do_lid2_state(self, state=True):
        """
        Opens lid 2 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._execute_server_task(self._cmdOpenLid2)
        else:
            self._execute_server_task(self._cmdCloseLid2)

    def _do_lid3_state(self, state=True):
        """
        Opens lid 3 if >state< == True, closes the lid otherwise

        :returns: None
        :rtype: None
        """
        if state:
            self._execute_server_task(self._cmdOpenLid3)
        else:
            self._execute_server_task(self._cmdCloseLid3)

    def _do_magnet_on(self):
        self._execute_server_task(self._cmdMagnetOn)

    def _do_magnet_off(self):
        self._execute_server_task(self._cmdMagnetOff)

    def _do_tool_open(self):
        self._execute_server_task(self._cmdToolOpen)

    def _do_tool_close(self):
        self._execute_server_task(self._cmdToolClose)

    # ########################          PROTECTED          #########################

    def _execute_task(self, wait, method, *args):
        ret = self._run(method, wait=False, *args)
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
            raise exception
        return ret

    # ########################           PRIVATE           #########################

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

    def _updateBarcode(self, value):
        self._barcode = value
        self.emit("barcodeChanged", (value,))

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
            "abort": True,
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
            if tool in [TOOL_DOUBLE, TOOL_UNIPUCK]:
                args = [str(tool), str(lid)]
            else:
                raise Exception("Can SOAK only when UNIPUCK tool is mounted")

        if cmd_name == "back":
            if tool is not None:
                args = [tool, toolcal]
            else:
                raise Exception("Cannot detect type of TOOL in Cats. Command ignored")

        cmd = getattr(self.cats_device, cmd_name)

        try:
            if args is not None:
                if len(args) > 1:
                    ret = cmd(map(str, args))
                else:
                    ret = cmd(*args)
            else:
                ret = cmd()
            return ret
        except Exception as exc:
            import traceback

            traceback.print_exc()
            msg = exc[0].desc
            raise Exception(msg)


def test_hwo(hwo):
    print((hwo.get_current_tool()))
