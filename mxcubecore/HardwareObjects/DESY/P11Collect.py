# encoding: utf-8
#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

__copyright__ = """ Copyright © 2010 - 2024 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


import errno
import socket
import time
import sys
import os
import logging
import traceback
import h5py
import numpy as np
import psutil
import subprocess
import time


from mxcubecore.HardwareObjects.abstract.AbstractCollect import AbstractCollect
from mxcubecore import HardwareRepository as HWR
from mxcubecore.TaskUtils import task
from mxcubecore.Command.Tango import DeviceProxy

FILE_TIMEOUT = 5


class P11Collect(AbstractCollect):
    def __init__(self, *args):
        super().__init__(*args)

    def init(self):

        super().init()

        self.default_speed = self.get_property("omega_default_speed", 130)
        self.turnback_time = self.get_property("turnback_time", 0.3)
        self.filter_server_name = self.get_property("filterserver")
        self.mono_server_name = self.get_property("monoserver")
        self.filter_server = DeviceProxy(self.filter_server_name)
        self.mono_server = DeviceProxy(self.mono_server_name)

        self.lower_bound_ch = self.get_channel_object("acq_lower_bound")
        self.upper_bound_ch = self.get_channel_object("acq_upper_bound")

        self.acq_arm_cmd = self.get_command_object("acq_arm")
        self.acq_on_cmd = self.get_command_object("acq_on")
        self.acq_off_cmd = self.get_command_object("acq_off")
        self.acq_window_off_cmd = self.get_command_object("acq_window_off")

        self.latest_frames = None
        self.acq_speed = None

        if None in [
            self.lower_bound_ch,
            self.upper_bound_ch,
            self.acq_arm_cmd,
            self.acq_on_cmd,
            self.acq_off_cmd,
            self.acq_window_off_cmd,
        ]:
            self.init_ok = False
            self.log.debug("lower_bound_ch: %s" % self.lower_bound_ch)
            self.log.debug("upper_bound_ch: %s" % self.upper_bound_ch)
            self.log.debug("acq_arm_cmd: %s" % self.acq_arm_cmd)
            self.log.debug("acq_on_cmd: %s" % self.acq_on_cmd)
            self.log.debug("acq_off_cmd: %s" % self.acq_off_cmd)
            self.log.debug("acq_window_off_cmd: %s" % self.acq_window_off_cmd)
        else:
            self.init_ok = True

    @task
    def move_motors(self, motor_position_dict):
        HWR.beamline.diffractometer.move_motors(motor_position_dict)

    def _take_crystal_snapshot(self, filename):
        self.log.debug("#COLLECT# taking crystal snapshot.")

        if not HWR.beamline.diffractometer.is_centring_phase():
            self.log.debug("#COLLECT# take_snapshot. moving to centring phase")
            HWR.beamline.diffractometer.goto_centring_phase(wait=True)

        time.sleep(0.3)
        if not HWR.beamline.diffractometer.is_centring_phase():
            raise RuntimeError(
                "P11Collect. cannot reach centring phase for acquiring snapshots"
            )

        self.log.debug("#COLLECT# saving snapshot to %s" % filename)
        HWR.beamline.sample_view.save_snapshot(filename)

    def set_transmission(self, value):
        """
        Descript. :
        """
        HWR.beamline.transmission.set_value(value)

    def set_energy(self, value):
        """
        Descript. :
        """
        HWR.beamline.energy.set_value(value)

    def set_resolution(self, value):
        """
        Descript. :
        """
        if round(HWR.beamline.resolution.get_value(), 2) != round(value, 2):
            HWR.beamline.resolution.set_value(value)

    def do_collect(self, owner):
        """
        Actual collect sequence
        """
        log = logging.getLogger("user_level_log")
        log.info("Collection: Preparing to collect")
        self.emit("collectReady", (False,))
        self.emit(
            "collectOscillationStarted",
            (owner, None, None, None, self.current_dc_parameters, None),
        )
        self.emit("progressInit", ("Collection", 100, False))
        self.collection_id = None

        try:
            # ----------------------------------------------------------------
            # Prepare data collection

            self.open_detector_cover()
            self.open_safety_shutter()
            self.open_fast_shutter()

            # ----------------------------------------------------------------
            # Store information in LIMS

            self.current_dc_parameters["status"] = "Running"
            self.current_dc_parameters["collection_start_time"] = time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            logging.getLogger("HWR").info(
                "Collection parameters: %s", str(self.current_dc_parameters)
            )

            log.info("Collection: Storing data collection in LIMS")
            self.store_data_collection_in_lims()

            log.info(
                "Collection: Creating directories for raw images and processing files"
            )
            self.create_file_directories()

            log.info("Collection: Getting sample info from parameters")
            self.get_sample_info()

            log.info("Collection: Storing sample info in LIMS")
            self.store_sample_info_in_lims()

            if all(
                item is None for item in self.current_dc_parameters["motors"].values()
            ):
                # No centring point defined
                # create point based on the current position
                current_diffractometer_position = (
                    HWR.beamline.diffractometer.get_positions()
                )
                for motor in self.current_dc_parameters["motors"].keys():
                    self.current_dc_parameters["motors"][
                        motor
                    ] = current_diffractometer_position.get(motor)

            # ----------------------------------------------------------------
            # Move to the centered position and take crystal snapshots

            log.info("Collection: Moving to centred position")
            self.move_to_centered_position()
            self.take_crystal_snapshots()
            self.move_to_centered_position()

            # ----------------------------------------------------------------
            # Set data collection parameters

            if "transmission" in self.current_dc_parameters:
                log.info(
                    "Collection: Setting transmission to %.2f",
                    self.current_dc_parameters["transmission"],
                )
                self.set_transmission(self.current_dc_parameters["transmission"])

            if "wavelength" in self.current_dc_parameters:
                log.info(
                    "Collection: Setting wavelength to %.4f",
                    self.current_dc_parameters["wavelength"],
                )
                self.set_wavelength(self.current_dc_parameters["wavelength"])

            elif "energy" in self.current_dc_parameters:
                log.info(
                    "Collection: Setting energy to %.4f",
                    self.current_dc_parameters["energy"],
                )
                self.set_energy(self.current_dc_parameters["energy"])

            dd = self.current_dc_parameters.get("resolution")
            if dd and dd.get("upper"):
                resolution = dd["upper"]
                log.info("Collection: Setting resolution to %.3f", resolution)
                self.set_resolution(resolution)

            elif "detector_distance" in self.current_dc_parameters:
                log.info(
                    "Collection: Moving detector to %.2f",
                    self.current_dc_parameters["detector_distance"],
                )
                self.move_detector(self.current_dc_parameters["detector_distance"])

            # ----------------------------------------------------------------
            # Site specific implementation of a data collection

            # In order to call the hook with original parameters
            # before update_data_collection_in_lims changes them
            # TODO check why this happens

            self.data_collection_hook()

            # ----------------------------------------------------------------
            # Store information in LIMS

            log.info("Collection: Updating data collection in LIMS")
            self.update_data_collection_in_lims()

        except RuntimeError as e:
            failed_msg = "Data collection failed!\n%s" % str(e)
            self.collection_failed(failed_msg)
        else:
            self.collection_finished()
        finally:
            self.data_collection_cleanup()

    def data_collection_hook(self):
        if not self.init_ok:
            raise RuntimeError(
                "P11Collect. - object initialization failed. COLLECTION not possible"
            )

        dc_pars = self.current_dc_parameters
        collection_type = dc_pars["experiment_type"]

        self.log.debug(
            "======================= P11Collect. DATA COLLECTION HOOK =========================================="
        )
        self.log.debug(str(collection_type))
        self.log.debug(str(self.current_dc_parameters))

        osc_pars = self.current_dc_parameters["oscillation_sequence"][0]
        file_info = self.current_dc_parameters["fileinfo"]
        osc_pars["kappa"] = 0
        osc_pars["kappa_phi"] = 0

        start_angle = osc_pars["start"]
        img_range = osc_pars["range"]
        nframes = osc_pars["number_of_images"]
        self.latest_frames = nframes
        stop_angle = start_angle + img_range * nframes

        img_range = osc_pars["range"]
        exp_time = osc_pars["exposure_time"]
        self.acq_speed = img_range / exp_time

        if not self.diffractometer_prepare_collection():
            raise RuntimeError("Cannot prepare diffractometer for collection")

        try:
            self.log.debug("############# #COLLECT# Opening detector cover")
            HWR.beamline.diffractometer.detector_cover_open(wait=True)
            self.log.debug(
                "############ #COLLECT# detector cover is now open. Wait 2 more seconds"
            )
            time.sleep(2.0)  # wait extra time to allow det cover to be opened.

            basepath = file_info["directory"]
            prefix = file_info["prefix"]
            runno = file_info["run_number"]

            self.log.debug("#COLLECT# Programming detector for data collection")
            if collection_type == "Characterization":
                # Filepath for the presenterd to work
                filepath = os.path.join(
                    basepath,
                    prefix,
                    "screening_"
                    + str(runno).zfill(3)
                    + "/"
                    + "%s_%d" % (prefix, runno),
                )

                # Filepath to the EDNA processing
                # filepath = os.path.join(basepath,"%s_%d" % (prefix, runno))

                # setting up xds_dir for characterisation (used there internally to create dirs)
                self.current_dc_parameters["xds_dir"] = os.path.join(
                    basepath, "%s_%d" % (prefix, runno)
                )

                self.log.debug(
                    "======= CURRENT FILEPATH: "
                    + str(filepath)
                    + "======================================="
                )
                self.latest_h5_filename = "%s_master.h5" % filepath
                self.log.debug(
                    "======= LATEST H5 FILENAME FILEPATH: "
                    + str(self.latest_h5_filename)
                    + "======================================="
                )

                self.log.debug(
                    "======= CURRENT FILEPATH: "
                    + str(filepath)
                    + "======================================="
                )
                self.latest_h5_filename = "%s_master.h5" % filepath
                self.log.debug(
                    "======= LATEST H5 FILENAME FILEPATH: "
                    + str(self.latest_h5_filename)
                    + "======================================="
                )

                angle_inc = 90.0
                HWR.beamline.detector.prepare_characterisation(
                    exp_time, nframes, angle_inc, filepath
                )
            else:
                # Filepath to work with presenterd
                filepath = os.path.join(
                    basepath,
                    prefix,
                    "rotational_"
                    + str(runno).zfill(3)
                    + "/"
                    + "%s_%d" % (prefix, runno),
                )

                # Filepath to work with EDNA
                # filepath = os.path.join(basepath,"%s_%d" % (prefix, runno))

                self.log.debug(
                    "======= CURRENT FILEPATH: "
                    + str(filepath)
                    + "======================================="
                )
                self.latest_h5_filename = "%s_master.h5" % filepath
                self.log.debug(
                    "======= LATEST H5 FILENAME FILEPATH: "
                    + str(self.latest_h5_filename)
                    + "======================================="
                )

                HWR.beamline.detector.prepare_std_collection(
                    exp_time, nframes, filepath
                )

            self.log.debug("#COLLECT# Starting detector")
            HWR.beamline.detector.start_acquisition()

            # Check whether the live view monitoring is on. Restart if needed.
            process_name = os.getenv("MXCUBE_LIVEVIEW_NAME")
            command = [os.getenv("MXCUBE_LIVEVIEW")]
            if self.is_process_running(process_name) and self.is_process_running(
                "adxv"
            ):
                print(f"{process_name} is already running.")
            else:
                os.system(f"killall -9 {process_name}")
                print(f"{process_name} is not running. Starting...")
                self.start_process(command)

            if collection_type == "Characterization":
                self.log.debug("STARTING CHARACTERISATION")
                self.collect_characterisation(
                    start_angle, img_range, nframes, angle_inc, exp_time
                )
            else:
                self.log.debug("STARTING STANDARD COLLECTION")
                self.collect_std_collection(start_angle, stop_angle)

        except RuntimeError:
            self.log.error(traceback.format_exc())
        finally:
            self.add_h5_info(self.latest_h5_filename)
            self.acquisition_cleanup()

        # Show the latest image after collection
        latest_image = HWR.beamline.detector.get_eiger_name_pattern()
        latest_image = f"/gpfs{latest_image}_master.h5"
        self.adxv_notify(latest_image)

    def collect_std_collection(self, start_angle, stop_angle):
        """
        The function collects data from a standard acquisition by moving the omega motor from a start
        angle to a stop angle.

        :param start_angle: The starting angle for the collection
        :param stop_angle: The stop_angle parameter is the final angle at which the collection should
        stop
        """
        HWR.beamline.diffractometer.wait_omega()

        start_pos = start_angle - self.turnback_time * self.acq_speed
        stop_pos = stop_angle + self.turnback_time * self.acq_speed

        self.log.debug("#COLLECT# Running OMEGA through the std acquisition")
        if start_angle <= stop_angle:
            self.lower_bound_ch.set_value(start_angle)
            self.upper_bound_ch.set_value(stop_angle)

        else:
            self.lower_bound_ch.set_value(stop_angle)
            self.upper_bound_ch.set_value(start_angle)

        self.omega_mv(start_pos, self.default_speed)
        self.acq_arm_cmd()
        self.omega_mv(stop_pos, self.acq_speed)
        time.sleep(0.5)
        self.acq_off_cmd()
        self.acq_window_off_cmd()
        self.omega_mv(stop_angle, self.acq_speed)

    def collect_characterisation(
        self, start_angle, img_range, nimages, angle_inc, exp_time
    ):
        """
        The function `collect_characterisation` is used to collect a series of images at different
        angles for characterisation.

        :param start_angle: The starting angle for the characterisation acquisition
        :param img_range: The `img_range` parameter represents the range of angles over which the single image 
        will be collected
        :param nimages: The parameter `nimages` represents the number of images to be collected during
        the characterisation process (1, 2, 4).
        :param angle_inc: The `angle_inc` parameter represents the increment in angle between each image
        in the collection
        :param exp_time: The `exp_time` parameter represents the exposure time for each image
        """

        self.log.debug(
            "#COLLECT# Running OMEGA through the characteristation acquisition"
        )

        self.omega_mv(start_angle, self.default_speed)

        for img_no in range(nimages):
            self.log.debug("collecting image %s" % img_no)
            start_at = start_angle + angle_inc * img_no
            stop_angle = start_at + img_range * 1.0

            self.log.debug("collecting image %s, angle %f" % (img_no, start_at))

            # Keep it here for now. It is not clear if it is needed.
            # if start_at >= stop_angle:
            #     init_pos = start_at  # - self.acq_speed * self.turnback_time
            #     # init_pos = start_at - 1.5
            # else:
            #     init_pos = start_at  # + self.acq_speed * self.turnback_time
            #     # init_pos = start_at + 1.5
            # self.omega_mv(init_pos, self.default_speed)

            self.collect_std_collection(start_at, stop_angle)
            self.log.debug(
                "======= collect_characterisation  Waiting ======================================="
            )

    def adxv_notify(self, image_filename, image_num=1):
        """
        The `adxv_notify` function sends a notification to an ADXV to load an image file and
        display a specific slab.

        :param image_filename: The `image_filename` parameter is a string that represents the filename
        of the image that needs to be loaded into ADXV
        :param image_num: The `image_num` parameter is an optional parameter that specifies the image
        number to be loaded in ADXV. If not provided, it defaults to 1, defaults to 1 (optional)
        """
        logging.getLogger("HWR").info(f"ADXV notify {image_filename}")
        logging.getLogger("HWR").info(f"ADXV notify {image_num}")
        adxv_host = "localhost"
        adxv_port = 8100

        try:
            adxv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            adxv_socket.connect((adxv_host, adxv_port))
            adxv_socket.sendall(
                f"load_image {image_filename}\n slab {image_num}\n".encode()
            )
            adxv_socket.close()
        except RuntimeWarning:
            logging.getLogger("HWR").exception("")
        else:
            pass

    def is_process_running(self, process_name):
        for proc in psutil.process_iter():
            if proc.name() == process_name:
                return True
        return False

    def start_process(self, command):
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )

    def acquisition_cleanup(self):
        """
        The function `acquisition_cleanup` performs various cleanup tasks related to data acquisition,
        such as setting the omega velocity, turning off acquisition and window commands, closing the
        detector cover, and stopping the acquisition.
        """
        try:
            HWR.beamline.detector.stop_acquisition()
            HWR.beamline.diffractometer.wait_omega()
            # =================
            # It is probably already finished in a standard collection.
            self.acq_off_cmd()
            self.acq_window_off_cmd()
            # ==================
            HWR.beamline.diffractometer.set_omega_velocity(self.default_speed)
            self.log.debug("#COLLECT# Closing detector cover")
            HWR.beamline.diffractometer.detector_cover_close(wait=True)

            # Move omega to 0 at the end
            self.omega_mv(0, self.default_speed)

        except RuntimeError:
            self.log.error(traceback.format_exc())

    def add_h5_info(self, h5file):
        """
        Add information to an HDF5 file.

        :param h5file: The name or path of the HDF5 file.
        """
        self.log.debug("========== Writing H5 info ==============")

        # Wait for the HDF5 file to appear with a timeout
        start_time = time.time()
        while not os.path.exists(h5file):
            if time.time() - start_time > 5:
                raise IOError(
                    "Cannot add info to HDF5 file. Timeout waiting for file on disk."
                )
            time.sleep(0.5)

        try:
            with h5py.File(h5file, "r+") as h5fd:
                # Create or get the 'entry/source' group
                source_group = self.get_or_create_group(h5fd, "entry/source")
                source_group.attrs["NX_class"] = np.array("NXsource", dtype="S")

                # Create or get datasets within the 'entry/source' group
                self.create_or_get_dataset(
                    source_group, "name", np.array("PETRA III, DESY", dtype="S")
                )

                # Create or get the 'entry/instrument' group
                instrument_group = self.get_or_create_group(h5fd, "entry/instrument")

                # Create or get datasets within the 'entry/instrument' group
                self.create_or_get_dataset(
                    instrument_group, "name", np.array("P11", dtype="S")
                )

                # Create or get the 'entry/instrument/attenuator' group
                attenuator_group = self.get_or_create_group(
                    instrument_group, "attenuator"
                )
                attenuator_group.attrs["NX_class"] = np.array("NXattenuator", dtype="S")

                # Create or get datasets within the 'entry/instrument/attenuator' group
                self.create_or_get_dataset(
                    attenuator_group, "thickness", self.get_filter_thickness()
                )
                self.create_or_get_dataset(
                    attenuator_group, "type", np.array("Aluminum", dtype="S")
                )
                self.create_or_get_dataset(
                    attenuator_group,
                    "attenuator_transmission",
                    self.get_filter_transmission(),
                )

                # Keep it here as it is not clear if it is needed.
                # It was used in CC to fix the issue with the data processing
                # h5fd["entry/sample/transformations/omega"].attrs["vector"] = [
                #     1.0,
                #     0.0,
                #     0.0,
                # ]
                # h5fd["entry/instrument/detector/module/fast_pixel_direction"].attrs[
                #     "vector"
                # ] = [1.0, 0.0, 0.0]
                # h5fd["entry/instrument/detector/module/slow_pixel_direction"].attrs[
                #     "vector"
                # ] = [0.0, 1.0, 0.0]

                # Delete unwanted nodes
                unwanted_nodes = [
                    "entry/sample/goniometer/phi",
                    "entry/sample/goniometer/phi_end",
                    "entry/sample/goniometer/phi_range_average",
                    "entry/sample/goniometer/phi_range_total",
                ]
                for node in unwanted_nodes:
                    if node in h5fd:
                        del h5fd[node]
        except RuntimeWarning as err_msg:
            self.log.debug(f"Error while adding info to HDF5 file: {str(err_msg)}")
            self.log.debug(traceback.format_exc())

    def get_or_create_group(self, parent_group, group_name):
        """
        Get or create a group within a parent group.

        :param parent_group: The parent group where the new group will be created.
        :param group_name: The name of the group to get or create.
        :return: The group object.
        """
        if group_name in parent_group:
            return parent_group[group_name]
        else:
            return parent_group.create_group(group_name)

    def create_or_get_dataset(self, group, dataset_name, dataset_data):
        """
        Create or get a dataset within a group.

        :param group: The group where the dataset will be created or retrieved.
        :param dataset_name: The name of the dataset.
        :param dataset_data: The data to be stored in the dataset.
        """
        if dataset_name in group:
            dataset = group[dataset_name]
        else:
            dataset = group.create_dataset(dataset_name, data=dataset_data)

    def get_filter_thickness(self):
        """
        The function `get_filter_thickness` calculates the total thickness of three filters.
        :return: the total thickness of the filters in meters. If the filter server is not available, it
        returns -1.
        """
        if self.filter_server:
            thick1 = self.filter_server.Filter1Thickness
            thick2 = self.filter_server.Filter2Thickness
            thick3 = self.filter_server.Filter3Thickness

            thickness = int(thick1) + int(thick2) + int(thick3)

            return float(thickness) / 1_000_000
        else:
            return -1

    def get_filter_transmission(self):
        """
        The function returns the current transmission value from the filter server, or -1 if the filter
        server is not available.
        :return: The method is returning the current transmission value of the filter server. If the
        filter server is not available, it returns -1.
        """
        if self.filter_server:
            return self.filter_server.CurrentTransmission
        else:
            return -1

    def generate_xds_template(self):
        """
        The function generates an XDS template by executing a command on a remote server.
        """
        self.log.debug(
            "============== Generating XDS template.============================"
        )

        h5file = self.latest_h5_filename

        basedir, fname = os.path.split(h5file)

        self.log.debug(
            "============== BASEDIR for Generating XDS template "
            + str(basedir)
            + "============================"
        )

        process_dir = basedir.replace("/raw/", "/processed/") + "/manual"
        self.mkdir_with_mode(process_dir, mode=0o777)

        rel_image_dir = self.get_relative_path(process_dir, basedir)
        rel_image_path = os.path.join(rel_image_dir, fname)

        cmd_tpl = (
            "\"sleep 20; module load xdsapp/3.1.9; cd '{processpath:s}'; "
            + "generate_XDS.INP '{imagepath:s}'\" >/dev/null 2>&1\n"
        )

        cmd = cmd_tpl.format(imagepath=h5file, processpath=process_dir)
        os.system("ssh -n -f p11user@haspp11eval01 " + cmd)
        self.log.debug(
            "============== "
            + "ssh -n -f p11user@haspp11eval01 "
            + cmd
            + "============================"
        )

    def trigger_auto_processing(self, process_event=None, frame_number=None):
        """
        The function `trigger_auto_processing` triggers auto processing based on the experiment type and
        performs different actions for characterization and OSC experiments.

        :param process_event: The `process_event` parameter is an optional argument that specifies the
        type of event that triggered the auto processing. It can be used to provide additional
        information or context for the processing
        :param frame_number: The `frame_number` parameter is used to specify the number of frames in the
        processing. It is an integer value that represents the number of frames to be processed
        :return: The function does not return any value.
        """

        self.log.debug("Triggering auto processing")

        dc_pars = self.current_dc_parameters
        collection_type = dc_pars["experiment_type"]
        self.log.debug(
            "=============== Supported experiment types: ===========\n"
            + str(dc_pars["experiment_type"])
        )

        if collection_type == "Characterization":
            self.log.debug(
                "==== AUTOPROCESSING CHARACTERISATION IN PROGRESS =========="
            )

            resolution = self.get_resolution()
            frames = self.latest_frames

            image_dir_local, filename = os.path.split(self.latest_h5_filename)
            # AG: Image dir at this point is located locally. This path is not seen on the MAXWELL. Path needs to be converted.
            # /gpfs/current/ to  get_beamline_metadata()[2]
            image_dir = image_dir_local.replace(
                "/gpfs/current", HWR.beamline.session.get_beamtime_metadata()[2]
            )
            process_dir = image_dir.replace("/raw/", "/processed/")
            process_dir_local = image_dir_local.replace("/raw/", "/processed/")
            mosflm_path = os.path.join(process_dir, "mosflm")
            mosflm_path_local = os.path.join(process_dir_local, "mosflm")
            self.log.debug('============MOSFLM======== mosflm_path="%s"' % mosflm_path)
            self.log.debug(
                '============MOSFLM======== mosflm_path_local="%s"' % mosflm_path_local
            )

            ssh = HWR.beamline.session.get_ssh_command()

            try:
                self.mkdir_with_mode(mosflm_path_local, mode=0o777)
                self.log.debug(
                    "=========== MOSFLM ============ Mosflm directory created"
                )

            except OSError:
                self.log.debug(sys.exc_info())
                self.log.debug("Cannot create mosflm directory")

            base_process_dir = self.base_dir(process_dir_local, "processed")
            datasets_file = os.path.join(base_process_dir, "datasets.txt")

            # add to datasets.txt for presenterd
            try:
                open(datasets_file, "a").write(
                    mosflm_path_local.split("/gpfs/current/processed/")[1] + "\n"
                )
            except RuntimeWarning as err_msg:
                self.log.debug("Cannot write to datasets.txt")
                self.log.debug(sys.exc_info(), err_msg)

            # create call
            ssh = HWR.beamline.session.get_ssh_command()
            sbatch = HWR.beamline.session.get_sbatch_command(
                jobname_prefix="mosflm",
                logfile_path=mosflm_path.replace(
                    HWR.beamline.session.get_beamtime_metadata()[2],
                    "/beamline/p11/current",
                )
                + "/mosflm.log",
            )

            cmd = (
                "/asap3/petra3/gpfs/common/p11/processing/mosflm_sbatch.sh "
                + "{imagepath:s} {filename:s} {processpath:s} {frames:d} {res:f}"
            ).format(
                imagepath=image_dir,
                filename=filename,
                processpath=mosflm_path.replace(
                    HWR.beamline.session.get_beamtime_metadata()[2],
                    "/beamline/p11/current",
                ),
                frames=frames,
                res=resolution,
            )
            self.log.debug('=======MOSFLM========== ssh="%s"' % ssh)
            self.log.debug('=======MOSFLM========== sbatch="%s"' % sbatch)
            self.log.debug('=======MOSFLM========== executing process cmd="%s"' % cmd)
            self.log.debug(
                '=======MOSFLM========== {ssh:s} "{sbatch:s} --wrap \\"{cmd:s}\\""'.format(
                    ssh=ssh, sbatch=sbatch, cmd=cmd
                )
            )

            os.system(
                '{ssh:s} "{sbatch:s} --wrap \\"{cmd:s}"\\"'.format(
                    ssh=ssh, sbatch=sbatch, cmd=cmd
                )
            )
        else:
            if collection_type == "OSC":
                self.log.debug(
                    "==== AUTOPROCESSING STANDARD PROCESSING IS IN PROGRESS =========="
                )

                resolution = self.get_resolution()
                frames = self.latest_frames

                image_dir_local, filename = os.path.split(self.latest_h5_filename)

                image_dir = image_dir_local.replace(
                    "/gpfs/current", HWR.beamline.session.get_beamtime_metadata()[2]
                )
                process_dir = image_dir.replace("/raw/", "/processed/")
                process_dir_local = image_dir_local.replace("/raw/", "/processed/")
                xdsapp_path = os.path.join(process_dir, "xdsapp")
                xdsapp_path_local = os.path.join(process_dir_local, "xdsapp")
                self.log.debug(
                    '============XDSAPP======== xdsapp_path="%s"' % xdsapp_path
                )
                self.log.debug(
                    '============XDSAPP======== xdsapp_path_local="%s"'
                    % xdsapp_path_local
                )

                try:
                    self.mkdir_with_mode(xdsapp_path_local, mode=0o777)
                    self.log.debug(
                        "=========== XDSAPP ============ XDSAPP directory created"
                    )

                except OSError:
                    self.log.debug(sys.exc_info())
                    self.log.debug("Cannot create XDSAPP directory")

                base_process_dir = self.base_dir(process_dir_local, "processed")
                datasets_file = os.path.join(base_process_dir, "datasets.txt")

                # add to datasets.txt for presenterd
                try:
                    open(datasets_file, "a", encoding="utf-8").write(
                        xdsapp_path_local.split("/gpfs/current/processed/")[1] + "\n"
                    )
                except RuntimeError as err_msg:
                    self.log.debug("Cannot write to datasets.txt")
                    self.log.debug(sys.exc_info())

                # create call
                ssh = HWR.beamline.session.get_ssh_command()
                sbatch = HWR.beamline.session.get_sbatch_command(
                    jobname_prefix="xdsapp",
                    logfile_path=xdsapp_path.replace(
                        HWR.beamline.session.get_beamtime_metadata()[2],
                        "/beamline/p11/current",
                    )
                    + "/xdsapp.log",
                )

                self.log.debug(
                    "=============== XDSAPP ================"
                    + xdsapp_path.replace(
                        HWR.beamline.session.get_beamtime_metadata()[2],
                        "/beamline/p11/current",
                    )
                )
                cmd = (
                    "/asap3/petra3/gpfs/common/p11/processing/xdsapp_sbatch.sh "
                    + "{imagepath:s} {processpath:s} {res:f}"
                ).format(
                    imagepath=image_dir + "/" + filename,
                    processpath=xdsapp_path.replace(
                        HWR.beamline.session.get_beamtime_metadata()[2],
                        "/beamline/p11/current",
                    ),
                    res=resolution,
                )

                self.log.debug(
                    '{ssh:s} "{sbatch:s} --wrap \\"{cmd:s}\\""'.format(
                        ssh=ssh, sbatch=sbatch, cmd=cmd
                    )
                )

                os.system(
                    '{ssh:s} "{sbatch:s} --wrap \\"{cmd:s}\\""'.format(
                        ssh=ssh, sbatch=sbatch, cmd=cmd
                    )
                )

    def diffractometer_prepare_collection(self):

        self.log.debug("#COLLECT# preparing collection ")
        if not HWR.beamline.diffractometer.is_collect_phase():
            self.log.debug("#COLLECT# going to collect phase")
            HWR.beamline.diffractometer.goto_collect_phase(wait=True)

        self.log.debug(
            "#COLLECT# now in collect phase: %s"
            % HWR.beamline.diffractometer.is_collect_phase()
        )

        return HWR.beamline.diffractometer.is_collect_phase()

    def prepare_std_collection(self, start_angle, img_range):
        """
        The function prepares a standard collection by setting the start angle and angle increment in
        the header of the Eiger detector.

        :param start_angle: The start_angle parameter represents the starting angle of the standard collection
        sequence. It is used to also set the start angle in the header of the detector.
        :param img_range: The `img_range` parameter represents the range of angles over which the
        detector will collect single image. It is used to set the angle increment in the header of the Eiger
        detector
        :return: a boolean value of True.
        """
        # Add start angle to the header
        osc_pars = self.current_dc_parameters["oscillation_sequence"][0]
        start_angle = osc_pars["start"]
        HWR.beamline.detector.set_eiger_start_angle(start_angle)

        # Add angle increment to the header
        osc_pars = self.current_dc_parameters["oscillation_sequence"][0]
        img_range = osc_pars["range"]
        HWR.beamline.detector.set_eiger_angle_increment(img_range)

    def omega_mv(self, target, speed):
        """
        The function sets the velocity of the omega motor, moves the omega motor to a target position,
        and waits for the movement to complete.

        :param target: The target parameter is the desired position or angle that you want the omega
        motor to move to.
        :param speed: The speed parameter is the desired velocity at which the omega motor should move
        """
        HWR.beamline.diffractometer.set_omega_velocity(speed)
        HWR.beamline.diffractometer.move_omega(target)
        HWR.beamline.diffractometer.wait_omega()

    def prepare_characterization(self):
        """
        The function prepares for characterization data collection by setting the start angle and angle
        increment for the detector.
        :return: a boolean value of True.
        """
        self.log.debug("Preparing for characterization data collection.")

        # Add start angle to the header
        osc_pars = self.current_dc_parameters["oscillation_sequence"][0]
        start_angle = osc_pars["start"]
        HWR.beamline.detector.set_eiger_start_angle(start_angle)

        # Add angle increment to the header
        osc_pars = self.current_dc_parameters["oscillation_sequence"][0]
        img_range = osc_pars["range"]
        HWR.beamline.detector.set_eiger_angle_increment(img_range)

    def get_relative_path(self, path1, path2):
        """
        The function `get_relative_path` takes two paths as input and returns the relative path from the
        first path to the second path.

        :param path1: The `path1` parameter is a string representing the first path. It can be an
        absolute or relative path to a file or directory
        :param path2: The `path2` parameter is a string representing a file or directory path
        :return: the relative path between `path1` and `path2`.
        """
        path_1 = path1.split(os.path.sep)
        path_2 = path2.split(os.path.sep)

        for i, v__ in enumerate(path_2):
            if path_1[i] != v__:
                break

            parts = [".."] * (len(path_2) - i)
            parts.extend(path_1[i:])

        return os.path.join(*parts)

    def base_dir(self, path, what):
        """
        The function `base_dir` returns the base directory path of a given file or directory.

        :param path: The `path` parameter is a string representing a file path
        :param what: The "what" parameter is a string that represents the directory or file name that
        you are searching for within the given path
        :return: the base directory path that contains the specified "what" directory or file.
        """
        what = what.lstrip(os.path.sep)

        if path.startswith(os.path.sep):
            start_sep = os.path.sep
        else:
            start_sep = ""

        path_ = path.split(os.path.sep)
        for i, v__ in enumerate(path_):
            if path_[i] == what:
                break

        return start_sep + os.path.join(*path_[: i + 1])

    def mkdir_with_mode(self, directory, mode):
        """
        The function creates a directory with a specified mode if it does not already exist.

        :param directory: The "directory" parameter is the path of the directory that you want to
        create. It can be an absolute path or a relative path
        :param mode: The "mode" parameter in the above code refers to the permissions that will be set
        for the newly created directory. It is an optional parameter and can be specified as an octal
        value
        """
        if not os.path.isdir(directory):
            oldmask = os.umask(000)
            os.makedirs(directory, mode=mode)
            os.umask(oldmask)
            # self.checkPath(directory,force=True)

            self.log.debug("local directory created")

    def create_directories(self, *args):
        """
        Descript. :
        """
        for directory in args:
            try:
                self.mkdir_with_mode(directory, mode=0o777)
            except os.error as err_:
                if err_.errno != errno.EEXIST:
                    raise

    def check_path(self, path=None, force=False):
        """
        The function checks if a given path is valid and accessible, and creates the directories along
        the path if they don't exist.

        :param path: The `path` parameter is the file path that needs to be checked. It is optional and
        defaults to `None`
        :param force: The "force" parameter is a boolean flag that determines whether the function
        should create the directories in the given path if they do not exist. If "force" is set to True,
        the function will create the directories. If "force" is set to False, the function will return
        False if any, defaults to False (optional)
        :return: the path if it exists and is writable. If the path does not exist and the force
        parameter is set to True, the function will attempt to create the directory and return the path
        if successful. If the path does not exist and the force parameter is set to False, the function
        will print an error message and return False. If the path exists but is not writable, the
        function
        """
        path = str(path).replace("\\", "/")
        dirs = path.strip("/").split("/")
        path = ""
        for dir_ in dirs:
            if dir_.find("*") > -1 or dir_.find("?") > -1 or dir_.find("..") > -1:
                return False
            path += "/" + dir_
            if not os.access(path, os.F_OK):
                if force:
                    try:
                        os.mkdir(path, mode=0o777)
                    except RuntimeError:
                        self.log.debug("mkdir failed:", str(sys.exc_info()))
                        return False
                else:
                    self.log.debug("dir not found:", str(sys.exc_info()))
                    return False
        if not os.access(path, os.W_OK):
            self.log.debug("dir not writeable:", str(sys.exc_info()))
            return False
        return path

    def create_file_directories(self):
        """
        Method create directories for raw files and processing files.
        Directories for xds.input and auto_processing are created
        """
        self.create_directories(
            self.current_dc_parameters["fileinfo"]["directory"],
            self.current_dc_parameters["fileinfo"]["process_directory"],
        )

        """create processing directories and img links"""
        xds_directory, auto_directory = self.prepare_input_files()
        try:
            self.create_directories(xds_directory, auto_directory)
            os.system("chmod -R 777 %s %s" % (xds_directory, auto_directory))
        except Exception:
            logging.exception("Could not create processing file directory")
            return
        if xds_directory:
            self.current_dc_parameters["xds_dir"] = xds_directory
        if auto_directory:
            self.current_dc_parameters["auto_dir"] = auto_directory

    def prepare_input_files(self):
        """
        Descript. :
        """
        i = 1
        logging.getLogger("user_level_log").info(
            "Creating XDS processing input file directories"
        )

        xds_input_file_dirname = (
            "%s" % (self.current_dc_parameters["fileinfo"]["prefix"],)
            + "/rotational_"
            + str(self.current_dc_parameters["fileinfo"]["run_number"]).zfill(3)
        )
        xds_directory = os.path.join(
            self.current_dc_parameters["fileinfo"]["directory"].replace(
                "/current/raw", "/current/processed"
            ),
            xds_input_file_dirname,
            "xdsapp",
        )

        auto_directory = xds_directory

        logging.getLogger("HWR").info(
            "[COLLECT] Processing input file directories: XDS: %s, AUTO: %s"
            % (xds_directory, auto_directory)
        )
        return xds_directory, auto_directory

    def take_crystal_snapshots(self):
        """
        Descript. :
        """
        if self.current_dc_parameters["take_snapshots"]:
            snapshot_directory = os.path.join(
                self.current_dc_parameters["fileinfo"]["directory"], "snapshot"
            )
            if not os.path.exists(snapshot_directory):
                try:
                    self.create_directories(snapshot_directory)
                except Exception:
                    logging.getLogger("HWR").exception(
                        "Collection: Error creating snapshot directory"
                    )

            number_of_snapshots = 1  # 4
            logging.getLogger("user_level_log").info(
                "Collection: Taking %d sample snapshot(s)" % number_of_snapshots
            )
            if HWR.beamline.diffractometer.get_current_phase() != "Centring":
                logging.getLogger("user_level_log").info(
                    "Moving Diffractometer to CentringPhase"
                )
                HWR.beamline.diffractometer.goto_centring_phase(wait=True)
                self.move_to_centered_position()

            for snapshot_index in range(number_of_snapshots):
                snapshot_filename = os.path.join(
                    snapshot_directory,
                    "%s_%s_%s.snapshot.jpeg"
                    % (
                        self.current_dc_parameters["fileinfo"]["prefix"],
                        self.current_dc_parameters["fileinfo"]["run_number"],
                        (snapshot_index + 1),
                    ),
                )
                self.current_dc_parameters[
                    "xtalSnapshotFullPath%i" % (snapshot_index + 1)
                ] = snapshot_filename
                self._take_crystal_snapshot(snapshot_filename)
                time.sleep(1)  # needed, otherwise will get the same images
                if number_of_snapshots > 1:
                    HWR.beamline.diffractometer.move_omega_relative(90)
                    time.sleep(1)  # needed, otherwise will get the same images
