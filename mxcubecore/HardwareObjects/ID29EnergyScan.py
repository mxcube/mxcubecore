from ESRFEnergyScan import *
import logging
import calc_gaps

class ID29EnergyScan(ESRFEnergyScan):
    def __init__(self, name):
        ESRFEnergyScan.__init__(self, name, TunableEnergy())

    @task
    def energy_scan_hook(self, energy_scan_parameters):
        self.energy = energy_scan_parameters["edgeEnergy"]
        self.move_undulators(self.calculate_und_gaps(self.energy, "u21d"))
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
        self.execute_command("calculateMcaRoi",eroi_min, eroi_max)

    @task
    def choose_attenuation(self):
        self.execute_command("chooseAttenuation")
        self.energy_scan_parameters["transmissionFactor"] = self.transmission.getAttFactor()

    @task
    def execute_energy_scan(self, energy_scan_parameters):
        self.execute_command("executeScan", energy_scan_parameters)
        
    def canScanEnergy(self):
        return True

    def canMoveEnergy(self):
        return self.canScanEnergy()
