from .ESRFEnergyScan import ESRFEnergyScan, TunableEnergy, task
from datetime import datetime


class ID29EnergyScan(ESRFEnergyScan):
    def __init__(self, name):
        ESRFEnergyScan.__init__(self, name, TunableEnergy())

    @task
    def energy_scan_hook(self, energy_scan_parameters):
        self.energy = energy_scan_parameters["edgeEnergy"]
        if self.energy_scan_parameters["findattEnergy"]:
            ESRFEnergyScan.move_energy(self, energy_scan_parameters["findattEnergy"])

    @task
    def move_undulators(self, gaps):
        pass

    def calculate_und_gaps(self, energy, undulator=None):
        pass

    @task
    def set_mca_roi(self, eroi_min, eroi_max):
        self.mca = self.get_object_by_role("MCA")
        self.energy_scan_parameters["fluorescenceDetector"] = self.mca.get_property(
            "username"
        )
        # check if roi in eV or keV
        if eroi_min > 1000:
            eroi_min /= 1000.0
            eroi_max /= 1000.0
        self.mca.set_roi(
            eroi_min,
            eroi_max,
            channel=1,
            element=self.energy_scan_parameters["element"],
            atomic_nb=self.energy_scan_parameters["atomic_nb"],
        )
        print(self.mca.get_roi())

    @task
    def choose_attenuation(self):
        eroi_min = self.energy_scan_parameters["eroi_min"]
        eroi_max = self.energy_scan_parameters["eroi_max"]
        self.ctrl.detcover.set_in()
        self.ctrl.find_max_attenuation(
            ctime=2, roi=[eroi_min, eroi_max], datafile="/tmp/abb"
        )
        self.energy_scan_parameters[
            "transmissionFactor"
        ] = self.transmission.get_value()

    @task
    def execute_energy_scan(self, energy_scan_parameters):
        startE = energy_scan_parameters["startEnergy"]
        endE = energy_scan_parameters["endEnergy"]
        dd = datetime.now()
        fname = "%s/%s_%s_%s_%s.scan" % (
            energy_scan_parameters["directory"],
            energy_scan_parameters["prefix"],
            datetime.strftime(dd, "%d"),
            datetime.strftime(dd, "%B"),
            datetime.strftime(dd, "%Y"),
        )
        self.ctrl.do_energy_scan(startE, endE, datafile=fname)
        # self.energy_scan_parameters["exposureTime"] = exposure_time
        self.energy_scan_parameters["exposureTime"] = 10.11

    def escan_prepare(self):
<<<<<<< HEAD
        self.ctrl = self.get_object_by_role("controller")

=======
        self.ctrl = self.get_object_by_role("controller")
>>>>>>> upstream/master
        self.ctrl.detcover.set_in()
        self.ctrl.diffractometer.fldet_in()
        self.ctrl.diffractometer.set_phase("DataCollection", wait=True)

        if self.beamsize:
            # get the aperture size
            bsX = self.beamsize.get_size(self.beamsize.get_value().name)
            self.energy_scan_parameters["beamSizeHorizontal"] = bsX
            self.energy_scan_parameters["beamSizeVertical"] = bsX

    def escan_postscan(self):
        self.ctrl.diffractometer.fldet_out()

    def close_fast_shutter(self):
        self.ctrl.diffractometer.msclose()

    def open_fast_shutter(self):
        self.ctrl.diffractometer.msopen()

    def open_safety_shutter(self, timeout=None):
        pass

    def close_safety_shutter(self, timeout=None):
        pass
