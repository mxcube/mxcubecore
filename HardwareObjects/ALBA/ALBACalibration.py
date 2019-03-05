#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
[Name] ALBACalibration

[Description]
HwObj used to grab the zoom/pixel size calibration from
PySignal simulator (TangoDS).

[Signals]
"""

from __future__ import print_function

import logging
from HardwareRepository import BaseHardwareObjects

__credits__ = ["ALBA Synchrotron"]
__version__ = "2.3"
__category__ = "General"


class ALBACalibration(BaseHardwareObjects.Device):

    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)
        self.chan_calib_x = None
        self.chan_calib_y = None

    def init(self):

        self.chan_calib_x = self.getChannelObject("calibx")
        self.chan_calib_y = self.getChannelObject("caliby")

        if self.chan_calib_x is not None and self.chan_calib_y is not None:
            logging.getLogger().info("Connected to pixel size calibration channels")

    def get_calibration(self):
        calib_x = self.chan_calib_x.getValue()
        calib_y = self.chan_calib_y.getValue()
        logging.getLogger().debug("Calibration: x = %s, y = %s" % (calib_x, calib_y))
        return [calib_x, calib_y]


def test_hwo(hwo):
    print("Calibration is: ", hwo.get_calibration())
