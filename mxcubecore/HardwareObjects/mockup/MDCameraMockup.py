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

from HardwareRepository import HardwareRepository as HWR

MAX_TRIES = 3
SLOW_INTERVAL = 1000


class MDCameraMockup(BaseHardwareObjects.Device):
    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)

    def _init(self):
        self.stream_hash = "#"
        self.udiffVER_Ok = False
        self.badimg = 0
        self.pollInterval = 500
        self.connected = False
        self.image_name = self.get_property("image_name")
        xml_path = HWR.getHardwareRepository().server_address[0]
        self.image = os.path.join(xml_path, self.image_name)
        self.setIsReady(True)

    def init(self):
        logging.getLogger("HWR").info("initializing camera object")
        if self.get_property("interval"):
            self.pollInterval = self.get_property("interval")
        self.stopper = False  # self.polling_timer(self.pollInterval, self.poll)
        gevent.spawn(self.poll)

    def udiffVersionChanged(self, value):
        if value == "MD2_2":
            print(("start polling MD camera with poll interval=", self.pollInterval))
        else:
            print(
                "stop polling the camera. This microdiff version does not support a camera"
            )
            self.stopper = True

    def connectToDevice(self):
        self.connected = True
        return self.connected

    def poll(self):
        logging.getLogger("HWR").info("going to poll images")
        while not self.stopper:
            time.sleep(1)
            try:
                img = open(self.image, "rb").read()
                self.emit("imageReceived", img, 659, 493)
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

    def get_available_stream_sizes(self):
        return [(self.getWidth(), self.getHeight())]

    def get_stream_size(self):
        return self.getWidth(), self.getHeight(), 1
