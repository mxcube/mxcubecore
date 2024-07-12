"""Class for cameras connected to framegrabbers run by Taco Device Servers

template:
  <object class = "Camera">
    <username>user label</username>
    <!-- <taconame>device server name (//host/.../.../...)</taconame> -->
    <interval>polling interval (in ms.)</interval>
    <!-- <calibration>
      <zoomMotor>Zoom motor Hardware Object reference</zoomMotor>
      <calibrationData>
        <offset>Zoom motor position (user units)</offset>
        <pixelsPerMmY>pixels per mm (Y axis)</pixelsPerMmY>
        <pixelsPerMmZ>pixels per mm (Z axis)</pixelsPerMmZ>
      </calibrationData>
    </calibration> -->
  </object>
"""
from mxcubecore import BaseHardwareObjects
from mxcubecore import CommandContainer
import gevent
import logging
import os
import time
import sys

try:
    from Qub.CTools.qttools import BgrImageMmap
except ImportError:
    logging.getLogger("HWR").warning(
        "Qub memory map not available: cannot use mmap image type"
    )
    BgrImageMmap = None

try:
    import Image
except ImportError:
    logging.getLogger("HWR").warning("PIL not available: cannot take snapshots")
    canTakeSnapshots = False
else:
    canTakeSnapshots = True


class ImageType:
    def __init__(self, type=None):
        self.image_type = type

    def type(self):
        return self.image_type


class JpegType(ImageType):
    def __init__(self):
        ImageType.__init__(self, "jpeg")


class BayerType(ImageType):
    def __init__(self, bayer_matrix):
        ImageType.__init__(self, "bayer")
        self.bayer_matrix = bayer_matrix.upper()


class RawType(ImageType):
    def __init__(self):
        ImageType.__init__(self, "raw")


class MmapType(ImageType):
    def __init__(self, mmapFile):
        ImageType.__init__(self, "mmap")
        self.mmapFile = mmapFile


class RGBType(ImageType):
    def __init__(self, mmapFile):
        ImageType.__init__(self, "rgb")


