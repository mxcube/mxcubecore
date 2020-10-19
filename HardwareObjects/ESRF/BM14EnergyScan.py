import logging
from HardwareRepository.TaskUtils import task
from ESRFEnergyScan import ESRFEnergyScan, TunableEnergy


class BM14EnergyScan(ESRFEnergyScan):
    def __init__(self, name):
        ESRFEnergyScan.__init__(self, name, TunableEnergy())

    @task
    def energy_scan_hook(self, energy_scan_parameters):
        self.energy = energy_scan_parameters["edgeEnergy"]
        if self.energy_scan_parameters["findattEnergy"]:
            ESRFEnergyScan.move_energy(self, energy_scan_parameters["findattEnergy"])

    @task
    def move_undulators(self, gaps):
        return

    @task
    def set_mca_roi(self, eroi_min, eroi_max):
        self.execute_command("calculateMcaRoi", eroi_min, eroi_max)

    @task
    def choose_attenuation(self):
        if self.execute_command("chooseAttenuation") == -1:
            logging.getLogger("user_level_log").error(
                "Cannot find appropriate attenuation"
            )
            raise RuntimeError("Cannot find appropriate attenuation")
        self.energy_scan_parameters[
            "transmissionFactor"
        ] = self.transmission.get_value()

    @task
    def execute_energy_scan(self, energy_scan_parameters):
        energy_scan_parameters["exposureTime"] = self.get_property("exposureTime")
        self.execute_command("executeScan", energy_scan_parameters)
        self.energy_scan_parameters["exposureTime"] = energy_scan_parameters[
            "exposureTime"
        ]
