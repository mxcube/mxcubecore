from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository.TaskUtils import *
import numpy
import time
import logging
from PyTango.gevent import DeviceProxy

class ID30A1PhotonFlux(Equipment):
    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)

    def init(self):
        controller = self.getObjectByRole("controller")
        self.musst = controller.musst
        self.energy_motor = self.getDeviceByRole("energy")
        self.shutter = self.getDeviceByRole("shutter")
        self.aperture = self.getObjectByRole("aperture")
        self.factor = self.getProperty("current_photons_factor")

        self.shutter.connect("shutterStateChanged", self.shutterStateChanged)
        
        self.tg_device = DeviceProxy("id30/keithley_massif1/i0")
        self.counts_reading_task = self._read_counts_task(wait=False)

    @task
    def _read_counts_task(self):
        old_counts = None
        while True:
            counts = self._get_counts()
            if counts != old_counts:
                old_counts = counts
                self.countsUpdated(counts)
            time.sleep(1)

    def _get_counts(self):
        """counts = abs((2/2.1)*10*int(self.musst.putget("#?VAL CH5")) / float(0x7FFFFFFF))
        if counts < 0:
            counts = 0
        """
        self.tg_device.MeasureSingle()
        counts = abs(self.tg_device.ReadData)*1E6
        if self.aperture:
            try:
                aperture_coef = self.aperture.getApertureCoef()
            except Exception:
                aperture_coef = 1
        else:
            aperture_coef = 1

        counts *= aperture_coef
        return counts

    def connectNotify(self, signal):
        if signal == "valueChanged":
          self.emitValueChanged()

    def shutterStateChanged(self, _):
        self.countsUpdated(self._get_counts())

    def updateFlux(self, _):
        self.countsUpdated(self._get_counts(), ignore_shutter_state=True)

    def countsUpdated(self, counts, ignore_shutter_state=False):
        #if not ignore_shutter_state and self.shutter.getShutterState()!="opened":
        #  self.emitValueChanged(0)
        #  return
        flux = counts * self.factor
        self.emitValueChanged("%1.3g" % flux)

    def getCurrentFlux(self):
        return self.current_flux

    def emitValueChanged(self, flux=None):
        self.current_flux = flux

        if flux is None:
            self.emit("valueChanged", ("?", ))
        else:
            self.emit("valueChanged", (self.current_flux, ))
