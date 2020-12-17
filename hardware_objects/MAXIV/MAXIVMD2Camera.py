from mx3core.BaseHardwareObjects import Device
import math
import logging
import time
import gevent
from threading import Event, Thread
import base64
import array


class MD2TimeoutError(Exception):
    pass


class MAXIVMD2Camera(Device):
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0, 1, 2, 3, 4, 5)
    EXPORTER_TO_MOTOR_STATE = {
        "Invalid": NOTINITIALIZED,
        "Fault": UNUSABLE,
        "Ready": READY,
        "Moving": MOVING,
        "Created": NOTINITIALIZED,
        "Initializing": NOTINITIALIZED,
        "Unknown": UNUSABLE,
        "LowLim": ONLIMIT,
        "HighLim": ONLIMIT,
    }

    def __init__(self, name):
        Device.__init__(self, name)
        self.set_is_ready(True)

    def init(self):
        logging.getLogger("HWR").info("initializing camera object")
        self.specName = self.motor_name
        self.pollInterval = 80

        self.image_attr = self.add_channel(
            {"type": "exporter", "name": "image"}, "ImageJPG"
        )

        if self.get_property("interval"):
            self.pollInterval = self.get_property("interval")
        self.stopper = False  # self.polling_timer(self.pollInterval, self.poll)
        thread = Thread(target=self.poll)
        thread.daemon = True
        thread.start()

    def getImage(self):
        return self.image_attr.get_value()

    def poll(self):
        logging.getLogger("HWR").info("going to poll images")
        self.image_attr = self.add_channel(
            {"type": "exporter", "name": "image"}, "ImageJPG"
        )
        while not self.stopper:
            time.sleep(float(self.pollInterval) / 1000)
            # time.sleep(1)
            # print "polling", datetime.datetime.now().strftime("%H:%M:%S.%f")
            try:
                img = self.image_attr.get_value()
                imgArray = array.array("b", img)
                imgStr = imgArray.tostring()
                # self.emit("imageReceived", self.imageaux,1360,1024)
                self.emit("imageReceived", imgStr, 768, 576)
            except KeyboardInterrupt:
                self.connected = False
                self.stopper = True
                logging.getLogger("HWR").info("poll images stopped")
                return
            except Exception:
                logging.getLogger("HWR").exception("Could not read image")
                self.image_attr = self.add_channel(
                    {"type": "exporter", "name": "image"}, "ImageJPG"
                )

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

    def get_width(self):
        return 768  # JN ,20140807,adapt the MD2 screen to mxCuBE2
        return 659

    def get_height(self):
        return 576  # JN ,20140807,adapt the MD2 screen to mxCuBE2
        return 493

    def set_live(self, state):
        self.liveState = state
        return True

    def imageType(self):
        return None

    def takeSnapshot(self, snapshot_filename, bw=True):
        img = self.image_attr.get_value()
        imgArray = array.array("b", img)
        imgStr = imgArray.tostring()
        f = open(snapshot_filename, "wb")
        f.write(imgStr)
        f.close()
        return True

    def get_snapshot_img_str(self):
        img = self.image_attr.get_value()
        imgArray = array.array("b", img)
        return imgArray.tostring()
