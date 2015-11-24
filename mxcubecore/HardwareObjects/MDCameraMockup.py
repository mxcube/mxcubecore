"""Class for cameras connected to framegrabbers run by Taco Device Servers
"""
from HardwareRepository import BaseHardwareObjects
import logging
import os, time, datetime
import PyTango
from PIL import Image
import numpy as np
from threading import Event, Thread
import base64
import gevent
MAX_TRIES     = 3
SLOW_INTERVAL = 1000

class MDCameraMockup(BaseHardwareObjects.Device):

    def __init__(self,name):
        BaseHardwareObjects.Device.__init__(self,name)

    def _init(self):
        self.udiffVER_Ok  = False
        self.badimg       = 0
        self.pollInterval = 500
        self.connected    = False
        self.tangoname = self.getProperty("tangoname")
        self.image = self.getProperty("image_path")
        try:
            pass
        except PyTango.DevFailed, traceback:
            last_error = traceback[-1]
            print "last error ",str(last_error)
            logging.getLogger('HWR').error("%s: %s", str(self.name()), last_error['desc'])
    
            self.device = BaseHardwareObjects.Null()
        else:
           self.setIsReady(True)
  
    def init(self):
        logging.getLogger("HWR").info( "initializing camera object")
         #self.pollingTimer = qt.QTimer()
         #self.pollingTimer.connect(self.pollingTimer, qt.SIGNAL("timeout()"), self.poll)
        if self.getProperty("interval"):
            self.pollInterval = self.getProperty("interval")
        self.stopper = False#self.pollingTimer(self.pollInterval, self.poll)
        thread = Thread(target=self.poll)
        thread.start()

    def udiffVersionChanged(self, value):
        if value == "MD2_2":
            print "start polling MD camera with poll interval=",self.pollInterval
            #self.pollingTimer.start(self.pollInterval)
            #self.startPolling()
        else:
            print "stop polling the camera. This microdiff version does not support a camera"
            #self.pollingTimer.stop()
            self.stopper=True

    def connectToDevice(self):
        self.connected = True
        return self.connected

    #@timer.setInterval(self.pollInterval)
    def poll(self):
        logging.getLogger("HWR").info( "going to poll images")
        while not self.stopper:
            #time.sleep(float(self.pollInterval)/1000)
            time.sleep(1)
            #print "polling", datetime.datetime.now().strftime("%H:%M:%S.%f")
            try:
                img = open( self.image, 'rb').read()
                #img = base64.b64encode(img)
                self.emit("imageReceived", img, 659, 493)
                #logging.getLogger("HWR").info( "polling images")
            except PyTango.ConnectionFailed:
                self.connected = False  
                return
            except:
                import traceback
                traceback.print_exc()

    def imageUpdated(self, value):
       print "<HW> got new image"
       print value

    def gammaExists(self):
        return False
    def contrastExists(self):
        return False
    def brightnessExists(self):
        return False
    def gainExists(self):
        return False
    def getWidth(self):
        #return 768 #JN ,20140807,adapt the MD2 screen to mxCuBE2
        return 659
    def getHeight(self):
        #return 576 # JN ,20140807,adapt the MD2 screen to mxCuBE2
        return 493

    def setLive(self, state):
        self.liveState = state
        return True
    def imageType(self):
        return None

    def takeSnapshot(self,snapshot_filename, bw=True):
        return True