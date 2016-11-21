from ESRF.ESRFEnergyScan import *
import logging
import id29_calc_gaps as calc_gaps
from datetime import datetime

class ID29EnergyScan(ESRFEnergyScan):
    def __init__(self, name):
        ESRFEnergyScan.__init__(self, name, TunableEnergy())

    @task
    def energy_scan_hook(self, energy_scan_parameters):
        self.energy = energy_scan_parameters["edgeEnergy"]
        #self.move_undulators(self.calculate_und_gaps(self.energy, "u21d"))
        if self.energy_scan_parameters['findattEnergy']:
            ESRFEnergyScan.move_energy(self,energy_scan_parameters['findattEnergy'])

    @task
    def move_undulators(self, gaps):
        self.undulators = self.getObjectByRole("undulators")
        for key in gaps:   
            logging.getLogger("HWR").debug("Moving undulator %s to %g" %( key, gaps[key]))

        self.undulators.moveUndulatorGaps(gaps)

      
    def calculate_und_gaps(self, energy, undulator="u21d"):
        GAPS = {}
        cg = calc_gaps.CalculateGaps(energy)
        GAPS = cg._calc_gaps(energy,undulator)
        return GAPS

    @task
    def set_mca_roi(self, eroi_min, eroi_max):
        self.mca = self.getObjectByRole("MCA")
        self.energy_scan_parameters['fluorescenceDetector'] = self.mca.getProperty("username")
        #check if roi in ev or keV
        if eroi_min > 1000:
            eroi_min /= 1000
            eroi_max /= 1000
        self.mca.set_roi(eroi_min, eroi_max, channel=1, element=self.energy_scan_parameters["element"], atomic_nb=self.energy_scan_parameters["atomic_nb"])
        print self.mca.get_roi()

    @task
    def choose_attenuation(self):
        eroi_min = self.energy_scan_parameters["eroi_min"]
        eroi_max = self.energy_scan_parameters["eroi_max"]
        min_ic = self.getProperty("min_integrated_counts")
        max_ic = self.getProperty("max_integrated_counts")
        self.ctrl.detcover.set_in()
        self.ctrl.find_attenuation(ctime=2,emin=eroi_min,emax=eroi_max, min_ic=min_ic,max_ic=max_ic, tm=self.transmission._Transmission__transmission)
        self.energy_scan_parameters["transmissionFactor"] = self.transmission.get_value()

    @task
    def execute_energy_scan(self, energy_scan_parameters):
        startE = energy_scan_parameters["startEnergy"]
        endE = energy_scan_parameters["endEnergy"]
        dd = datetime.now()
        fname = "%s/%s_%s_%s_%s.scan" % (energy_scan_parameters["directory"], energy_scan_parameters["prefix"], datetime.strftime(dd, "%d"), datetime.strftime(dd, "%B"), datetime.strftime(dd, "%Y"))

        self.ctrl.do_energy_scan(startE, endE, datafile=fname)

        self.energy_scan_parameters["exposureTime"] = self.ctrl.MONOSCAN_INITSTATE["exposure_time"]
        
        
    def canScanEnergy(self):
        return True

    def canMoveEnergy(self):
        return self.canScanEnergy()

    def escan_prepare(self):
        self.ctrl = self.getObjectByRole("controller")

        self.ctrl.detcover.set_in()
        self.ctrl.diffractometer.fldetin()
        self.ctrl.diffractometer.set_phase("DataCollection", wait=True) 

        if self.beamsize:
            bsX = self.beamsize.getCurrentPositionName()
            bsY = bsX
        else:
            bsX = self.execute_command("get_beam_size_x") * 1000.
            bsY = self.execute_command("get_beam_size_y") * 1000.
        self.energy_scan_parameters["beamSizeHorizontal"] = bsX
        self.energy_scan_parameters["beamSizeVertical"] = bsY


    def escan_postscan(self):
        self.ctrl.diffractometer.fldetout()

    def close_fast_shutter(self):
        self.ctrl.diffractometer.msclose()

    def open_fast_shutter(self):
        self.ctrl.diffractometer.msopen()

    def open_safety_shutter(self, timeout=None):
        pass

    def close_safety_shutter(self, timeout=None):
        pass
