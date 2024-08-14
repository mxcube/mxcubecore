from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.TaskUtils import task
import time

# from PyTango.gevent import DeviceProxy
from PyTango import DeviceProxy


class TangoKeithleyPhotonFlux(HardwareObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def init(self):
        self.get_object_by_role("controller")
        self.shutter = self.get_deviceby_role("shutter")
        self.aperture = self.get_object_by_role("aperture")
        self.factor = self.get_property("current_photons_factor")

        self.shutter.connect("shutterStateChanged", self.shutterStateChanged)

        self.tg_device = DeviceProxy(self.get_property("tango_device"))
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
        self.tg_device.MeasureSingle()
        counts = abs(self.tg_device.ReadData) * 1e6
        if self.aperture:
            try:
                aperture_coef = self.aperture.getApertureCoef()
            except Exception:
                aperture_coef = 1
        else:
            aperture_coef = 1

        counts *= aperture_coef
        return counts

    def connect_notify(self, signal):
        if signal == "valueChanged":
            self.emitValueChanged()

    def shutterStateChanged(self, _):
        self.countsUpdated(self._get_counts())

    def updateFlux(self, _):
        self.countsUpdated(self._get_counts(), ignore_shutter_state=True)

    def countsUpdated(self, counts, ignore_shutter_state=False):
        if not ignore_shutter_state and self.shutter.getShutterState() != "opened":
            self.emitValueChanged(0)
            return
        flux = counts * self.factor
        self.emitValueChanged("%1.3g" % flux)

    def get_value(self):
        return self.current_flux

    def emitValueChanged(self, flux=None):
        self.current_flux = flux

        if flux is None:
            self.emit("valueChanged", ("?",))
        else:
            self.emit("valueChanged", (self.current_flux,))
