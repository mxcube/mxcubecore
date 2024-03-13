from mxcubecore.BaseHardwareObjects import HardwareObject
import logging
import time
import gevent
from threading import Thread
import array
import numpy as np


class MD2TimeoutError(Exception):
    pass


class BIOMAXMD3Camera(HardwareObject):
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
        super().__init__(name)
        self.set_is_ready(True)

    def init(self):
        logging.getLogger("HWR").info("initializing camera object")
        self.specName = self.motor_name
        self.pollInterval = 80

        self.image_attr = self.add_channel(
            {"type": "exporter", "name": "image"}, "ImageJPG"
        )

        # new attrs for the MD3 with extra camera options
        self.width = 680
        self.height = 512
        self.chan_zoom = self.add_channel(
            {"type": "exporter", "name": "ImageZoom"}, "ImageZoom"
        )
        self.roi_x = self.add_channel({"type": "exporter", "name": "RoiX"}, "RoiX")
        self.roi_y = self.add_channel({"type": "exporter", "name": "RoiY"}, "RoiY")
        self.roi_width = self.add_channel(
            {"type": "exporter", "name": "RoiWidth"}, "RoiWidth"
        )
        self.roi_height = self.add_channel(
            {"type": "exporter", "name": "RoiHeight"}, "RoiHeight"
        )
        self.set_camera_roi = self.add_command(
            {"type": "exporter", "name": "setCameraROI"}, "setCameraROI"
        )

        self.width = self.roi_width.get_value()
        self.height = self.roi_height.get_value()

        if self.get_property("interval"):
            self.pollInterval = self.get_property("interval")
        self.stopper = False  # self.polling_timer(self.pollInterval, self.poll)
        # if self.get_property("image_zoom"):
        try:
            self.zoom = float(self.get_property("image_zoom"))
            self.chan_zoom.set_value(self.zoom)
            self.width = self.roi_width.get_value() * self.zoom
            self.height = self.roi_height.get_value() * self.zoom
        except Exception:
            logging.getLogger("HWR").info("cannot set image zoom level")
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
                self.emit("imageReceived", imgStr, 1360, 1024)
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

    def stopPolling(self):
        self.stopper = True

    def startPolling(self):
        # assuming that it is already stop, more advances features with
        # threading.Event, Event.is_set...
        self.stopper = False
        thread.stop()
        thread = Thread(target=self.poll)
        thread.daemon = True
        thread.start()

    def setCameraRoi(self, x1, y1, x2, y2):
        """
        Configure the camera Region Of Interest.
        X1 (int): abscissa of top left corner
        Y1 (int): ordinate of top left corner
        X2 (int): abscissa of bottom right corner
        Y2 (int): ordinate of bottom right corner
        """
        try:
            self.set_camera_roi(x1, y1, x1, y2)
            self.width = x2 - x1
            self.height = y1 - y2
            return True
        except Exception:
            logging.getLogger("HWR").exception("Could not set image roi")
            return False

    def getCameraRoi(self):
        """
        Retrieve camera roi settings
        """
        try:
            return [
                self.roi_x.get_value(),
                self.roi_y.get_value(),
                self.roi_width.get_value(),
                self.roi_height.get_value(),
            ]
        except Exception:
            logging.getLogger("HWR").exception("Could not retrieve image roi settings")
            return False

    def getImageZoom(self):
        try:
            return self.zoom.get_value()
        except Exception as e:
            logging.getLogger("HWR").exception("Could not retrieve image zoom settings")
            return False

    def setImageZoom(self, new_zoom):
        try:
            return self.zoom.set_value(new_zoom)
        except Exception as e:
            logging.getLogger("HWR").exception("Could not retrieve image zoom settings")
            return False

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
        # return self.roi_width.get_value()
        return self.width

    def get_height(self):
        # return self.roi_height.get_value()
        return self.height

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
