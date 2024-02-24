# encoding: utf-8
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

__copyright__ = """ Copyright © 2010 - 2023 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


import sys
import time
from PIL import Image

sys.path.append("/opt/dectris/albula/4.0/python/")

from mxcubecore.BaseHardwareObjects import HardwareObject

try:
    from dectris import albula
except:
    print("albula module not found")


class P11AlbulaView(HardwareObject):

    default_interval = 0.5  # secs
    stoptimer = -1.0

    def init(self):

        self.alive = False
        self.stream = False
        self.viewer = None
        self.subframe = None

        interval = self.get_property("update_interval")

        self.interval = interval is not None and interval or self.default_interval

        self.mask_4m = None
        self.mask_16m = None

        mask_path_4m = self.get_property("mask_4m")
        mask_path_16m = self.get_property("mask_16m")

        self.eigerMonitor = None
        self.eigerThread = None

        if parent is not None and hasattr(parent, "eigerThread"):
            try:
                prop = parent.eigerThread.proxyMonitor.get_property("Host")["Host"]
            except:
                pass
            else:
                self.eigerMonitor = albula.DEigerMonitor(prop[0])
                self.eigerThread = parent.eigerThread

        try:
            mask_tif_4m = Image.open(mask_path_4m)
            mask_tif_16m = Image.open(mask_path_16m)
        except:
            pass
        else:
            mask_array_4m = np.asarray(mask_tif_4m)
            mask_array_16m = np.asarray(mask_tif_16m)

            self.mask_4m = albula.DImage(mask_array_4m)
            self.mask_16m = albula.DImage(mask_array_16m)

    def start(self, path=None, filetype=None, interval=None, stream=False):
        if filetype is not None:
            self.filetype = filetype
        if interval is not None:
            self.interval = interval
        self.stream = stream
        self.stoptimer = -1

        # HDF5
        self.eigerThread.setMonitorMode("enabled")
        if stream:
            self.eigerThread.setMonitorDiscardNew(False)
        else:
            self.eigerThread.clearMonitorBuffer()
            self.eigerThread.setMonitorDiscardNew(True)

        super().start()

    def stop(self, interval=0.0):

        if self.stoptimer < 0.0 and interval > 0.0:
            self.stoptimer = interval
            return

        print("Live view thread: Stopping thread")
        self.alive = False
        self.wait()  # waits until run stops on his own

    def check_app(self):
        try:
            self.subframe.setOffsetX(0)
        except BaseException as e:
            self.subframe = None

        if self.subframe is None:
            try:
                self.viewer.enableClose()
            except BaseException as e:
                self.viewer = None

        if self.viewer is None:
            self.viewer = albula.openMainFrame()

        if self.subframe is None:
            self.subframe = self.viewer.openSubFrame()

    def run(self):
        self.alive = True

        while self.alive:

            # hdf5
            wavelength = 12398.4 / energy

            try:
                energy = self.eigerThread.photonEnergy
                detector_distance = self.eigerThread.proxyEiger.read_attribute(
                    "DetectorDistance"
                ).value
                beam_center_x = self.eigerThread.proxyEiger.read_attribute(
                    "BeamCenterX"
                ).value
                beam_center_y = self.eigerThread.proxyEiger.read_attribute(
                    "BeamCenterY"
                ).value
            except:
                detector_distance = 1.0
                beam_center_x = 2074
                beam_center_y = 2181

            # get latest file from reveiver
            timestamp = time.time()
            if self.stream:
                try:
                    img = self.eigerMonitor.next()
                except:
                    time.sleep(0.1)
                    if self.stoptimer > 0:
                        self.stoptimer -= 0.1
                        if self.stoptimer <= 0.0:
                            self.stoptimer = -1.0
                            self.alive = False
                    continue
            else:
                try:
                    img = self.eigerMonitor.monitor()
                    self.eigerThread.clearMonitorBuffer()
                except:
                    print(sys.exc_info())
                    continue

            # display image
            img.optionalData().set_wavelength(wavelength)
            img.optionalData().set_detector_distance(detector_distance)
            img.optionalData().set_beam_center_x(beam_center_x)
            img.optionalData().set_beam_center_y(beam_center_y)
            img.optionalData().set_x_pixel_size(0.000075)
            img.optionalData().set_y_pixel_size(0.000075)

            if self.eigerMask16M is not None and img.width() == 4148:
                img.optionalData().set_pixel_mask(mask_16m)
            elif self.eigerMask4M is not None and img.width() == 2068:
                img.optionalData().set_pixel_mask(mask_4m)

            self.check_app()

            self.subframe.hideResolutionRings()
            self.subframe.loadImage(img)
            self.subframe.showResolutionRings()

            # wait interval / check if stop requested
            interval = time.time() - timestamp
            if self.stoptimer > 0:
                self.stoptimer -= interval
                if self.stoptimer <= 0.0:
                    self.stoptimer = -1.0
                    self.alive = False

            if self.stream:
                time.sleep(0.1)
                continue

            # sleep for self.interval and check stop in between
            while interval < self.interval and self.alive:
                if self.stoptimer > 0.0:
                    self.stoptimer -= 0.05
                    if self.stoptimer <= 0.0:
                        self.stoptimer = -1.0
                        self.alive = False
                time.sleep(0.05)
                interval += 0.05

        # end hdf5

        print("Live view thread: Thread for Live view died")
        self.alive = False

        if interval is not None:
            self.interval = interval


if __name__ == "__main__":

    lv = LiveView()
    lv.start()
    time.sleep(200)
    lv.stop()
