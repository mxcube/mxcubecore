"""Class for cameras connected to framegrabbers run by Taco Device Servers
"""
from HardwareRepository import BaseHardwareObjects
import logging
import os
import time
import datetime
from PIL import Image
import numpy as np
from threading import Event, Thread
import base64
import gevent

MAX_TRIES = 3
SLOW_INTERVAL = 1000


class MDCameraMockup(BaseHardwareObjects.Device):
    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

    def _init(self):
        self.udiffVER_Ok = False
        self.badimg = 0
        self.pollInterval = 500
        self.connected = False
        self.image_name = self.getProperty("image_name")
        cwd = os.getcwd()
        path = os.path.join(cwd, "./test/HardwareObjectsMockup.xml/")
        self.image = os.path.join(path, self.image_name)
        self.setIsReady(True)

    def init(self):
        logging.getLogger("HWR").info("initializing camera object")
        # self.pollingTimer = qt.QTimer()
        # self.pollingTimer.connect(self.pollingTimer, qt.SIGNAL("timeout()"), self.poll)
        if self.getProperty("interval"):
            self.pollInterval = self.getProperty("interval")
        self.stopper = False  # self.pollingTimer(self.pollInterval, self.poll)
        thread = Thread(target=self.poll)
        thread.daemon = True
        thread.start()

    def udiffVersionChanged(self, value):
        if value == "MD2_2":
            print(("start polling MD camera with poll interval=", self.pollInterval))
            # self.pollingTimer.start(self.pollInterval)
            # self.startPolling()
        else:
            print("stop polling the camera. This microdiff version does not support a camera")
            # self.pollingTimer.stop()
            self.stopper = True

    def connectToDevice(self):
        self.connected = True
        return self.connected

    # @timer.setInterval(self.pollInterval)
    def poll(self):
        logging.getLogger("HWR").info("going to poll images")
        while not self.stopper:
            # time.sleep(float(self.pollInterval)/1000)
            time.sleep(1)
            # print "polling", datetime.datetime.now().strftime("%H:%M:%S.%f")
            try:
                img = open(self.image, "rb").read()
                # img = base64.b64encode(img)
                self.emit("imageReceived", img, 659, 493)
                # logging.getLogger("HWR").info( "polling images")
            except KeyboardInterrupt:
                self.connected = False
                self.stopper = True
                logging.getLogger("HWR").info("poll images stopped")
                return
            except BaseException:
                logging.getLogger("HWR").exception("Could not read image")

    def imageUpdated(self, value):
        print("<HW> got new image")
        print(value)

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

    def takeSnapshot(self, snapshot_filename, bw=True):
        return True
