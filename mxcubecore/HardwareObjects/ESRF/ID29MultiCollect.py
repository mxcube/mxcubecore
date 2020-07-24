import gevent
import shutil
import logging
import os

from HardwareRepository.TaskUtils import task
from .ESRFMultiCollect import ESRFMultiCollect, PixelDetector, TunableEnergy
from HardwareRepository.HardwareObjects.LimaPilatusDetector import LimaPilatusDetector


class ID29MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name, TunableEnergy())

    @task
    def data_collection_hook(self, data_collect_parameters):
        ESRFMultiCollect.data_collection_hook(self, data_collect_parameters)

        self._detector.shutterless = data_collect_parameters["shutterless"]

    def stop_oscillation(self):
        self.get_object_by_role("diffractometer").abort()
        self.get_object_by_role("diffractometer")._wait_ready(20)

    def close_fast_shutter(self):
        state = self.get_object_by_role("fastshut").get_actuator_state(read=True)
        if state != "out":
            self.close_fast_shutter()

    @task
    def get_beam_size(self):
        return self.bl_control.beam_info.get_beam_size()

    @task
    def get_slit_gaps(self):
        self.get_object_by_role("controller")

        return (None, None)

    @task
    def get_beam_shape(self):
        return self.bl_control.beam_info.get_beam_shape()

    def get_resolution_at_corner(self):
        return self.bl_control.resolution.get_value_at_corner()

    def ready(*motors):
        return not any([m.motorIsMoving() for m in motors])

    @task
    def move_motors(self, motors_to_move_dict):
        # We do not wnta to modify the input dict
        motor_positions_copy = motors_to_move_dict.copy()
        diffr = self.bl_control.diffractometer
        for tag in ("kappa", "kappa_phi"):
            if tag in motor_positions_copy:
                del motor_positions_copy[tag]
        diffr.move_sync_motors(motors_to_move_dict, wait=True, timeout=200)

    @task
    def take_crystal_snapshots(self, number_of_snapshots):
        diffr = self.get_object_by_role("diffractometer")
        if self.bl_control.diffractometer.in_plate_mode():
            if number_of_snapshots > 0:
                number_of_snapshots = 1
        # diffr.moveToPhase("Centring", wait=True, timeout=200)
        if number_of_snapshots:
            # put the back light in
            diffr.get_deviceByRole("BackLightSwitch").actuatorIn()
            self.bl_control.diffractometer.take_snapshots(
                number_of_snapshots, wait=True
            )
            diffr._wait_ready(20)

    @task
    def do_prepare_oscillation(self, *args, **kwargs):
        self.get_object_by_role("controller").detcover.set_out()
        diffr = self.get_object_by_role("diffractometer")
        # send again the command as MD2 software only handles one
        # centered position!!
        # has to be where the motors are and before changing the phase
        diffr.get_command_object("save_centring_positions")()
        # move to DataCollection phase
        if diffr.getPhase() != "DataCollection":
            logging.getLogger("user_level_log").info("Moving MD2 to Data Collection")
        diffr.moveToPhase("DataCollection", wait=True, timeout=200)
        # switch on the front light
        diffr.get_object_by_role("FrontLight").set_value(2)

    @task
    def oscil(self, start, end, exptime, npass):
        diffr = self.get_object_by_role("diffractometer")
        if self.helical:
            diffr.oscilScan4d(start, end, exptime, self.helical_pos, wait=True)
        elif self.mesh:
            det = self._detector._detector
            latency_time = (
                det.config.get_property("latecy_time_mesh") or det.get_deadtime()
            )
            diffr.oscilScanMesh(
                start,
                end,
                exptime,
                latency_time,
                self.mesh_num_lines,
                self.mesh_total_nb_frames,
                self.mesh_center,
                self.mesh_range,
                wait=True,
            )
        else:
            diffr.oscilScan(start, end, exptime, wait=True)

    def prepare_acquisition(
        self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""
    ):
        if self.mesh:
            trigger_mode = "EXTERNAL_GATE"
        else:
            trigger_mode = None  # will be determined by ESRFMultiCollect
        return ESRFMultiCollect.prepare_acquisition(
            self,
            take_dark,
            start,
            osc_range,
            exptime,
            npass,
            number_of_images,
            comment,
            trigger_mode,
        )

    def open_fast_shutter(self):
        self.get_object_by_role("fastshut").actuatorIn()

    def close_fast_shutter(self):
        self.get_object_by_role("fastshut").actuatorOut()

    def set_helical(self, helical_on):
        self.helical = helical_on

    def set_helical_pos(self, helical_oscil_pos):
        self.helical_pos = helical_oscil_pos

    # specifies the next scan will be a mesh scan
    def set_mesh(self, mesh_on):
        self.mesh = mesh_on

    def set_mesh_scan_parameters(
        self, num_lines, total_nb_frames, mesh_center_param, mesh_range_param
    ):
        """
        sets the mesh scan parameters :
         - vertcal range
         - horizontal range
         - nb lines
         - nb frames per line
         - invert direction (boolean)  # NOT YET DONE
         """
        self.mesh_num_lines = num_lines
        self.mesh_total_nb_frames = total_nb_frames
        self.mesh_range = mesh_range_param
        self.mesh_center = mesh_center_param

    def get_cryo_temperature(self):
        return 0

    @task
    def prepare_intensity_monitors(self):
        return

    def get_beam_centre(self):
        return self.bl_control.resolution.get_beam_centre()

    @task
    def write_input_files(self, datacollection_id):
        try:
            process_dir = os.path.join(self.xds_directory, "..")
            raw_process_dir = os.path.join(self.raw_data_input_file_dir, "..")
            for dir in (process_dir, raw_process_dir):
                for filename in ("x_geo_corr.cbf.bz2", "y_geo_corr.cbf.bz2"):
                    dest = os.path.join(dir, filename)
                    if os.path.exists(dest):
                        continue
                    shutil.copyfile(
                        os.path.join("/data/id29/inhouse/opid291", filename), dest
                    )
        except BaseException:
            logging.exception("Exception happened while copying geo_corr files")

        return ESRFMultiCollect.write_input_files(self, datacollection_id)
