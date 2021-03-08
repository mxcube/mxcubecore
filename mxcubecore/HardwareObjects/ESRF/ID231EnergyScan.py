from mxcubecore.TaskUtils import task
from .ESRFEnergyScan import ESRFEnergyScan, TunableEnergy


class ID231EnergyScan(ESRFEnergyScan):
    def __init__(self, name):
        ESRFEnergyScan.__init__(self, name, TunableEnergy())

    @task
    def energy_scan_hook(self, energy_scan_parameters):
        self.energy = energy_scan_parameters["edgeEnergy"]
        if self.energy_scan_parameters["findattEnergy"]:
            ESRFEnergyScan.move_energy(self, energy_scan_parameters["findattEnergy"])

    def calculate_und_gaps(self, energy, undulator="u21d"):
        GAPS = {}
        return GAPS

    @task
    def move_undulators(self, gaps):
        pass

    @task
    def set_mca_roi(self, eroi_min, eroi_max):
        self.execute_command("calculateMcaRoi", eroi_min, eroi_max)

    @task
    def choose_attenuation(self):
        self.execute_command("chooseAttenuation")
        self.energy_scan_parameters[
            "transmissionFactor"
        ] = self.transmission.get_value()

    @task
    def execute_energy_scan(self, energy_scan_parameters):
        self.execute_command("executeScan", energy_scan_parameters)
