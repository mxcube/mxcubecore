"""Class for cameras connected to framegrabbers run by Taco Device Servers
"""
from HardwareRepository import BaseHardwareObjects
import logging
import os
import gevent
import time
import numpy
from PIL import Image

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO


class CameraMockup(BaseHardwareObjects.Device):
    def __init__(self, name):
        BaseHardwareObjects.Device.__init__(self, name)
        self.liveState = False

    def _init(self):
        self.setIsReady(True)

    def init(self):
        self.imagegen = None

    def imageGenerator(self, delay):
        while True:
            newImage = self.getOneImage()
            self.emit("imageReceived", newImage, 650, 485)
            time.sleep(delay)

    def getOneImage(self):
        a = numpy.random.rand(485, 650) * 255
        im_out = Image.fromarray(a.astype("uint8")).convert("RGBA")
        buf = StringIO()
        im_out.save(buf, "JPEG")
        return buf

    def contrastExists(self):
        return False

    def brightnessExists(self):
        return False

    def gainExists(self):
        return False

    def setLive(self, live):
        print(("Setting camera live ", live))
        if live and self.liveState == live:
            return

        if live:
            self.imagegen = gevent.spawn(
                self.imageGenerator, (self.get_property("interval") or 500) / 1000.0
            )
            self.liveState = live
        else:
            self.imagegen.kill()
            self.liveState = live
        return True

    def imageType(self):
        return None

    def takeSnapshot(self, *args):
        jpeg_data = self.getOneImage()
        f = open(*(args + ("w",)))
        f.write("".join(map(chr, jpeg_data)))
        f.close()
