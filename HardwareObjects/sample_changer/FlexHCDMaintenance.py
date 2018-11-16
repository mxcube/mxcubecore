"""
CATS maintenance mockup.
"""
import logging

from HardwareRepository.TaskUtils import *
from HardwareRepository.BaseHardwareObjects import Equipment

import gevent
import time

from PyTango import DeviceProxy


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


class FlexHCDMaintenance(Equipment):

    __TYPE__ = "FLEX_HCD"
    NO_OF_LIDS = 3

    """
    """

    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)

    def init(self):
        self._sc = self.getObjectByRole("sample_changer")

    def get_current_tool(self):
        return self._sc.get_gripper()

    def _doAbort(self):
        """
        Abort current command

        :returns: None
        :rtype: None
        """
        return self._sc._doAbort()

    def _doHome(self):
        """
        Abort current command

        :returns: None
        :rtype: None
        """
        self._sc._doAbort()
        return self._sc._doReset()

    def _doReset(self):
        """
        Reset sample changer

        :returns: None
        :rtype: None
        """
        self._sc._doReset()

    def _doDefreezeGripper(self):
        """
        :returns: None
        :rtype: None
        """
        self._sc.defreeze()

    def _doChangeGripper(self):
        """
        :returns: None
        :rtype: None
        """
        self._sc.change_gripper()

    def _doResetSampleNumber(self):
        """
        :returns: None
        :rtype: None
        """
        self._sc.reset_loaded_sample()

    def _updateGlobalState(self):
        state_dict, cmd_state, message = self.get_global_state()
        self.emit("globalStateChanged", (state_dict, cmd_state, message))

    def get_global_state(self):
        """
        """
        state = self._sc._readState()
        ready = self._sc._isDeviceBusy()
        running = state in ("RUNNING",)

        state_dict = {"running": running, "state": state}

        cmd_state = {
            "home": True,
            "defreeze": True,
            "reset_sample_number": True,
            "change_gripper": True,
            "abort": True,
        }

        message = ""

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
                "Actions",
                [
                    ["home", "Home", "Actions"],
                    ["defreeze", "Defreeze gripper", "Actions"],
                    ["reset_sample_number", "Reset sample number", "Actions"],
                    ["change_gripper", "Change Gripper", "Actions"],
                    ["abort", "Abort", "Actions"],
                ],
            ]
        ]
        return cmd_list

    def send_command(self, cmdname, args=None):
        tool = self.get_current_tool()

        if cmdname in ["home"]:
            self._doHome()
        if cmdname in ["defreeze"]:
            self._doDefreezeGripper()
        if cmdname in ["reset_sample_number"]:
            self._doResetSampleNumber()
        if cmdname == "change_gripper":
            self._doChangeGripper()
        if cmdname == "abort":
            self._doAbort()

        return True
