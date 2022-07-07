"""
  File:  X17UMCollect derived from BIOMAXCollect.py

  Description:  This module implements the hardware object for the data collection

todo list:
cancellation
exception
stopCollect
abort

"""

import os
import logging
import gevent
import time
import math
import requests
import uuid
import json
import sys
from subprocess import Popen, PIPE

from mxcubecore.TaskUtils import task
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractCollect import AbstractCollect

from mxcubecore import HardwareRepository as HWR


class X17UMCollect(AbstractCollect, HardwareObject):
    """
    Descript: Data collection class, inherited from AbstractCollect
    """

    # min images to trigger auto processing
    NIMAGES_TRIGGER_AUTO_PROC = 50

    def __init__(self, name):
        """
        Descript. :
        """
        AbstractCollect.__init__(self, name)
        HardwareObject.__init__(self, name)

        self._centring_status = None

        self.osc_id = None
        self.owner = None
        self._collecting = False
        self._error_msg = ""
        self._error_or_aborting = False
        self.collect_frame = None
        self.helical = False
        self.helical_pos = None
        self.ready_event = None
        self.stopCollect = self.stop_collect
        self.triggers_to_collect = None

        self.exp_type_dict = None
        self.display = {}
        self.stop_display = False

        self.datacatalog_enabled = True
        self.datacatalog_url = None
        self.collection_uuid = ""
        self.detector_cover_hwobj = None
        self.detector_cover_open = None
        self.images_per_file = None

    def init(self):
        """
        Descript. :
        """
        self.ready_event = gevent.event.Event()
        self.sample_changer_maint_hwobj = self.get_object_by_role(
            "sample_changer_maintenance"
        )
        # self.detector_cover_open = self.get_channel_object("detector_cover")
        self.datacatalog_url = self.get_property("datacatalog_url", None)
        self.datacatalog_enabled = self.get_property("datacatalog_enabled", True)
        self.images_per_file = self.get_property("images_per_file", 1)

        if self.datacatalog_enabled:
            logging.getLogger("HWR").info(
                "[COLLECT] Datacatalog enabled, url: %s" % self.datacatalog_url
            )
        else:
            logging.getLogger("HWR").warning("[COLLECT] Datacatalog not enabled")

        # todo
        # self.cryo_stream_hwobj = self.getObjectByRole("cryo_stream")

        undulators = []
        # todo
        try:
            for undulator in self["undulators"]:
                undulators.append(undulator)
        except Exception:
            pass

        self.exp_type_dict = {"Mesh": "Mesh", "Helical": "Helical"}
        try:
            min_exp = HWR.beamline.detector.get_minimum_exposure_time()
        except Exception:
            logging.getLogger("HWR").error(
                "[HWR] *** Detector min exposure not available, set to 0.1"
            )
            min_exp = 0.1
        try:
            pix_x = HWR.beamline.detector.get_pixel_size_x()
        except Exception:
            logging.getLogger("HWR").error(
                "[HWR] *** Detector X pixel size not available, set to 7-5e5"
            )
            pix_x = 7.5e-5
        try:
            pix_y = HWR.beamline.detector.get_pixel_size_y()
        except Exception:
            logging.getLogger("HWR").error(
                "[HWR] *** Detector Y pixel size not available, set to 7-5e5"
            )
            pix_y = 7.5e-5

            beam_div_hor, beam_div_ver = HWR.beamline.beam.get_beam_divergence()

            self.set_beamline_configuration(
                synchrotron_name="SSRF",
                directory_prefix=self.get_property("directory_prefix"),
                default_exposure_time=self.get_property("default_exposure_time"),
                minimum_exposure_time=min_exp,
                detector_fileext=HWR.beamline.detector.get_property("file_suffix"),
                detector_type=HWR.beamline.detector.get_property("type"),
                detector_manufacturer=HWR.beamline.detector.get_property("manufacturer"),
                detector_model=HWR.beamline.detector.get_property("model"),
                detector_binning_mode=HWR.beamline.detector.get_property("binning_mode"),
                detector_px=pix_x,
                detector_py=pix_y,
                undulators=undulators,
                focusing_optic=self.get_property("focusing_optic"),
                monochromator_type=self.get_property("monochromator"),
                beam_divergence_vertical=beam_div_ver,
                beam_divergence_horizontal=beam_div_hor,
                polarisation=self.get_property("polarisation"),
                input_files_server=self.get_property("input_files_server"),
            )

        """ to add """
        # self.chan_undulator_gap = self.get_channel_object('UndulatorGap')
        # self.chan_machine_current = self.get_channel_object("MachineCurrent")

        self.emit("collectReady", (True,))
        # TODO get correct value for osc_id
        self.osc_id = 1
        AbstractCollect.init(self)

    def move_to_center_position(self):
        """
        Descript. : go to middle of grid shape
        """
        logging.getLogger("HWR").info("[COLLECT] Moving to center position")
        shape = HWR.beamline.sample_view.get_selected_shapes()[0].as_dict()
        # screen_coord has top-left corner point and then center point
        x = shape.get("screen_coord")[2]
        y = shape.get("screen_coord")[3]

        center_positions = HWR.beamline.diffractometer.get_centred_point_from_coord(
            x, y, return_by_names=True
        )

        print("====== move to target in shape : screen coord = %f,%f motors = "
              % (x, y) + str(center_positions))

        self.move_motors(center_positions)

    # ---------------------------------------------------------
    # refactor do_collect
    def do_collect(self, owner):
        """
        Actual collect sequence
        """
        log = logging.getLogger("user_level_log")
        log.info("Collection: Preparing to collect")
        # todo, add more exceptions and abort
        try:
            self.emit("collectReady", (False,))
            self.emit("collectStarted", (owner, 1))

            # ----------------------------------------------------------------
            """ should all go data collection hook
            self.open_detector_cover()
            self.open_safety_shutter()
            self.open_fast_shutter()
            """
            # ----------------------------------------------------------------

            self.current_dc_parameters["status"] = "Running"
            self.current_dc_parameters["collection_start_time"] = time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            self.current_dc_parameters["synchrotronMode"] = self.get_machine_fill_mode()

            log.info("Collection: Storing data collection in LIMS")
            self.store_data_collection_in_lims()

            log.info(
                "Collection: Creating directories for raw images and processing files"
            )
            self.create_file_directories()

            log.info("Collection: Getting sample info from parameters")
            self.get_sample_info()

            # log.info("Collect: Storing sample info in LIMS")
            # self.store_sample_info_in_lims()

            HWR.beamline.diffractometer.emitCentringSuccessful() # Force curent pos a centred pos

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
                    ] = current_diffractometer_position[motor]

            #  elf.move_to_centered_position() is inside take_crystal_snapshots,
            # which makes sure it move motors to the correct positions and move back
            # if there is a phase change


            log.debug("Collection: going to take snapshots...")
            self.x17um_take_crystal_snapshots()
            log.debug("Collection: snapshots taken")
            # to fix permission issues
            snapshots_files = []

            for key, value in self.current_dc_parameters.items():
                if key.startswith("xtalSnapshotFullPath"):
                    snapshots_files.append(value)
            try:
                archive_directory = self.current_dc_parameters["fileinfo"][
                    "archive_directory"
                ]
                os.chmod(archive_directory, 0o777)
                for file in snapshots_files:
                    os.chmod(file, 0o777)
            except Exception as ex:
                print(ex)
            # prepare beamline for data acquisiion
            self.prepare_acquisition()
            self.emit(
                "collectOscillationStarted",
                (owner, None, None, None, self.current_dc_parameters, None),
            )

            self.data_collection_hook()
            #self.transfer_data() TODO add data transfer here
            self.emit_collection_finished()
        except Exception as ex:
            logging.getLogger("HWR").error("[COLLECT] Data collection failed: %s", ex)
            #if HWR.beamline.detector.last_frame_saved >0: # TODO add data transfer here
            #    self.transfer_data()
            self.emit_collection_failed()
            self.close_fast_shutter()
            self.close_detector_cover()

    def prepare_acquisition(self):
        """ todo
        1. check the currrent value is the same as the tobeset value
        2. check how to add detroi in the mode
        """
        logging.getLogger("HWR").info(
            "[COLLECT] Preparing data collection with parameters: %s"
            % self.current_dc_parameters
        )

        self.stop_display = False
        log = logging.getLogger("user_level_log")

        if "transmission" in self.current_dc_parameters:
            log.info(
                "Collection: Setting transmission to %.3f",
                self.current_dc_parameters["transmission"],
            )
            try:
                HWR.beamline.transmission.set_value(
                    self.current_dc_parameters["transmission"]
                )
            except Exception as ex:
                log.error("Collection: cannot set beamline transmission.")
                logging.getLogger("HWR").error(
                    "[COLLECT] Error setting transmission: %s" % ex
                )
                raise Exception("[COLLECT] Error setting transmission: %s" % ex)

        if "wavelength" in self.current_dc_parameters:
            log.info(
                "Collection: Setting wavelength to %.3f",
                self.current_dc_parameters["wavelength"],
            )
            try:
                self.set_wavelength(self.current_dc_parameters["wavelength"])
            except Exception as ex:
                log.error("Collection: cannot set beamline wavelength.")
                logging.getLogger("HWR").error(
                    "[COLLECT] Error setting wavelength: %s" % ex
                )
                raise Exception("[COLLECT] Error setting wavelength: %s" % ex)

        elif "energy" in self.current_dc_parameters:
            log.info(
                "Collection: Setting energy to %.3f",
                self.current_dc_parameters["energy"],
            )
            try:
                self.set_energy(self.current_dc_parameters["energy"])
            except Exception as ex:
                log.error("Collection: cannot set beamline energy.")
                logging.getLogger("HWR").error(
                    "[COLLECT] Error setting energy: %s" % ex
                )
                raise Exception("[COLLECT] Error setting energy: %s" % ex)

        if "detroi" in self.current_dc_parameters:
            try:
                log.info(
                    "Collection: Setting detector to %s",
                    self.current_dc_parameters["detroi"],
                )
                HWR.beamline.detector.set_roi_mode(self.current_dc_parameters["detroi"])
            except Exception as ex:
                log.error("Collection: cannot set detector roi.")
                logging.getLogger("HWR").error(
                    "[COLLECT] Error setting detector roi: %s" % ex
                )
                raise Exception("[COLLECT] Error setting detector roi: %s" % ex)

        if "resolution" in self.current_dc_parameters:
            try:
                resolution = self.current_dc_parameters["resolution"]["upper"]
                log.info("Collection: Setting resolution to %.3f", resolution)
                HWR.beamline.resolution.set_value(resolution)
            except Exception as ex:
                log.error("Collection: cannot set resolution.")
                logging.getLogger("HWR").error(
                    "[COLLECT] Error setting resolution: %s" % ex
                )
                raise Exception("[COLLECT] Error setting resolution: %s" % ex)

        elif "detector_distance" in self.current_dc_parameters:
            try:
                log.info(
                    "Collection: Moving detector to %f",
                    self.current_dc_parameters["detector_distance"],
                )
                HWR.beamline.detector.distance.set_value(
                    self.current_dc_parameters["detector_distance"]
                )

            except Exception as ex:
                log.error("Collection: cannot set detector distance.")
                logging.getLogger("HWR").error(
                    "[COLLECT] Error setting detector distance: %s" % ex
                )
                raise Exception("[COLLECT] Error setting detector distance: %s" % ex)

        self.triggers_to_collect = self.prepare_triggers_to_collect()

        log.info("Collection: Updating data collection in LIMS")
        self.update_data_collection_in_lims()

        # Generate and set a unique id, used in the data catalog and the detector
        # must know it
        self.collection_uuid = str(uuid.uuid4())
        logging.getLogger("HWR").info(
            "[COLLECT] Generating UUID: %s" % self.collection_uuid
        )

        try:
            HWR.beamline.detector.set_collection_uuid(self.collection_uuid)
        except Exception as ex:
            logging.getLogger("HWR").warning(
                "[COLLECT] Error setting UUID in the detector: %s" % ex
            )
        if self.datacatalog_enabled:
            try:
                self.store_datacollection_uuid_datacatalog()
            except Exception as ex:
                logging.getLogger("HWR").warning(
                    "[COLLECT] Error sending uuid to data catalog: %s", ex
                )

        try:
            self.prepare_detector()
        except Exception as ex:
            log.error("Collection: cannot set prepare detector.")
            logging.getLogger("HWR").error(
                "[COLLECT] Error preparing detector: %s" % ex
            )
            raise Exception("[COLLECT] Error preparing detector: %s" % ex)

        # move MD3 to DataCollection phase if it's not
        if HWR.beamline.diffractometer.get_current_phase() != "DataCollection":
            HWR.beamline.diffractometer.wait_ready()
            log.info("Moving Diffractometer to Data Collection")
            HWR.beamline.diffractometer.set_phase(
                "DataCollection", wait=True, timeout=200
            )

        self.move_to_centered_position()

        # HWR.beamline.diffractometer.save_centring_positions();

    # -------------------------------------------------------------------------------

    def prepare_triggers_to_collect(self):

        oscillation_parameters = self.current_dc_parameters["oscillation_sequence"][0]
        osc_start = oscillation_parameters["start"]
        osc_range = oscillation_parameters["range"]
        nframes = oscillation_parameters["number_of_images"]
        overlap = oscillation_parameters["overlap"]
        triggers_to_collect = []



        if overlap > 0 or overlap < 0:
            # currently for characterization, only collect one image at each omega
            # position
            ntriggers = nframes
            nframes_per_trigger = 1
            for trigger_num in range(1, ntriggers + 1):
                triggers_to_collect.append(
                    (osc_start, trigger_num, nframes_per_trigger, osc_range)
                )
                osc_start += osc_range * nframes_per_trigger - overlap
        elif self.current_dc_parameters["experiment_type"] == "Mesh":

            logging.getLogger("HWR").info(
                "osc_start %s, nframes %s, osc_range %s num_lines %s"
                % (osc_start, nframes, osc_range, self.get_mesh_num_lines())
            )
            triggers_to_collect.append(
                (osc_start, self.get_mesh_num_lines(), nframes, osc_range)
            )
        else:
            triggers_to_collect.append((osc_start, 1, nframes, osc_range))

        return triggers_to_collect

    def data_collection_hook(self):
        """
        Descript. : main collection command
        """

        try:
            self._collecting = True
            oscillation_parameters = self.current_dc_parameters["oscillation_sequence"][0]
            self.open_detector_cover()

            # if (HWR.beamline.safety_shutter.getShutterState() != "opened"):
            #     raise RuntimeError("[COLLECT] Error: the safety shutter is not open. "
            #                        "Please do it manually")

            # TODO: investigate gevent.timeout exception handing, this wait is to ensure
            # that conf is done before arming
            time.sleep(2)
            try:
                HWR.beamline.detector.wait_config_done()
                HWR.beamline.detector.start_acquisition()
                # Check that detector state was correctly armed by start_acquisition()
                HWR.beamline.detector.wait_ready()
            except Exception as ex:
                logging.getLogger("HWR").error("[COLLECT] Detector Error: %s", ex)
                raise RuntimeError("[COLLECT] Detector error while arming.")

            for (
                osc_start,
                trigger_num,
                nframes_per_trigger,
                osc_range,
            ) in self.triggers_to_collect:

                # Line below is only for shutterless EXTS mode
                shutterless_exptime = oscillation_parameters["exposure_time"] * nframes_per_trigger

                # Line below is only for shutterless EXTS mode
                # with one full oscillation for all images in normal scan
                # with one oscillation per line (= per trigger)
                osc_end = osc_start + osc_range * nframes_per_trigger

                # self.display_task = gevent.spawn(self._update_image_to_display)
                self.progress_task = gevent.spawn(self._update_task_progress)
                self.oscil(osc_start, osc_end, shutterless_exptime, 1, wait=True)
            try:
                # disarm is necessary to get the last image even if the good number of triggers arrived
                HWR.beamline.detector.disarm()
                # Check that detector state is idle when correctly disarmed
                HWR.beamline.detector.wait_idle()
                num_images = oscillation_parameters["number_of_images"] * oscillation_parameters["number_of_lines"]

                # wait that last image is really flushed
                logging.getLogger("HWR").info("[COLLECT] Waiting last image flush...")
                timeout_time = time.time() + 20
                while self.last_image_saved() < num_images and time.time() < timeout_time:
                    time.sleep(0.5)

                if time.time() > timeout_time:
                    raise Exception("Timeout waiting last images")

                logging.getLogger("HWR").info(
                        "[COLLECT] Detector images saved: %s/%s" % (num_images, num_images)
                )
                self.emit("collectImageTaken", num_images)
                self.emit("progressStep", 100)

            except Exception as ex:
                HWR.beamline.detector.stop_acquisition()

                self.close_detector_cover()
                self.emit(
                    "collectImageTaken", self.last_image_saved()
                )
        except RuntimeError as ex:
            HWR.beamline.detector.stop_acquisition()
            self.data_collection_cleanup()
            logging.getLogger("HWR").error("[COLLECT] Runtime Error: %s" % ex)
            raise Exception("data collection hook failed... ", str(ex))
        except Exception:
            HWR.beamline.detector.stop_acquisition()
            self.data_collection_cleanup()
            logging.getLogger("HWR").error("Unexpected error:", sys.exc_info()[0])
            raise Exception("data collection hook failed... ", sys.exc_info()[0])

    def get_mesh_num_lines(self):
        return self.mesh_num_lines

    def get_mesh_total_nb_frames(self):
        return self.mesh_total_nb_frames

    def get_current_shape_id(self):
        return self.current_dc_parameters["shape"]

    def oscil(self, start, end, exptime, npass, wait=True):
        oscillation_parameters = self.current_dc_parameters["oscillation_sequence"][0]
        msg = (
            "[COLLECT] Oscillation requested oscillation_parameters: %s"
            % oscillation_parameters
        )
        # msg += " || dc parameters: %s" % self.current_dc_parameters
        logging.getLogger("HWR").info(msg)

        trigger_mode = HWR.beamline.detector.get_property("trigger_mode")

        if trigger_mode == "exte":
            # In gate mode, the MD must have the number of triggers
            HWR.beamline.diffractometer.setNbImages(oscillation_parameters["number_of_images"])

        if self.helical:
            print(" ^^^^^^^^^^ HELICAL SCAN ^^^^^^^^^^^^")
            HWR.beamline.diffractometer.oscilScan4d(
                start, end, exptime, self.helical_pos, wait=True
            )
        elif self.current_dc_parameters["experiment_type"] == "Mesh":
            mesh_range = oscillation_parameters["mesh_range"]
            # HWR.beamline.diffractometer.raster_scan(20, 22, 10, 0.2, 0.2, 10, 10)
            logging.getLogger("HWR").info(
                "Mesh oscillation requested: number of lines %s"
                % self.get_mesh_num_lines()
            )
            logging.getLogger("HWR").info(
                "Mesh oscillation requested: total number of frames %s"
                % self.get_mesh_total_nb_frames()
            )
            det = HWR.beamline.detector
            latency_time = det.get_latency_time()
            # shape_id = self.get_current_shape_id()
            shape = HWR.beamline.sample_view.get_selected_shapes()[0].as_dict()
            self.width = "cell_width"
            range_x = shape.get("num_cols") * shape.get(self.width) / 1000.0
            range_y = shape.get("num_rows") * shape.get("cell_height") / 1000.0
            print(" ^^^^^^^^^^^^ RASTER SCAN ^^^^^^^^^^^^^^^^^^^")
            while(HWR.beamline.diffractometer.get_state() != "Ready"):
                time.sleep(0.1)
            HWR.beamline.diffractometer.oscilScanMesh(
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
            print(" ^^^^^^^^^^^^ OSC SCAN ^^^^^^^^^^^")
            HWR.beamline.diffractometer.oscilScan(start, end, exptime, wait=True)

    def _update_task_progress(self):
        logging.getLogger("HWR").info("[COLLECT] update task progress launched")
        num_images = self.current_dc_parameters["oscillation_sequence"][0][
            "number_of_images"
        ]
        if self.current_dc_parameters.get("experiment_type") == "Mesh":
            # shape_id = self.get_current_shape_id()
            shape = HWR.beamline.sample_view.get_selected_shapes()[0].as_dict()
            num_cols = shape.get("num_cols")
            num_rows = shape.get("num_rows")
            num_images = num_cols * num_rows

        num_steps = 10.0 # arbitrary, 10 progress steps or messages

        if num_images < num_steps:
            step_size = 1
            num_steps = num_images
        else:
            step_size = float(num_images / num_steps)

        exp_time = self.current_dc_parameters["oscillation_sequence"][0]["exposure_time"]

        step_count = 0
        current_frame = 0
        previous_frame = -1

        while self.last_image_saved() == 0:
            time.sleep(exp_time * step_size)

        while step_count < num_steps:
            time.sleep(exp_time * step_size)
            current_frame = self.last_image_saved()

            if previous_frame != current_frame:
                previous_frame = current_frame
                logging.getLogger("HWR").info(
                    "[COLLECT] Detector images saved: %s/%s" % (current_frame, num_images)
                )
                self.emit("collectImageTaken", current_frame)
                self.emit("progressStep", round(100 * current_frame / num_images, 1))
            step_count += 1

    def emit_collection_failed(self):
        """
        Descrip. :
        """
        failed_msg = "Data collection failed!"
        self.current_dc_parameters["status"] = failed_msg
        self.current_dc_parameters["comments"] = "%s\n%s" % (
            failed_msg,
            self._error_msg,
        )
        self.emit(
            "collectOscillationFailed",
            (
                self.owner,
                False,
                failed_msg,
                self.current_dc_parameters.get("collection_id"),
                self.osc_id,
            ),
        )
        self.emit("collectEnded", self.owner, False, failed_msg)
        self.emit("collectReady", (True,))
        self._collecting = None
        self.ready_event.set()

        logging.getLogger("HWR").error(
            "[COLLECT] COLLECTION FAILED, self.current_dc_parameters: %s"
            % self.current_dc_parameters
        )
        self.update_data_collection_in_lims()

    def emit_collection_finished(self):
        """
        Descript. :
        """
        # if self.current_dc_parameters["experiment_type"] == "Mesh":
            # disable stream interface
            # stop spot finding
            # HWR.beamline.detector.disable_stream()
            # self.stop_spot_finder()
        success_msg = "Data collection successful"
        # self.current_dc_parameters["status"] = success_msg
        self.emit(
            "collectOscillationFinished",
            (
                self.owner,
                True,
                success_msg,
                self.current_dc_parameters.get("collection_id"),
                self.osc_id,
                self.current_dc_parameters,
            ),
        )
        self.emit("collectEnded", self.owner, True, success_msg)
        self.emit("collectReady", (True,))
        self.emit("progressStop", ())
        self._collecting = None
        self.ready_event.set()
        self.update_data_collection_in_lims()
        logging.getLogger("HWR").debug(
            "[COLLECT] COLLECTION FINISHED, self.current_dc_parameters: %s"
            % self.current_dc_parameters
        )

        xds_dir = self.current_dc_parameters["xds_dir"]
        raw_data_dir = self.current_dc_parameters["fileinfo"]["process_directory"]

        HWR.beamline.diffractometer.set_phase("Centring", wait=False)

        process = Popen(
                    "~/scripts_mxcube/process_data.sh %s %s"
                    % (raw_data_dir, xds_dir),
                    stdout=PIPE, stderr=PIPE, shell=True, executable="/bin/bash"
                 )

        stdout, stderr = process.communicate()

        if len(stderr)  > 0:
            logging.getLogger("HWR").info('[PROCESS] errors : ' + stderr.decode('utf-8'))

        logging.getLogger("HWR").info('[PROCESS] output : ' + stdout.decode('utf-8'))

        HWR.beamline.diffractometer.wait_ready()


        # if self.current_dc_parameters.get("experiment_type") != "Mesh":
        #     try:
        #         logging.getLogger("HWR").info(
        #             "[X17UMCOLLECT] Going to generate XDS input files"
        #         )
        #         # generate XDS.INP only in raw/process
        #         data_path = self.current_dc_parameters["fileinfo"]["filename"]
        #         logging.getLogger("HWR").info(
        #             "[X17UMCOLLECT] DATA file: %s" % data_path
        #         )
        #         logging.getLogger("HWR").info(
        #             "[X17UMCOLLECT] XDS file: %s"
        #             % self.current_dc_parameters["xds_dir"]
        #         )
        #         # Wait for the master file
        #         self.wait_for_file_copied(data_path)
        #         os.system(
        #             "cd %s;/mxn/groups/biomax/wmxsoft/scripts_mxcube/generate_xds_inp.sh %s &"
        #             % (self.current_dc_parameters["xds_dir"], data_path)
        #         )
        #         logging.getLogger("HWR").info(
        #             "[X17UMCOLLECT] AUTO file: %s"
        #             % self.current_dc_parameters["auto_dir"]
        #         )
        #         os.system(
        #             "cd %s;/mxn/groups/biomax/wmxsoft/scripts_mxcube/generate_xds_inp_auto.sh %s &"
        #             % (self.current_dc_parameters["auto_dir"], data_path)
        #         )
        #         if (
        #             self.current_dc_parameters["experiment_type"] in ("OSC", "Helical")
        #             and self.current_dc_parameters["oscillation_sequence"][0]["overlap"]
        #             == 0
        #             and self.current_dc_parameters["oscillation_sequence"][0][
        #                 "number_of_images"
        #             ]
        #             >= self.NIMAGES_TRIGGER_AUTO_PROC
        #         ):
        #             self.trigger_auto_processing("after", self.current_dc_parameters, 0)
        #     except Exception as ex:
        #         logging.getLogger("HWR").error(
        #             "[COLLECT] Error creating XDS files, %s" % ex
        #         )
        #
        #     # we store the first and the last images, TODO: every 45 degree
        #     logging.getLogger("HWR").info("Storing images in lims, frame number: 1")
        #     try:
        #         self.store_image_in_lims(1)
        #         # self.generate_and_copy_thumbnails(
        #         #     self.current_dc_parameters["fileinfo"]["filename"], 1
        #         # )
        #     except Exception as ex:
        #         print(ex)
        #
        #     last_frame = self.current_dc_parameters["oscillation_sequence"][0][
        #         "number_of_images"
        #     ]
        #     if last_frame > 1:
        #         logging.getLogger("HWR").info(
        #             "Storing images in lims, frame number: %d" % last_frame
        #         )
        #         try:
        #             self.store_image_in_lims(last_frame)
        #             # self.generate_and_copy_thumbnails(
        #             #     self.current_dc_parameters["fileinfo"]["filename"], last_frame
        #             # )
        #         except Exception as ex:
        #             print(ex)
        #
        # if self.datacatalog_enabled:
        #     self.store_datacollection_datacatalog()

    def get_resolution_at_corner(self):
        print("Find good value for get_resolution_at_corner ")
        return HWR.beamline.resolution.get_value_at_corner()

    def store_image_in_lims_by_frame_num(self, frame, motor_position_id=None):
        """
        Descript. :
        """
        # Dont save mesh first and last images
        # Mesh images (best positions) are stored after data analysis
        logging.getLogger("HWR").info(
            "TODO: fix store_image_in_lims_by_frame_num method for nimages>1"
        )
        return

    def generate_and_copy_thumbnails(self, data_path, frame_number):
        #  generare diffraction thumbnails
        image_file_template = self.current_dc_parameters["fileinfo"]["template"]
        archive_directory = self.current_dc_parameters["fileinfo"]["archive_directory"]
        thumb_filename = "%s.thumb.jpeg" % os.path.splitext(image_file_template)[0]
        jpeg_thumbnail_file_template = os.path.join(archive_directory, thumb_filename)
        jpeg_thumbnail_full_path = jpeg_thumbnail_file_template % frame_number

        logging.getLogger("HWR").info(
            "[COLLECT] Generating thumbnails, output filename: %s"
            % jpeg_thumbnail_full_path
        )
        logging.getLogger("HWR").info(
            "[COLLECT] Generating thumbnails, data path: %s" % data_path
        )
        input_file = data_path
        binfactor = 1
        nimages = 1
        first_image = 0
        rootname, ext = os.path.splitext(input_file)
        rings = [0.25, 0.50, 0.75, 1.00, 1.25]
        # master file is need but also data files
        # 100 frames per data file, so adapt accordingly for the file name in case not the first frame
        # TODO: get num_images_per_file as variable
        time.sleep(2)
        if frame_number > 1:
            frame_number = frame_number / 100

        self.wait_for_file_copied(data_path)  # master file

        data_file = data_path.replace("master", "data_{:06d}".format(frame_number))

        self.wait_for_file_copied(data_path)  # data file

        if not os.path.exists(os.path.dirname(jpeg_thumbnail_full_path)):
            os.makedirs(os.path.dirname(jpeg_thumbnail_full_path))
        try:
            # dataset = EigerDataSet(data_path)
            dataset.save_thumbnail(
                binfactor,
                output_file=jpeg_thumbnail_full_path,
                start_image=first_image,
                nb_images=nimages,
                rings=rings,
            )
        except Exception as ex:
            print(ex)

        try:
            os.chmod(os.path.dirname(jpeg_thumbnail_full_path), 0o777)
            os.chmod(jpeg_thumbnail_full_path, 0o777)
        except Exception as ex:
            print(ex)

    def wait_for_file_copied(self, full_file_path):
        # first wait for the file being created
        with gevent.Timeout(
            30, Exception("Timeout waiting for the data file available.")
        ):
            while not os.path.exists(full_file_path):
                gevent.sleep(0.1)

        # then wait to finish the copy
        size1 = -1
        with gevent.Timeout(
            300, Exception("Timeout waiting for the data to be copied available.")
        ):
            while size1 != os.path.getsize(full_file_path):
                size1 = os.path.getsize(full_file_path)
                gevent.sleep(1)

    def store_image_in_lims(self, frame_number, motor_position_id=None):
        """
        Descript. :
        """
        if HWR.beamline.lims:
            file_location = self.current_dc_parameters["fileinfo"]["directory"]
            image_file_template = self.current_dc_parameters["fileinfo"]["template"]
            filename = image_file_template % frame_number
            lims_image = {
                "dataCollectionId": self.current_dc_parameters["collection_id"],
                "fileName": filename,
                "fileLocation": file_location,
                "imageNumber": frame_number,
                "measuredIntensity": HWR.beamline.flux.get_value(),
                "synchrotronCurrent": self.get_machine_current(),
                "machineMessage": self.get_machine_message(),
                "temperature": self.get_cryo_temperature(),
            }
            archive_directory = self.current_dc_parameters["fileinfo"][
                "archive_directory"
            ]

            if archive_directory:
                jpeg_filename = (
                    "%s.thumb.jpeg" % os.path.splitext(image_file_template)[0]
                )
                thumb_filename = (
                    "%s.thumb.jpeg" % os.path.splitext(image_file_template)[0]
                )
                jpeg_file_template = os.path.join(archive_directory, jpeg_filename)
                jpeg_thumbnail_file_template = os.path.join(
                    archive_directory, thumb_filename
                )
                jpeg_full_path = jpeg_file_template % frame_number
                jpeg_thumbnail_full_path = jpeg_thumbnail_file_template % frame_number
                lims_image["jpegFileFullPath"] = jpeg_full_path
                lims_image["jpegThumbnailFileFullPath"] = jpeg_thumbnail_full_path
                lims_image["fileLocation"] = os.path.dirname(jpeg_thumbnail_full_path)
            if motor_position_id:
                lims_image["motorPositionId"] = motor_position_id
            logging.getLogger("HWR").info(
                "LIMS IMAGE: %s, %s, %s, %s"
                % (
                    jpeg_filename,
                    thumb_filename,
                    jpeg_full_path,
                    jpeg_thumbnail_full_path,
                )
            )
            try:
                image_id = HWR.beamline.lims.store_image(lims_image)
            except Exception as ex:
                print(ex)
            # temp fix for ispyb permission issues
            try:
                session_dir = os.path.join(archive_directory, "../../../")
                os.system("chmod -R 777 %s" % (session_dir))
            except Exception as ex:
                print(ex)

            return image_id

    def x17um_take_crystal_snapshots(self):
        """
        Descript. :
        """

        HWR.beamline.diffractometer.wait_ready(1000)  # TODO check why sometimes the MD3 is in running state while we call movePhase

        if self.current_dc_parameters["take_snapshots"]:
            # save the image to the data collection directory for the moment
            snapshot_directory = os.path.join(
                self.current_dc_parameters["fileinfo"]["archive_directory"], "snapshot"
            )
            if not os.path.exists(snapshot_directory):
                try:
                    self.create_directories(snapshot_directory)
                except Exception:
                    logging.getLogger("HWR").exception("Collection: Error creating snapshot directory")

            # for plate head, takes only one image
            if (self.current_dc_parameters["experiment_type"] == "Mesh" #or
                # HWR.beamline.diffractometer.head_type == HWR.beamline.diffractometer.HEAD_TYPE_PLATE
            ):
                number_of_snapshots = 1
            else:
                number_of_snapshots = 1  #  take only one image for the moment TODO use the GUI parameter

            logging.getLogger("user_level_log").info(
                "Collection: Taking %d sample snapshot(s)" % number_of_snapshots
            )
            if HWR.beamline.diffractometer.get_current_phase() != "Centring":
                logging.getLogger("user_level_log").info(
                    "Moving Diffractometer to CentringPhase"
                )
                HWR.beamline.diffractometer.set_phase(
                    "Centring", wait=True, timeout=200
                )
            # TODO check if is useful in case of mesh scan to move to center
            #  with self.move_to_center_position()

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
                # self._do_take_snapshot(snapshot_filename)
                self._take_crystal_snapshot(snapshot_filename)
                time.sleep(1)  # needed, otherwise will get the same images
                if number_of_snapshots > 1:
                    HWR.beamline.diffractometer.phiMotor.set_value_relative(90)
                    time.sleep(1)  # needed, otherwise will get the same images

    def trigger_auto_processing(self, process_event, params_dict, frame_number):
        """
        Descript. :
        """
        # todo
        fast_dp_dir = os.path.join(params_dict["auto_dir"], "fast_dp")
        biomax_pipeline_dir = os.path.join(params_dict["auto_dir"], "biomax_pipeline")
        # autoPROC_dir = os.path.join(params_dict["auto_dir"],"autoPROC")

        self.create_directories(fast_dp_dir)  # , biomax_pipeline_dir)#, autoPROC_dir)

        logging.getLogger("HWR").info(
            "[COLLECT] triggering auto processing, parameters: %s" % params_dict
        )
        logging.getLogger("HWR").info(
            "[COLLECT] triggering auto processing, self.current_dc_parameters: %s"
            % self.current_dc_parameters
        )

        logging.getLogger("HWR").info("[COLLECT] Launching fast_dp")
        os.system(
            "cd %s;/mxn/groups/biomax/wmxsoft/scripts_mxcube/fast_dp.sh %s &"
            % (fast_dp_dir, params_dict["fileinfo"]["filename"])
        )

        # logging.getLogger("HWR").info("[COLLECT] Launching biomax_pipeline")
        # os.system("cd %s;/mxn/groups/biomax/wmxsoft/scripts_mxcube/biomax_pipeline.sh %s &" \
        #    % (biomax_pipeline_dir, params_dict['fileinfo']['filename']))
        # os.system("cd %s;/mxn/groups/biomax/wmxsoft/scripts_mxcube/autoPROC.sh %s &"  \
        #    % (autoPROC_dir, params_dict['fileinfo']['filename']))
        # return

        logging.getLogger("HWR").info("[COLLECT] Launching MAXIV Autoprocessing")
        if HWR.beamline.offline_processing is not None:
            HWR.beamline.offline_processing.execute_autoprocessing(
                process_event, self.current_dc_parameters, frame_number
            )

    def get_beam_centre(self):
        """
        Descript. :
        """
        # if HWR.beamline.resolution is not None:
        #     return HWR.beamline.resolution.get_beam_centre()
        # else:
        #     return None, None
        return (
            HWR.beamline.diffractometer.beam_position_horizontal.get_value(),
            HWR.beamline.diffractometer.beam_position_vertical.get_value(),
        )

    def get_beam_shape(self):
        """
        Descript. :
        """
        if HWR.beamline.beam is not None:
            return HWR.beamline.beam.get_beam_shape()

    def open_detector_cover(self):
        """
        Descript. :
        """
        try:
            logging.getLogger("HWR").info("Openning the detector cover.")
            #self.detector_cover_open.set_value(1)

            if self.detector_cover_hwobj is not None:
                self.detector_cover_hwobj.openShutter()
            time.sleep(3)  # make sure the cover is up before the data collection stars
        except Exception:
            logging.getLogger("HWR").exception("Could not open the detector cover")
            pass

    def close_detector_cover(self):
        """
        Descript. :
        """
        try:
            logging.getLogger("HWR").info("Closing the detector cover")
            #self.detector_cover_open.set_value(0)

            #if self.detector_cover_hwobj is not None:
            #    self.detector_cover_hwobj.closeShutter()
            time.sleep(3)  # make sure the cover is closed before continuing
        except Exception:
            logging.getLogger("HWR").exception("Could not close the detector cover")
            pass

    def open_safety_shutter(self):
        """
        Descript. :
        """
        # todo add time out? if over certain time, then stop acquisiion and
        # popup an error message
        if HWR.beamline.safety_shutter.getShutterState() == "opened":
            return
        timeout = 5
        count_time = 0
        logging.getLogger("HWR").info("Opening the safety shutter.")
        HWR.beamline.safety_shutter.openShutter()
        while (
            HWR.beamline.safety_shutter.getShutterState() == "closed"
            and count_time < timeout
        ):
            time.sleep(0.1)
            count_time += 0.1
        if HWR.beamline.safety_shutter.getShutterState() == "closed":
            logging.getLogger("HWR").exception("Could not open the safety shutter")
            raise Exception("Could not open the safety shutter")

    def close_safety_shutter(self):
        """
        Descript. :
        """
        # todo, add timeout, same as open
        logging.getLogger("HWR").info("Closing the safety shutter.")
        HWR.beamline.safety_shutter.closeShutter()
        while HWR.beamline.safety_shutter.getShutterState() == "opened":
            time.sleep(0.1)

    def open_fast_shutter(self):
        """
        Descript. : important to make sure it's passed, as we
                    don't open the fast shutter in MXCuBE
        """
        pass

    def close_fast_shutter(self):
        """
        Descript. :
        """
        # to do, close the fast shutter as early as possible in case
        # MD3 fails to do so
        pass

    @task
    def _take_crystal_snapshot(self, filename):
        """
        Descript. :
        """
        # take image from server
        HWR.beamline.sample_view._camera.take_snapshot(filename)

    def set_helical(self, helical_on):
        """
        Descript. :
        """
        self.helical = helical_on

    def set_helical_pos(self, helical_oscil_pos):
        """
        Descript. :
        """
        self.helical_pos = helical_oscil_pos

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

        # TODO the hack below overrides the num_lines from queue entry
        # that is correct for MD2 but not for MD3
        # a better implementation would be to fix the value in the set_dc_params
        shape = HWR.beamline.sample_view.get_selected_shapes()[0].as_dict()
        self.mesh_num_lines = shape.get("num_cols")  # total_nb_frames is bad

        # TODO the hack below overrides the mesh_total_nb_frames from queue entry
        self.mesh_total_nb_frames = shape.get("num_cols") * shape.get("num_rows") # mesh_total_nb_frames

        self.mesh_range = {"horizontal_range": mesh_range_param[0]*2, "vertical_range": mesh_range_param[1]*2}
        self.mesh_center = mesh_center_param

        self.log.debug("set mesh scan params: nlines (columns) %d, total frames %d, range %s" % (self.mesh_num_lines , self.mesh_total_nb_frames, self.mesh_range))
        self.log.debug("set mesh scan params: " + str(self.mesh_center))
    def set_energy(self, value):
        logging.getLogger("HWR").info("[COLLECT] Setting beamline energy")
        HWR.beamline.energy.set_value(value)  # keV
        logging.getLogger("HWR").info("[COLLECT] Setting detector energy")
        # HWR.beamline.detector.set_photon_energy(value * 1000)  # ev

    def set_wavelength(self, value):
        HWR.beamline.energy.set_wavelength(value)
        current_energy = HWR.beamline.energy.get_energy()
        HWR.beamline.detector.set_photon_energy(current_energy * 1000)

    @task
    def move_motors(self, motor_position_dict):
        """
        Descript. : synchronized move start of a series of motors, with a wait for the end of all moves
        """
        HWR.beamline.diffractometer.move_sync_motors(motor_position_dict, wait=True)

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
            # temporary, to improve
            os.system("chmod -R 777 %s %s" % (xds_directory, auto_directory))
            """todo, create link of imgs for auto_processing
            try:
                os.symlink(files_directory, os.path.join(process_directory, "img"))
            except os.error, e:
                if e.errno != errno.EEXIST:
                    raise
            """
            # os.symlink(files_directory, os.path.join(process_directory, "img"))
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
            "Creating XDS (SSRF-X17UM) processing input file directories"
        )

        while True:
            xds_input_file_dirname = "xds_%s_%s_%d" % (
                self.current_dc_parameters["fileinfo"]["prefix"],
                self.current_dc_parameters["fileinfo"]["run_number"],
                i,
            )
            xds_directory = os.path.join(
                self.current_dc_parameters["fileinfo"]["directory"],
                "process",
                xds_input_file_dirname,
            )
            if not os.path.exists(xds_directory):
                break
            i += 1
        auto_directory = os.path.join(
            self.current_dc_parameters["fileinfo"]["process_directory"],
            xds_input_file_dirname,
        )
        logging.getLogger("HWR").info(
            "[COLLECT] Processing input file directories: XDS: %s, AUTO: %s"
            % (xds_directory, auto_directory)
        )
        return xds_directory, auto_directory

    # def move_detector(self, value):
    #     """
    #     Descript. : move detector to the set distance
    #     """
    #     lower_limit, upper_limit = self.get_detector_distance_limits()
    #     logging.getLogger("HWR").info(
    #         "...................value %s, detector movement start..... %s"
    #         % (value, HWR.beamline.detector.distance.get_value())
    #     )
    #     if upper_limit is not None and lower_limit is not None:
    #         if value >= upper_limit or value <= lower_limit:
    #             logging.getLogger("HWR").exception(
    #                 "Can't move detector, the value is out of limits"
    #             )
    #             self.stop_collect()
    #         else:
    #             try:
    #                 if HWR.beamline.detector.distance is not None:
    #                     HWR.beamline.detector.distance.set_value(value, timeout=50)
    #                     # 30s is not enough for the whole range
    #             except Exception:
    #                 logging.getLogger("HWR").exception(
    #                     "Problems when moving detector!!"
    #                 )
    #                 self.stop_collect()
    #     else:
    #         logging.getLogger("HWR").exception(
    #             "Can't get distance limits, not moving detector!!"
    #         )
    #     logging.getLogger("HWR").info(
    #         "....................value %s detector movement finished.....%s"
    #         % (value, HWR.beamline.detector.distance.get_value())
    #     )

    def last_image_saved(self):
        """
            Description: returns the number of images saved once detector was armed
        """
        image_list =  HWR.beamline.detector.get_file_list()
        if image_list is None:
            return 0
        else:
            nimages = len(image_list) - 1  # -1 because there is the master file
            return nimages

    def prepare_detector(self):
        logging.getLogger("HWR").info("Cleaning old detector images !!!!!")
        HWR.beamline.detector.clear()  # TODO remove this line here to help debugging new image files
        config = HWR.beamline.detector.col_config

        oscillation_parameters = self.current_dc_parameters["oscillation_sequence"][0]
        (
            osc_start,
            trigger_num,
            nframes_per_trigger,
            osc_range,
        ) = self.triggers_to_collect[0]

        if self.current_dc_parameters["experiment_type"] == "Mesh":
            if HWR.beamline.detector.is_exte_enabled():
                ntrigger = self.get_mesh_total_nb_frames()
                nframes_per_trigger = 1  # by definition of Dectris EXTE mode
            else:
                ntrigger = self.get_mesh_num_lines()

            config["nimages"] = round(self.get_mesh_total_nb_frames() / ntrigger);  # TODO restore use of input param nframes_per_trigger when its value is correct

            self.log.debug("Preparing detector for %d triggers of %d images (%f sec per image)" %
                           (ntrigger, nframes_per_trigger, oscillation_parameters["exposure_time"]))
        else:
            ntrigger = len(self.triggers_to_collect)
            config["nimages"] = oscillation_parameters["number_of_images"]

        """ move after setting energy
        if roi == "4M":
            config['RoiMode'] = "4M"
        else:
            config['RoiMode'] = "disabled" #disabled means 16M      
        """

        config["photon_energy"] = self.current_dc_parameters["energy"] * 1000   # must be in eV in detector
        config["omega_start"] = osc_start  # oscillation_parameters['start']
        config["omega_increment"] = osc_range  # oscillation_parameters["range"]
        beam_centre_x, beam_centre_y = self.get_beam_centre()  # returns pixel
        config["beam_center_x"] = beam_centre_x  # unit, should be pixel for master file
        config["beam_center_y"] = beam_centre_y
        config["detector_distance"] = HWR.beamline.detector.distance.get_value() / 1000.0
        config["frame_time"] = oscillation_parameters["exposure_time"]
        config["count_time"] = config["frame_time"] - 0.001  # TODO check if it can ne exactly same as frame_time
        config["ntrigger"] = ntrigger

        try:
            # TODO check if oscillation_parameters["images_per_file"] is provided
            config["nimages_per_file"] = {"value": self.images_per_file,
                                        "api_name": "filewriter"}
        except Exception:
            config["nimages_per_file"] = {"value": 1, "api_name": "filewriter"}

        if nframes_per_trigger * ntrigger < config["nimages_per_file"]["value"]:
            self.display["delay"] = (
                nframes_per_trigger * ntrigger * oscillation_parameters["exposure_time"]
            )
        else:
            self.display["delay"] = (
                config["nimages_per_file"]["value"] * oscillation_parameters["exposure_time"]
            )
        self.display["exp"] = oscillation_parameters["exposure_time"]
        self.display["nimages"] = nframes_per_trigger * ntrigger
        config["image_nr_start"] = {"value": oscillation_parameters["start_image_number"], "api_name": "filewriter"}

        file_parameters = self.current_dc_parameters["fileinfo"]
        file_parameters["suffix"] = self.bl_config.detector_fileext
        image_file_template = "%(prefix)s_%(run_number)s" % file_parameters
        name_pattern = os.path.join(file_parameters["directory"], image_file_template)
        #    file_parameters["template"] = image_file_template
        file_parameters["filename"] = "%s_master.h5" % name_pattern
        self.display["file_name1"] = file_parameters["filename"]

        # os.path.join(file_parameters["directory"], image_file_template)

        import re
        config["name_pattern"]["value"] = re.sub(
            "^/data", "", name_pattern
        )  # remove "/data in the beginning" because it is added automatically on the detector

        # TODO check if live streaming of images with a spotfinder like BIOMAXCollect is interesting
        # if self.current_dc_parameters["experiment_type"] == "Mesh":
        #     # enable stream interface
        #     # appendix with grid name, collection id
        #     HWR.beamline.detector.enable_stream()
        #     img_appendix = {
        #         "exp_type": "mesh",
        #         "col_id": self.current_dc_parameters["collection_id"],
        #         "shape_id": self.get_current_shape_id(),
        #     }
        #     HWR.beamline.detector.set_image_appendix(json.dumps(img_appendix))
        # self.start_spot_finder(
        #    oscillation_parameters["exposure_time"],
        #    file_parameters["directory"],
        #    image_file_template,
        # )

        return HWR.beamline.detector.prepare_acquisition(config)

    def stop_collect(self, owner):
        """
        Stops data collection
        """
        logging.getLogger("HWR").error("Stopping collection ....")
        HWR.beamline.diffractometer.abort()
        HWR.beamline.detector.cancel()
        HWR.beamline.detector.disarm()
        if self.current_dc_parameters["experiment_type"] == "Mesh":
            # disable stream interface
            # stop spot finding
            HWR.beamline.detector.disable_stream()
            self.stop_spot_finder()
        if self.data_collect_task is not None:
            self.data_collect_task.kill(block=False)
        logging.getLogger("HWR").error("Collection stopped")
        self.stop_display = True

    def get_undulators_gaps(self):
        """
        Descript. :
        """
        # todo
        return None

    def get_slit_gaps(self):
        """
        Descript. :
        """
        try:
            return HWR.beamline.beam.get_beam_size()
        except Exception:
            return None

    def get_machine_current(self):
        """
        Descript. :
        """
        try:
            return HWR.beamline.machine_info.getCurrent()
        except Exception:
            return None

    def get_machine_message(self):
        """
        Descript. :
        """
        # todo
        return ""

    def get_machine_fill_mode(self):
        """
        Descript. :
        """
        try:
            return HWR.beamline.machine_info.getFillingMode()
        except Exception:
            return ""

    def prepare_for_new_sample(self, manual_mode=True):
        """
        Descript.: prepare beamline for a new sample,
        """
        logging.getLogger("HWR").info("[HWR] Preparing beamline for a new sample.")
        if manual_mode:
            if self.detector_cover_hwobj is not None:
                self.close_detector_cover()
            HWR.beamline.diffractometer.set_phase("Transfer", wait=False)
            #if (
            #    HWR.beamline.safety_shutter is not None
            #    and HWR.beamline.safety_shutter.getShutterState() == "opened"
            #):
            #    self.close_safety_shutter()
        HWR.beamline.detector.distance.set_value(800)

    def _update_image_to_display(self):
        fname1 = "/mxn/groups/biomax/wmxsoft/auto_load_img_cc/to_display"
        fname2 = "/mxn/groups/biomax/ctrl_soft/auto_load_img_cc/to_display"
        time.sleep(self.display["delay"] + 3)
        frequency = 5
        step = int(math.ceil(frequency / self.display["exp"]))
        if step == 1:
            frequency = self.display["exp"]
        for i in range(1, self.display["nimages"] + 1, step):
            # if self.stop_display:
            #    break
            # time.sleep(frequency)
            try:
                os.system("echo %s, %s > %s" % (self.display["file_name1"], i, fname1))
                os.system("echo %s, %s > %s" % (self.display["file_name2"], i, fname2))
            except Exception as ex:
                print(ex)
                if self.stop_display:
                    break
                time.sleep(frequency)

    def enable_datacatalog(self, enable):
        self.datacatalog_enabled = enable

    def store_datacollection_uuid_datacatalog(self):
        msg = {}
        collection = self.current_dc_parameters
        proposal_code = HWR.beamline.session.proposal_code
        proposal_number = HWR.beamline.session.proposal_number

        proposal_info = HWR.beamline.lims.get_proposal(proposal_code, proposal_number)
        msg["time"] = time.time()
        msg["proposal"] = proposal_number
        msg["uuid"] = self.collection_uuid
        msg["beamline"] = "BioMAX"
        msg["event"] = "biomax-experiment-began"
        msg["directory"] = collection.get("fileinfo").get("directory")

        logging.getLogger("HWR").info(
            "[HWR] Sending collection started info to the data catalog: %s" % msg
        )
        proxies = {"http": None, "https": None}

        if self.datacatalog_url:
            try:
                requests.post(
                    self.datacatalog_url, data=json.dumps(msg), proxies=proxies
                )
            except Exception as ex:
                logging.getLogger("HWR").error(
                    "[HWR] Error sending collection started info to the data catalog: %s %s"
                    % (self.datacatalog_url, ex)
                )
        else:
            logging.getLogger("HWR").error(
                "[HWR] Error sending collection started info to the data catalog: No datacatalog URL specified"
            )

    def store_datacollection_datacatalog(self):
        """
        Send the data collection parameters to the data catalog. In the form:
        """
        msg = {}
        # files = []
        collection = self.current_dc_parameters
        proposal_code = HWR.beamline.session.proposal_code
        proposal_number = HWR.beamline.session.proposal_number

        proposal_info = HWR.beamline.lims.get_proposal(proposal_code, proposal_number)
        # session info is missing!
        sessionId = collection.get("sessionId", None)
        if sessionId:
            session_info = HWR.beamline.lims.get_session(sessionId)
            proposal_info["Session"] = session_info
        else:
            # We do not send this info when the commissioning is the fake proposal
            return

        collection["proposalInfo"] = proposal_info

        # the following lines are fot helping with serialization
        try:
            collection["proposalInfo"]["Session"]["lastUpdate"] = collection[
                "proposalInfo"
            ]["Session"]["lastUpdate"].isoformat()
            collection["proposalInfo"]["Session"]["timeStamp"] = collection[
                "proposalInfo"
            ]["Session"]["timeStamp"].isoformat()
        except Exception:
            if "Session" in collection["proposalInfo"].keys():
                collection["proposalInfo"]["Session"]["lastUpdate"] = ""
                collection["proposalInfo"]["Session"]["timeStamp"] = ""
        try:
            # Default of 100 images per h5 file. TODO: move to xml config
            num_files = int(
                math.ceil(
                    collection["oscillation_sequence"][0]["number_of_images"] / 100.0
                )
            )
        except Exception as ex:
            logging.getLogger("HWR").error("[HWR] Error during data catalog: %s" % ex)
            num_files = -1

        collection["fileinfo"]["num_files"] = num_files  # num_images per files
        proxies = {"http": None, "https": None}

        # files.append(collection.get('fileinfo').get('filename')) # this is the
        # master file
        template = collection.get("fileinfo").get("template")
        directory = collection.get("fileinfo").get("directory")
        # for num in range(1, num_files + 1):
        #    files.append(os.path.join(directory, template % num))
        # now we build the dict as hannes requested
        msg["event"] = "biomax-experiment-ended"
        msg["proposal"] = proposal_number
        msg["uuid"] = self.collection_uuid
        msg["beamline"] = proposal_info.get("Session", {}).get("beamlineName", "")
        msg["directory"] = directory
        # msg['files'] = files
        msg["scientific"] = collection

        logging.getLogger("HWR").info(
            "[HWR] Sending collection info to the data catalog: %s" % msg
        )

        if self.datacatalog_url:
            try:
                requests.post(
                    self.datacatalog_url, data=json.dumps(msg), proxies=proxies
                )
            except Exception as ex:
                logging.getLogger("HWR").error(
                    "[HWR] Error sending collection info to the data catalog: %s %s"
                    % (self.datacatalog_url, ex)
                )
        else:
            logging.getLogger("HWR").error(
                "[HWR] Error sending collection info to the data catalog: No datacatalog URL specified"
            )
