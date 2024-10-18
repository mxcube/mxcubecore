import logging
import math
import time

from calc_flux import CalculateFlux
from PyTango.gevent import DeviceProxy

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.TaskUtils import task


class ID23PhotonFlux(HardwareObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.threshold = []

    def init(self):
        self.counter = DeviceProxy(self.get_property("url"))
        try:
            self.threshold = map(float, self.get_property("threshold").split())
        except AttributeError:
            self.threshold = [0, 9999]
        self.shutter = self.get_deviceby_role("shutter")
        self.aperture = self.get_object_by_role("aperture")
        fname = self.get_property("calibrated_diodes_file")

        self.flux_calc = CalculateFlux()
        self.flux_calc.init(fname)
        self.shutter.connect("shutterStateChanged", self.shutterStateChanged)

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
        try:
            self.counter.MeasureSingle()
            counts = abs(self.counter.ReadData)
            if counts < self.threshold[0] or counts > self.threshold[1]:
                counts = 0
        except AttributeError:
            counts = 0
            logging.getLogger("HWR").exception("%s: could not get counts", self.name())
        try:
            egy = HWR.beamline.energy.get_value() * 1000.0
            calib = self.flux_calc.calc_flux_coef(egy)
        except Exception:
            logging.getLogger("HWR").exception("%s: could not get energy", self.name())
        else:
            if self.aperture is None:
                aperture_coef = 1
            else:
                try:
                    aperture_coef = self.aperture.getApertureCoef()
                except Exception:
                    aperture_coef = 1.0
            counts = math.fabs(counts * calib[0] * aperture_coef) * 10e6
        return counts

    def connect_notify(self, signal):
        if signal == "valueChanged":
            self.emitValueChanged()

    def shutterStateChanged(self, _):
        self.countsUpdated(self._get_counts())

    def updateFlux(self, _):
        self.countsUpdated(self._get_counts(), ignore_shutter_state=False)

    def countsUpdated(self, counts, ignore_shutter_state=False):
        self.emitValueChanged("%1.3g" % counts)

    def get_value(self):
        self.updateFlux("dummy")
        return self.current_flux

    def emitValueChanged(self, flux=None):
        if flux is None:
            self.current_flux = None
            self.emit("valueChanged", ("?",))
        else:
            self.current_flux = flux
            self.emit("valueChanged", (self.current_flux,))
