"""
Class for cameras connected by EPICS Area Detector
"""
import os
import logging
import gevent
from io import BytesIO
from threading import Thread

from PIL import Image
import numpy as np

from HardwareRepository import BaseHardwareObjects

CAMERA_DATA = "epicsCameraSample_data"
CAMERA_BACK = "epicsCameraSample_back"
CAMERA_EN_BACK = "epicsCameraSample_en_back"
CAMERA_ACQ_START = "epicsCameraSample_acq_start"
CAMERA_ACQ_STOP = "epicsCameraSample_acq_stop"
CAMERA_GAIN = "epicsCameraSample_gain"
CAMERA_GAIN_RBV = "epicsCameraSample_gain_rbv"
CAMERA_AUTO_GAIN = "epicsCameraSample_auto_gain"
CAMERA_AUTO_GAIN_RBV = "epicsCameraSample_auto_gain_rbv"
CAMERA_FPS_RBV = "epicsCameraSample_frames_per_second_rbv"
CAMERA_ACQ_TIME = "epicsCameraSample_acq_time"
CAMERA_ACQ_TIME_RBV = "epicsCameraSample_acq_time_rbv"
CAMERA_IMG_PIXEL_SIZE = "epicsCameraSample_img_pixel_size"
CAMERA_IMG_WIDTH = "epicsCameraSample_img_width"
CAMERA_IMG_HEIGHT = "epicsCameraSample_img_height"

