import gevent
import shutil
import logging
import os

from HardwareRepository.TaskUtils import task
from .ESRFMultiCollect import ESRFMultiCollect, PixelDetector, TunableEnergy
from HardwareRepository.HardwareObjects.LimaPilatusDetector import LimaPilatusDetector


class ID232MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name, TunableEnergy())

    @task
    def data_collection_hook(self, data_collect_parameters):
        ESRFMultiCollect.data_collection_hook(self, data_collect_parameters)
        self._detector.shutterless = data_collect_parameters["shutterless"]

    def stop_oscillation(self):
        self.getObjectByRole("diffractometer").abort()
        self.getObjectByRole("diffractometer")._wait_ready(20)

    def close_fast_shutter(self):
        state = self.getObjectByRole("fastshut").getActuatorState(read=True)
        if state != "out":
            self.close_fast_shutter()

    @task
    def get_beam_size(self):
        return self.bl_control.beam_info.get_beam_size()

    @task
    def get_slit_gaps(self):
        return (None, None)

    def get_measured_intensity(self):
        return 0

    @task
    def get_beam_shape(self):
        return self.bl_control.beam_info.get_beam_shape()

    @task
    def move_detector(self, detector_distance):
        det_distance = self.getObjectByRole("detector_distance")
        det_distance.set_value(detector_distance)
        while det_distance.motorIsMoving():
            gevent.sleep(0.1)

    @task
    def set_resolution(self, new_resolution):
        self.bl_control.resolution.set_value(new_resolution)
        while self.bl_control.resolution.motorIsMoving():
            gevent.sleep(0.1)

    def get_resolution_at_corner(self):
        return self.bl_control.resolution.get_value_at_corner()

    def get_detector_distance(self):
        det_distance = self.getObjectByRole("detector_distance")
        return det_distance.get_value()

    def ready(*motors):
        return not any([m.motorIsMoving() for m in motors])

    @task
    def move_motors(self, motors_to_move_dict):
        diffr = self.bl_control.diffractometer
        try:
            self.getObjectByRole("controller").detcover.set_out()
        except BaseException:
            pass
        try:
            motors_to_move_dict.pop("kappa")
            motors_to_move_dict.pop("kappa_phi")
        except BaseException:
            pass
        diffr.moveSyncMotors(motors_to_move_dict, wait=True, timeout=200)

    @task
    def take_crystal_snapshots(self, number_of_snapshots):
        diffr = self.getObjectByRole("diffractometer")
        if self.bl_control.diffractometer.in_plate_mode():
            if number_of_snapshots > 0:
                number_of_snapshots = 1
        # diffr.moveToPhase("Centring", wait=True, timeout=200)
        if number_of_snapshots:
            # put the back light in
            diffr.getDeviceByRole("BackLightSwitch").actuatorIn()
            self.bl_control.diffractometer.takeSnapshots(number_of_snapshots, wait=True)
            diffr._wait_ready(20)

    @task
    def do_prepare_oscillation(self, *args, **kwargs):
        diffr = self.getObjectByRole("diffractometer")
        # send again the command as MD2 software only handles one
        # centered position!!
        # has to be where the motors are and before changing the phase
        diffr.getCommandObject("save_centring_positions")()
        # move to DataCollection phase
        if diffr.getPhase() != "DataCollection":
            logging.getLogger("user_level_log").info("Moving MD2 to Data Collection")
        diffr.moveToPhase("DataCollection", wait=True, timeout=200)
        # switch on the front light
        diffr.getObjectByRole("FrontLight").set_value(2)
        # take the back light out
        diffr.getObjectByRole("BackLightSwitch").actuatorOut()

    @task
    def oscil(self, start, end, exptime, npass):
        diffr = self.getObjectByRole("diffractometer")
        if self.helical:
            diffr.oscilScan4d(start, end, exptime, self.helical_pos, wait=True)
        elif self.mesh:
            diffr.oscilScanMesh(
                start,
                end,
                exptime,
                self._detector.get_deadtime(),
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
        energy = self._tunable_bl.get_current_energy()
        diffr = self.getObjectByRole("diffractometer")
        diffr.setNbImages(number_of_images)
        if self.mesh:
            return self._detector.prepare_acquisition(
                take_dark,
                start,
                osc_range,
                exptime,
                npass,
                number_of_images,
                comment,
                energy,
                trigger_mode="EXTERNAL_GATE",
            )
        else:
            return self._detector.prepare_acquisition(
                take_dark,
                start,
                osc_range,
                exptime,
                npass,
                number_of_images,
                comment,
                energy,
                trigger_mode="EXTERNAL_TRIGGER",
            )

    def open_fast_shutter(self):
        self.getObjectByRole("fastshut").actuatorIn()

    def close_fast_shutter(self):
        self.getObjectByRole("fastshut").actuatorOut()

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

    def set_transmission(self, transmission):
        self.getObjectByRole("transmission").set_value(transmission)

    def get_transmission(self):
        return self.getObjectByRole("transmission").get_value()

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
