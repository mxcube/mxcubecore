import gevent
import shutil
import logging
import os

from HardwareRepository.TaskUtils import task
from .ESRFMultiCollect import ESRFMultiCollect
from HardwareRepository.HardwareObjects.LimaPilatusDetector import LimaPilatusDetector

from HardwareRepository import HardwareRepository as HWR


class MD2MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name)

    @task
    def data_collection_hook(self, data_collect_parameters):
        ESRFMultiCollect.data_collection_hook(self, data_collect_parameters)
        self._detector.shutterless = data_collect_parameters["shutterless"]

        try:
            comment = HWR.beamline.sample_changer.get_crystal_id()
            data_collect_parameters["comment"] = comment
        except Exception:
            pass

        check_flux_and_cryo = self.getProperty("check_flux_and_cryo", False)
        flux_threshold = self.getProperty("flux_threshold")
        cryo_threshold = self.getProperty("cryo_threshold")

        if check_flux_and_cryo:
            # Wait for flux
            while HWR.beamline.flux.get_value() < flux_threshold:
                logging.getLogger("user_level_log").info("Waiting for beam ...")
                gevent.sleep(0.5)

            # Wait for cryo
            while HWR.beamline.diffractometer.cryostream.get_value() > cryo_threshold:
                logging.getLogger("user_level_log").info("Cryo temperature too high ...")
                gevent.sleep(0.5)

    @task
    def get_beam_size(self):
        return HWR.beamline.beam.beam_width, HWR.beamline.beam.beam_height

    @task
    def get_slit_gaps(self):
        self.getObjectByRole("controller")

        return (None, None)

    @task
    def get_beam_shape(self):
        return HWR.beamline.beam.get_value()[2].name

    def get_resolution_at_corner(self):
        return HWR.beamline.resolution.get_value_at_corner()

    def ready(*motors):
        return not any([m.motorIsMoving() for m in motors])

    @task
    def move_motors(self, motors_to_move_dict):
        # We do not want to modify the input dict
        motor_positions_copy = motors_to_move_dict.copy()
        diffr = HWR.beamline.diffractometer
        for tag in ("kappa", "kappa_phi", "zoom"):
            if tag in motor_positions_copy:
                del motor_positions_copy[tag]

        diffr.move_sync_motors(motor_positions_copy, wait=True, timeout=200)

    @task
    def take_crystal_snapshots(self, number_of_snapshots):
        if HWR.beamline.diffractometer.in_plate_mode():
            if number_of_snapshots > 0:
                number_of_snapshots = 1
        else:
            # this has to be done before each chage of phase
            HWR.beamline.diffractometer.save_centring_positions()
            # not going to centring phase if in plate mode (too long)
            HWR.beamline.diffractometer.set_phase("Centring", wait=True, timeout=200)

        HWR.beamline.diffractometer.take_snapshots(number_of_snapshots, wait=True)

    def do_prepare_oscillation(self, *args, **kwargs):
        # set the detector cover out
        try:
            detcover = self.getObjectByRole("controller").detcover

            if detcover.state == "IN":
                detcover.set_out(10)
        except:
            logging.getLogger("HWR").exception("Got the tricky one !")

        diffr = HWR.beamline.diffractometer

        # send again the command as MD2 software only handles one
        # centered position!!
        # has to be where the motors are and before changing the phase
        # diffr.get_command_object("save_centring_positions")()

        # move to DataCollection phase
        logging.getLogger("user_level_log").info("Moving MD2 to Data Collection")
        diffr.set_phase("DataCollection", wait=True, timeout=200)

        # switch on the front light
        front_light_switch = diffr.getObjectByRole("FrontLightSwitch")
        front_light_switch.set_value(front_light_switch.VALUES.IN)
        # diffr.getObjectByRole("FrontLight").set_value(2)

    @task
    def data_collection_cleanup(self):
        self.getObjectByRole("diffractometer")._wait_ready(10)
        self.close_fast_shutter()

    @task
    def oscil(self, start, end, exptime, npass, wait=True):
        diffr = self.getObjectByRole("diffractometer")
        if self.helical:
            diffr.oscilScan4d(start, end, exptime, self.helical_pos, wait=True)
        elif self.mesh:
            det = HWR.beamline.detector
            latency_time = det.getProperty("latecy_time_mesh") or det.get_deadtime()
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
        trigger_mode = "EXTERNAL_GATE" if self.mesh else None
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
        fs = HWR.beamline.fast_shutter
        fs.set_value(fs.VALUES.OPEN)

    def close_fast_shutter(self):
        fs = HWR.beamline.fast_shutter
        fs.set_value(fs.VALUES.CLOSED)

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
        return HWR.beamline.detector.get_beam_position()

    @task
    def write_input_files(self, datacollection_id):
        # copy *geo_corr.cbf* files to process directory
        try:
            process_dir = os.path.join(self.xds_directory, "..")
            raw_process_dir = os.path.join(self.raw_data_input_file_dir, "..")
            for dir in (process_dir, raw_process_dir):
                for filename in ("x_geo_corr.cbf.bz2", "y_geo_corr.cbf.bz2"):
                    dest = os.path.join(dir, filename)
                    if os.path.exists(dest):
                        continue
                    shutil.copyfile(
                        os.path.join(
                            self.getProperty(template_file_directory), filename
                        ),
                        dest,
                    )
        except BaseException:
            logging.exception("Exception happened while copying geo_corr files")

        return ESRFMultiCollect.write_input_files(self, datacollection_id)
