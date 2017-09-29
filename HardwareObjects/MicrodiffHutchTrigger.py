from HardwareRepository import BaseHardwareObjects
import logging
import PyTango.gevent
import gevent
import time
import sys

"""
Read the state of the hutch from the PSS device server and take actions
when enter (1) or interlock (0) the hutch.
0 = The hutch has been interlocked and the sample environment should be made 
     ready for data collection. The actions are extract the detector cover,
     move the detector to its previous position, set the MD2 to Centring.
1 = The interlock is cleared and the user is entering the hutch to change
      the sample(s). The actions are insert the detector cover, move the
      detecto to a safe position, set MD2 to sample Transfer.
"""

class MicrodiffHutchTrigger(BaseHardwareObjects.HardwareObject):
    def __init__(self, name):
        BaseHardwareObjects.HardwareObject.__init__(self, name)

    def _do_polling(self):
        while True: 
          try:
              self.poll()
          except:
              sys.excepthook(*sys.exc_info())
          time.sleep(self.getProperty("interval")/1000.0 or 1)

    def init(self):
        try:
            self.device = PyTango.gevent.DeviceProxy(self.getProperty("tangoname"))
        except PyTango.DevFailed, traceback:
            last_error = traceback[-1]
            logging.getLogger('HWR').error("%s: %s", str(self.name()), last_error['desc'])
            self.device = None

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
 
    def hutchIsOpened(self):
        return self.hutch_opened

    def isConnected(self):
        return True

        
    def connected(self):
        self.emit('connected')
        
        
    def disconnected(self):
        self.emit('disconnected')


    def abort(self):
        pass
    
    def macro(self, entering_hutch, old={"dtox":None}):
        logging.info("%s: %s hutch", self.name(), "entering" if entering_hutch else "leaving")
        dtox = self.getObjectByRole("detector_distance")
        udiff_ctrl = self.getObjectByRole("predefined")
        ctrl_obj = self.getObjectByRole("controller")
        if not entering_hutch:
            ctrl_obj.detcover.set_out()
            if old["dtox"] is not None:
                print "Moving %s to %g" % (dtox.name(), old["dtox"])
                dtox.move(old["dtox"])
            udiff_ctrl.moveToPhase(phase="Centring",wait=True)
        else:
            ctrl_obj.detcover.set_in()
            old["dtox"] = dtox.getPosition()
            dtox.move(700)
            udiff_ctrl.moveToPhase(phase="Transfer",wait=True)

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

        self.hutch_opened = 1-value
        self.initialized = True

