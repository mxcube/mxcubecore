import logging
import os
import time

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractMultiCollect import (
    AbstractMultiCollect,
)
from mxcubecore.TaskUtils import task


class MultiCollectMockup(AbstractMultiCollect, HardwareObject):
    def __init__(self, name):
        AbstractMultiCollect.__init__(self)
        HardwareObject.__init__(self, name)
        self._centring_status = None
        self.ready_event = None
        self.actual_frame_num = 0

    def execute_command(self, command_name, *args, **kwargs):
        return

    def init(self):
        self.setControlObjects(
            diffractometer=HWR.beamline.diffractometer,
            sample_changer=HWR.beamline.sample_changer,
            lims=HWR.beamline.lims,
            safety_shutter=HWR.beamline.safety_shutter,
            machine_current=HWR.beamline.machine_info,
            cryo_stream=HWR.beamline.cryo,
            energy=HWR.beamline.energy,
            resolution=HWR.beamline.resolution,
            detector_distance=HWR.beamline.detector.distance,
            transmission=HWR.beamline.transmission,
            undulators=HWR.beamline.undulators,
            flux=HWR.beamline.flux,
            detector=HWR.beamline.detector,
            beam_info=HWR.beamline.beam,
        )
        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True,))

    @task
    def loop(self, owner, data_collect_parameters_list):
        failed_msg = "Data collection failed!"
        failed = True
        collections_analyse_params = []
        self.emit("collectReady", (False,))
        self.emit("collectStarted", (owner, 1))

        for data_collect_parameters in data_collect_parameters_list:
            logging.debug("collect parameters = %r", data_collect_parameters)
            failed = False
            data_collect_parameters["status"] = "Data collection successful"
            (
                osc_id,
                sample_id,
                sample_code,
                sample_location,
            ) = self.update_oscillations_history(data_collect_parameters)
            self.emit(
                "collectOscillationStarted",
                (
                    owner,
                    sample_id,
                    sample_code,
                    sample_location,
                    data_collect_parameters,
                    osc_id,
                ),
            )

            for image in range(
                data_collect_parameters["oscillation_sequence"][0]["number_of_images"]
            ):
                time.sleep(
                    data_collect_parameters["oscillation_sequence"][0]["exposure_time"]
                )
                self.emit("collectImageTaken", image)

            data_collect_parameters["status"] = "Running"
            data_collect_parameters["status"] = "Data collection successful"
            self.emit(
                "collectOscillationFinished",
                (
                    owner,
                    True,
                    data_collect_parameters["status"],
                    "12345",
                    osc_id,
                    data_collect_parameters,
                ),
            )

        self.emit(
            "collectEnded",
            owner,
            not failed,
            failed_msg if failed else "Data collection successful",
        )
        logging.getLogger("HWR").info("data collection successful in loop")
        self.emit("collectReady", (True,))

    @task
    def data_collection_hook(self, data_collect_parameters):
        return

    def do_prepare_oscillation(self, start, end, exptime, npass):
        self.actual_frame_num = 0

    @task
    def oscil(self, start, end, exptime, npass):
        return

    @task
    def data_collection_cleanup(self):
        return

    @task
    def close_fast_shutter(self):
        return

    @task
    def open_fast_shutter(self):
        return

    @task
    def move_motors(self, motor_position_dict):
        return

    @task
    def open_safety_shutter(self):
        return

    def safety_shutter_opened(self):
        return

    @task
    def close_safety_shutter(self):
        return

    @task
    def prepare_intensity_monitors(self):
        return

    def prepare_acquisition(
        self, take_dark, start, osc_range, exptime, npass, number_of_images, comment=""
    ):
        return

    def set_detector_filenames(
        self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path
    ):
        return

    def prepare_oscillation(self, start, osc_range, exptime, npass):
        return (start, start + osc_range)

    def do_oscillation(self, start, end, exptime, shutterless, npass, first_frame):
        gevent.sleep(exptime)

    def start_acquisition(self, exptime, npass, first_frame):
        return

    def write_image(self, last_frame):
        self.actual_frame_num += 1
        return

    def last_image_saved(self):
        return self.actual_frame_num

    def stop_acquisition(self):
        return

    def reset_detector(self):
        return

    def prepare_input_files(
        self, files_directory, prefix, run_number, process_directory
    ):
        self.actual_frame_num = 0
        i = 1
        while True:
            xds_input_file_dirname = "xds_%s_run%s_%d" % (prefix, run_number, i)
            xds_directory = os.path.join(process_directory, xds_input_file_dirname)

            if not os.path.exists(xds_directory):
                break

            i += 1

        mosflm_input_file_dirname = "mosflm_%s_run%s_%d" % (prefix, run_number, i)
        mosflm_directory = os.path.join(process_directory, mosflm_input_file_dirname)

        hkl2000_dirname = "hkl2000_%s_run%s_%d" % (prefix, run_number, i)
        hkl2000_directory = os.path.join(process_directory, hkl2000_dirname)

        self.raw_data_input_file_dir = os.path.join(
            files_directory, "process", xds_input_file_dirname
        )
        self.mosflm_raw_data_input_file_dir = os.path.join(
            files_directory, "process", mosflm_input_file_dirname
        )
        self.raw_hkl2000_dir = os.path.join(files_directory, "process", hkl2000_dirname)

        return xds_directory, mosflm_directory, hkl2000_directory

    @task
    def write_input_files(self, collection_id):
        return

    def get_wavelength(self):
        return

    def get_undulators_gaps(self):
        return []

    def get_resolution_at_corner(self):
        return

    def get_beam_size(self):
        return None, None

    def get_slit_gaps(self):
        return None, None

    def get_beam_shape(self):
        return

    def get_machine_current(self):
        if self.bl_control.machine_current is not None:
            return self.bl_control.machine_current.get_current()
        else:
            return 0

    def get_machine_message(self):
        if self.bl_control.machine_current is not None:
            return self.bl_control.machine_current.get_message()
        else:
            return ""

    def get_machine_fill_mode(self):
        if self.bl_control.machine_current is not None:
            return self.bl_control.machine_current.get_fill_mode()
        else:
            """"""

    def get_cryo_temperature(self):
        if self.bl_control.cryo_stream is not None:
            return self.bl_control.cryo_stream.getTemperature()

    def get_current_energy(self):
        return

    def get_beam_centre(self):
        return None, None

    def get_beamline_configuration(self, *args):
        return self.bl_config._asdict()

    def is_connected(self):
        return True

    def is_ready(self):
        return True

    def sample_changer_HO(self):
        return self.bl_control.sample_changer

    def diffractometer(self):
        return self.bl_control.diffractometer

    def sanity_check(self, collect_params):
        return

    def set_brick(self, brick):
        return

    def directory_prefix(self):
        return self.bl_config.directory_prefix

    def store_image_in_lims(self, frame, first_frame, last_frame):
        return True

    def get_oscillation(self, oscillation_id):
        return self.oscillations_history[oscillation_id - 1]

    def sample_accept_centring(self, accepted, centring_status):
        self.sample_centring_done(accepted, centring_status)

    def set_centring_status(self, centring_status):
        self._centring_status = centring_status

    def get_oscillations(self, session_id):
        return []

    def set_helical(self, helical_on):
        return

    def set_helical_pos(self, helical_oscil_pos):
        return

    def get_archive_directory(self, directory):
        archive_dir = os.path.join(directory, "archive")
        return archive_dir

    @task
    def generate_image_jpeg(self, filename, jpeg_path, jpeg_thumbnail_path):
        pass
