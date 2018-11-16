#
from CatsMaint import CatsMaint

import logging
import time


class PX1CatsMaint(CatsMaint):
    def __init__(self, *args):
        CatsMaint.__init__(self, *args)
        self.home_opened = None

    def init(self):

        CatsMaint.init(self)

        self._chnHomeOpened = self.addChannel(
            {
                "type": "tango",
                "name": "_chnHomeOpened",
                "tangoname": self.tangoname,
                "polling": "events",
            },
            "homeOpened",
        )

        self._chnHomeOpened.connectSignal("update", self.update_home_opened)

        self._cmdDrySoak = self.addCommand(
            {"type": "tango", "name": "_cmdDrySoak", "tangoname": self.tangoname},
            "DryAndSoak",
        )

        self._cmdReset = self.addCommand(
            {"type": "tango", "name": "_cmdReset", "tangoname": self.tangoname},
            "ResetError",
        )

        self.cats_hwo = self.getObjectByRole("sample_changer")

    def update_home_opened(self, value):
        if value != self.home_opened:
            self.home_opened = value
            self._updateGlobalState()

    def get_global_state(self):
        state_dict, cmd_state, message = CatsMaint.get_global_state(self)
        state_dict["homeopen"] = self.home_opened
        return state_dict, cmd_state, message

    def _doHomeOpen(self, unload=False):
        if unload and self.loaded:
            logging.getLogger("HWR").debug("Unloading sample first")
            self.cats_hwo._doUnload()
            time.sleep(3)
            while self.cats_hwo._isDeviceBusy():
                time.sleep(0.3)

        logging.getLogger("HWR").debug("Running the home command (home/open) now")
        self._cmdHome()

    def _doDrySoak(self):
        self._cmdDrySoak()

    def _doReset(self):
        logging.getLogger("HWR").debug("PX1CatsMaint: executing the _doReset function")
        self._cmdReset()