class LNLSCamera(BaseHardwareObjects.Device):

    def __init__(self,name):
        BaseHardwareObjects.Device.__init__(self,name)
        self.liveState = False
        self.refreshing = False
        self.imagegen = None
        self.refreshgen = None
        self.imgArray = None
        self.qImage = None
        self.qImageHalf = None
        self.delay = None
        self.array_size = None
        # Status (cam is getting images)
        # This flag makes errors to be printed only when needed in the log,
        # which prevents the log file to get gigantic.
        self._print_cam_sucess = True
        self._print_cam_error = True

    def _init(self):
        self.setIsReady(True)

    def init(self):
        self.pixel_size = self.get_pixel_size()
        self.width = self.get_width()
        self.height = self.get_height()
        self.array_size = self.get_array_size()
        # Start camera image acquisition
        self.setLive(True)
        # Snapshot
        self.centring_status = {"valid": False}
        self.snapshots_procedure = None

    def poll(self):
        logging.getLogger("HWR").debug('LNLS Camera image acquiring has started.')
        self.imageGenerator(self.delay)

    def imageGenerator(self, delay):
        while self.liveState:
            self.getCameraImage()
            gevent.sleep(delay)
        logging.getLogger("HWR").debug('LNLS Camera image acquiring has stopped.')

    def getCameraImage(self):
        # Get the image from uEye camera IOC
        self.imgArray = self.get_channel_value(CAMERA_DATA)
        if self.imgArray is None:
            if self._print_cam_error:
                logging.getLogger("HWR").error("%s - Error: null camera image!" % (self.__class__.__name__))
                self._print_cam_sucess = True
                self._print_cam_error = False
            # Return error for this frame, but cam remains live for new frames
            return -1

        if len(self.imgArray) != self.array_size:
            if self._print_cam_error:
                logging.getLogger("HWR").error(\
                "%s - Error in array lenght! Expected %d, but got %d." % \
                (self.__class__.__name__, self.array_size, len(self.imgArray)))
                self._print_cam_sucess = True
                self._print_cam_error = False
            # Return error for this frame, but cam remains live for new frames
            return -1

        if self.refreshing:
            logging.getLogger("user_level_log").info("Camera was refreshed!")
            self.refreshing = False

        try:
            # Get data
            data = self.imgArray
            arr = np.array(data).reshape(self.height, self.width, self.pixel_size)
            # Convert data to rgb image
            img = Image.fromarray(arr)
            #img_rot = img.rotate(angle=0, expand=True)
            img_rgb = img.convert('RGB')
            # Get binary image
            with BytesIO() as f:
                img_rgb.save(f, format='JPEG')
                f.seek(0)
                img_bin_str = f.getvalue()
            # Sent image to gui
            self.emit("imageReceived", img_bin_str, self.height, self.width)
            #logging.getLogger("HWR").debug('Got camera image: ' + \
            #str(img_bin_str[0:10]))
        except:
            if self._print_cam_error:
                logging.getLogger("user_level_log").error('Error while formatting camera image')
                self._print_cam_sucess = True
                self._print_cam_error = False

        if self._print_cam_sucess:
            logging.getLogger("HWR").info("LNLSCamera is emitting images! Cam routine is ok.")
            self._print_cam_sucess = False
            self._print_cam_error = True
        return 0

    def get_pixel_size(self):
        pixel_size = 1
        try:
            pixel_size = self.get_channel_value(CAMERA_IMG_PIXEL_SIZE)
            if pixel_size is None or pixel_size <= 0:
                pixel_size = 1
        except:
            print("Error on getting camera pixel size.")
        finally:
            logging.getLogger("HWR").info("LNLSCamera pixel size is %d." % (pixel_size))
            return pixel_size

    def get_width(self):
        width = 0
        try:
            width = self.get_channel_value(CAMERA_IMG_WIDTH)
            if width is None:
                width = 0
        except:
            print("Error on getting camera width.")
        finally:
            logging.getLogger("HWR").info("LNLSCamera width is %d." % (width))
            return width

    def get_height(self):
        height = 0
        try:
            height = self.get_channel_value(CAMERA_IMG_HEIGHT)
            if height is None:
                height = 0
        except:
            print("Error on getting camera height.")
        finally:
            logging.getLogger("HWR").info("LNLSCamera height is %d." % (height))
            return height

    def get_array_size(self):
        array_size = -1
        try:
            pixel_size = self.get_pixel_size()
            width = self.get_width()
            height = self.get_height()
            array_size = pixel_size * width * height
        except:
            print("Error on getting camera array size.")
        return array_size

    def getStaticImage(self):
        pass
        #qtPixMap = QtGui.QPixmap(self.source, "1")
        #self.emit("imageReceived", qtPixMap)

    def get_image_dimensions(self):
        return (640*512)

    def getWidth(self):
        # X
        return 640

    def getHeight(self):
        # Z
        return 512

    def contrastExists(self):
        return False

    def brightnessExists(self):
        return False

    def gainExists(self):
        return True

    def get_gain(self):
        gain = None

        try:
            gain = self.get_channel_value(CAMERA_GAIN_RBV)
        except:
            print("Error getting gain of camera...")

        return gain

    def set_gain(self, gain):
        try:
            self.setValue(CAMERA_GAIN, gain)
        except:
            print("Error setting gain of camera...")

    def get_gain_auto(self):
        auto = None

        try:
            auto = self.get_channel_value(CAMERA_AUTO_GAIN_RBV)
        except:
            print("Error getting auto-gain of camera...")

        return auto

    def set_gain_auto(self, auto):
        try:
            self.setValue(CAMERA_AUTO_GAIN, auto)
        except:
            print("Error setting auto-gain of camera...")


    def get_exposure_time(self):
        exp = None

        try:
            exp = self.get_channel_value(CAMERA_ACQ_TIME_RBV)
        except:
            print("Error getting exposure time of camera...")

        return exp

    def set_exposure_time(self, exp):
        try:
            self.setValue(CAMERA_ACQ_TIME, exp)
        except:
            print("Error setting exposure time of camera...")

    def start_camera(self):
        try:
            self.setValue(CAMERA_BACK, 1)
            self.setValue(CAMERA_EN_BACK, 1)
            self.setValue(CAMERA_ACQ_STOP, 0)
            self.setValue(CAMERA_ACQ_START, 1)
        except:
            pass

    def stop_camera(self):
        try:
            self.setValue(CAMERA_ACQ_START, 0)
            self.setValue(CAMERA_ACQ_STOP, 1)
        except:
            pass

    def refresh_camera_procedure(self):
        self.refreshing = True

        # Try to reconnect to PVs
        self.reconnect(CAMERA_DATA)
        self.reconnect(CAMERA_IMG_PIXEL_SIZE)
        self.reconnect(CAMERA_IMG_WIDTH)
        self.reconnect(CAMERA_IMG_HEIGHT)
        self.reconnect(CAMERA_BACK)
        self.reconnect(CAMERA_EN_BACK)
        self.reconnect(CAMERA_ACQ_START)
        self.reconnect(CAMERA_ACQ_STOP)
        self.reconnect(CAMERA_GAIN)
        self.reconnect(CAMERA_GAIN_RBV)
        self.reconnect(CAMERA_AUTO_GAIN)
        self.reconnect(CAMERA_AUTO_GAIN_RBV)
        self.reconnect(CAMERA_FPS_RBV)
        self.reconnect(CAMERA_ACQ_TIME)
        self.reconnect(CAMERA_ACQ_TIME_RBV)

        # Try to stop camera image acquisition
        self.setLive(False)
        # Wait a while
        gevent.sleep(0.2)
        # Set PVs to start
        self.start_camera()
        # (Re)start camera image acquisition
        self.setLive(True)

    def refresh_camera(self):
        logging.getLogger("user_level_log").error("Resetting camera, please, wait a while...")
        print("refresh_camera")

        # Start a new thread to don't freeze UI
        self.refreshgen = gevent.spawn(self.refresh_camera_procedure)

    def setLive(self, live):
        try:
            if live and self.liveState == live:
                return

            self.liveState = live

            if live:
                logging.getLogger("HWR").info("LNLSCamera is going to poll images")
                self.delay = float(int(self.getProperty("interval"))/1000.0)
                thread = Thread(target=self.poll)
                thread.daemon = True
                thread.start()
            else:
                self.stop_camera()

            return True
        except:
            return False

    def imageType(self):
        return None

    def takeSnapshot(self, *args):
        pass
        #imgFile = QtCore.QFile(args[0])
        #imgFile.open(QtCore.QIODevice.WriteOnly)
        #self.qtPixMap.save(imgFile,"PNG")
        #imgFile.close()

    def take_snapshots_procedure(self, image_count, snapshotFilePath, snapshotFilePrefix, logFilePath, runNumber, collectStart, collectEnd, motorHwobj, detectorHwobj):
        """
        Descript. : It takes snapshots of sample camera and camserver execution.
        """
        # Avoiding a processing of AbstractMultiCollect class for saving snapshots
        #centred_images = []
        centred_images = None
        positions = []

        try:
            # Calculate goniometer positions where to take snapshots
            if (collectEnd is not None and collectStart is not None):
                interval = (collectEnd - collectStart)
            else:
                interval = 0

            # To increment in angle increment
            increment = 0 if ((image_count -1) == 0) else (interval / (image_count -1))

            for incrementPos in range(image_count):
                if (collectStart is not None):
                    positions.append(collectStart + (incrementPos * increment))
                else:
                    positions.append(motorHwobj.getPosition())

            # Create folders if not found
            if (not os.path.exists(snapshotFilePath)):
                try:
                    os.makedirs(snapshotFilePath, mode=0o700)
                except OSError as diag:
                    logging.getLogger().error("Snapshot: error trying to create the directory %s (%s)" % (snapshotFilePath, str(diag)))

            for index in range(image_count):
                while (motorHwobj.getPosition() < positions[index]):
                    gevent.sleep(0.02)

                logging.getLogger("HWR").info("%s - taking snapshot #%d" % (self.__class__.__name__, index + 1))

                # Save snapshot image file
                imageFileName = os.path.join(snapshotFilePath, snapshotFilePrefix + "_" + str(round(motorHwobj.getPosition(),2)) + "_" + motorHwobj.getEgu() + "_snapshot.png")

                #imageInfo = self.takeSnapshot(imageFileName)

                # This way all shapes will be also saved...
                self.emit("saveSnapshot", imageFileName)

                # Send a command to detector hardware-object to take snapshot of camserver execution...
                if (logFilePath and detectorHwobj):
                    detectorHwobj.takeScreenshotOfXpraRunningProcess(image_path=logFilePath, run_number=runNumber)

                #centred_images.append((0, str(imageInfo)))
                #centred_images.reverse()
        except:
            logging.getLogger("HWR").exception("%s - could not take crystal snapshots" % (self.__class__.__name__))

        return centred_images

    def take_snapshots(self, image_count, snapshotFilePath, snapshotFilePrefix, logFilePath, runNumber, collectStart, collectEnd, motorHwobj, detectorHwobj, wait=False):
        """
        Descript. :  It takes snapshots of sample camera and camserver execution.
        """
        if image_count > 0:
            self.snapshots_procedure = gevent.spawn(self.take_snapshots_procedure, image_count, snapshotFilePath, snapshotFilePrefix, logFilePath, runNumber, collectStart, collectEnd, motorHwobj, detectorHwobj)

            self.centring_status["images"] = []

            self.snapshots_procedure.link(self.snapshots_done)

            if wait:
                self.centring_status["images"] = self.snapshots_procedure.get()

    def snapshots_done(self, snapshots_procedure):
        """
        Descript. :
        """
        try:
            self.centring_status["images"] = snapshots_procedure.get()
        except:
            logging.getLogger("HWR").exception("%s - could not take crystal snapshots" % (self.__class__.__name__))

    def cancel_snapshot(self):
        try:
            self.snapshots_procedure.kill()
        except:
            pass

    def __del__(self):
        logging.getLogger().exception("%s - __del__()!" % (self.__class__.__name__))
        self.stop_camera()
        self.setLive(False)
