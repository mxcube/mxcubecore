from datetime import datetime

from mxcubecore import HardwareRepository as HWR

from .ESRFEnergyScan import ESRFEnergyScan


class ID29EnergyScan(ESRFEnergyScan):

    def energy_scan_hook(self, energy_scan_parameters):
        self.energy = energy_scan_parameters["edgeEnergy"]
        if self.energy_scan_parameters["findattEnergy"]:
            HWR.beamline.energy.set_value(energy_scan_parameters["findattEnergy"])

    def set_mca_roi(self, eroi_min, eroi_max):
        """
        self.mca = self.get_object_by_role("MCA")
        self.energy_scan_parameters["fluorescenceDetector"] = self.mca.get_property(
            "username"
        )
        """
        self.energy_scan_parameters["fluorescenceDetector"] = "KETEK_AXAS-A"
        # check if roi in eV or keV
        if eroi_min > 1000:
            eroi_min /= 1000.0
            eroi_max /= 1000.0
        self.ctrl.mca.set_roi(
            eroi_min,
            eroi_max,
            channel=1,
            element=self.energy_scan_parameters["element"],
            atomic_nb=self.energy_scan_parameters["atomic_nb"],
        )
        print(self.ctrl.mca.get_roi())

    def choose_attenuation(self):
        eroi_min = self.energy_scan_parameters["eroi_min"]
        eroi_max = self.energy_scan_parameters["eroi_max"]
        self.ctrl.detcover.set_in()
        self.ctrl.find_max_attenuation(ctime=2, roi=[eroi_min, eroi_max], datafile="/tmp/abb")
        self.energy_scan_parameters[
            "transmissionFactor"
        ] = HWR.beamline.transmission.get_value()

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
        self.ctrl.energy_scan.do_energy_scan(startE, endE, datafile=fname)

        """
        self.energy_scan_parameters["exposureTime"] = self.ctrl.MONOSCAN_INITSTATE[
            "exposure_time"
        ]
        """

    def escan_prepare(self):
        self.ctrl = self.get_object_by_role("controller")

        self.ctrl.detcover.set_in()
        self.ctrl.diffractometer.fldet_in()
        #self.ctrl.fluodet.IN
        self.ctrl.diffractometer.set_phase("DataCollection")

        if self.beamsize:
            # get the aperture size
            bsX = self.beamsize.get_size(self.beamsize.get_value().name)
            self.energy_scan_parameters["beamSizeHorizontal"] = bsX
            self.energy_scan_parameters["beamSizeVertical"] = bsX
