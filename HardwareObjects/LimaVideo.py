"""
Lima video HO to capture images from camera
"""
import time
import logging
import gevent
from Lima import Core
from Qub.CTools import pixmaptools
from HardwareRepository import BaseHardwareObjects
from HardwareRepository.HardwareObjects.Camera import JpegType, BayerType, MmapType, RawType

class LimaVideo(BaseHardwareObjects.Device):

    def __init__(self, name):
	BaseHardwareObjects.Device.__init__(self, name)

        self.scaling = pixmaptools.LUT.Scaling()

    def _init(self):
	self.scalingType = None	
	self.forceUpdate = False

	self.__brightnessExists = False
	self.__contrastExists = False
	self.__gainExists = False
	self.__gammaExists = False 

	self.camType = self.getProperty("type").lower()
	self.camAddress = self.getProperty("address")

        try:
 	  self.camMirror = eval(self.getProperty("mirror_hor_ver"))
        except:
          self.camMirror = None

	if self.camType == 'prosilica':
	    from Lima import Prosilica
	    self.camera = Prosilica.Camera(self.camAddress)
            self.interface = Prosilica.Interface(self.camera)	
        if self.camType == 'simulation':
            from Lima import Simulator
            self.camera = Simulator.Camera()
            self.interface = Simulator.Interface(self.camera)
        try:
	    self.control = Core.CtControl(self.interface)
	    self.video = self.control.video()
	    self.video.setExposure(self.getProperty("interval")/1000.0)	
	    self.__imageDimensions = self.camera.getMaxWidthHeight()
        except KeyError:
            logging.getLogger().warning('%s: not initialized. Check camera settings', self.name())

	self.setImageTypeFromXml('imagetype')
 	self.setIsReady(True)

    def setImageTypeFromXml(self, property_name):
        image_type = self.getProperty(property_name) or 'Jpeg'
        if image_type.lower() == 'jpeg':
            self.imgtype = JpegType()
        elif image_type.lower().startswith("bayer:"):
            self.imgtype = BayerType(image_type.split(":")[1])
	    if image_type.lower() == "bayer:8":
		self.scalingType = pixmaptools.LUT.Scaling.BAYER_RG8
	    elif image_type.lower() == "bayer:16":  	
		self.scalingType = pixmaptools.LUT.Scaling.BAYER_RG16
        elif image_type.lower().startswith("raw") :
            self.imgtype = RawType()
        elif image_type.lower().startswith("mmap:"):
            self.imgtype = MmapType(image_type.split(":")[1])

    def imageType(self):
        """Returns a 'jpeg' or 'bayer' type object depending on the image type"""
        return self.imgtype

    #############   CONTRAST   #################
    def contrastExists(self):
        return self.__contrastExists

    def setContrast(self, contrast):
        pass

    def getContrast(self):
	return 

    def getContrastMinMax(self):
	return 

    #############   BRIGHTNESS   #################
    def brightnessExists(self):
        return self.__brightnessExists

    def setBrightness(self, brightness):
	pass

    def getBrightness(self):
	return 

    def getBrightnessMinMax(self):
	return 

    #############   GAIN   #################
    def gainExists(self):
        return self.__gainExists

    def setGain(self, gain):
	self.video.setGain(gain)

    def getGain(self):
	return self.video.getGain()

    def getGainMinMax(self):
	return 

    #############   GAMMA   #################
    def gammaExists(self):
        return self.__gammaExists

    def setGamma(self, gamma):
 	pass

    def getGamma(self):
	return 

    def getGammaMinMax(self):
	return (0, 1)

    def setLive(self, mode):
	if mode:
	    self.video.startLive()
        else:
	    self.video.stopLive()
    
    def getWidth(self):
	return self.__imageDimensions[0]
	
    def getHeight(self):
	return self.__imageDimensions[1]

    def _do_imagePolling(self, sleep_time):
        while True:
              self.newImage()
              time.sleep(sleep_time)
	     	
    def connectNotify(self, signal):
	if signal=="imageReceived":
            self.__imagePolling = gevent.spawn(self._do_imagePolling, self.getProperty("interval")/1000.0)


    def takeSnapshot(self, *args, **kw):
        filename = args[0]
        qimage = None
        image = self.video.getLastImage()

        if image.frameNumber() > -1:
            raw_buffer = image.buffer()

            self.scaling.autoscale_min_max(raw_buffer,
                                      image.width(), image.height(),
                                      self.scalingType)
            validFlag, qimage = pixmaptools.LUT.raw_video_2_image(raw_buffer,
                                                                  image.width(), image.height(),
                                                                  self.scalingType,
                                                                  self.scaling)
            if validFlag:
               if self.camMirror is not None:
                   qimage = qimage.mirror(self.camMirror[0], self.camMirror[1])
               qimage.save(filename, "PNG")
 

    def newImage(self):
	if self.video.getLive():
 	    image = self.video.getLastImage()
            qimage = None
	    if image.frameNumber() > -1:
      		raw_buffer = image.buffer()	
			
	        self.scaling.autoscale_min_max(raw_buffer,
                                          image.width(), image.height(),
                                          self.scalingType)
                validFlag, qimage = pixmaptools.LUT.raw_video_2_image(raw_buffer,
                                                                      image.width(), image.height(),
                                                                      self.scalingType,
                                                                      self.scaling)
		if validFlag:
                    if self.camMirror is not None:
                        qimage = qimage.mirror(self.camMirror[0], self.camMirror[1])     
   	            self.emit("imageReceived", qimage, qimage.width(), qimage.height(), self.forceUpdate)
