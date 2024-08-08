"""
  File:  BIOMAXDozor.py
  Description:  This module generates dozor.dat to run dozor
"""
import os
import logging
from mxcubecore.BaseHardwareObjects import HardwareObject


class BIOMAXDozor(HardwareObject):
    def __init__(self, name):
        super().__init__(name)
        self.config = {}
        self.dozor_script = None
        self.collector_script = None
        self.hpc_host = None
        self.dozor_proc_dir = None

    def init(self):
        self.config = {
            "nx": 4150,
            "ny": 4371,
            "pixel": 0.075,
            "pixel_min": 0,
            "pixel_max": 65534,
            "fraction_polarization": 0.99,
            "detector_distance": 0,
            "X-ray_wavelength": 1.0,
            "orgx": 0,
            "orgy": 0,
            "spot_size": 3,
            "exposure": 0.01,
            "oscillation_range": 0.10,
            "ix_min": 0,
            "ix_max": 0,
            "iy_min": 0,
            "iy_max": 0,
        }
        self.dozor_script = self.get_property("dozor_script")
        self.collector_script = self.get_property("collector_script")
        self.stop_script = self.get_property("stop_script")
        self.hpc_host = self.get_property("hpc_host")

    def write_dozor_dat(self, path):
        self.dozor_proc_dir = path
        dozor_filename = os.path.join(path, "dozor.dat")
        try:
            output = ""
            for key, value in self.config.items():
                output += f"{key} {str(value)}\n"
            output += "end"
            dozor_dat = open(dozor_filename, "w")
            dozor_dat.write(output)
        except Exception as ex:
            logging.getLogger("HWR").exception(
                "[DOZOR] Cannot write Dozor.dat Error: %s" % ex
            )
            raise RuntimeError("[DOZOR] Error while writting dozor.dat file")
        finally:
            dozor_dat.close()

        return dozor_filename

    def execute_dozor(self, path):
        cmd = f"cd {os.path.dirname(path)};{self.dozor_script} 3 {path}"
        ssh_cmd = f'echo "{cmd}" | ssh {self.hpc_host} &'
        os.system(ssh_cmd)
        logging.getLogger("HWR").debug(ssh_cmd)
        logging.getLogger("HWR").info("[DOZOR] Launching dozor now")
        return

    def execute_dozor_collector(self, path):
        cmd = f"cd {os.path.dirname(path)};{self.collector_script} {path}"
        ssh_cmd = f'echo "{cmd}" | ssh {self.hpc_host} &'
        os.system(ssh_cmd)
        logging.getLogger("HWR").info(ssh_cmd)
        logging.getLogger("HWR").info("[DOZOR] Launching dozor collector now")
        return

    def stop_dozor(self, jobid_path=None):
        cmd = f"cd {self.dozor_proc_dir};{self.stop_script} {jobid_path}"
        ssh_cmd = f'echo "{cmd}" | ssh {self.hpc_host} &'
        os.system(ssh_cmd)
        logging.getLogger("HWR").info(ssh_cmd)
        logging.getLogger("HWR").info("[DOZOR] Stopping dozor and collector now")
        return
