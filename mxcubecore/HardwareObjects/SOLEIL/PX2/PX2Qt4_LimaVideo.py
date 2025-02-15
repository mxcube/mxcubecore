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
Qt4_LimaVideo

[Description]
HwObj used to grab images via LImA library or Lima Tango server.

[Configuration]
See example below.  To select between "Library" or "Tango" simply
use and configure the field <address> (for Library)
or <tangoname> (for Tango)
in the XML file.


Example Hardware Object XML file :
==================================
<object class="Qt4_LimaVideo">
   <type>basler</type>
   <encoding>yuv422p</encoding>
   <address>84.89.227.6</address>
   <gain>0.5</gain>
   <exposure>0.01</exposure>
   <mirror>(False, False)</mirror>
   <interval>30</interval>
</object>
"""

import logging
import os
import struct
import time

from mxcubecore.HardwareObjects.QtLimaVideo import QtLimaVideo

try:
    from Lima import Core
except Exception:
    pass

try:
    from Lima import Prosilica
except ImportError as e:
    pass

try:
    from Lima import Basler
except ImportError as e:
    pass


class PX2Qt4_LimaVideo(QtLimaVideo):
    default_exposure_time = 0.5

    def init(self):
        exposure_time = self.get_property("exposure_time")

        if exposure_time is not None:
            self.exposure_time = float(exposure_time)
        else:
            self.exposure_time = self.default_exposure_time

        QtLimaVideo.init(self)

    def set_cam_encoding(self, set_cam_encoding):
        if cam_encoding == "yuv422p":
            self.video.setMode(Core.YUV422)
            self.decoder = self.yuv_2_rgb
        elif cam_encoding == "y8":
            self.video.setMode(Core.Y8)
            self.decoder = self.y8_2_rgb
        elif cam_encoding == "y16":
            self.video.setMode(Core.Y16)

    def get_image(self):
        image = self.video.getLastImage()
        raw_buffer = image.buffer()
        return raw_buffer, image.width(), image.height()

    def set_exposure_time(self, exposure_time):
        was_live = False
        print("Setting exposure to %s" % exposure_time)
        if self.get_video_live():
            was_live = True
            self.set_video_live(False)
            print("Stopped")

        self.video.setExposure(exposure_time)

        if was_live:
            print("Starting")
            self.set_video_live(True)


def test_hwo():
    import time

    from mxcubecore import HardwareRepository as HWR
    from mxcubecore.utils.qt_import import *

    hwr = HWR.get_hardware_repository()
    hwr.connect()

    hwo = hwr.get_hardware_object("/singleton_objects/limavideo")

    print("Image dimensions: ", hwo.get_image_dimensions())
    print("Live Mode: ", hwo.get_video_live())

    app = QApplication([])

    win = QMainWindow()
    lab = QLabel("toto")

    print("Image dimensions: ", hwo.get_image_dimensions())
    hwo.set_video_live(True)
    hwo.set_exposure_time(0.05)
    time.sleep(1)

    qimg = hwo.get_new_image()
    px = QPixmap(qimg)

    px = px.scaled(QSize(px.width() * 0.5, px.height() * 0.5))

    lab.setPixmap(px)
    win.setCentralWidget(lab)
    win.show()
    app.exec_()


if __name__ == "__main__":
    test_hwo()
