import io

from mxcubecore.BaseHardwareObjects import Device
import math
import logging
import time
import gevent
from threading import Event, Thread
import base64
import array
import datetime
#import Image
import uuid
import numpy as np
from PIL import  Image as im
import psutil
import subprocess
from mxcubecore.utils.video_utils import streaming_processes


class MD2TimeoutError(Exception):
    pass


class BL19U1MD2Camera(Device):
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
        self.stream_hash = str(uuid.uuid1())
        print("stream hash:", self.stream_hash)

    def init(self):
        logging.getLogger("HWR").info("initializing camera object")
        self.specName = self.motor_name
        self.pollInterval = 100
        #self.pollInterval = 1000
        self._mpeg_scale = 1
        self._debug = False
        self._quality = 10
        self._current_stream_size = "-1, -1"

        self.image_attr = self.add_channel(
            {"type": "exporter", "name": "image"}, "ImageJPG"
        )

        if self.getProperty("interval"):
            self.pollInterval = self.getProperty("interval")
        self.stopper = False  # self.pollingTimer(self.pollInterval, self.poll)
        thread = Thread(target=self.poll)
        thread.daemon = True
        thread.start()
        #self.poll()

    def getImage(self):
        return self.image_attr.getValue()

    def poll(self):
        logging.getLogger("HWR").info("going to poll images")
        self.image_attr = self.add_channel(
            {"type": "exporter", "name": "image"}, "ImageJPG"
        )
        count = 1
        while not self.stopper:
            time.sleep(float(self.pollInterval) / 1000)
            # time.sleep(1)
            if count % 100 == 0:
                print("polling", datetime.datetime.now().strftime("%H:%M:%S.%f"))
            try:
                img = self.image_attr.get_value()
                #print(img)
                #img = self.image_attr.value
                imgArray = array.array("b", img)
                imgStr = imgArray.tobytes()
                # self.emit("imageReceived", self.imageaux,1360,1024)
                #self.emit("imageReceived", imgStr, 768, 576)
                #print(imgStr)


                #arr = np.array(imgArray)
                #img = im.open(io.BytesIO(imgArray))
                #img.save('1.jpg')

                self.emit("imageReceived", imgStr, 659, 493)
                count = count + 1
            except KeyboardInterrupt:
                self.connected = False
                self.stopper = True
                logging.getLogger("HWR").info("poll images stopped")
                return
            except Exception as ex:
                logging.getLogger("HWR").exception("Could not read image")
                self.image_attr = self.add_channel(
                    {"type": "exporter", "name": "image"}, "ImageJPG"
                )

    def get_available_stream_sizes(self):
        try:
            w = 659
            h = 453
            video_sizes = [(w, h)]
        except (ValueError, AttributeError):
            video_sizes = []
        return video_sizes

    def get_stream_size(self):
        current_size = self._current_stream_size.split(",")
        scale = float(current_size[0]) / self.get_width()
        return current_size + list((scale,))

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
        #return 768  # JN ,20140807,adapt the MD2 screen to mxCuBE2
        return 659

    def getHeight(self):
        #return 576  # JN ,20140807,adapt the MD2 screen to mxCuBE2
        return 493

    def setLive(self, state):
        self.liveState = state
        return True

    def imageType(self):
        return None

    def takeSnapshot(self, snapshot_filename, bw=True):
        img = self.image_attr.getValue()
        imgArray = array.array("b", img)
        imgStr = imgArray.tostring()
        f = open(snapshot_filename, "wb")
        f.write(imgStr)
        f.close()
        return True

    def get_snapshot_img_str(self):
        img = self.image_attr.getValue()
        imgArray = array.array("b", img)
        return imgArray.tostring()

    def start_video_stream_process(self):
        # import pdb; pdb.set_trace()
        if (not self._video_stream_process or self._video_stream_process.poll() is not None):
            # python_executable = os.sep.join(
            #     os.path.dirname(os.__file__).split(os.sep)[:-2] + ["bin", "python"]
            # )
            python_executable = "/home/mxcube19u1/anaconda3/envs/mxcubeweb/bin/python"

            self._video_stream_process = subprocess.Popen(
                [
                    python_executable,
                    streaming_processes.__file__,
                    self.getProperty("tangoname"),
                    "%s, %s" % (self.get_width(), self.get_height()),
                    self._current_stream_size,
                    self.stream_hash,
                    "rgb24",
                    "",
                    str(self._debug),
                    str(self.pollInterval / 1000.0),
                    str(self._quality)
                ],
                close_fds=True,
            )

            with open("/tmp/mxcube.pid", "a") as f:
                f.write("%s " % self._video_stream_process.pid)

    def stop_streaming(self):
        if self._video_stream_process:
            ps = [self._video_stream_process] + psutil.Process(
                self._video_stream_process.pid
            ).children()
            for p in ps:
                p.kill()
            self._video_stream_process = None

    def start_streaming(self, size=()):
        if not size:
            w, h = self.get_width(), self.get_height()
        else:
            w, h = size

        self.set_stream_size(w * self._mpeg_scale, h * self._mpeg_scale)
        self.start_video_stream_process()

        # return self.video_device

    def restart_streaming(self, size=()):
        self.stop_streaming()
        self.start_streaming(size)

    def _encoder_friendly_size(self, w, h):
        # Some video decoders have difficulties to decode videos with odd image dimensions
        # (JSMPEG beeing one of them) so we make sure that the size is even
        w = w if w % 2 == 0 else w + 1
        h = h if h % 2 == 0 else h + 1

        return w, h

    def set_stream_size(self, w, h):
        w, h = self._encoder_friendly_size(w, h)
        self._current_stream_size = "%s,%s" % (int(w), int(h))

    def get_width(self):
        return self.getWidth()

    def get_height(self):
        return self.getHeight()