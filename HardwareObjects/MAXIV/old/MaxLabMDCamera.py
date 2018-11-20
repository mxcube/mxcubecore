"""Class for cameras connected to framegrabbers run by Taco Device Servers
"""
from HardwareRepository import BaseHardwareObjects
import logging
import os
import PyTango
import Image
import numpy as np

import qt

# try:
#  import Image
# except ImportError:
#  logging.getLogger("HWR").warning("PIL not available: cannot take snapshots")
#  canTakeSnapshots=False
# else:
#  canTakeSnapshots=True

MAX_TRIES = 3
SLOW_INTERVAL = 1000


class MaxLabMDCamera(BaseHardwareObjects.Device):
    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

    def _init(self):

        self.udiffVER_Ok = False
        self.badimg = 0
        self.pollInterval = 500
        self.connected = False

        try:
            self.device = PyTango.DeviceProxy(self.tangoname)
        except PyTango.DevFailed as traceback:
            last_error = traceback[-1]
            print "last error ", str(last_error)
            logging.getLogger("HWR").error(
                "%s: %s", str(self.name()), last_error["desc"]
            )

            self.device = BaseHardwareObjects.Null()
        else:
            self.setIsReady(True)

    def init(self):

        if self.device is not None:
            print "initializing camera object"

            self.pollingTimer = qt.QTimer()
            self.pollingTimer.connect(
                self.pollingTimer, qt.SIGNAL("timeout()"), self.poll
            )

            if self.getProperty("interval"):
                self.pollInterval = self.getProperty("interval")

            self.getChannelObject("UdiffVersion").connectSignal(
                "update", self.udiffVersionChanged
            )

    def udiffVersionChanged(self, value):

        print "udiff version is ", value
        if value == "MD2_2":
            print "start polling MD camera with poll interval=", self.pollInterval
            self.pollingTimer.start(self.pollInterval)
            # self.startPolling()
        else:
            print "stop polling the camera. This microdiff version does not support a camera"
            self.pollingTimer.stop()

    def connectToDevice(self):

        print "Connecting to camera device"

        try:
            cmds = self.device.command_list_query()
            self.connected = True
        except PyTango.ConnectionFailed:
            print "Microdiff DS not running or bad name in config"
            self.connected = False
        except BaseException:
            self.connected = False

        if "getImageJPG" in cmds:
            print "YES"
        else:
            print "NO"

        return self.connected

    def poll(self):

        if not self.connected:
            if not self.connectToDevice():
                self.pollingTimer.changeInterval(SLOW_INTERVAL)
                return
            else:
                self.pollingTimer.changeInterval(self.pollInterval)

        # print "reading the image"

        try:
            img = None
            img = self.device.getImageJPG()
            # JN, 20140807,adapt the MD2 screen (768x576) to mxCuBE2
            #          logging.getLogger('HWR').info("Img_chr dimension %s",img.shape)
            if img is not None:
                f = open("/tmp/mxcube_tmp.jpg", "w")
                f.write("".join(map(chr, img)))
                f.close()
                img_tmp = Image.open("/tmp/mxcube_tmp.jpg").crop((55, 42, 714, 535))
                img_tmp.save("/tmp/mxcube_crop.jpg")
                img = np.fromfile("/tmp/mxcube_crop.jpg", dtype="uint8")
        #               logging.getLogger('HWR').info("Img dimension2 %s",img.shape)

        #   print img
        #   print len(img)
        except PyTango.ConnectionFailed:
            self.connected = False
            return
        except BaseException:
            import traceback

            traceback.print_exc()

        if img is not None:
            if img.any():
                # JN,20140807,adapt the MD2 screen to mxCuBE2
                self.emit("imageReceived", img, 659, 493)
                if self.badimg > MAX_TRIES:
                    self.badimg = 0
            else:
                print "bad"
                self.badimg += 1

            if self.badimg > MAX_TRIES:
                print "seems too bad. polling with a slow interval now"
                self.pollingTimer.changeInterval(SLOW_INTERVAL)

    def imageUpdated(self, value):
        print "<HW> got new image"
        print value

    def gammaExists(self):
        return False

    def contrastExists(self):
        return False

    def brightnessExists(self):
        return False

    def gainExists(self):
        return False

    def getWidth(self):
        # return 768 #JN ,20140807,adapt the MD2 screen to mxCuBE2
        return 659

    def getHeight(self):
        # return 576 # JN ,20140807,adapt the MD2 screen to mxCuBE2
        return 493

    def setLive(self, state):
        self.liveState = state
        return True

    def imageType(self):
        return None

    def takeSnapshot(self, *args):
        # jpeg_data=self.device.GrabImage()
        jpeg_data = self.device.getImageJPG()

        # JN 20150206, have the same resolution as the one shown on the mxCuBE video
        f = open("/tmp/mxcube_tmpSnapshot.jpeg", "w")
        f.write("".join(map(chr, jpeg_data)))
        f.close()
        img_tmp = Image.open("/tmp/mxcube_tmpSnapshot.jpeg").crop((55, 42, 714, 535))
        img_tmp.save("/tmp/mxcube_cropSnapshot.jpeg")
        img = np.fromfile("/tmp/mxcube_cropSnapshot.jpeg", dtype="uint8")

        f = open(*(args + ("w",)))
        f.write("".join(map(chr, img)))
        f.close()
