from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository.TaskUtils import task
import time
import logging


class ID30BPhotonFlux(Equipment):
    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)

    def init(self):
        self.controller = self.getObjectByRole("controller")
        self.shutter = self.getDeviceByRole("shutter")
        self.aperture = self.getObjectByRole("aperture")
        self.flux_calc = self.controller.CalculateFlux()
        fname = self.getProperty("calibrated_diodes_file")
        if fname:
            self.flux_calc.init(fname)
        counter = self.getProperty("counter_name")
        if counter:
            self.counter = getattr(self.controller, counter)
        else:
            self.counter = self.getObjectByRole("counter")
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
            counts = self.counter.read()
            if counts == -9999:
                counts = 0
        except Exception:
            counts = 0
            logging.getLogger("HWR").exception("%s: could not get counts", self.name())
        try:
            egy = beamline_object.energy.get_current_energy() * 1000.0
            calib = self.flux_calc.calc_flux_factor(egy)
        except BaseException:
            logging.getLogger("HWR").exception("%s: could not get energy", self.name())
        try:
            aperture_factor = self.aperture.getApertureCoef()
        except AttributeError:
            aperture_factor = 1
        counts = abs(counts * calib[self.counter.name] * aperture_factor)
        return counts

    def connectNotify(self, signal):
        if signal == "valueChanged":
            self.emitValueChanged()

    def shutterStateChanged(self, _):
        self.countsUpdated(self._get_counts())

    def updateFlux(self, _):
        self.countsUpdated(self._get_counts(), ignore_shutter_state=False)

    def countsUpdated(self, counts, ignore_shutter_state=False):
        if not ignore_shutter_state and self.shutter.getShutterState() != "opened":
            self.emitValueChanged(0)
            return
        flux = counts
        self.emitValueChanged("%1.3g" % flux)

    def getCurrentFlux(self):
        self.updateFlux("dummy")
        return self.current_flux

    def emitValueChanged(self, flux=None):
        if flux is None:
            self.current_flux = None
            self.emit("valueChanged", ("?",))
        else:
            self.current_flux = flux
            self.emit("valueChanged", (self.current_flux,))
