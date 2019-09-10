from HardwareRepository.BaseHardwareObjects import Equipment
import numpy
import logging


class PhotonFlux(Equipment):
    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)

    def init(self):
        self.read_counts_chan = self.getChannelObject("counts")
        self.gain = 1e6
        self.calibration_chan = self.getChannelObject("calibration")
        try:
            self.aperture = self.getObjectByRole("aperture")
        except BaseException:
            pass
        self.energy_motor = self.getDeviceByRole("energy")
        self.shutter = self.getDeviceByRole("shutter")
        self.counter = self.getProperty("cnt")
        if self.counter == "i0":
            self.index = self.getProperty("index")
            if self.index is None:
                self.index = 1
        else:
            self.index = 1

        self.read_counts_chan.connectSignal("update", self.countsUpdated)
        self.getChannelObject("flag").connectSignal("update", self.updateFlux)
        self.shutter.connect("shutterStateChanged", self.shutterStateChanged)

    def connectNotify(self, signal):
        if signal == "valueChanged":
            self.emitValueChanged()

    def shutterStateChanged(self, _):
        self.countsUpdated(self.read_counts_chan.getValue())

    def updateFlux(self, _):
        self.countsUpdated(self.read_counts_chan.getValue(), ignore_shutter_state=True)

    def countsUpdated(self, counts, ignore_shutter_state=False):
        if not ignore_shutter_state and self.shutter.getShutterState() != "opened":
            self.emitValueChanged(0)
            return

        try:
            counts = counts[self.index] * self.gain
        except TypeError:
            logging.getLogger("HWR").error("%s: counts is None", self.name())
            return
        flux = None

        try:
            egy = self.energy_motor.getPosition() * 1000.0
        except BaseException:
            logging.getLogger("HWR").exception("%s: could not get energy", self.name())
        else:
            try:
                calib_dict = self.calibration_chan.getValue()
                if calib_dict is None:
                    logging.getLogger("HWR").error(
                        "%s: calibration is None", self.name()
                    )
                else:
                    calibs = sorted(
                        [
                            (float(c["energy"]), float(c[self.counter]))
                            for c in calib_dict.values()
                        ]
                    )
                    E = [c[0] for c in calibs]
                    C = [c[1] for c in calibs]
            except BaseException:
                logging.getLogger("HWR").exception(
                    "%s: could not get calibration", self.name()
                )
            else:
                try:
                    aperture_coef = self.aperture.getApertureCoef()
                except BaseException:
                    aperture_coef = 1
                if aperture_coef <= 0:
                    aperture_coef = 1
                calib = numpy.interp([egy], E, C)
                flux = counts * calib * aperture_coef
                # logging.getLogger("HWR").debug("%s: flux-> %f * %f=%f , calib_dict=%r", self.name(), counts, calib, counts*calib, calib_dict)
                self.emitValueChanged("%1.3g" % flux)

    def getCurrentFlux(self):
        return self.current_flux

    def emitValueChanged(self, counts=None):
        if counts is None:
            self.current_flux = None
            self.emit("valueChanged", ("?",))
        else:
            self.current_flux = float(counts)
            self.emit("valueChanged", (counts,))
