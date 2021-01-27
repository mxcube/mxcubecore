#
from mxcubecore.hardware_objects.CatsMaint import CatsMaint
from mxcubecore import HardwareRepository as HWR

import logging
import time


class PX1CatsMaint(CatsMaint):
    def __init__(self, *args):
        CatsMaint.__init__(self, *args)
        self.home_opened = None

    def init(self):

        CatsMaint.init(self)

        self._chnHomeOpened = self.add_channel(
            {
                "type": "tango",
                "name": "_chnHomeOpened",
                "tangoname": self.tangoname,
                "polling": "events",
            },
            "homeOpened",
        )

        self._chnHomeOpened.connect_signal("update", self.update_home_opened)

        self._cmdDrySoak = self.add_command(
            {"type": "tango", "name": "_cmdDrySoak", "tangoname": self.tangoname},
            "DryAndSoak",
        )

        self._cmdReset = self.add_command(
            {"type": "tango", "name": "_cmdReset", "tangoname": self.tangoname},
            "ResetError",
        )

    def update_home_opened(self, value):
        if value != self.home_opened:
            self.home_opened = value
            self._update_global_state()

    def get_global_state(self):
        state_dict, cmd_state, message = CatsMaint.get_global_state(self)
        state_dict["homeopen"] = self.home_opened
        return state_dict, cmd_state, message

    def _do_home_open(self, unload=False):
        if unload and self.loaded:
            logging.getLogger("HWR").debug("Unloading sample first")
            self.cats_hwo._do_unload()
            time.sleep(3)
            while HWR.beamline.sample_changer._is_device_busy():
                time.sleep(0.3)

        logging.getLogger("HWR").debug("Running the home command (home/open) now")
        self._cmdHome()

    def _do_dry_soak(self):
        self._cmdDrySoak()

    def _do_reset(self):
        logging.getLogger("HWR").debug("PX1CatsMaint: executing the _do_reset function")
        self._cmdReset()