class Camera(BaseHardwareObjects.Device):
    def _init(self):
        if self.get_property("tangoname"):
            # Tango device
            import PyTango

            class TangoCamera(BaseHardwareObjects.Device):
                def __init__(self, name):
                    BaseHardwareObjects.Device.__init__(self, name)

                def oprint(self, msg):
                    print(("Camera.py--tango device-- %s" % msg))

                def _init(self):
                    self.forceUpdate = False
                    self.device = None
                    self.imgtype = None
                    try:
                        self.device = PyTango.DeviceProxy(self.tangoname)
                        # try a first call to get an exception if the device
                        # is not exported
                        self.device.ping()
                    except PyTango.DevFailed as traceback:
                        last_error = traceback[-1]
                        logging.getLogger("HWR").error(
                            "%s: %s", str(self.name()), last_error.desc
                        )

                        self.device = BaseHardwareObjects.Null()
                        self.bpmDevice = None
                    else:
                        self.setImageTypeFromXml("imagetype")

                        self.__brightnessExists = False
                        self.__contrastExists = False
                        self.__gainExists = False
                        self.__gammaExists = False

                        _attribute_list = self.device.get_attribute_list()
                        # self.oprint ("attribute list:")
                        # self.oprint (_attribute_list)

                        imgChan = self.add_channel(
                            {"type": "tango", "name": "image", "read_as_str": 1},
                            "RgbImage",
                        )
                        imgWidth = self.add_channel(
                            {"type": "tango", "name": "width"}, "Width"
                        )
                        imgHeight = self.add_channel(
                            {"type": "tango", "name": "height"}, "Height"
                        )
                        fullWidth = self.add_channel(
                            {"type": "tango", "name": "fullwidth"}, "FullWidth"
                        )
                        fullHeight = self.add_channel(
                            {"type": "tango", "name": "fullheight"}, "FullHeight"
                        )
                        roi = self.add_channel({"type": "tango", "name": "roi"}, "Roi")
                        exposure = self.add_channel(
                            {"type": "tango", "name": "exposure"}, "Exposure"
                        )

                        if "Brightness" in _attribute_list:
                            print("add brightness")
                            brightness = self.add_channel(
                                {"type": "tango", "name": "brightness"}, "Brightness"
                            )
                            self.__brightnessExists = True

                        if "Contrast" in _attribute_list:
                            contrast = self.add_channel(
                                {"type": "tango", "name": "contrast"}, "Contrast"
                            )
                            self.__contrastExists = True

                        if "Gain" in _attribute_list:
                            gain = self.add_channel(
                                {"type": "tango", "name": "gain"}, "Gain"
                            )
                            self.__gainExists = True

                        if "Gamma" in _attribute_list:
                            gamma = self.add_channel(
                                {"type": "tango", "name": "gamma"}, "Gamma"
                            )
                            self.__gammaExists = True

                        self.set_is_ready(True)

                        """
                        Check wether there is a BPM device defined or not
                        """
                        if self.get_property("bpmname"):
                            self.bpmDevice = CommandContainer.CommandContainer()
                            self.bpmDevice.tangoname = self.bpmname
                            threshold = self.bpmDevice.add_channel(
                                {"type": "tango", "name": "threshold"}, "Threshold"
                            )
                            centerx = self.bpmDevice.add_channel(
                                {"type": "tango", "name": "centerx"}, "X"
                            )
                            centery = self.bpmDevice.add_channel(
                                {"type": "tango", "name": "centery"}, "Y"
                            )
                            fwhmx = self.bpmDevice.add_channel(
                                {"type": "tango", "name": "fwhmx"}, "XFwhm"
                            )
                            fwhmy = self.bpmDevice.add_channel(
                                {"type": "tango", "name": "fwhmy"}, "YFwhm"
                            )
                            maxpix = self.bpmDevice.add_channel(
                                {"type": "tango", "name": "maxpix"}, "MaxPixelValue"
                            )
                            intensity = self.bpmDevice.add_channel(
                                {"type": "tango", "name": "intensity"}, "Intensity"
                            )
                            onCmd = self.bpmDevice.add_command(
                                {"type": "tango", "name": "on"}, "On"
                            )
                            offCmd = self.bpmDevice.add_command(
                                {"type": "tango", "name": "off"}, "Off"
                            )
                            stateCmd = self.bpmDevice.add_command(
                                {"type": "tango", "name": "state"}, "State"
                            )
                        else:
                            self.bpmDevice = None
                            logging.getLogger("HWR").warning(
                                "%s: No BPM defined", str(self.name())
                            )

                def setImageTypeFromXml(self, property_name):
                    image_type = self.get_property(property_name) or "Jpeg"

                    if image_type.lower() == "jpeg":
                        streamChan = self.add_channel(
                            {"type": "tango", "name": "stream", "read_as_str": 1},
                            "JpegImage",
                        )
                        self.imgtype = JpegType()
                    elif image_type.lower().startswith("bayer:"):
                        streamChan = self.add_channel(
                            {"type": "tango", "name": "stream", "read_as_str": 1},
                            "BayerImage",
                        )
                        self.imgtype = BayerType(image_type.split(":")[1])
                    elif image_type.lower().startswith("raw"):
                        streamChan = self.add_channel(
                            {"type": "tango", "name": "stream", "read_as_str": 1},
                            "Image",
                        )
                        self.imgtype = RawType()
                    elif image_type.lower().startswith("mmap:"):
                        self.imgtype = MmapType(image_type.split(":")[1])

                def imageType(self):
                    """Returns a 'jpeg' or 'bayer' type object depending on the image type"""
                    return self.imgtype

                def newImage(self, img_cnt):
                    streamChan = self.get_channel_object("stream")
                    self.emit(
                        "imageReceived",
                        streamChan.get_value(),
                        self.get_width(),
                        self.get_height(),
                        self.forceUpdate,
                    )

                def __checkImageCounter(self, lastImageNumber=[0]):
                    lastNumber = lastImageNumber[0]
                    currentNumber = self.__mmapBgr.getImageCount()
                    if currentNumber != lastNumber:
                        lastImageNumber[0] = currentNumber
                        newImage = self.__mmapBgr.getNewImage()
                        self.emit(
                            "imageReceived",
                            (
                                newImage,
                                newImage.width(),
                                newImage.height(),
                                self.forceUpdate,
                            ),
                        )

                def _do_mmapBrgPolling(self, sleep_time):
                    while True:
                        self.__checkImageCounter()
                        time.sleep(sleep_time)

                def connect_notify(self, signal):
                    if signal == "imageReceived":
                        try:
                            display_num = os.environ["DISPLAY"].split(":")[1]
                        except Exception:
                            remote_client = False
                        else:
                            remote_client = display_num != "0.0"

                        if remote_client and self.get_property("remote_imagetype"):
                            self.setImageTypeFromXml("remote_imagetype")

                        if isinstance(self.imgtype, MmapType):
                            self.__mmapBgr = BgrImageMmap(self.imgtype.mmapFile)
                            self.__mmapBrgPolling = gevent.spawn(
                                self._do_mmapBrgPolling,
                                self.get_property("interval") / 1000.0,
                            )
                        else:
                            try:
                                imgCnt = self.add_channel(
                                    {
                                        "type": "tango",
                                        "name": "img_cnt",
                                        "polling": self.get_property("interval"),
                                    },
                                    "ImageCounter",
                                )
                                imgCnt.connect_signal("update", self.newImage)
                            except Exception:
                                pass

                # ############   CONTRAST   #################

                def contrastExists(self):
                    return self.__contrastExists

                def setContrast(self, contrast):
                    """tango"""
                    try:
                        contrastChan = self.get_channel_object("contrast")
                        contrastChan.set_value(str(contrast))
                    except Exception:
                        self.oprint("setContrast failed")
                        sys.excepthook(
                            sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]
                        )

                def getContrast(self):
                    """tango"""
                    try:
                        contrastChan = self.get_channel_object("contrast")
                        contrast = contrastChan.get_value()
                        return contrast
                    except Exception:
                        self.oprint("getContrast failed")
                        sys.excepthook(
                            sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]
                        )
                        return -1

                def getContrastMinMax(self):
                    _config = self.device.get_attribute_config("contrast")
                    return (_config.min_value, _config.max_value)

                # ############   BRIGHTNESS   #################

                def brightnessExists(self):
                    return self.__brightnessExists

                def setBrightness(self, brightness):
                    """tango"""
                    try:
                        brightnessChan = self.get_channel_object("brightness")
                        brightnessChan.set_value(brightness)
                    except Exception:
                        self.oprint("setBrightness failed")
                        sys.excepthook(
                            sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]
                        )

                def getBrightness(self):
                    """tango"""
                    try:
                        brightnessChan = self.get_channel_object("brightness")
                        brightness = brightnessChan.get_value()
                        return brightness
                    except Exception:
                        sys.excepthook(
                            sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]
                        )
                        return -1

                def getBrightnessMinMax(self):
                    _config = self.device.get_attribute_config("brightness")
                    return (_config.min_value, _config.max_value)

                # ############   GAIN   #################

                def gainExists(self):
                    return self.__gainExists

                def setGain(self, gain):
                    """tango"""
                    try:
                        gainChan = self.get_channel_object("gain")
                        # ???? gainChan.set_value(str(gain))
                        gainChan.set_value(gain)
                    except Exception:
                        self.oprint("setGain failed")
                        sys.excepthook(
                            sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]
                        )

                def getGain(self):
                    """tango"""
                    try:
                        gainChan = self.get_channel_object("gain")
                        gain = gainChan.get_value()
                        return gain
                    except Exception:
                        sys.excepthook(
                            sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]
                        )
                        self.oprint("getGain failed")
                        return -1

                def getGainMinMax(self):
                    _config = self.device.get_attribute_config("gain")
                    return (_config.min_value, _config.max_value)

                # ############   GAMMA   #################

                def gammaExists(self):
                    return self.__gammaExists

                def setGamma(self, gamma):
                    """tango"""
                    try:
                        gammaChan = self.get_channel_object("gamma")
                        gammaChan.set_value(gamma)
                    except Exception:
                        sys.excepthook(
                            sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]
                        )

                def getGamma(self):
                    """tango"""
                    try:
                        gammaChan = self.get_channel_object("gamma")
                        gamma = gammaChan.get_value()
                        return gamma
                    except Exception:
                        sys.excepthook(
                            sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2]
                        )
                        return -1

                def getGammaMinMax(self):
                    _config = self.device.get_attribute_config("gamma")
                    return (_config.min_value, _config.max_value)

                # ############   WIDTH   #################

                def get_width(self):
                    """tango"""
                    width = self.get_channel_object("width")
                    return width.get_value()

                def get_height(self):
                    """tango"""
                    height = self.get_channel_object("height")

                    return height.get_value()

                def setSize(self, width, height):
                    """Set new image size

                    Only takes width into account, because anyway
                    we can only set a scale factor
                    """
                    return

                def takeSnapshot(self, *args, **kwargs):
                    """tango"""
                    if canTakeSnapshots:
                        imgChan = self.get_channel_object("image")
                        rawimg = imgChan.get_value()
                        w = self.get_width()
                        h = self.get_height()
                        if len(rawimg) == w * h * 3:
                            img_type = "RGB"
                        else:
                            img_type = "L"
                        try:
                            if kwargs.get("bw", False) and img_type == "RGB":
                                img = Image.frombuffer(
                                    img_type,
                                    (self.get_width(), self.get_height()),
                                    rawimg,
                                ).convert("L")
                            else:
                                img = Image.frombuffer(
                                    img_type,
                                    (self.get_width(), self.get_height()),
                                    rawimg,
                                )
                            img = img.transpose(Image.FLIP_TOP_BOTTOM)
                            # img.save(*args)
                        except Exception:
                            logging.getLogger("HWR").exception(
                                "%s: could not save snapshot", self.name()
                            )
                        else:
                            if len(args):
                                try:
                                    img.save(*args)
                                except Exception:
                                    logging.getLogger("HWR").exception(
                                        "%s: could not save snapshot", self.name()
                                    )
                                else:
                                    return True
                            else:
                                return img
                    else:
                        logging.getLogger("HWR").error(
                            "%s: could not take snapshot: sorry PIL is not available :-(",
                            self.name(),
                        )
                    return False

                """
                BPM method
                """

                def setBpm(self, bpmOn):
                    """tango"""
                    if self.bpmDevice is not None:
                        if bpmOn:
                            self.bpmDevice.execute_command("on")
                        else:
                            self.bpmDevice.execute_command("off")

                def getBpmState(self):
                    """tango"""
                    if self.bpmDevice is not None:
                        return self.bpmDevice.execute_command("state")
                    else:
                        return PyTango.DevState.UNKNOWN

                def getBpmValues(self):
                    """Tango"""
                    if self.bpmDevice is not None:
                        # self.oprint("bpmDevice name =%s"%self.bpmDevice.tangoname)
                        try:
                            threshold = self.bpmDevice.get_channel_object(
                                "threshold"
                            ).get_value()
                        except Exception:
                            threshold = -1
                        try:
                            centerx = self.bpmDevice.get_channel_object(
                                "centerx"
                            ).get_value()
                        except Exception:
                            centerx = -1
                        try:
                            centery = self.bpmDevice.get_channel_object(
                                "centery"
                            ).get_value()
                        except Exception:
                            centery = -1
                        try:
                            fwhmx = self.bpmDevice.get_channel_object(
                                "fwhmx"
                            ).get_value()
                        except Exception:
                            fwhmx = -1
                        try:
                            fwhmy = self.bpmDevice.get_channel_object(
                                "fwhmy"
                            ).get_value()
                        except Exception:
                            fwhmy = -1
                        try:
                            maxpix = self.bpmDevice.get_channel_object(
                                "maxpix"
                            ).get_value()
                        except Exception:
                            maxpix = -1
                        try:
                            intensity = self.bpmDevice.get_channel_object(
                                "intensity"
                            ).get_value()
                        except Exception:
                            intensity = -1
                        # self.oprint("Device name =%s"%self.device.name())
                        try:
                            exposure = self.get_channel_object("exposure").get_value()
                        except Exception:
                            exposure = -1

                        # SIZES
                        try:
                            width = self.get_channel_object("fullwidth").get_value()
                        except Exception:
                            width = -1
                        try:
                            height = self.get_channel_object("fullheight").get_value()
                        except Exception:
                            height = -1

                        # FLIPS
                        try:
                            fliphorizontal = self.get_channel_object(
                                "fliphorizontal"
                            ).get_value()
                        except Exception:
                            fliphorizontal = 0

                        try:
                            flipvertical = self.get_channel_object(
                                "flipvertical"
                            ).get_value()
                        except Exception:
                            flipvertical = 0

                        # GAIN
                        try:
                            gain = self.get_channel_object("gain").get_value()
                        except Exception:
                            gain = 0

                        # GAMMA
                        try:
                            gamma = self.get_channel_object("gamma").get_value()
                        except Exception:
                            gamma = 0

                        try:
                            if self.device.State() == PyTango.DevState.ON:
                                live = True
                            else:
                                live = False
                        except Exception:
                            live = False
                        try:
                            if self.getBpmState() == PyTango.DevState.ON:
                                bpm = True
                            else:
                                bpm = False
                        except Exception:
                            bpm = False
                        try:
                            # ?????????? #  (startx, starty, endx, endy, d1, d2, d3, d4) = self.get_channel_object("roi").get_value()
                            (
                                startx,
                                endx,
                                starty,
                                endy,
                                d1,
                                d2,
                                d3,
                                d4,
                            ) = self.get_channel_object("roi").get_value()
                            # print "Camera.py -- startx=", startx
                            # print self.get_channel_object("roi").get_value()
                        except Exception:
                            (startx, starty, endx, endy, d1, d2, d3, d4) = (
                                -1,
                                -1,
                                -1,
                                -1,
                                -1,
                                -1,
                                -1,
                                -1,
                            )

                    else:
                        self.oprint("bpmDevice is None")

                        (
                            threshold,
                            centerx,
                            centery,
                            fwhmx,
                            fwhmy,
                            maxpix,
                            intensity,
                            exposure,
                            width,
                            height,
                            gain,
                        ) = (-2, -2, -2, -2, -2, -2, -2, -2, -2, -2, -2)
                        (startx, starty, endx, endy, d1, d2, d3, d4) = (
                            -2,
                            -2,
                            -2,
                            -2,
                            -2,
                            -2,
                            -2,
                            -2,
                        )
                        (live, bpm) = (False, False)
                    self.res = {}
                    self.res["time"] = exposure
                    self.res["threshold"] = threshold
                    self.res["width"] = width
                    self.res["height"] = height
                    self.res["fliph"] = fliphorizontal
                    self.res["flipv"] = flipvertical
                    self.res["startx"] = startx
                    self.res["starty"] = starty
                    self.res["endx"] = endx
                    self.res["endy"] = endy
                    self.res["centerx"] = centerx
                    self.res["centery"] = centery
                    self.res["fwhmx"] = fwhmx
                    self.res["fwhmy"] = fwhmy
                    self.res["maxpix"] = maxpix
                    self.res["intensity"] = intensity
                    self.res["gain"] = gain
                    self.res["gamma"] = gamma
                    self.res["live"] = live
                    self.res["bpmon"] = bpm

                    return self.res

                def set_live(self, mode):
                    """tango"""
                    if mode:
                        self.device.Live()
                    else:
                        self.device.Stop()

                def setBpm(self, bpmOn):
                    """tango"""
                    if self.bpmDevice is not None:
                        if bpmOn:
                            self.bpmDevice.execute_command("on")
                        else:
                            self.bpmDevice.execute_command("off")

                def resetROI(self):
                    """tango"""
                    self.device.resetROI()

                def setROI(self, startx, endx, starty, endy):
                    """tango"""
                    # ?????# self.get_channel_object("roi").set_value([startx, starty, endx, endy])
                    self.get_channel_object("roi").set_value(
                        [startx, endx, starty, endy]
                    )

                def setExposure(self, exposure):
                    self.get_channel_object("exposure").set_value(exposure)

                def setThreshold(self, threshold):
                    if self.bpmDevice is not None:
                        self.bpmDevice.get_channel_object("threshold").set_value(
                            threshold
                        )

            self.__class__ = TangoCamera
            self._init()
        elif self.get_property("taconame"):
            # this is a Taco device
            import TacoDevice

            class TacoCamera(TacoDevice.TacoDevice):
                def init(self):
                    self.imgtype = JpegType()
                    self.forceUpdate = False

                    if self.device.imported:
                        # device is already in tcp mode (done in _init)
                        self.device.DevCcdLive(1)  # start acquisition
                        self.setPollCommand(
                            "DevCcdReadJpeg", 75, direct=True, compare=False
                        )  # 75: quality
                        self.set_is_ready(True)

                def oprint(self, msg):
                    print(("Camera.py--taco device--%s" % msg))

                def imageType(self):
                    """Returns a 'jpeg' or 'bayer' type object depending on the image type"""
                    return self.imgtype

                def value_changed(self, deviceName, value):
                    self.emit(
                        "imageReceived",
                        (value, self.get_width(), self.get_height(), self.forceUpdate),
                    )

                def setContrast(self, contrast):
                    """taco"""
                    brightness = self.getBrightness()

                    if brightness != -1:
                        str_val = "%d %d" % (int(brightness), int(contrast))
                        self.device.DevCcdSetHwPar(str_val)

                def getContrast(self):
                    """taco"""
                    str_val = self.device.DevCcdGetHwPar()

                    if isinstance(str_val, type("")):
                        [brightness, contrast] = str_val.split()
                        return int(contrast)
                    else:
                        return -1

                def setBrightness(self, brightness):
                    """taco"""
                    contrast = self.getContrast()

                    if contrast != -1:
                        str_val = "%d %d" % (int(brightness), int(contrast))
                        self.device.DevCcdSetHwPar(str_val)

                def getBrightness(self):
                    """taco"""
                    str_val = self.device.DevCcdGetHwPar()

                    if isinstance(str_val, type("")):
                        [brightness, contrast] = str_val.split()
                        return int(brightness)
                    else:
                        return -1

                def get_width(self):
                    """taco"""
                    if self.is_ready():
                        return self.device.DevCcdXSize()

                def get_height(self):
                    """taco"""
                    if self.is_ready():
                        return self.device.DevCcdYSize()

                def setSize(self, width, height):
                    """taco"""
                    if self.is_ready():
                        return self.device.DevCcdOutputSize(width, height)

                def takeSnapshot(self, *args):
                    """taco"""
                    if canTakeSnapshots:
                        rawimg = self.device.DevCcdRead(1)
                        try:
                            img = Image.frombuffer(
                                "RGB", (self.get_width(), self.get_height()), rawimg
                            )
                            pixmap = img.tostring("raw", "BGR")
                            img = Image.frombuffer("RGB", img.size, pixmap)
                            # img.save(*args)
                        except Exception:
                            logging.getLogger("HWR").exception(
                                "%s: could not save snapshot", self.name()
                            )
                        else:
                            if len(args):
                                try:
                                    img.save(*args)
                                except Exception:
                                    logging.getLogger("HWR").exception(
                                        "%s: could not save snapshot", self.name()
                                    )
                                else:
                                    return True
                            else:
                                return img
                    else:
                        logging.getLogger("HWR").error(
                            "%s: could not take snapshot: sorry PIL is not available :-(",
                            self.name(),
                        )
                    return False

                def getBpmValues(self):
                    """Taco"""
                    if self.is_ready():
                        values = self.device.DevReadSigValues()
                        gain = self.device.DevCcdGetGain()

                        self.res = {}
                        if values[9] == 0:
                            self.res["live"] = False
                        else:
                            self.res["live"] = True
                        self.res["time"] = values[0]
                        self.res["threshold"] = values[1]
                        self.res["width"] = values[3]
                        self.res["height"] = values[4]
                        self.res["startx"] = values[5]
                        self.res["starty"] = values[6]
                        self.res["endx"] = values[7]
                        self.res["endy"] = values[8]
                        self.res["centerx"] = values[12]
                        self.res["centery"] = values[13]
                        self.res["fwhmx"] = values[14]
                        self.res["fwhmy"] = values[15]
                        self.res["maxpix"] = values[18]
                        self.res["gain"] = gain
                        self.res["intensity"] = values[11]
                        # bpm is always on
                        self.res["bpmon"] = True
                        return self.res
                    else:
                        self.res = {}
                        self.res["live"] = False
                        self.res["time"] = -2
                        self.res["threshold"] = -2
                        self.res["width"] = -2
                        self.res["height"] = -2
                        self.res["startx"] = -2
                        self.res["starty"] = -2
                        self.res["endx"] = -2
                        self.res["endy"] = -2
                        self.res["centerx"] = -2
                        self.res["centery"] = -2
                        self.res["fwhmx"] = -2
                        self.res["fwhmy"] = -2
                        self.res["maxpix"] = -2
                        self.res["gain"] = -2
                        self.res["intensity"] = -2
                        # bpm is always on
                        self.res["bpmon"] = False
                        return self.res

                def set_live(self, mode):
                    """taco"""
                    if mode:
                        self.device.DevCcdLive(1)
                    else:
                        self.device.DevCcdLive(0)

                def setBpm(self, bpmOn):
                    """taco"""

                def getBpmState(self):
                    """taco"""
                    return "ON"

                def setROI(self, startx, endx, starty, endy):
                    """taco"""
                    if self.is_ready():

                        self.getBpmValues()
                        if self.res["live"]:
                            self.set_live(False)
                            time.sleep(0.1)

                        self.device.DevCcdSetRoI(startx, starty, endx, endy)

                        if self.res["live"]:
                            time.sleep(0.1)
                            self.set_live(True)

                def setExposure(self, exposure):
                    """taco"""
                    if self.is_ready():

                        self.getBpmValues()
                        if self.res["live"]:
                            self.set_live(False)
                            time.sleep(0.1)

                        self.device.DevCcdSetExposure(exposure)

                        if self.res["live"]:
                            time.sleep(0.1)
                            self.set_live(True)

                def setGain(self, gain):
                    """taco"""
                    if self.is_ready():

                        self.getBpmValues()
                        if self.res["live"]:
                            self.set_live(False)
                            time.sleep(0.1)

                        self.device.DevCcdSetGain(gain)

                        if self.res["live"]:
                            time.sleep(0.1)
                            self.set_live(True)

                def setThreshold(self, threshold):
                    """taco"""
                    if self.is_ready():

                        self.getBpmValues()
                        if self.res["live"]:
                            self.set_live(False)
                            time.sleep(0.1)

                        self.device.DevCcdSetThreshold(threshold)

                        if self.res["live"]:
                            time.sleep(0.1)
                            self.set_live(True)

            self.__class__ = TacoCamera
            self._TacoDevice__dc = False
            self._init()
