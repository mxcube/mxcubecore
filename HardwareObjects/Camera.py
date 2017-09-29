"""Class for cameras connected to framegrabbers run by Taco Device Servers

template:
  <device class = "Camera">
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
  </device>
"""
from HardwareRepository import BaseHardwareObjects
from HardwareRepository import CommandContainer
from HardwareRepository import HardwareRepository
import gevent
import logging
import os
import time
import sys

try:
    from Qub.CTools.qttools import BgrImageMmap
except ImportError:
    logging.getLogger("HWR").warning("Qub memory map not available: cannot use mmap image type")
    BgrImageMmap = None

try:
  import Image
except ImportError:
  logging.getLogger("HWR").warning("PIL not available: cannot take snapshots")
  canTakeSnapshots=False
else:
  canTakeSnapshots=True


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
  def __init__(self,mmapFile):
    ImageType.__init__(self, "mmap")
    self.mmapFile = mmapFile

class RGBType(ImageType):
  def __init__(self,mmapFile):
    ImageType.__init__(self, "rgb")



class Camera(BaseHardwareObjects.Device):
    def _init(self):
       if self.getProperty("tangoname"):
            # Tango device
            import PyTango

            class TangoCamera(BaseHardwareObjects.Device):
                def __init__(self, name):
                    BaseHardwareObjects.Device.__init__(self, name)

                def oprint(self, msg):
                    print("Camera.py--tango device-- %s"%msg)

                def _init(self):
                    self.forceUpdate = False
                    self.device = None
                    self.imgtype = None
                    try:
                        self.device = PyTango.DeviceProxy(self.tangoname)
                        #try a first call to get an exception if the device
                        #is not exported
                        self.device.ping()
                    except PyTango.DevFailed as traceback:
                        last_error = traceback[-1]
                        logging.getLogger('HWR').error("%s: %s", str(self.name()), last_error.desc)

                        self.device = BaseHardwareObjects.Null()
                        self.bpmDevice = None
                    else:
                        self.setImageTypeFromXml('imagetype')


                        self.__brightnessExists = False
                        self.__contrastExists   = False
                        self.__gainExists       = False
                        self.__gammaExists      = False

                        _attribute_list = self.device.get_attribute_list()
                        #self.oprint ("attribute list:")
                        #self.oprint (_attribute_list)

                        imgChan    = self.addChannel({ 'type': 'tango', 'name': 'image', "read_as_str": 1 }, "RgbImage")
                        imgWidth   = self.addChannel({ 'type': 'tango', 'name': 'width' },     "Width")
                        imgHeight  = self.addChannel({ 'type': 'tango', 'name': 'height'},     "Height")
                        fullWidth  = self.addChannel({ 'type': 'tango', 'name': 'fullwidth' }, "FullWidth")
                        fullHeight = self.addChannel({ 'type': 'tango', 'name': 'fullheight'}, "FullHeight")
                        roi        = self.addChannel({ 'type': 'tango', 'name': 'roi'},        "Roi")
                        exposure   = self.addChannel({ 'type': 'tango', 'name': 'exposure'},   "Exposure")

                        if "Brightness" in _attribute_list:
                            print("add brightness")
                            brightness = self.addChannel({ 'type': 'tango', 'name': 'brightness'}, "Brightness")
                            self.__brightnessExists = True

                        if "Contrast" in _attribute_list:
                            contrast = self.addChannel({ 'type': 'tango', 'name': 'contrast'},   "Contrast")
                            self.__contrastExists = True

                        if "Gain" in _attribute_list:
                            gain = self.addChannel({ 'type': 'tango', 'name': 'gain'},       "Gain")
                            self.__gainExists = True

                        if "Gamma" in _attribute_list:
                            gamma = self.addChannel({ 'type': 'tango', 'name': 'gamma'},      "Gamma")
                            self.__gammaExists = True

                        self.setIsReady(True)

                        """
                        Check wether there is a BPM device defined or not
                        """
                        if self.getProperty("bpmname"):
                            self.bpmDevice = CommandContainer.CommandContainer()
                            self.bpmDevice.tangoname = self.bpmname
                            threshold = self.bpmDevice.addChannel({ 'type': 'tango', 'name': 'threshold'}, "Threshold")
                            centerx   = self.bpmDevice.addChannel({ 'type': 'tango', 'name': 'centerx'}, "X")
                            centery   = self.bpmDevice.addChannel({ 'type': 'tango', 'name': 'centery'}, "Y")
                            fwhmx     = self.bpmDevice.addChannel({ 'type': 'tango', 'name': 'fwhmx'}, "XFwhm")
                            fwhmy     = self.bpmDevice.addChannel({ 'type': 'tango', 'name': 'fwhmy'}, "YFwhm")
                            maxpix    = self.bpmDevice.addChannel({ 'type': 'tango', 'name': 'maxpix'}, "MaxPixelValue")
                            intensity = self.bpmDevice.addChannel({ 'type': 'tango', 'name': 'intensity'}, "Intensity")
                            onCmd     = self.bpmDevice.addCommand({ 'type': 'tango', 'name': 'on'}, "On")
                            offCmd    = self.bpmDevice.addCommand({ 'type': 'tango', 'name': 'off'}, "Off")
                            stateCmd  = self.bpmDevice.addCommand({ 'type': 'tango', 'name': 'state'}, "State")
                        else:
                            self.bpmDevice = None
                            logging.getLogger('HWR').warning("%s: No BPM defined", str(self.name()))

                def setImageTypeFromXml(self, property_name):
                        image_type = self.getProperty(property_name) or 'Jpeg'

                        if image_type.lower() == 'jpeg':
                            streamChan = self.addChannel({ 'type': 'tango', 'name': 'stream', "read_as_str": 1 }, "JpegImage")
                            self.imgtype = JpegType()
                        elif image_type.lower().startswith("bayer:"):
                            streamChan = self.addChannel({ 'type': 'tango', 'name': 'stream', "read_as_str": 1 }, "BayerImage")
                            self.imgtype = BayerType(image_type.split(":")[1])
                        elif image_type.lower().startswith("raw") :
                            streamChan = self.addChannel({ 'type': 'tango', 'name': 'stream', "read_as_str": 1 }, "Image")
                            self.imgtype = RawType()
                        elif image_type.lower().startswith("mmap:"):
                            self.imgtype = MmapType(image_type.split(":")[1])
  

                def imageType(self):
                    """Returns a 'jpeg' or 'bayer' type object depending on the image type"""
                    return self.imgtype


                def newImage(self, img_cnt):
                    streamChan = self.getChannelObject("stream")
                    self.emit("imageReceived", streamChan.getValue(), self.getWidth(), self.getHeight(), self.forceUpdate)

                def __checkImageCounter(self,lastImageNumber = [0]) :
                    lastNumber = lastImageNumber[0]
                    currentNumber = self.__mmapBgr.getImageCount()
                    if currentNumber != lastNumber:
                        lastImageNumber[0] = currentNumber
                        newImage = self.__mmapBgr.getNewImage()
                        self.emit("imageReceived",(newImage,newImage.width(),newImage.height(), self.forceUpdate))


                def _do_mmapBrgPolling(self, sleep_time):
                    while True:
                      self.__checkImageCounter()
                      time.sleep(sleep_time)

                def connectNotify(self, signal):
                    if signal=="imageReceived":
                      try:
                         display_num = os.environ['DISPLAY'].split(':')[1]
                      except:
                         remote_client = False
                      else:
                         remote_client = display_num != '0.0'

                      if remote_client and self.getProperty("remote_imagetype"):
                         self.setImageTypeFromXml("remote_imagetype")

                      if isinstance(self.imgtype, MmapType):
                          self.__mmapBgr = BgrImageMmap(self.imgtype.mmapFile)
                          self.__mmapBrgPolling = gevent.spawn(self._do_mmapBrgPolling, self.getProperty("interval")/1000.0) 
                      else:
                        try:
                          imgCnt = self.addChannel({ 'type': 'tango', 'name':'img_cnt', 'polling': self.getProperty("interval") }, "ImageCounter")
                          imgCnt.connectSignal("update", self.newImage)
                        except:
                          pass


                #############   CONTRAST   #################
                def contrastExists(self):
                    return self.__contrastExists

                def setContrast(self, contrast):
                    """tango"""
                    try:
                        contrastChan = self.getChannelObject("contrast")
                        contrastChan.setValue(str(contrast))
                    except:
                        self.oprint("setContrast failed")
                        sys.excepthook(sys.exc_info()[0],
                                       sys.exc_info()[1],
                                       sys.exc_info()[2])

                def getContrast(self):
                    """tango"""
                    try:
                        contrastChan = self.getChannelObject("contrast")
                        contrast = contrastChan.getValue()
                        return(contrast)
                    except:
                        self.oprint("getContrast failed")
                        sys.excepthook(sys.exc_info()[0],
                                       sys.exc_info()[1],
                                       sys.exc_info()[2])
                        return(-1)

                def getContrastMinMax(self):
                    _config = self.device.get_attribute_config("contrast")
                    return ( _config.min_value, _config.max_value)


                #############   BRIGHTNESS   #################
                def brightnessExists(self):
                    return self.__brightnessExists

                def setBrightness(self, brightness):
                    """tango"""
                    try:
                        brightnessChan = self.getChannelObject("brightness")
                        brightnessChan.setValue(brightness)
                    except:
                        self.oprint("setBrightness failed")
                        sys.excepthook(sys.exc_info()[0],
                                       sys.exc_info()[1],
                                       sys.exc_info()[2])

                def getBrightness(self):
                    """tango"""
                    try:
                        brightnessChan = self.getChannelObject("brightness")
                        brightness = brightnessChan.getValue()
                        return(brightness)
                    except:
                        sys.excepthook(sys.exc_info()[0],
                                       sys.exc_info()[1],
                                       sys.exc_info()[2])
                        return(-1)

                def getBrightnessMinMax(self):
                    _config = self.device.get_attribute_config("brightness")
                    return ( _config.min_value, _config.max_value)


                #############   GAIN   #################
                def gainExists(self):
                    return self.__gainExists

                def setGain(self, gain):
                    """tango"""
                    try:
                        gainChan = self.getChannelObject("gain")
                        # ???? gainChan.setValue(str(gain))
                        gainChan.setValue(gain)
                    except:
                        self.oprint("setGain failed")
                        sys.excepthook(sys.exc_info()[0],
                                       sys.exc_info()[1],
                                       sys.exc_info()[2])

                def getGain(self):
                    """tango"""
                    try:
                        gainChan = self.getChannelObject("gain")
                        gain = gainChan.getValue()
                        return(gain)
                    except:
                        sys.excepthook(sys.exc_info()[0],
                                       sys.exc_info()[1],
                                       sys.exc_info()[2])
                        self.oprint("getGain failed")
                        return(-1)

                def getGainMinMax(self):
                    _config = self.device.get_attribute_config('gain')
                    return ( _config.min_value, _config.max_value)


                #############   GAMMA   #################
                def gammaExists(self):
                    return self.__gammaExists

                def setGamma(self, gamma):
                    """tango"""
                    try:
                        gammaChan = self.getChannelObject("gamma")
                        gammaChan.setValue(gamma)
                    except:
                        sys.excepthook(sys.exc_info()[0],
                                       sys.exc_info()[1],
                                       sys.exc_info()[2])
                        pass

                def getGamma(self):
                    """tango"""
                    try:
                        gammaChan = self.getChannelObject("gamma")
                        gamma = gammaChan.getValue()
                        return(gamma)
                    except:
                        sys.excepthook(sys.exc_info()[0],
                                       sys.exc_info()[1],
                                       sys.exc_info()[2])
                        return(-1)

                def getGammaMinMax(self):
                    _config = self.device.get_attribute_config('gamma')
                    return ( _config.min_value, _config.max_value)


                #############   WIDTH   #################
                def getWidth(self):
                    """tango"""
                    width = self.getChannelObject("width")
                    return width.getValue()


                def getHeight(self):
                    """tango"""
                    height = self.getChannelObject("height")

                    return height.getValue()


                def setSize(self, width, height):
                    """Set new image size

                    Only takes width into account, because anyway
                    we can only set a scale factor
                    """
                    return


                def takeSnapshot(self, *args, **kwargs):
                    """tango"""
                    if canTakeSnapshots:
                       imgChan = self.getChannelObject("image")
                       rawimg = imgChan.getValue()
                       w = self.getWidth()
                       h = self.getHeight()
                       if len(rawimg) == w*h*3:
                         img_type="RGB"
                       else:
                         img_type="L"
                       try:
                         if kwargs.get("bw", False) and img_type=="RGB":
                           img = Image.frombuffer(img_type, (self.getWidth(), self.getHeight()), rawimg).convert("L")
                         else:
                           img = Image.frombuffer(img_type, (self.getWidth(), self.getHeight()), rawimg)
                         img = img.transpose(Image.FLIP_TOP_BOTTOM)
                         #img.save(*args)
                       except:
                         logging.getLogger("HWR").exception("%s: could not save snapshot", self.name())
                       else:
                         if len(args):
                           try:
                             img.save(*args)
                           except:
                             logging.getLogger("HWR").exception("%s: could not save snapshot", self.name())
                           else:
                             return True
                         else:
                           return img
                    else:
                       logging.getLogger("HWR").error("%s: could not take snapshot: sorry PIL is not available :-(", self.name())
                    return False

                """
                BPM method
                """
                def setBpm(self, bpmOn):
                    """tango"""
                    if self.bpmDevice is not None:
                            if bpmOn: self.bpmDevice.executeCommand('on')
                            else: self.bpmDevice.executeCommand('off')

                def getBpmState(self):
                    """tango"""
                    if self.bpmDevice is not None:
                        return self.bpmDevice.executeCommand('state')
                    else:
                        return  PyTango.DevState.UNKNOWN

                def getBpmValues(self):
                    """Tango"""
                    if self.bpmDevice is not None:
                        #self.oprint("bpmDevice name =%s"%self.bpmDevice.tangoname)
                        try:
                            threshold  = self.bpmDevice.getChannelObject("threshold").getValue()
                        except:
                            threshold = -1
                        try:
                            centerx    = self.bpmDevice.getChannelObject("centerx").getValue()
                        except:
                            centerx = -1
                        try:
                            centery    = self.bpmDevice.getChannelObject("centery").getValue()
                        except:
                            centery = -1
                        try:
                            fwhmx      = self.bpmDevice.getChannelObject("fwhmx").getValue()
                        except:
                            fwhmx = -1
                        try:
                            fwhmy      = self.bpmDevice.getChannelObject("fwhmy").getValue()
                        except:
                            fwhmy = -1
                        try:
                            maxpix     = self.bpmDevice.getChannelObject("maxpix").getValue()
                        except:
                            maxpix = -1
                        try:
                            intensity     = self.bpmDevice.getChannelObject("intensity").getValue()
                        except:
                            intensity = -1
                        #self.oprint("Device name =%s"%self.device.name())
                        try:
                          exposure = self.getChannelObject("exposure").getValue()
                        except:
                          exposure = -1

                        # SIZES
                        try:
                          width    = self.getChannelObject("fullwidth").getValue()
                        except:
                          width = -1
                        try:
                          height   = self.getChannelObject("fullheight").getValue()
                        except:
                          height = -1

                        # FLIPS
                        try:
                          fliphorizontal = self.getChannelObject("fliphorizontal").getValue()
                        except:
                          fliphorizontal = 0

                        try:
                          flipvertical = self.getChannelObject("flipvertical").getValue()
                        except:
                          flipvertical = 0

                        # GAIN
                        try:
                            gain     = self.getChannelObject("gain").getValue()
                        except:
                            gain = 0

                        # GAMMA
                        try:
                            gamma     = self.getChannelObject("gamma").getValue()
                        except:
                            gamma = 0


                        try:
                          if self.device.State() == PyTango.DevState.ON:
                              live    = True
                          else:
                              live      = False
                        except:
                          live = False
                        try:
                          if self.getBpmState() == PyTango.DevState.ON:
                              bpm = True
                          else:
                              bpm = False
                        except:
                          bpm = False
                        try:
                          # ?????????? #  (startx, starty, endx, endy, d1, d2, d3, d4) = self.getChannelObject("roi").getValue()
                          (startx, endx, starty, endy, d1, d2, d3, d4) = self.getChannelObject("roi").getValue()
                          # print "Camera.py -- startx=", startx
                          # print self.getChannelObject("roi").getValue()
                        except:
                          (startx, starty, endx, endy, d1, d2, d3, d4) = (-1,-1,-1,-1,-1,-1,-1,-1)

                    else:
                        self.oprint("bpmDevice is None")

                        (threshold, centerx, centery, fwhmx, fwhmy, maxpix,intensity,exposure,width,height,gain) = (-2,-2,-2,-2,-2,-2,-2,-2,-2,-2,-2)
                        (startx, starty, endx, endy, d1, d2, d3, d4) = (-2,-2,-2,-2,-2,-2,-2,-2)
                        (live,bpm) = (False, False)
                    self.res = {}
                    self.res["time"]      = exposure
                    self.res["threshold"] = threshold
                    self.res["width"]     = width
                    self.res["height"]    = height
                    self.res["fliph"]     = fliphorizontal
                    self.res["flipv"]     = flipvertical
                    self.res["startx"]    = startx
                    self.res["starty"]    = starty
                    self.res["endx"]      = endx
                    self.res["endy"]      = endy
                    self.res["centerx"]   = centerx
                    self.res["centery"]   = centery
                    self.res["fwhmx"]     = fwhmx
                    self.res["fwhmy"]     = fwhmy
                    self.res["maxpix"]    = maxpix
                    self.res["intensity"] = intensity
                    self.res["gain"]      = gain
                    self.res["gamma"]     = gamma
                    self.res["live"]      = live
                    self.res["bpmon"]     = bpm

                    return self.res

                def setLive(self, mode):
                    """tango"""
                    if mode:
                      self.device.Live()
                    else:
                      self.device.Stop()

                def setBpm(self, bpmOn):
                    """tango"""
                    if self.bpmDevice is not None:
                        if bpmOn: self.bpmDevice.executeCommand('on')
                        else: self.bpmDevice.executeCommand('off')

                def resetROI(self):
                    """tango"""
                    self.device.resetROI()

                def setROI(self, startx, endx, starty, endy):
                    """tango"""
                    # ?????# self.getChannelObject("roi").setValue([startx, starty, endx, endy])
                    self.getChannelObject("roi").setValue([startx, endx, starty, endy])

                def setExposure(self, exposure):
                    self.getChannelObject("exposure").setValue(exposure)


                def setThreshold(self, threshold):
                    if self.bpmDevice is not None:
                        self.bpmDevice.getChannelObject("threshold").setValue(threshold)

            self.__class__ = TangoCamera
            self._init()
       elif self.getProperty("taconame"):
            # this is a Taco device
            import TacoDevice

            class TacoCamera(TacoDevice.TacoDevice):
                def init(self):
                    self.imgtype = JpegType()
                    self.forceUpdate = False
                    
                    if self.device.imported:
                        # device is already in tcp mode (done in _init)
                        self.device.DevCcdLive(1) #start acquisition
                        self.setPollCommand("DevCcdReadJpeg", 75, direct=True, compare=False) #75: quality
                        self.setIsReady(True)

                def oprint(self, msg):
                    print("Camera.py--taco device--%s"%msg)

                def imageType(self):
                    """Returns a 'jpeg' or 'bayer' type object depending on the image type"""
                    return self.imgtype

                def valueChanged(self, deviceName, value):
                    self.emit('imageReceived', (value, self.getWidth(), self.getHeight(), self.forceUpdate))

                def setContrast(self, contrast):
                    """taco"""
                    brightness = self.getBrightness()

                    if brightness != -1:
                        str_val = "%d %d"%(int(brightness), int(contrast))
                        self.device.DevCcdSetHwPar(str_val)

                def getContrast(self):
                    """taco"""
                    str_val = self.device.DevCcdGetHwPar()

                    if type(str_val) == type(""):
                        [brightness, contrast] = str_val.split()
                        return(int(contrast))
                    else:
                        return -1

                def setBrightness(self, brightness):
                    """taco"""
                    contrast = self.getContrast()

                    if contrast != -1:
                        str_val = "%d %d"%(int(brightness), int(contrast))
                        self.device.DevCcdSetHwPar(str_val)

                def getBrightness(self):
                    """taco"""
                    str_val = self.device.DevCcdGetHwPar()

                    if type(str_val) == type(""):
                        [brightness, contrast] = str_val.split()
                        return(int(brightness))
                    else:
                        return -1

                def getWidth(self):
                    """taco"""
                    if self.isReady():
                        return self.device.DevCcdXSize()


                def getHeight(self):
                    """taco"""
                    if self.isReady():
                        return self.device.DevCcdYSize()


                def setSize(self, width, height):
                    """taco"""
                    if self.isReady():
                        return self.device.DevCcdOutputSize(width, height)

                def takeSnapshot(self, *args):
                    """taco"""
                    if canTakeSnapshots:
                       rawimg = self.device.DevCcdRead(1)
                       try:
                         img = Image.frombuffer("RGB", (self.getWidth(), self.getHeight()), rawimg)
                         pixmap = img.tostring("raw", "BGR")
                         img = Image.frombuffer("RGB", img.size, pixmap)
                         #img.save(*args)
                       except:
                         logging.getLogger("HWR").exception("%s: could not save snapshot", self.name())
                       else:
                         if len(args):
                           try:
                             img.save(*args)
                           except:
                             logging.getLogger("HWR").exception("%s: could not save snapshot", self.name())
                           else:
                             return True
                         else:
                           return img
                    else:
                       logging.getLogger("HWR").error("%s: could not take snapshot: sorry PIL is not available :-(", self.name())
                    return False

                def getBpmValues(self):
                    """Taco"""
                    if self.isReady():
                        values = self.device.DevReadSigValues()
                        gain = self.device.DevCcdGetGain()

                        self.res = {}
                        if values[9] == 0:
                            self.res["live"] = False
                        else:
                            self.res["live"] = True
                        self.res["time"]      = values[0]
                        self.res["threshold"] = values[1]
                        self.res["width"]     = values[3]
                        self.res["height"]    = values[4]
                        self.res["startx"]    = values[5]
                        self.res["starty"]    = values[6]
                        self.res["endx"]      = values[7]
                        self.res["endy"]      = values[8]
                        self.res["centerx"]   = values[12]
                        self.res["centery"]   = values[13]
                        self.res["fwhmx"]     = values[14]
                        self.res["fwhmy"]     = values[15]
                        self.res["maxpix"]    = values[18]
                        self.res["gain"]      = gain
                        self.res["intensity"] = values[11]
                        #bpm is always on
                        self.res["bpmon"] = True
                        return self.res
                    else:
                      self.res = {}
                      self.res["live"] = False
                      self.res["time"]      = -2
                      self.res["threshold"] = -2
                      self.res["width"]     = -2
                      self.res["height"]    = -2
                      self.res["startx"]    = -2
                      self.res["starty"]    = -2
                      self.res["endx"]      = -2
                      self.res["endy"]      = -2
                      self.res["centerx"]   = -2
                      self.res["centery"]   = -2
                      self.res["fwhmx"]     = -2
                      self.res["fwhmy"]     = -2
                      self.res["maxpix"]    = -2
                      self.res["gain"]      = -2
                      self.res["intensity"] = -2
                      #bpm is always on
                      self.res["bpmon"] = False
                      return self.res

                def setLive(self, mode):
                    """taco"""
                    if mode:
                        self.device.DevCcdLive(1)
                    else:
                        self.device.DevCcdLive(0)

                def setBpm(self, bpmOn):
                    """taco"""
                    pass

                def getBpmState(self):
                    """taco"""
                    return 'ON'

                def setROI(self, startx, endx, starty, endy):
                    """taco"""
                    if self.isReady():

                        self.getBpmValues()
                        if self.res["live"]:
                            self.setLive(False)
                            time.sleep(0.1)

                        self.device.DevCcdSetRoI(startx, starty, endx, endy)

                        if self.res["live"]:
                            time.sleep(0.1)
                            self.setLive(True)

                def setExposure(self, exposure):
                    """taco"""
                    if self.isReady():

                        self.getBpmValues()
                        if self.res["live"]:
                            self.setLive(False)
                            time.sleep(0.1)

                        self.device.DevCcdSetExposure(exposure)

                        if self.res["live"]:
                            time.sleep(0.1)
                            self.setLive(True)

                def setGain(self, gain):
                    """taco"""
                    if self.isReady():

                        self.getBpmValues()
                        if self.res["live"]:
                            self.setLive(False)
                            time.sleep(0.1)

                        self.device.DevCcdSetGain(gain)

                        if self.res["live"]:
                            time.sleep(0.1)
                            self.setLive(True)

                def setThreshold(self, threshold):
                    """taco"""
                    if self.isReady():

                        self.getBpmValues()
                        if self.res["live"]:
                            self.setLive(False)
                            time.sleep(0.1)

                        self.device.DevCcdSetThreshold(threshold)

                        if self.res["live"]:
                            time.sleep(0.1)
                            self.setLive(True)

            self.__class__ = TacoCamera
            self._TacoDevice__dc= False
            self._init()


