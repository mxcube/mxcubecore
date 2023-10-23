"""
  File:  BIOMAXCatsMaint.py

  Description:  This module implements the hardware object for the Biomax ISARA operation

"""
from mxcubecore.HardwareObjects.CatsMaint import CatsMaint
import logging


class BIOMAXCatsMaint(CatsMaint):
    def _updateGlobalState(self):
        state_dict, cmd_state, message = self.get_global_state()
        # handling the case of pin frozen to the puck base and the whole puck is lifted up
        if (
            message is not None
            and "the puck has been pulled out of its base" in message
        ):
            state_dict["state"] = "FAULT"
            state_dict["running"] = True
            logging.getLogger("HWR").error("[SC] Error %s" % message)
            logging.getLogger("user_level_log").error("[SC] Error %s" % message)
        self.emit("globalStateChanged", (state_dict, cmd_state, message))

    def get_cmd_info(self):
        """return information about existing commands for this object
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
            [
                "Abort",
                [
                    ["abort", "Abort", "Abort Execution of Command"],
                ],
            ],
        ]
        return cmd_list
