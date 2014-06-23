from HardwareRepository import BaseHardwareObjects
import logging
import PyTango.gevent
import gevent
import time


class ID30HutchTrigger(BaseHardwareObjects.HardwareObject):
    def __init__(self, name):
        BaseHardwareObjects.HardwareObject.__init__(self, name)

    def _do_polling(self):
        while True:
          self.poll()
          time.sleep(self.getProperty("interval")/1000.0 or 1)

    def init(self):
        try:
            self.device = PyTango.gevent.DeviceProxy(self.getProperty("tangoname"))
        except PyTango.DevFailed, traceback:
            last_error = traceback[-1]
            logging.getLogger('HWR').error("%s: %s", str(self.name()), last_error['desc'])
            self.device = None
            self.device.imported = False
        else:
            self.device.imported = True

        self.pollingTask=None
        self.initialized = False
        self.__oldValue = None
        self.card = None
        self.channel = None

        PSSinfo = self.getProperty("pss")
        try:
            self.card, self.channel = map(int, PSSinfo.split("/"))
        except:
            logging.getLogger().error("%s: cannot find PSS number", self.name())
            return

        if self.device is not None:
            self.pollingTask = gevent.spawn(self._do_polling)
           
        self.connected()
 

    def isConnected(self):
        return True

        
    def connected(self):
        self.emit('connected')
        
        
    def disconnected(self):
        self.emit('disconnected')


    def abort(self):
        pass
        
  
    def macro(self, entering_hutch):
        #import pdb;pdb.set_trace()
        logging.debug("HUTCHTRIGGER, entering_hutch=%s", entering_hutch)
        if entering_hutch:
          self.getObjectByRole("detector_distance")
          self.getObjectByRole("beamstop")
        else:
          self.getObjectByRole("detector_distance")
          self.getObjectByRole("beamstop")

 
    def poll(self):
        a=self.device.GetInterlockState([self.card-1, 2*(self.channel-1)])[0]
        b=self.device.GetInterlockState([self.card-1, 2*(self.channel-1)+1])[0]
        value = a&b

        if value == self.__oldValue:
            return
        else:
            self.__oldValue = value

        self.valueChanged(value)
        

    def valueChanged(self, value, *args):
        if value == 0:
            if self.initialized:
                self.emit('hutchTrigger', (1, ))
        elif value == 1 and self.initialized:
            self.emit('hutchTrigger', (0, ))

	self.initialized = True

