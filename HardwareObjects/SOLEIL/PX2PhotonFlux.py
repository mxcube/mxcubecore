# -*- coding: utf-8 -*-
from HardwareRepository.BaseHardwareObjects import Equipment
import numpy
import logging
from PyTango.gevent import DeviceProxy


class PX2PhotonFlux(Equipment):
    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)

    def init(self):
        self.read_counts_chan = self.getChannelObject("intensity")
        #self.read_counts_chan = self.getChannelObject("counts")
        #self.calibration_chan = self.getChannelObject("calibration")
        #try:
          #self.aperture_chan = self.getChannelObject("aperture")
        #except:
          #self.aperture_chan = None
        #self.energy_motor = self.getDeviceByRole("energy")
        self.shutter = self.getDeviceByRole("shutter")
        #self.counter = self.getProperty("cnt")
        #if self.counter == "i0":
          #self.index = 1
        #else:
          #self.index = 2
       
        self.read_counts_chan.connectSignal("update", self.countsUpdated) 
        #self.getChannelObject("flag").connectSignal("update", self.updateFlux)

    def connectNotify(self, signal):
        if signal == "valueChanged":
          self.emitValueChanged()

    def updateFlux(self, _):
        self.countsUpdated(self.read_counts_chan.getValue(), ignore_shutter_state=True)

    def countsUpdated(self, counts, ignore_shutter_state=False):
        if not ignore_shutter_state and self.shutter.getShutterState()!="opened":
          self.emitValueChanged(0)
          return

        counts = counts[self.index]
        flux = None

        try:
          egy = self.energy_motor.getPosition()*1000.0
        except:
          logging.getLogger("HWR").exception("%s: could not get energy", self.name())
        else:
          try:
            calib_dict = self.calibration_chan.getValue()
            if calib_dict is None:
              logging.getLogger("HWR").error("%s: calibration is None", self.name())
            else:
              calibs = [(float(c["energy"]), float(c[self.counter])) for c in calib_dict.itervalues()]
              calibs.sort()
              E = [c[0] for c in calibs]
              C = [c[1] for c in calibs]
          except:
            logging.getLogger("HWR").exception("%s: could not get calibration", self.name())
          else:
            try:
              aperture_coef = self.aperture_chan.getValue()
            except:
              aperture_coef = 1
            if aperture_coef <= 0:
              aperture_coef = 1
            calib = numpy.interp([egy], E, C)
            flux = counts * calib * aperture_coef
            #logging.getLogger("HWR").debug("%s: flux-> %f * %f=%f , calib_dict=%r", self.name(), counts, calib, counts*calib, calib_dict)
            self.emitValueChanged("%1.3g" % flux)


    def emitValueChanged(self, counts=None):
        if counts is None:
          self.emit("valueChanged", ("?", ))
        else:
          self.emit("valueChanged", (counts, ))
