"""Class for cameras connected to framegrabbers run by Taco Device Servers
"""
from HardwareRepository import BaseHardwareObjects
import logging
import os
import PyTango

# try:
#  import Image
# except ImportError:
#  logging.getLogger("HWR").warning("PIL not available: cannot take snapshots")
#  canTakeSnapshots=False
# else:
#  canTakeSnapshots=True


class MicrodiffCamera(BaseHardwareObjects.Device):
    def _init(self):
        try:
            self.device = PyTango.DeviceProxy(self.tangoname)
        except PyTango.DevFailed as traceback:
            last_error = traceback[-1]
            logging.getLogger("HWR").error(
                "%s: %s", str(self.name()), last_error["desc"]
            )

            self.device = BaseHardwareObjects.Null()
        else:
            self.setIsReady(True)

    def takeSnapshot(self, *args):
        jpeg_data = self.device.GrabImage()
        f = open(*(args + ("w",)))
        f.write("".join(map(chr, jpeg_data)))
        f.close()
