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
[Name]
ALBACalibration

[Description]
HwObj used to grab the zoom/pixel size calibration from
PySignal simulator (TangoDS).


Example Hardware Object XML file :
==================================
<device class="ALBACalibration">
  <username>Calibration</username>
  <taurusname>bl13/ct/variables</taurusname>
  <channel type="sardana" name="calibx">OAV_PIXELSIZE_X</channel>
  <channel type="sardana" name="caliby">OAV_PIXELSIZE_Y</channel>
  <interval>200</interval>
  <threshold>0.001</threshold>
</device>
"""

from HardwareRepository import HardwareRepository as HWR
from HardwareRepository import BaseHardwareObjects
import logging

__author__ = "Jordi Andreu"
__credits__ = ["MXCuBE collaboration"]

__version__ = "2.2."
__maintainer__ = "Jordi Andreu"
__email__ = "jandreu[at]cells.es"
__status__ = "Draft"


class ALBACalibration(BaseHardwareObjects.Device):
    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

    def init(self):

        self.calibx = self.get_channel_object("calibx")
        self.caliby = self.get_channel_object("caliby")

        if self.calibx is not None and self.caliby is not None:
            logging.getLogger().info("Connected to pixel size calibration channels")

    def getCalibration(self):
        calibx = self.calibx.get_value()
        caliby = self.caliby.get_value()
        logging.getLogger().debug(
            "Returning calibration: x=%s, y=%s" % (calibx, caliby)
        )
        return [calibx, caliby]


def test():
    hwr = HWR.getHardwareRepository()
    hwr.connect()

    calib = hwr.get_hardware_object("/calibration")
    print("Calibration is: ", calib.getCalibration())


if __name__ == "__main__":
    test()
