import logging
import os
import shutil

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.LimaPilatusDetector import LimaPilatusDetector
from mxcubecore.TaskUtils import task

from .ESRFMultiCollect import ESRFMultiCollect


class MD2MultiCollect(ESRFMultiCollect):
    def __init__(self, name):
        ESRFMultiCollect.__init__(self, name)
        self.fast_characterisation = None

    @task
    def data_collection_hook(self, data_collect_parameters):
        ESRFMultiCollect.data_collection_hook(self, data_collect_parameters)
        self._detector.shutterless = data_collect_parameters["shutterless"]

        try:
            comment = HWR.beamline.sample_changer.get_crystal_id()
            data_collect_parameters["comment"] = comment
        except Exception:
            pass

    @task
    def get_beam_size(self):
        _width, _height, _, _ = HWR.beamline.beam.get_value()
        return _width, _height

    @task
    def get_slit_gaps(self):
        self.get_object_by_role("controller")

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
    def take_crystal_snapshots(self, number_of_snapshots, image_path_list=[]):
        HWR.beamline.diffractometer.take_snapshot(image_path_list)

    def do_prepare_oscillation(self, *args, **kwargs):
        diffr = HWR.beamline.diffractometer

        # set the detector cover out
        try:
            diffr.open_detector_cover()
        except Exception:
            logging.getLogger("HWR").exception("Could not open detector cover")
        """
        try:
            detcover = self.get_object_by_role("controller").detcover

            if detcover.state == "IN":
                detcover.set_out(10)
        except:
            logging.getLogger("HWR").exception("Could not open detector cover")
        """

        # send again the command as MD2 software only handles one
        # centered position!!
        # has to be where the motors are and before changing the phase
        # diffr.get_command_object("save_centring_positions")()

        # switch on the front light
        front_light_switch = diffr.get_object_by_role("FrontLightSwitch")
        front_light_switch.set_value(front_light_switch.VALUES.IN)
        # diffr.get_object_by_role("FrontLight").set_value(2)

        # move to DataCollection phase
        logging.getLogger("user_level_log").info("Moving MD2 to DataCollection")
        # AB next line to speed up the data collection
        diffr.set_phase("DataCollection", wait=False, timeout=0)

    @task
    def data_collection_cleanup(self):
        self.get_object_by_role("diffractometer")._wait_ready(10)
        self.close_fast_shutter()

    @task
    def oscil(self, start, end, exptime, number_of_images, wait=True):
        diffr = self.get_object_by_role("diffractometer")
        # make sure the diffractometer is ready to do the scan
        diffr.wait_ready(100)
        if self.helical:
            diffr.oscilScan4d(
                start, end, exptime, number_of_images, self.helical_pos, wait=True
            )
        elif self.mesh:
            det = HWR.beamline.detector
            latency_time = det.get_property("latecy_time_mesh") or det.get_deadtime()
            sequence_trigger = self.get_property("lima_sequnce_trigger_mode") or False

            if sequence_trigger:
                msg = "Using LIMA sequnce trigger mode for Eiger"
                logging.getLogger("HWR").info(msg)
                mesh_total_nb_frames = self.mesh_num_lines
            else:
                mesh_total_nb_frames = self.mesh_total_nb_frames

            diffr.oscilScanMesh(
                start,
                end,
                exptime,
                latency_time,
                self.mesh_num_lines,
                mesh_total_nb_frames,
                self.mesh_center,
                self.mesh_range,
                wait=True,
            )
        elif self.fast_characterisation:
            self.nb_frames = 10
            self.nb_scan = 4
            self.angle = 90
            exptime *= 10
            range = (end - start) * 10
            diffr.characterisation_scan(
                start,
                range,
                self.nb_frames,
                exptime,
                self.nb_scan,
                self.angle,
                wait=True,
            )
        else:
            diffr.oscilScan(start, end, exptime, number_of_images, wait=True)

    @task
    def prepare_acquisition(
        self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""
    ):
        if self.fast_characterisation:
            number_of_images *= 40
        ext_gate = self.mesh or self.fast_characterisation

        self._detector.prepare_acquisition(
            take_dark,
            start,
            osc_range,
            exptime,
            npass,
            number_of_images,
            comment,
            ext_gate,
            self.mesh_num_lines,
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

    def set_fast_characterisation(self, value=False):
        self.fast_characterisation = value

    def get_cryo_temperature(self):
        return 0

    @task
    def prepare_intensity_monitors(self):
        return

    def get_beam_centre(self):
        pixel_x, pixel_y = HWR.beamline.detector.get_pixel_size()
        bcx, bcy = HWR.beamline.detector.get_beam_position()
        return [bcx * pixel_x, bcy * pixel_y]

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
                            self.get_property("template_file_directory"), filename
                        ),
                        dest,
                    )
        except Exception:
            logging.exception("Exception happened while copying geo_corr files")

        return ESRFMultiCollect.write_input_files(self, datacollection_id)
