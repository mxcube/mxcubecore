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

__copyright__ = """ Copyright © 2010 - 2020 by MXCuBE Collaboration """
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



from mxcubecore.HardwareObjects.abstract.AbstractCollect import AbstractCollect
from mxcubecore import HardwareRepository as HWR
from mxcubecore.TaskUtils import task

from mxcubecore.Command.Tango import DeviceProxy



import triggerUtils


FILE_TIMEOUT = 5


class P11Collect(AbstractCollect):
    def __init__(self, *args):
        super(P11Collect, self).__init__(*args)

        self.default_speed = self.get_property("omega_default_speed", 130)
        self.turnback_time = self.get_property("turnback_time", 0.1)
        self.filter_server_name = self.get_property("filterserver")
        self.mono_server_name = self.get_property("monoserver")
        self.filter_server = DeviceProxy(self.filter_server_name)
        self.mono_server = DeviceProxy(self.mono_server_name)
        self.diffr = HWR.beamline.diffractometer

        self.lower_bound_ch = self.get_channel_object("acq_lower_bound")
        self.upper_bound_ch = self.get_channel_object("acq_upper_bound")

        self.acq_arm_cmd = self.get_command_object("acq_arm")
        self.acq_on_cmd = self.get_command_object("acq_on")
        self.acq_off_cmd = self.get_command_object("acq_off")
        self.acq_window_off_cmd = self.get_command_object("acq_window_off")

        self.latest_frames = 1
        self.acq_speed = 1.0
        self.init_ok = False
        self.latest_h5_filename = "TEST_master.h5"

    def init(self):
        super(P11Collect, self).init()

        # os.system("/opt/xray/bin/adxv -socket -colors Gray -rings &")

        # os.system("/bin/bash /gpfs/local/shared/MXCuBE/STRELA/start_viewer_zmq.sh")

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
        HWR.beamline.diffractometer.wait_omega()
        HWR.beamline.diffractometer.move_motors(motor_position_dict)

    def _take_crystal_snapshot(self, filename):
        diffr = HWR.beamline.diffractometer
        self.log.debug("#COLLECT# taking crystal snapshot.")

        if not diffr.is_centring_phase():
            self.log.debug("#COLLECT# take_snapshot. moving to centring phase")
            diffr.goto_centring_phase(wait=True)

        time.sleep(0.3)
        if not diffr.is_centring_phase():
            raise RuntimeError(
                "P11Collect. cannot reach centring phase for acquiring snapshots"
            )

        self.log.debug("#COLLECT# saving snapshot to %s" % filename)
        HWR.beamline.sample_view.save_snapshot(filename)

    def data_collection_hook(self):
        if not self.init_ok:
            raise RuntimeError(
                "P11Collect. - object initialization failed. COLLECTION not possible"
            )

        self.diffr = HWR.beamline.diffractometer
        detector = HWR.beamline.detector

        dc_pars = self.current_dc_parameters
        collection_type = dc_pars["experiment_type"]

        self.log.debug(
            "======================= P11Collect. DATA COLLECTION HOOK =========================================="
        )
        self.log.debug(str(collection_type))
        self.log.debug(str(self.current_dc_parameters))

        osc_pars = self.current_dc_parameters["oscillation_sequence"][0]
        file_info = self.current_dc_parameters["fileinfo"]

        start_angle = osc_pars["start"]
        nframes = osc_pars["number_of_images"]
        self.latest_frames = nframes

        img_range = osc_pars["range"]
        exp_time = osc_pars["exposure_time"]
        self.acq_speed = img_range / exp_time

        if not self.diffractometer_prepare_collection():
            raise BaseException("Cannot prepare diffractometer for collection")

        if collection_type == "Characterization":
            self.log.debug("P11Collect.  Characterization")
            ret = self.prepare_characterization()
        else:
            stop_angle = start_angle + img_range * nframes

            self.log.debug("P11Collect.  Standard Collection")
            self.log.debug(
                "  - collection starts at: %3.2f - ends at: %3.2f "
                % (start_angle, stop_angle)
            )

            ret = self.prepare_std_collection(start_angle, img_range)

        if not ret:
            raise BaseException("Cannot set prepare collection . Aborting")

        # writeInfo (is it necessary?)

        # # Separate_instance of the modified Dectris pyqt Viewer.
        # print("=============== STARTING THE VIEWER ===============")
        # new_gui = subprocess.Popen("/bin/bash /gpfs/local/shared/MXCuBE/STRELA/start_viewer.sh")
        # print("=============== FINISHED STARTING THE VIEWER ===============")

        try:
            self.log.debug("############# #COLLECT# Opening detector cover")
            self.diffr.detector_cover_open(wait=True)
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

                # # === if folder exists - increase run number
                # print("========CHECKING EXISTING DIRECTORY ===========")
                # print(os.path.exists(self.latest_h5_filename))
                # if os.path.exists(self.latest_h5_filename):
                #     print("======= File exists! Increasing run number ===========")
                #     self.current_dc_parameters["fileinfo"]["run_number"]=self.current_dc_parameters["fileinfo"]["run_number"]+1
                #     print("Run number has changed to ", self.current_dc_parameters["fileinfo"]["run_number"])
                #     runno = self.current_dc_parameters["fileinfo"]["run_number"]
                #     filepath = os.path.join(basepath,prefix,"screening_"+str(runno).zfill(3)+"/"+"%s_%d" % (prefix, runno))

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

                # overlap = osc_pars["overlap"]
                angle_inc = 90.0
                detector.prepare_characterisation(
                    exp_time, nframes, angle_inc, filepath
                )
            else:
                # AG: Create rotational_001, etc the same way as for CC in case of characterisation

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

                detector.prepare_std_collection(exp_time, nframes, filepath)

            self.log.debug("#COLLECT# Starting detector")
            detector.start_acquisition()

            if collection_type == "Characterization":
                self.collect_characterisation(
                    start_angle, img_range, nframes, angle_inc, exp_time
                )
                # TODO: Add LiveView here
                # os.system("killall albula")
                # os.system("/opt/dectris/albula/4.0/bin/albula "+self.latest_h5_filename +" &")
                # os.system("adxv "+self.latest_h5_filename +" &")

                # Open index_html
                os.system("firefox /gpfs/current/processed/index.html")

                # Create diffraction snapshots
                for i in range(nframes):
                    os.system(
                        "python3 /gpfs/local/shared/MXCuBE/hdf5tools/albula_api/generate_image.py --input "
                        + self.latest_h5_filename
                        + " --output "
                        + os.path.join(
                            basepath, prefix, "screening_" + str(runno).zfill(3)
                        )
                        + "/"
                        + " --image_number "
                        + str(i + 1)
                    )

            else:
                self.collect_std_collection(start_angle, stop_angle)
                self.generate_xds_template()
                # self.adxv_notify(self.latest_h5_filename)
                # TODO: Add LiveView here
                # os.system("killall albula")
                # os.system("/opt/dectris/albula/4.0/bin/albula "+self.latest_h5_filename +" &")

                # Open index_html
                os.system("firefox /gpfs/current/processed/index.html")

                # Create diffraction snapshots
                os.system(
                    "python3 /gpfs/local/shared/MXCuBE/hdf5tools/albula_api/generate_image.py --input "
                    + self.latest_h5_filename
                    + " --output "
                    + os.path.join(
                        basepath, prefix, "rotational_" + str(runno).zfill(3)
                    )
                    + "/"
                    + " --image_number 1"
                )

        except RuntimeError:
            self.log.error(traceback.format_exc())
        finally:
            self.acquisition_cleanup()

        # self.add_h5_info(self.latest_h5_filename)
        self.trigger_auto_processing()

    def collect_std_collection(self, start_angle, stop_angle):
        """
        The function collects data from a standard acquisition by moving the omega motor from a start
        angle to a stop angle.

        :param start_angle: The starting angle for the collection
        :param stop_angle: The stop_angle parameter is the final angle at which the collection should
        stop
        """

        self.omega_mv(start_angle, self.default_speed)

        self.log.debug("#COLLECT# Running OMEGA through the std acquisition")
        if start_angle <= stop_angle:
            self.lower_bound_ch.set_value(start_angle)
            self.upper_bound_ch.set_value(stop_angle)
        else:
            self.lower_bound_ch.set_value(stop_angle)
            self.upper_bound_ch.set_value(start_angle)
        self.acq_arm_cmd()

        final_pos = stop_angle + self.acq_speed * self.turnback_time

        self.omega_mv(final_pos, self.acq_speed)

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

        diffr = HWR.beamline.diffractometer

        self.log.debug("#COLLECT# Running OMEGA through the char acquisition")

        self.omega_mv(start_angle, self.default_speed)

        for img_no in range(nimages):
            print("collecting image %s" % img_no)
            start_at = start_angle + angle_inc * img_no
            stop_angle = start_at + img_range * 1.0
            print("collecting image %s, angle %f" % (img_no, start_at))

            if start_at >= stop_angle:
                init_pos = start_at - self.acq_speed * self.turnback_time
                # init_pos = start_at - 1.5
            else:
                init_pos = start_at + self.acq_speed * self.turnback_time
                # init_pos = start_at + 1.5
            self.omega_mv(init_pos, self.default_speed)
            self.collect_std_collection(start_angle, stop_angle)

            diffr.set_omega_velocity(self.default_speed)
            self.acq_window_off_cmd()
            self.acq_off_cmd()
            self.log.debug(
                "======= collect_characterisation  Waiting ======================================="
            )

            # Let adxv know whether it is
            # self.adxv_notify(self.latest_h5_filename,img_no+1)

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
        adxv_host = "localhost"  # self.getProperty("adxv_host", "localhost")
        adxv_port = 8100  # int(self.getProperty("adxv_port", "8100"))

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

    def acquisition_cleanup(self):
        """
        The function `acquisition_cleanup` performs various cleanup tasks related to data acquisition,
        such as setting the omega velocity, turning off acquisition and window commands, closing the
        detector cover, and stopping the acquisition.
        """
        try:
            diffr = HWR.beamline.diffractometer
            detector = HWR.beamline.detector
            diffr.set_omega_velocity(self.default_speed)
            self.acq_window_off_cmd()
            self.acq_off_cmd()
            self.log.debug("#COLLECT# Closing detector cover")
            diffr.detector_cover_close(wait=True)
            detector.stop_acquisition()
        except RuntimeError:
            self.log.error(traceback.format_exc())

    def add_h5_info(self, h5file):
        """
        The function `add_h5_info` waits for a specified amount of time for a file to appear on disk and
        raises an exception if the file does not appear within the timeout period.

        :param h5file: The `h5file` parameter is the name or path of the H5 file that you want to add
        information to
        """
        self.log.debug("========== Writing H5 info ==============")
        h5file = self.latest_h5_filename

        # wait up to 5 seconds to see the file appear
        start_wait = time.time()
        while not os.path.exists(h5file):
            if time.time() - start_wait > FILE_TIMEOUT:
                raise RuntimeWarning(
                    "Cannot add info to H5 file. Timeout waiting for file on disk."
                )
            time.sleep(0.5)

        try:
            h5fd = h5py.File(h5file, "r+")
            group = h5fd.create_group("entry/source")
            group.attrs["NX_class"] = np.array("NXsource", dtype="S")
            group.create_dataset("name", data=np.array("PETRA III, DESY", dtype="S"))
            group = h5fd.get("entry/instrument")
            group.create_dataset("name", data=np.array("P11", dtype="S"))
            group = h5fd.create_group("entry/instrument/attenuator")
            group.attrs["NX_class"] = np.array("NXattenuator", dtype="S")

            data_set = group.create_dataset(
                "thickness", dtype="f8", data=self.get_filter_thickness()
            )
            data_set.attrs["units"] = np.array("m", dtype="S")
            data_set = group.create_dataset(
                "type", data=np.array("Aluminum", dtype="S")
            )
            data_set = group.create_dataset(
                "attenuator_transmission",
                dtype="f8",
                data=self.get_filter_transmission(),
            )
            # fix rotation axis and detector orientation
            data_set = h5fd.get("entry/sample/transformations/omega")
            data_set.attrs["vector"] = [1.0, 0.0, 0.0]
            data_set = h5fd.get("entry/instrument/detector/module/fast_pixel_direction")
            data_set.attrs["vector"] = [1.0, 0.0, 0.0]
            data_set = h5fd.get("entry/instrument/detector/module/slow_pixel_direction")
            data_set.attrs["vector"] = [0.0, 1.0, 0.0]
            # delete phi angle info to avoid confusion
            nodes = [
                "entry/sample/goniometer/phi",
                "entry/sample/goniometer/phi_end",
                "entry/sample/goniometer/phi_range_average",
                "entry/sample/goniometer/phi_range_total",
            ]
            for node in nodes:
                if node in h5fd:
                    del h5fd[node]
            h5fd.close()

        except RuntimeError as err_msg:
            self.log.debug("Error while adding info to HDF5 file (%s)" % str(err_msg))
            self.log.debug(traceback.format_exc())

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

            return float(thickness) / 1000000
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

    # TODO: Move to Maxwell completely
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
        self.log.debug("Writing HDF% file header final information")
        self.add_h5_info(self.latest_h5_filename)
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

            # creation will fail if beamtime folder, slurm reservation or
            # bl-fs mount on the compute nodes can not be found
            try:
                btHelper = triggerUtils.Trigger()
            except RuntimeError:
                self.log.debug(sys.exc_info())
                self.log.error("Cannot trigger auto processing")
                return

            resolution = self.get_resolution()
            frames = self.latest_frames

            image_dir_local, filename = os.path.split(self.latest_h5_filename)
            # AG: Image dir at this point is located locally. This path is not seen on the MAXWELL. Path needs to be converted.
            # /gpfs/current/ to  get_beamline_metadata()[2]
            image_dir = image_dir_local.replace(
                "/gpfs/current", triggerUtils.get_beamtime_metadata()[2]
            )
            process_dir = image_dir.replace("/raw/", "/processed/")
            process_dir_local = image_dir_local.replace("/raw/", "/processed/")
            mosflm_path = os.path.join(process_dir, "mosflm")
            mosflm_path_local = os.path.join(process_dir_local, "mosflm")
            self.log.debug('============MOSFLM======== mosflm_path="%s"' % mosflm_path)
            self.log.debug(
                '============MOSFLM======== mosflm_path_local="%s"' % mosflm_path_local
            )

            ssh = btHelper.get_ssh_command()

            try:
                self.mkdir_with_mode(mosflm_path_local, mode=0o777)

                # AG: Explicit write of the non-empty file so that the directory is synchronised with /asap3/...
                # Is is substituted by appropriate process from mosflm_sbatch.sh --output.
                # f=open(mosflm_path_local+"/mosflm.log", 'a')
                # f.write("mosflm.log")
                # f.close()

                # Create mosflm remote dir explicitly:
                # os.system("{ssh:s} \"mkdir -p {mosflm_path:s}\"".format(
                #  ssh = ssh,
                #  mosflm_path = mosflm_path
                # ))

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
            except:
                print(sys.exc_info())

            # create call
            # btHelper.user_sshkey = btHelper.user_sshkey.replace("/gpfs/current",triggerUtils.get_beamtime_metadata()[2])
            ssh = btHelper.get_ssh_command()
            sbatch = btHelper.get_sbatch_command(
                jobname_prefix="mosflm",
                job_dependency="singleton",
                logfile_path=mosflm_path.replace(
                    triggerUtils.get_beamtime_metadata()[2], "/beamline/p11/current"
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
                    triggerUtils.get_beamtime_metadata()[2], "/beamline/p11/current"
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
                    "==== AUTOPROCESSING STANDARD PROCESSING IN PROGRESS =========="
                )

                try:
                    btHelper = triggerUtils.Trigger()
                except RuntimeError:
                    self.log.debug(sys.exc_info())
                    self.log.error("Cannot trigger auto processing")
                    return

                resolution = self.get_resolution()
                frames = self.latest_frames

                image_dir_local, filename = os.path.split(self.latest_h5_filename)

                image_dir = image_dir_local.replace(
                    "/gpfs/current", triggerUtils.get_beamtime_metadata()[2]
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
                    # f=open(xdsapp_path_local+"/xdsapp.log", 'a')
                    # f.write("xdsapp.log")
                    # f.close()

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
                except RuntimeError:
                    print(sys.exc_info())

                # create call
                ssh = btHelper.get_ssh_command()
                sbatch = btHelper.get_sbatch_command(
                    jobname_prefix="xdsapp",
                    job_dependency="",
                    logfile_path=xdsapp_path.replace(
                        triggerUtils.get_beamtime_metadata()[2], "/beamline/p11/current"
                    )
                    + "/xdsapp.log",
                )

                self.log.debug(
                    "=============== XDSAPP ================"
                    + xdsapp_path.replace(
                        triggerUtils.get_beamtime_metadata()[2], "/beamline/p11/current"
                    )
                )
                cmd = (
                    "/asap3/petra3/gpfs/common/p11/processing/xdsapp_sbatch.sh "
                    + "{imagepath:s} {processpath:s} {res:f}"
                ).format(
                    imagepath=image_dir + "/" + filename,
                    processpath=xdsapp_path.replace(
                        triggerUtils.get_beamtime_metadata()[2], "/beamline/p11/current"
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

    #        imagepath = self.path.get_path(
    #                "/central/beamtime/raw/user/sample/rotational_number/" +
    #                "sample_rotational_number_master.h5")
    #        processpath = "/beamline/p11/current" + self.path.get_path(
    #                "/processed/user/sample/rotational_number/xdsapp")
    #
    #
    #
    #
    #       #create processing folder with 0o777
    #        self.path.get_path("/beamline/beamtime/processed/user/sample/" +
    #                "rotational_number/xdsapp", force=True)
    #        #add to datasets.txt for presenterd
    #        try:
    #            f = open(self.path.get_path(
    #                    "/beamline/beamtime/processed/datasets.txt"), "a")
    #            f.write(self.path.get_path(
    #                    "user/sample/rotational_number/xdsapp\n").lstrip("/"))
    #            f.close()
    #        except:
    #            print(sys.exc_info())
    #
    #        #create call
    #        ssh = btHelper.get_ssh_command()
    #        sbatch = btHelper.get_sbatch_command(
    #            jobname_prefix = "xdsapp",
    #            job_dependency = "",
    #            logfile_path = processpath + "/xdsapp.log"
    #        )
    #        cmd = ("/asap3/petra3/gpfs/common/p11/processing/xdsapp_sbatch.sh " + \
    #                "{imagepath:s} {processpath:s} {res:f}").format(
    #            imagepath = imagepath,
    #            processpath = processpath,
    #            res = res
    #        )
    #        print(cmd)
    #        os.system("{ssh:s} \"{sbatch:s} --wrap \\\"{cmd:s}\\\"\"".format(
    #            ssh = ssh,
    #            sbatch = sbatch,
    #            cmd = cmd
    #        ))

    # Test of the autoprocessing as in CC (AG)
    #    def trigger_auto_processing(self, process_event=None, frame_number=None):
    #        self.log.debug("Triggering auto processing. NOT IMPLEMENTED YET. Direct test from CC.")
    #
    #       #creation will fail if beamtime folder, slurm reservation or
    #        #bl-fs mount on the compute nodes can not be found
    #        try:
    #            btHelper = triggerUtils.Trigger()
    #        except:
    #            print(sys.exc_info())
    #            return
    #
    #        energy = self.petraThread.currentMonoEnergy / 1000.
    #        wavelength = 12.3984 / energy #in Angstrom
    #        res = wavelength / (2. * math.sin(0.5 * math.atan(
    #                (311. / 2.) / self.parameters["detectordistance"])))
    #        frames = self.parameters["frames"]
    #        imagepath = self.path.get_path(
    #                "/central/beamtime/raw/user/sample/rotational_number/" +
    #                "sample_rotational_number_master.h5")
    #        processpath = "/beamline/p11/current" + self.path.get_path(
    #                "/processed/user/sample/rotational_number/xdsapp")
    #
    #        #create processing folder with 0o777
    #        self.path.get_path("/beamline/beamtime/processed/user/sample/" +
    #                "rotational_number/xdsapp", force=True)
    #        #add to datasets.txt for presenterd
    #        try:
    #            f = open(self.path.get_path(
    #                    "/beamline/beamtime/processed/datasets.txt"), "a")
    #            f.write(self.path.get_path(
    #                    "user/sample/rotational_number/xdsapp\n").lstrip("/"))
    #            f.close()
    #        except:
    #            print(sys.exc_info())
    #
    #        #create call
    #        ssh = btHelper.get_ssh_command()
    #        sbatch = btHelper.get_sbatch_command(
    #            jobname_prefix = "xdsapp",
    #            job_dependency = "",
    #            logfile_path = processpath + "/xdsapp.log"
    #        )
    #        cmd = ("/asap3/petra3/gpfs/common/p11/processing/xdsapp_sbatch.sh " + \
    #                "{imagepath:s} {processpath:s} {res:f}").format(
    #            imagepath = imagepath,
    #            processpath = processpath,
    #            res = res
    #        )
    #        print(cmd)
    #        os.system("{ssh:s} \"{sbatch:s} --wrap \\\"{cmd:s}\\\"\"".format(
    #            ssh = ssh,
    #            sbatch = sbatch,
    #            cmd = cmd
    #        ))

    def diffractometer_prepare_collection(self):
        diffr = HWR.beamline.diffractometer

        self.log.debug("#COLLECT# preparing collection ")
        if not diffr.is_collect_phase():
            self.log.debug("#COLLECT# going to collect phase")
            # # If the pinhole is Down set pinhole to 200
            # if HWR.beamline.diffractometer.pinhole_hwobj.get_position() == "Down":
            #     print("Pinhole is down. Setting pinhole to 200.")
            #     HWR.beamline.diffractometer.pinhole_hwobj.set_position("200")
            #     HWR.beamline.diffractometer.wait_phase()
            diffr.goto_collect_phase(wait=True)

        self.log.debug("#COLLECT# now in collect phase: %s" % diffr.is_collect_phase())

        return diffr.is_collect_phase()

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

        detector = HWR.beamline.detector
        detector.set_eiger_start_angle(start_angle)

        # Add angle increment to the header
        osc_pars = self.current_dc_parameters["oscillation_sequence"][0]
        img_range = osc_pars["range"]
        detector.set_eiger_angle_increment(img_range)

        return True

    def omega_mv(self, target, speed):
        """
        The function sets the velocity of the omega motor, moves the omega motor to a target position,
        and waits for the movement to complete.

        :param target: The target parameter is the desired position or angle that you want the omega
        motor to move to.
        :param speed: The speed parameter is the desired velocity at which the omega motor should move
        """
        self.diffr.set_omega_velocity(speed)
        self.diffr.move_omega(target)
        self.diffr.wait_omega()

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

        detector = HWR.beamline.detector
        detector.set_eiger_start_angle(start_angle)

        # Add angle increment to the header
        osc_pars = self.current_dc_parameters["oscillation_sequence"][0]
        img_range = osc_pars["range"]
        detector.set_eiger_angle_increment(img_range)

        return True

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

            parts = ["..",] * (len(path_2) - i)
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
                # os.makedirs(directory)
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
                        print("mkdir failed:", str(sys.exc_info()))
                        return False
                else:
                    print("dir not found:", str(sys.exc_info()))
                    return False
        if not os.access(path, os.W_OK):
            print("dir not writeable:", str(sys.exc_info()))
            return False
        return path

    # def mkdir_with_mode_remote(self, directory, mode):
    #    ssh = btHelper.get_ssh_command()
    #
    #    os.system("{ssh:s} \"{sbatch:s} --wrap \\\"{cmd:s}\\\"\"".format(
    #        ssh = ssh,
    #        sbatch = sbatch,
    #        cmd = cmd
    #    ))
