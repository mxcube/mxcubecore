from mxcubecore.BaseHardwareObjects import Equipment
from mxcubecore.TaskUtils import task
import time
from PyTango.gevent import DeviceProxy


class ID30A3PhotonFlux(Equipment):
    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)

    def init(self):
        controller = self.get_object_by_role("controller")
        self.musst = controller.musst
        self.shutter = self.get_deviceby_role("shutter")
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
        """gain = 20 #20uA
        keithley_voltage = 2
        musst_voltage = int("".join([x for x in self.musst.putget("#?CHCFG CH5") if x.isdigit()]))
        musst_fs = float(0x7FFFFFFF)
        counts = abs((gain/keithley_voltage)*musst_voltage*int(self.musst.putget("#?VAL CH5"))/musst_fs)
        """
        # try:
        self.tg_device.MeasureSingle()
        counts = abs(self.tg_device.ReadData) * 1e6
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

        """
        try:
          counts = counts[self.index]
        except TypeError:
          logging.getLogger("HWR").error("%s: counts is None", self.name())
          return
        flux = None

        try:
          egy = HWR.beamline.energy.get_value()*1000.0
        except:
          logging.getLogger("HWR").exception("%s: could not get energy", self.name())
        else:
          try:
            calib_dict = self.calibration_chan.get_value()
            if calib_dict is None:
              logging.getLogger("HWR").error("%s: calibration is None", self.name())
            else:
              calibs = [(float(c["energy"]), float(c[self.counter])) for c in calib_dict.values()]
              calibs.sort()
              E = [c[0] for c in calibs]
              C = [c[1] for c in calibs]
          except:
            logging.getLogger("HWR").exception("%s: could not get calibration", self.name())
          else:
            try:
              aperture_coef = self.aperture.getApertureCoef()
            except:
              aperture_coef = 1
            if aperture_coef <= 0:
              aperture_coef = 1
            calib = numpy.interp([egy], E, C)
            flux = counts * calib * aperture_coef
            #logging.getLogger("HWR").debug("%s: flux-> %f * %f=%f , calib_dict=%r", self.name(), counts, calib, counts*calib, calib_dict)
            self.emitValueChanged("%1.3g" % flux)
        """

    def get_value(self):
        return self.current_flux

    def emitValueChanged(self, flux=None):
        if flux is None:
            self.current_flux = None
            self.emit("valueChanged", ("?",))
        else:
            self.current_flux = flux
            self.emit("valueChanged", (self.current_flux,))
