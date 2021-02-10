from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareObjects.abstract.AbstractMultiCollect import (
    AbstractMultiCollect,
)
from HardwareRepository.TaskUtils import task
from HardwareRepository import HardwareRepository as HWR
import logging
import time
import os
import gevent


class LNLSCollect(AbstractMultiCollect, HardwareObject):
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
            diffractometer=self.getObjectByRole("diffractometer"),
            sample_changer=self.getObjectByRole("sample_changer"),
            lims=self.getObjectByRole("dbserver"),
            safety_shutter=self.getObjectByRole("safety_shutter"),
            machine_current=self.getObjectByRole("machine_current"),
            cryo_stream=self.getObjectByRole("cryo_stream"),
            energy=HWR.beamline.energy,
            resolution=self.getObjectByRole("resolution"),
            detector_distance=self.getObjectByRole("detector_distance"),
            transmission=self.getObjectByRole("transmission"), # Returns attenuators.
            undulators=self.getObjectByRole("undulators"),
            flux=self.getObjectByRole("flux"),
            detector=self.getObjectByRole("detector"),
            beam_info=self.getObjectByRole("beam_info"),
        )
        # Adding this line to get transmission value:
        self.filter_transmission = self.getObjectByRole('filter_transmission')
        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True,))

    @task
    def loop(self, owner, data_collect_parameters_list):
        print('\nCALL LOOP\n')
        print('\nDC PARAM LIST:\n')
        print('data_collect_parameters_list = {}\n'.format(data_collect_parameters_list))
        failed_msg = "Data collection failed!"
        failed = True
        collections_analyse_params = []
        self.emit("collectReady", (False,))
        self.emit("collectStarted", (owner, 1))

        for data_collect_parameters in data_collect_parameters_list:
            print('\nSUB LOOP SINGLE COLLECT?\n')
            print('data_collect_parameters = {}\n'.format(data_collect_parameters))
            logging.debug("collect parameters = %r", data_collect_parameters)
            failed = False
            data_collect_parameters["status"] = "Data collection successful"
            osc_id, sample_id, sample_code, sample_location = self.update_oscillations_history(
                data_collect_parameters
            )

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

            # Translate parameters to scan-utils flyscan
            config_yml = 'pilatus'
            message = "Flyscan called from mxcube3."

            output_directory = data_collect_parameters['fileinfo']['directory']
            # Create dir
            path = output_directory
            try:
                if os.path.isdir(path):
                    logging.getLogger("HWR").info("Directory exists: %s " % path)
                else:
                    os.makedirs(path)
                    logging.getLogger("HWR").info("Successfully created the directory %s " % path)
            except OSError:
                logging.getLogger("HWR").error("Creation of the directory %s failed." % path)
            
            if not output_directory.endswith('/'):
                output_directory = output_directory + '/'
            output_prefix =  data_collect_parameters['fileinfo']['prefix']
            output_file = output_directory + output_prefix

            motor_mnenomic = 'gonio'
            xlabel = motor_mnenomic
            plot_type = 'none'
            mode = '--points-mode'

            start_float = float(data_collect_parameters['oscillation_sequence'][0]['start']) # omega start pos
            start = str(start_float)

            step_size = float(data_collect_parameters['oscillation_sequence'][0]['range'])
            num_of_points = int(data_collect_parameters['oscillation_sequence'][0]['number_of_images'])
            end_float = start_float + step_size*num_of_points
            end = str(end_float)

            step_or_points = str(num_of_points)

            time_float = float(data_collect_parameters['oscillation_sequence'][0]['exposure_time'])
            time = str(time_float)

            prescan = ' '
            postscan = ' '

            # flyscan-only params
            start_offset = str(0)
            end_offset = str(0)
            aquire_period = str(time_float + 0.0023) # + pilatus readout time

            command = 'flyscan -c {} -m "{}" -o {} -s --motor {} {} --start {} --end {} --step-or-points {} --time {} --prescan={} --postscan={} --start-offset {} --end-offset {} --aquire-period {}'.format(config_yml, message, output_file, motor_mnenomic, mode, start, end, step_or_points, time, prescan, postscan, start_offset, end_offset, aquire_period)

            #command = 'scan -c {} -m "{}" -o {} --motor {} --xlabel {} --plot-type {} {} --start {} --end {} --step-or-points {} --time {} --prescan={} --postscan={}'.format(config_yml, message, output_file, motor_mnenomic, xlabel, plot_type, mode, start, end, step_or_points, time, prescan, postscan)

            logging.getLogger("HWR").info("[SCAN-UTILS] Command: " + str(command))
            print('\n[SCAN-UTILS] Command: ' + str(command) + '\n')

            # Store values for clean up
            logging.getLogger("HWR").info("[Clean up] Configuring...")
            omega = HWR.beamline.diffractometer.motor_hwobj_dict.get("phi")
            if omega is None:
                logging.getLogger("HWR").error("[Clean up] Could not get omega motor.")
            else:
                omega_original_velo = omega.get_velocity()
                logging.getLogger("HWR").info(
                    "[Clean up] Omega velo: {}".format(omega_original_velo))
            logging.getLogger("HWR").info("[Clean up] Configured.")

            # Set detector cbf header
            header_ok = self.set_pilatus_det_header(start_float, step_size)
            if not header_ok:
                logging.getLogger("HWR").error(
                        "[Collect] Pilatus header params could not be set! Collection aborted."
                )
                return

            import sys, subprocess
            try:
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

                logging.getLogger("HWR").info('[SCAN-UTILS] Executing scan...')
                logging.getLogger("user_level_log").info("Executing scan...")
                stdout, stderr = process.communicate()
                # stdout
                logging.getLogger("HWR").info('[SCAN-UTILS] output : ' + stdout.decode('utf-8'))
                print('[SCAN-UTILS] output : ' + stdout.decode('utf-8'))
                # stderr
                logging.getLogger("HWR").error('[SCAN-UTILS] errors : ' + stderr.decode('utf-8'))
                print('[SCAN-UTILS] errors : ' + stderr.decode('utf-8'))

            except BaseException:
                logging.getLogger("HWR").error("[SCAN-UTILS] Error in calling scan.")
                # print("[SCAN-UTILS] Error in calling scan.")
                raise
            else:
                logging.getLogger("HWR").info("[SCAN-UTILS] Finished scan!")
                logging.getLogger("user_level_log").info("Finished scan!")
                #print("[SCAN-UTILS] Finished scan!")
            finally:
                # Clean up
                logging.getLogger("HWR").info("[Clean up] Applying...")
                import time as timee
                timee.sleep(10)
                if omega is not None:
                    # Restore omega default velocity
                    omega.set_velocity(omega_original_velo)
                    logging.getLogger("HWR").info(
                        "[Clean up] Omega velo reset to: {}".format(
                            omega_original_velo))
                logging.getLogger("HWR").info("[Clean up] Done!")

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

    def set_pilatus_det_header(self, start_angle, step_size):
        # Read current params
        logging.getLogger("HWR").info("Setting Pilatus CBF header...")
        wl = self.bl_control.energy.get_wavelength()
        dd = self.bl_control.detector_distance.get_value()
        te = self.bl_control.energy.get_value()
        ft = self.filter_transmission.get_value()
        try:
            ft = ft / 100  # [0, 1]
        except Exception as e:
            print("Error on setting Pilatus transmission: {}".format(str(e)))
            return False

        # Write to det (values will be on the cbf header)
        wl_ok = self.bl_control.detector.set_wavelength(wl)
        dd_ok = self.bl_control.detector.set_detector_distance(dd)
        bx_ok = self.bl_control.detector.set_beam_x(from_user=True)
        by_ok = self.bl_control.detector.set_beam_y(from_user=True)
        te_ok = self.bl_control.detector.set_threshold_energy(te)
        ft_ok = self.bl_control.detector.set_transmission(ft)
        sa_ok = self.bl_control.detector.set_start_angle(start_angle)
        ss_ok = self.bl_control.detector.set_angle_incr(step_size)

        return wl_ok and dd_ok and bx_ok and by_ok and te_ok and ft_ok and sa_ok and ss_ok

    @task
    def take_crystal_snapshots(self, number_of_snapshots):
        self.bl_control.diffractometer.take_snapshots(number_of_snapshots, wait=True)

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

    def do_oscillation(self, start, end, exptime, npass):
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
            return self.bl_control.machine_current.getCurrent()
        else:
            return 0

    def get_machine_message(self):
        if self.bl_control.machine_current is not None:
            return self.bl_control.machine_current.getMessage()
        else:
            return ""

    def get_machine_fill_mode(self):
        if self.bl_control.machine_current is not None:
            return self.bl_control.machine_current.getFillMode()
        else:
            ""

    def get_cryo_temperature(self):
        if self.bl_control.cryo_stream is not None:
            return self.bl_control.cryo_stream.getTemperature()

    def get_current_energy(self):
        return

    def get_beam_centre(self):
        return None, None

    def getBeamlineConfiguration(self, *args):
        return self.bl_config._asdict()

    def isConnected(self):
        return True

    def is_ready(self):
        return True

    def sampleChangerHO(self):
        return self.bl_control.sample_changer

    def diffractometer(self):
        return self.bl_control.diffractometer

    def sanityCheck(self, collect_params):
        return

    def setBrick(self, brick):
        return

    def directoryPrefix(self):
        return self.bl_config.directory_prefix

    def store_image_in_lims(self, frame, first_frame, last_frame):
        return True

    def getOscillation(self, oscillation_id):
        return self.oscillations_history[oscillation_id - 1]

    def sampleAcceptCentring(self, accepted, centring_status):
        self.sample_centring_done(accepted, centring_status)

    def setCentringStatus(self, centring_status):
        self._centring_status = centring_status

    def getOscillations(self, session_id):
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
