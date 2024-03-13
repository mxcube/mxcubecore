import os
import logging
import gevent
import time
import math
import requests
import uuid
import json
import re
import PyTango
import sys

from mxcubecore.TaskUtils import task
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractCollect import AbstractCollect
from mxcubecore.HardwareObjects.MAXIV.DataCollect import DataCollect


class BIOMAXCollect(DataCollect):
    """
    Descript: Data collection class, inherited from AbstractCollect
    """

    # min images to trigger auto processing
    NIMAGES_TRIGGER_AUTO_PROC = 20

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
        self.char = False
        self.hve = False
        self.ready_event = None
        self.stopCollect = self.stop_collect
        self.triggers_to_collect = None

        self.exp_type_dict = None
        self.display = {}
        self.stop_display = False

        self.datacatalog_enabled = True
        self.datacatalog_url = None
        self.datacatalog_token = None
        self.collection_uuid = ""

        self.flux_before_collect = None
        self.flux_after_collect = None

    def init(self):
        """
        Descript. :
        """
        self.ready_event = gevent.event.Event()
        self.diffractometer_hwobj = self.get_object_by_role("diffractometer")
        self.lims_client_hwobj = self.get_object_by_role("lims_client")
        self.machine_info_hwobj = self.get_object_by_role("mach_info")
        self.energy_hwobj = self.get_object_by_role("energy")
        self.resolution_hwobj = self.get_object_by_role("resolution")
        self.detector_hwobj = self.get_object_by_role("detector")
        self.flux_hwobj = self.get_object_by_role("flux")
        self.autoprocessing_hwobj = self.get_object_by_role("auto_processing")
        self.beam_info_hwobj = self.get_object_by_role("beam_info")
        self.transmission_hwobj = self.get_object_by_role("transmission")
        self.sample_changer_hwobj = self.get_object_by_role("sample_changer")
        self.sample_changer_maint_hwobj = self.get_object_by_role(
            "sample_changer_maintenance"
        )
        self.dtox_hwobj = self.get_object_by_role("dtox")
        self.detector_cover_hwobj = self.get_object_by_role("detector_cover")
        self.session_hwobj = self.get_object_by_role("session")
        self.datacatalog_url = self.get_property("datacatalog_url", None)
        self.datacatalog_token = self.get_property("datacatalog_token", None)
        self.datacatalog_enabled = self.get_property("datacatalog_enabled", True)
        self.shape_history_hwobj = self.get_object_by_role("shape_history")
        self.dozor_hwobj = self.get_object_by_role("dozor")
        self.polarisation = float(self.get_property("polarisation", 0.99))

        if self.datacatalog_enabled:
            logging.getLogger("HWR").info(
                "[COLLECT] Datacatalog enabled, url: %s" % self.datacatalog_url
            )
        else:
            logging.getLogger("HWR").warning("[COLLECT] Datacatalog not enabled")

        self.safety_shutter_hwobj = self.get_object_by_role("safety_shutter")
        # todo
        # self.fast_shutter_hwobj = self.get_object_by_role("fast_shutter")
        # self.cryo_stream_hwobj = self.get_object_by_role("cryo_stream")

        self.exp_type_dict = {"Mesh": "Mesh", "Helical": "Helical"}
        try:
            min_exp = self.detector_hwobj.get_minimum_exposure_time()
        except Exception:
            logging.getLogger("HWR").error(
                "[HWR] *** Detector min exposure not available, set to 0.1"
            )
            min_exp = 0.1
        try:
            pix_x = self.detector_hwobj.get_pixel_size_x()
        except Exception:
            logging.getLogger("HWR").error(
                "[HWR] *** Detector X pixel size not available, set to 7-5e5"
            )
            pix_x = 7.5e-5
        try:
            pix_y = self.detector_hwobj.get_pixel_size_y()
        except Exception:
            logging.getLogger("HWR").error(
                "[HWR] *** Detector Y pixel size not available, set to 7-5e5"
            )
            pix_y = 7.5e-5

        self.set_beamline_configuration(
            synchrotron_name="MAXIV",
            directory_prefix=self.get_property("directory_prefix"),
            default_exposure_time=self.get_property("default_exposure_time"),
            minimum_exposure_time=min_exp,
            detector_fileext=self.detector_hwobj.get_property("file_suffix"),
            detector_type=self.detector_hwobj.get_property("type"),
            detector_manufacturer=self.detector_hwobj.get_property("manufacturer"),
            detector_model=self.detector_hwobj.get_property("model"),
            detector_px=pix_x,
            detector_py=pix_y,
            undulators=self.get_property("undulator"),
            focusing_optic=self.get_property("focusing_optic"),
            monochromator_type=self.get_property("monochromator"),
            beam_divergence_vertical=self.beam_info_hwobj._beam_divergence[1],
            beam_divergence_horizontal=self.beam_info_hwobj._beam_divergence[0],
            detector_binning_mode=None,
            polarisation=self.polarisation,
            input_files_server=self.get_property("input_files_server"),
        )

        self.add_channel(
            {
                "type": "tango",
                "name": "undulator_gap",
                "tangoname": self.get_property("undulator_gap"),
                "timeout": 10000,
            },
            "Position",
        )

        self.emit("collectReady", (True,))

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

            if all(
                item is None for item in self.current_dc_parameters["motors"].values()
            ):
                # No centring point defined
                # create point based on the current position
                current_diffractometer_position = self.diffractometer_hwobj.get_value()
                for motor in self.current_dc_parameters["motors"].keys():
                    self.current_dc_parameters["motors"][
                        motor
                    ] = current_diffractometer_position[motor]

            # todo, self.move_to_centered_position() should go inside take_crystal_snapshots,
            # which makes sure it move motors to the correct positions and move back
            # if there is a phase change
            log.debug("Collection: going to take snapshots...")
            self.take_crystal_snapshots()
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
                if not os.path.exists(archive_directory):
                    try:
                        self.create_directories(archive_directory)
                    except:
                        logging.getLogger("HWR").exception(
                            "Collection: Error creating archive directory"
                        )

                os.chmod(archive_directory, 0o777)
                for file in snapshots_files:
                    os.chmod(file, 0o777)
            except Exception as ex:
                log.error(
                    "[COLLECT] Archive directory preparation failed. Data collection continues. Error was: %s"
                    % str(ex)
                )

            #
            self.close_fast_shutter()
            self.close_detector_cover()
            self.open_safety_shutter()

            # prepare beamline for data acquisiion
            self.prepare_acquisition()
            self.emit(
                "collectOscillationStarted",
                (owner, None, None, None, self.current_dc_parameters, None),
            )

            self.data_collection_hook()
            if (
                self.char
            ):  # correct the omega values in the master file for characterization
                oscillation_parameters = self.current_dc_parameters[
                    "oscillation_sequence"
                ][0]
                overlap = oscillation_parameters["overlap"]
                master_filename = self.current_dc_parameters["fileinfo"]["filename"]
                self.correct_omega_in_master_file(
                    filename=master_filename, overlap=overlap
                )
            self.emit_collection_finished()
        except Exception as ex:
            logging.getLogger("HWR").error("[COLLECT] Data collection failed: %s" % ex)
            self.emit_collection_failed()
            self.close_fast_shutter()
            self.close_detector_cover()

    def prepare_acquisition(self):
        """todo
        1. check the currrent value is the same as the tobeset value
        2. check how to add detroi in the mode
        """
        logging.getLogger("HWR").info(
            "[COLLECT] Preparing data collection with parameters: %s"
            % self.current_dc_parameters
        )

        self.stop_display = False
        log = logging.getLogger("user_level_log")

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

            checkbeam = self.prepare_set_energy()
            try:
                self.set_energy(self.current_dc_parameters["energy"], checkbeam)
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
                self.set_detector_roi(self.current_dc_parameters["detroi"])
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
                self.set_resolution(resolution)
            except Exception as ex:
                log.error("Collection: cannot set resolution.")
                logging.getLogger("HWR").error(
                    "[COLLECT] Error setting resolution: %s" % ex
                )
                raise Exception("[COLLECT] Error setting resolution: %s" % ex)

        elif "detdistance" in self.current_dc_parameters:
            try:
                log.info(
                    "Collection: Moving detector to %f",
                    self.current_dc_parameters["detdistance"],
                )
                self.move_detector(self.current_dc_parameters["detdistance"])
            except Exception as ex:
                log.error("Collection: cannot set detector distance.")
                logging.getLogger("HWR").error(
                    "[COLLECT] Error setting detector distance: %s" % ex
                )
                raise Exception("[COLLECT] Error setting detector distance: %s" % ex)

        if "transmission" in self.current_dc_parameters:
            log.info(
                "Collection: Setting transmission to %.3f",
                self.current_dc_parameters["transmission"],
            )
            try:
                self.set_transmission(self.current_dc_parameters["transmission"])
            except Exception as ex:
                log.error("Collection: cannot set beamline transmission.")
                logging.getLogger("HWR").error(
                    "[COLLECT] Error setting transmission: %s" % ex
                )
                raise Exception("[COLLECT] Error setting transmission: %s" % ex)

        self.triggers_to_collect = self.prepare_triggers_to_collect()
        log.info("Collection: Updating data collection in LIMS")
        self.update_data_collection_in_lims()

        # Generate and set a unique id, used in the data catalog and the detector must know it
        self.collection_uuid = str(uuid.uuid4())
        logging.getLogger("HWR").info(
            "[COLLECT] Generating UUID: %s" % self.collection_uuid
        )

        # try:
        #    self.detector_hwobj.set_collection_uuid(self.collection_uuid)
        # except Exception as ex:
        #    logging.getLogger("HWR").warning("[COLLECT] Error setting UUID in the detector: %s" % ex)
        if self.datacatalog_enabled:
            try:
                self.store_datacollection_uuid_datacatalog()
            except Exception as ex:
                logging.getLogger("HWR").warning(
                    "[COLLECT] Error sending uuid to data catalog: %s" % ex
                )

        try:
            self.prepare_detector()
        except Exception as ex:
            log.error("Collection: cannot set prepare detector.")
            logging.getLogger("HWR").error(
                "[COLLECT] Error preparing detector: %s" % ex
            )
            raise Exception("[COLLECT] Error preparing detector: %s" % ex)

        # important this step is after detector configuration, which otherwise would give the wrong count_rate_cutoff
        if self.current_dc_parameters["experiment_type"] == "Mesh" or self.hve:
            self.start_spot_finder_dozor()

        # move MD3 to DataCollection phase if it"s not
        if self.diffractometer_hwobj.get_current_phase() != "DataCollection":
            log.info("Moving Diffractometer to Data Collection")
            self.diffractometer_hwobj.set_phase(
                "DataCollection", wait=True, timeout=200
            )

        self.flux_before_collect = self.get_instant_flux()
        self.flux_after_collect = None
        # flux value is a string
        if float(self.flux_before_collect) < 1:
            log.error("Collection: Flux is 0, please check the beam!!")

        self.diffractometer_hwobj.wait_device_ready(5)
        self.move_to_centered_position()
        self.diffractometer_hwobj.wait_device_ready(5)

        logging.getLogger("HWR").info(
            "Collection: Updating data collection in LIMS with data: %s"
            % self.current_dc_parameters
        )
        self.update_data_collection_in_lims()

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
            self.char = True
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
            oscillation_parameters = self.current_dc_parameters["oscillation_sequence"][
                0
            ]
            self.open_detector_cover()
            # self.open_safety_shutter()

            # TODO: investigate gevent.timeout exception handing, this wait is to ensure
            # that conf is done before arming
            time.sleep(2)
            try:
                self.detector_hwobj.wait_config_done()
                self.detector_hwobj.start_acquisition()
                self.detector_hwobj.wait_ready()
            except Exception as ex:
                logging.getLogger("HWR").error("[COLLECT] Detector Error: %s" % ex)
                raise RuntimeError("[COLLECT] Detector error while arming.")

            # call after start_acquisition (detector is armed), when all the config parameters are definitely
            # implemented
            try:
                """
                add 3ms into the total acquisition time, to compensate the unsynchronization between
                fastshutter and detector, otherwise the last image sample is less radiated.
                """
                shutterless_exptime = self.detector_hwobj.get_acquisition_time() + 0.003
            except Exception as ex:
                logging.getLogger("HWR").error(
                    "[COLLECT] Detector error getting acquisition time: %s" % ex
                )
                shutterless_exptime = 0.01

            # wait until detector is ready (will raise timeout RuntimeError), sometimes arm command
            # is accepted by the detector but without any effect at all... sad...
            # self.detector_hwobj.wait_ready()
            for (
                osc_start,
                trigger_num,
                nframes_per_trigger,
                osc_range,
            ) in self.triggers_to_collect:
                osc_end = osc_start + osc_range * nframes_per_trigger
            self.display_task = gevent.spawn(self._update_image_to_display)
            self.progress_task = gevent.spawn(self._update_task_progress)
            self.oscillation_task = self.oscil(
                osc_start, osc_end, shutterless_exptime, 1, wait=True
            )
            try:
                self.detector_hwobj.stop_acquisition()
            except Exception as ex:
                logging.getLogger("HWR").error(
                    "[COLLECT] Detector error stopping acquisition: %s" % ex
                )

                # not closing the safety shutter here, but in prepare_beamline
                # to avoid extra open/closes
                # self.close_safety_shutter()
            self.close_detector_cover()
            self.emit("collectImageTaken", oscillation_parameters["number_of_images"])
        except RuntimeError as ex:
            self.data_collection_cleanup()
            logging.getLogger("HWR").error("[COLLECT] Runtime Error: %s" % ex)
            self.close_detector_cover()
            raise Exception("data collection hook failed... ", str(ex))
        except:
            self.data_collection_cleanup()
            logging.getLogger("HWR").error("Unexpected error:", sys.exc_info()[0])
            self.close_detector_cover()
            raise Exception("data collection hook failed... ", sys.exc_info()[0])

    def get_mesh_num_lines(self):
        return self.mesh_num_lines

    def get_mesh_total_nb_frames(self):
        return self.mesh_total_nb_frames

    def get_current_shape_id(self):
        return self.current_dc_parameters["shape"]

    def oscil(self, start, end, exptime, npass, wait=True):
        time.sleep(1)
        oscillation_parameters = self.current_dc_parameters["oscillation_sequence"][0]
        msg = (
            "[BIOMAXCOLLECT] Oscillation requested oscillation_parameters: %s"
            % oscillation_parameters
        )
        # msg += " || dc parameters: %s" % self.current_dc_parameters
        logging.getLogger("HWR").info(msg)

        if self.helical:
            self.diffractometer_hwobj.osc_scan_4d(
                start, end, exptime, self.helical_pos, wait=wait
            )
        elif self.current_dc_parameters["experiment_type"] == "Mesh":
            logging.getLogger("HWR").info(
                "Mesh oscillation requested: number of lines %s"
                % self.get_mesh_num_lines()
            )
            logging.getLogger("HWR").info(
                "Mesh oscillation requested: total number of frames %s"
                % self.get_mesh_total_nb_frames()
            )
            shape_id = self.get_current_shape_id()
            shape = self.shape_history_hwobj.get_shape(shape_id).as_dict()
            range_x = shape.get("num_cols") * shape.get("cell_width") / 1000.0
            range_y = shape.get("num_rows") * shape.get("cell_height") / 1000.0
            self.diffractometer_hwobj.raster_scan(
                start,
                end,
                exptime,
                range_y,  # vertical_range in mm,
                range_x,  # horizontal_range in mm,
                self.get_mesh_num_lines(),
                self.get_mesh_total_nb_frames(),  # is in fact nframes per line
                invert_direction=1,
                wait=wait,
            )
        else:
            self.diffractometer_hwobj.osc_scan(start, end, exptime, wait=wait)

    def _update_task_progress(self):
        logging.getLogger("HWR").info("[BIOMAXCOLLECT] update task progress launched")
        num_images = self.current_dc_parameters["oscillation_sequence"][0][
            "number_of_images"
        ]
        if self.current_dc_parameters.get("experiment_type") == "Mesh":
            shape_id = self.get_current_shape_id()
            shape = self.shape_history_hwobj.get_shape(shape_id).as_dict()
            num_cols = shape.get("num_cols")
            num_rows = shape.get("num_rows")
            num_images = num_cols * num_rows
        num_steps = 10.0
        if num_images < num_steps:
            step_size = 1
            num_steps = num_images
        else:
            step_size = float(
                num_images / num_steps
            )  # arbitrary, 10 progress steps or messages
        exp_time = self.current_dc_parameters["oscillation_sequence"][0][
            "exposure_time"
        ]
        step_count = 0
        current_frame = 0
        time.sleep(exp_time * step_size)
        while step_count < num_steps:
            time.sleep(exp_time * step_size)
            current_frame += step_size
            logging.getLogger("HWR").info(
                "[BIOMAXCOLLECT] collectImageTaken %s (%s, %s, %s)"
                % (current_frame, num_images, step_size, step_count)
            )
            self.emit("collectImageTaken", current_frame)
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
        if self.char:
            # stop char converter
            self.char = False
        if self.current_dc_parameters["experiment_type"] == "Mesh" or self.hve:
            # disable stream interface
            # stop spot finding
            self.detector_hwobj.disable_stream()
            self.stop_spot_finder_dozor()

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
        if (
            self.current_dc_parameters["experiment_type"] in ("OSC", "Helical")
            and self.current_dc_parameters["oscillation_sequence"][0]["overlap"] == 0
            and self.current_dc_parameters["oscillation_sequence"][0][
                "number_of_images"
            ]
            >= self.NIMAGES_TRIGGER_AUTO_PROC
        ):
            gevent.spawn(self.trigger_auto_processing, "after", 0)

        # we store the first and the last images, TODO: every 45 degree
        gevent.spawn(self.post_collection_store_image)

        if self.current_dc_parameters["experiment_type"] == "Mesh" or self.hve:
            # disable stream interface
            # stop spot finding
            self.detector_hwobj.disable_stream()
            self.stop_spot_finder_dozor()
        if self.char:
            # stop char converter
            self.char = False
        self.diffractometer_hwobj.wait_device_ready(5)

        success_msg = "Data collection successful"
        self.current_dc_parameters["status"] = success_msg
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

        if self.current_dc_parameters.get("experiment_type") != "Mesh":
            try:
                logging.getLogger("HWR").info(
                    "[BIOMAXCOLLECT] Going to generate XDS input files"
                )
                # generate XDS.INP only in raw/process
                data_path = self.current_dc_parameters["fileinfo"]["filename"]
                logging.getLogger("HWR").info(
                    "[BIOMAXCOLLECT] DATA file: %s" % data_path
                )
                logging.getLogger("HWR").info(
                    "[BIOMAXCOLLECT] XDS file: %s"
                    % self.current_dc_parameters["xds_dir"]
                )
                if (
                    self.current_dc_parameters["experiment_type"] in ("OSC", "Helical")
                    and self.current_dc_parameters["oscillation_sequence"][0]["overlap"]
                    == 0
                    and self.current_dc_parameters["oscillation_sequence"][0][
                        "number_of_images"
                    ]
                    >= self.NIMAGES_TRIGGER_AUTO_PROC
                ):
                    self.trigger_auto_processing("after", 0)
            except Exception as ex:
                logging.getLogger("HWR").error(
                    "[COLLECT] Error creating XDS files, %s" % ex
                )

            # we store the first and the last images, TODO: every 45 degree
            logging.getLogger("HWR").info("Storing images in lims, frame number: 1")
            try:
                self._store_image_in_lims(1)
                self.generate_and_copy_thumbnails(
                    self.current_dc_parameters["fileinfo"]["filename"], 1
                )
            except Exception as ex:
                print(ex)

            last_frame = self.current_dc_parameters["oscillation_sequence"][0][
                "number_of_images"
            ]
            if last_frame > 1:
                logging.getLogger("HWR").info(
                    "Storing images in lims, frame number: %d" % last_frame
                )
                try:
                    self._store_image_in_lims(last_frame)
                    self.generate_and_copy_thumbnails(
                        self.current_dc_parameters["fileinfo"]["filename"], last_frame
                    )
                except Exception as ex:
                    print(ex)

        if self.datacatalog_enabled:
            self.store_datacollection_datacatalog()

    def post_collection_store_image(self):
        # we store the first and the last images, TODO: every 45 degree
        logging.getLogger("HWR").info("Storing images in lims, frame number: 1")
        try:
            self.store_image_in_lims(1)
            self.generate_and_copy_thumbnails(
                self.current_dc_parameters["fileinfo"]["filename"], 1
            )
        except Exception as ex:
            print(ex)

    def _store_image_in_lims_by_frame_num(self, frame, motor_position_id=None):
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
        first_image = frame_number - 1
        rootname, ext = os.path.splitext(input_file)
        rings = [0.25, 0.50, 0.75, 1.00, 1.25]
        script = "/mxn/groups/biomax/wmxsoft/scripts_mxcube/EigerDataSet.py"
        cmd = (
            "ssh b-biomax-eiger-dc-1 python %s -input %s -binfactor %d -output %s -start %d -nimages %d &"
            % (
                script,
                input_file,
                binfactor,
                jpeg_thumbnail_full_path,
                first_image,
                nimages,
            )
        )
        logging.getLogger("HWR").info(cmd)
        os.system(cmd)

    def _store_image_in_lims(self, frame_number, motor_position_id=None):
        """
        Descript. :
        """
        if self.lims_client_hwobj:
            file_location = self.current_dc_parameters["fileinfo"]["directory"]
            image_file_template = self.current_dc_parameters["fileinfo"]["template"]
            filename = image_file_template % frame_number
            lims_image = {
                "dataCollectionId": self.current_dc_parameters["collection_id"],
                "fileName": filename,
                "fileLocation": file_location,
                "imageNumber": frame_number,
                "measuredIntensity": self.get_measured_intensity(),
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
                lims_image["fileLocation"] = self.current_dc_parameters["fileinfo"][
                    "directory"
                ]
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
                image_id = self.lims_client_hwobj.store_image(lims_image)
            except Exception as ex:
                print(ex)
            # temp fix for ispyb permission issues
            try:
                session_dir = os.path.join(archive_directory, "../../../")
                os.system("chmod -R 777 %s" % (session_dir))
            except Exception as ex:
                print(ex)

            return image_id

    def take_crystal_snapshots(self):
        """
        Descript. :
        """
        if self.current_dc_parameters["take_snapshots"]:
            # snapshot_directory = self.current_dc_parameters["fileinfo"]["archive_directory"]
            # save the image to the data collection directory for the moment
            snapshot_directory = os.path.join(
                self.current_dc_parameters["fileinfo"]["directory"], "snapshot"
            )
            if not os.path.exists(snapshot_directory):
                try:
                    self.create_directories(snapshot_directory)
                except:
                    logging.getLogger("HWR").exception(
                        "Collection: Error creating snapshot directory"
                    )

            # for plate head, takes only one image
            if (
                self.diffractometer_hwobj.head_type
                == self.diffractometer_hwobj.HEAD_TYPE_PLATE
            ):
                number_of_snapshots = 1
            else:
                number_of_snapshots = 4  # 4 take only one image for the moment
            logging.getLogger("user_level_log").info(
                "Collection: Taking %d sample snapshot(s)" % number_of_snapshots
            )
            if self.diffractometer_hwobj.get_current_phase() != "Centring":
                logging.getLogger("user_level_log").info(
                    "Moving Diffractometer to CentringPhase"
                )
                self.diffractometer_hwobj.set_phase("Centring", wait=True, timeout=200)
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
                # self._do_take_snapshot(snapshot_filename)
                self._take_crystal_snapshot(snapshot_filename)
                time.sleep(1)  # needed, otherwise will get the same images
                if number_of_snapshots > 1:
                    self.diffractometer_hwobj.move_omega_relative(90)
                    time.sleep(1)  # needed, otherwise will get the same images

    def trigger_auto_processing(self, process_event, frame_number):
        """
        Descript. :
        """
        logging.getLogger("HWR").info(
            "[COLLECT] triggering auto processing, self.current_dc_parameters: %s"
            % self.current_dc_parameters
        )
        logging.getLogger("HWR").info("[COLLECT] Launching MAXIV Autoprocessing")
        if self.autoprocessing_hwobj is not None:
            self.autoprocessing_hwobj.execute_autoprocessing(
                process_event, self.current_dc_parameters, frame_number
            )

    def get_beam_centre(self):
        """
        Descript. :
        """
        if self.resolution_hwobj is not None:
            return self.resolution_hwobj.get_beam_centre()
        else:
            return None, None

    def get_beam_shape(self):
        """
        Descript. :
        """
        if self.beam_info_hwobj is not None:
            return self.beam_info_hwobj.get_beam_shape()

    def open_detector_cover(self):
        """
        Descript. :
        """
        try:
            logging.getLogger("HWR").info("Openning the detector cover.")
            self.detector_cover_hwobj.openShutter()
            time.sleep(1)  # make sure the cover is up before the data collection stars
        except:
            logging.getLogger("HWR").exception("Could not open the detector cover")
            raise RuntimeError("[COLLECT] Could not open the detector cover.")

    def close_detector_cover(self):
        """
        Descript. :
        """
        try:
            logging.getLogger("HWR").info("Closing the detector cover")
            self.detector_cover_hwobj.close()
        except:
            logging.getLogger("HWR").exception("Could not close the detector cover")

    def open_fast_shutter(self):
        """
        Descript. : important to make sure it"s passed, as we
                    don't open the fast shutter in MXCuBE
        """
        pass

    def close_fast_shutter(self):
        """
        Descript. :
        """
        # to do, close the fast shutter as early as possible in case
        # MD3 fails to do so

    @task
    def _take_crystal_snapshot(self, filename):
        """
        Descript. :
        """
        # take image from server
        self.diffractometer_hwobj.camera_hwobj.takeSnapshot(filename)

    def set_detector_roi(self, value):
        """
        Descript. : set the detector roi mode
        """
        self.detector_hwobj.set_roi_mode(value)

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

    def set_resolution(self, value):
        """
        Descript. :
        """
        new_distance = self.resolution_hwobj.res2dist(value)
        self.move_detector(new_distance)

    def set_energy(self, value, checkbeam):
        logging.getLogger("HWR").info("[COLLECT] Setting beamline energy to %s" % value)
        self.energy_hwobj.start_move_energy(value, checkbeam)  # keV
        logging.getLogger("HWR").info(
            "[COLLECT] Updating wavelength parameter to %s" % (12.3984 / value)
        )
        self.current_dc_parameters["wavelength"] = 12.3984 / value
        logging.getLogger("HWR").info("[COLLECT] Setting detector energy")
        self.detector_hwobj.set_photon_energy(value * 1000)  # ev

    def set_wavelength(self, value):
        logging.getLogger("HWR").info(
            "[COLLECT] Setting beamline wavelength to %s" % value
        )
        self.energy_hwobj.startMoveWavelength(value)
        current_energy = self.energy_hwobj.getCurrentEnergy()
        self.detector_hwobj.set_photon_energy(current_energy * 1000)

    @task
    def move_motors(self, motor_position_dict):
        """
        Descript. :
        """
        self.diffractometer_hwobj.move_sync_motors(motor_position_dict)

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
            os.system(
                "chmod -R 770 %s %s" % (os.path.dirname(xds_directory), auto_directory)
            )
            """todo, create link of imgs for auto_processing
            try:
                os.symlink(files_directory, os.path.join(process_directory, "img"))
            except os.error, e:
                if e.errno != errno.EEXIST:
                    raise
            """
            # os.symlink(files_directory, os.path.join(process_directory, "img"))
        except:
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
            "Creating XDS (MAXIV-BioMAX) processing input file directories"
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

    def move_detector(self, value):
        """
        Descript. : move detector to the set distance
        """
        lower_limit, upper_limit = self.get_detector_distance_limits()
        logging.getLogger("HWR").info(
            "...................value %s, detector movement start..... %s"
            % (value, self.dtox_hwobj.get_value())
        )
        if upper_limit is not None and lower_limit is not None:
            if value >= upper_limit or value <= lower_limit:
                logging.getLogger("HWR").exception(
                    "Can't move detector, the value is out of limits"
                )
                self.stop_collect()
            else:
                try:
                    if self.dtox_hwobj is not None:
                        self.dtox_hwobj.set_value(value)
                        self.dtox_hwobj.wait_end_of_move(
                            50
                        )  # 30s is not enough for the whole range
                except:
                    logging.getLogger("user_level_log").error(
                        "Cannot move detector, please check the key!!"
                    )
                    logging.getLogger("HWR").exception(
                        "Problems when moving detector!!"
                    )
                    self.stop_collect()
        else:
            logging.getLogger("HWR").exception(
                "Can't get distance limits, not moving detector!!"
            )
        logging.getLogger("HWR").info(
            "....................value %s detector movement finished.....%s"
            % (value, self.dtox_hwobj.get_value())
        )

        current_pos = self.dtox_hwobj.get_value()
        if abs(current_pos - value) > 0.05:
            logging.getLogger("user_level_log").exception(
                "Detector didn't go to the set position"
            )
            self.stop_collect()

    def get_detector_distance(self):
        """
        Descript. :
        """
        if self.dtox_hwobj is not None:
            return self.dtox_hwobj.get_value()

    def get_detector_distance_limits(self):
        """
        Descript. :
        """
        if self.dtox_hwobj is not None:
            return self.dtox_hwobj.get_limits()

    def prepare_detector(self):

        oscillation_parameters = self.current_dc_parameters["oscillation_sequence"][0]
        (
            osc_start,
            trigger_num,
            nframes_per_trigger,
            osc_range,
        ) = self.triggers_to_collect[0]

        if self.current_dc_parameters["experiment_type"] == "Mesh":
            ntrigger = self.get_mesh_num_lines()
        else:
            ntrigger = len(self.triggers_to_collect)
        config = self.detector_hwobj.col_config
        """ move after setting energy
        if roi == "4M":
            config["RoiMode"] = "4M"
        else:
            config["RoiMode"] = "disabled" #disabled means 16M

        config["PhotonEnergy"] = self._tunable_bl.getCurrentEnergy()
        """
        config["OmegaStart"] = osc_start  # oscillation_parameters["start"]
        config["OmegaIncrement"] = osc_range  # oscillation_parameters["range"]
        (
            beam_centre_x,
            beam_centre_y,
        ) = self.get_beam_centre()  # self.get_beam_centre_pixel() # returns pixel
        config["BeamCenterX"] = beam_centre_x  # unit, should be pixel for master file
        config["BeamCenterY"] = beam_centre_y
        config["DetectorDistance"] = self.get_detector_distance() / 1000.0

        config["CountTime"] = oscillation_parameters["exposure_time"]

        config["NbImages"] = nframes_per_trigger
        config["NbTriggers"] = ntrigger

        try:
            config["ImagesPerFile"] = oscillation_parameters["images_per_file"]
        except:
            config["ImagesPerFile"] = 100

        if nframes_per_trigger * ntrigger < config["ImagesPerFile"]:
            self.display["delay"] = (
                nframes_per_trigger * ntrigger * oscillation_parameters["exposure_time"]
            )
        else:
            self.display["delay"] = (
                config["ImagesPerFile"] * oscillation_parameters["exposure_time"]
            )
        self.display["exp"] = oscillation_parameters["exposure_time"]
        self.display["nimages"] = nframes_per_trigger * ntrigger

        file_parameters = self.current_dc_parameters["fileinfo"]
        file_parameters["suffix"] = self.bl_config.detector_fileext
        image_file_template = "%(prefix)s_%(run_number)s" % file_parameters
        name_pattern = os.path.join(file_parameters["directory"], image_file_template)
        #    file_parameters["template"] = image_file_template
        file_parameters["filename"] = "%s_master.h5" % name_pattern
        self.display["file_name1"] = file_parameters["filename"]
        self.display["file_name2"] = re.sub(
            "^/mxn/biomax-eiger-dc-1", "/localdata", file_parameters["filename"]
        )

        # os.path.join(file_parameters["directory"], image_file_template)
        config["FilenamePattern"] = name_pattern

        if self.current_dc_parameters["experiment_type"] == "Mesh":
            # enable stream interface
            # appendix with grid name, collection id
            self.detector_hwobj.enable_stream()
            img_appendix = {
                "exp_type": "mesh",
                "col_id": self.current_dc_parameters["collection_id"],
                "shape_id": self.get_current_shape_id(),
            }
            self.detector_hwobj.set_image_appendix(json.dumps(img_appendix))
        self.detector_hwobj.prepare_acquisition(config)

    def prepare_dozor_input(self, oscillation_parameters, path):
        config = self.dozor_hwobj.config
        try:
            config["fraction_polarization"] = self.polarisation
            config["detector_distance"] = self.get_detector_distance()
            config["X-ray_wavelength"] = self.get_wavelength()
            config["orgx"], config["orgy"] = self.get_beam_centre()
            config["exposure"] = oscillation_parameters["exposure_time"]
            config["oscillation_range"] = oscillation_parameters["range"]
            config["ix_min"] = 2073
            config["ix_max"] = 2165
            config["iy_min"] = 2135
            config["iy_max"] = 4371
            config["pixel_min"] = 1
            """
            todo, we should use countrate_correction_count_cutoff from detector
            but this attribute is missing in the eiger tango device.
            """
            config["pixel_max"] = 65534
            config["spot_size"] = 3
        except Exception as ex:
            logging.getLogger("HWR").error(
                "[COLLECT] Configuing Dozor input Error: %s" % ex
            )
            raise RuntimeError(
                "[COLLECT] Error while trying to get parameters for Dozor."
            )
        self.dozor_hwobj.config = config
        return self.dozor_hwobj.write_dozor_dat(path)

    def start_spot_finder_dozor(self):
        oscillation_parameters = self.current_dc_parameters["oscillation_sequence"][0]
        dozor_path = os.path.join(self.current_dc_parameters["auto_dir"], "dozor")
        self.create_directories(dozor_path)
        dozor_dat_path = (
            self.prepare_dozor_input(oscillation_parameters, dozor_path) or None
        )
        dozor_res_path = os.path.join(dozor_path, "dozor_res.txt")
        if dozor_dat_path:
            self.dozor_hwobj.execute_dozor(dozor_dat_path)
        else:
            raise RuntimeError("[COLLECT] Failed because dozor.dat is missing")
        self.dozor_hwobj.execute_dozor_collector(dozor_res_path)
        # launch stream reciever with dozor
        # if needed, the colID and shapeID are self.current_dc_parameters["collection_id"] and self.get_current_shape_id()

    def stop_spot_finder_dozor(self):
        """
        Stop dozor and collector
        """
        logging.getLogger("HWR").info("Will stop dozor on the HPC.")
        self.dozor_hwobj.stop_dozor()
        return

    def stop_collect(self, owner):
        """
        Stops data collection
        """
        logging.getLogger("HWR").error("Stopping collection ....")
        self.close_detector_cover()
        self.diffractometer_hwobj.abort()
        self.detector_hwobj.abort()
        self.detector_hwobj.disarm()
        if self.data_collect_task is not None:
            self.data_collect_task.kill(block=False)
        logging.getLogger("HWR").error("Collection stopped")
        self.stop_display = True

    def get_transmission(self):
        """
        Descript. :
        """
        return self.transmission_hwobj.get_value()

    def set_transmission(self, value):
        """
        Descript. :
        """
        try:
            self.transmission_hwobj.set_value(float(value), True)
        except Exception as ex:
            raise Exception("cannot set transmission", ex)

    def get_undulators_gaps(self):
        """
        Descript. :
        """
        try:
            chan = self.get_channel_object("undulator_gap")
            gap = "{:.2f}".format(chan.getValue())
            return gap
        except:
            return None

    def get_slit_gaps(self):
        """
        Descript. :
        """
        try:
            return self.beam_info_hwobj.get_beam_size()
        except:
            return None

    def get_machine_current(self):
        """
        Descript. :
        """
        try:
            return self.machine_info_hwobj.get_current()
        except:
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
            return self.machine_info_hwobj.getFillingMode()
        except:
            return ""

    def get_flux(self):
        """
        Descript. :
        """
        try:
            flux = self.flux_hwobj.get_flux()
        except Exception as ex:
            logging.getLogger("HWR").error("[HWR] Cannot retrieve flux value")
            flux = -1
        return flux

    def get_instant_flux(self, keep_position=False):
        """
        Descript. : get the instant flux value, w/o checking beamstability
        this method assuming that the MD3 is already in datacollection phase
        """
        # disable it temporarily until the EM works properly

        try:
            ori_motors, ori_phase = self.diffractometer_hwobj.set_calculate_flux_phase()
            flux = self.flux_hwobj.get_instant_flux()
        except Exception as ex:
            logging.getLogger("HWR").error(
                "[COLLECT] Cannot get the current flux value"
            )
            flux = -1
            raise Exception("[COLLECT] Cannot get the current flux value")
        finally:
            # close fast shutter
            self.close_fast_shutter()
            if keep_position:
                self.diffractometer_hwobj.finish_calculate_flux(ori_motors, ori_phase)
            else:
                self.diffractometer_hwobj.finish_calculate_flux(None, ori_phase)

        return flux

    def get_measured_intensity(self):
        return float(self.get_flux())

    def prepare_for_new_sample(self, manual_mode=True):
        """
        Descript.: prepare beamline for a new sample,
        """
        logging.getLogger("HWR").info("[HWR] Preparing beamline for a new sample.")
        if manual_mode:
            if self.detector_cover_hwobj is not None:
                self.close_detector_cover()
            self.diffractometer_hwobj.set_phase("Transfer", wait=False)
            self.close_safety_shutter()

        self.move_detector(800)

    def prepare_set_energy(self):
        """
        Descript.: figure out if we should check the beam after the energy changes
        """
        checkbeam = True
        try:
            if float(self.get_machine_current()) < 10.0:
                checkbeam = False
                logging.getLogger("HWR").warning("[COLLECT] Very low ring current")
                logging.getLogger("user_level_log").warning(
                    "[COLLECT] Very low ring current"
                )

            self.ha = PyTango.DeviceProxy("b311a-fe/vac/ha-01")
            if self.ha.StatusClosed:
                checkbeam = False
                logging.getLogger("HWR").warning("[COLLECT] Heat Absorber Closed")
                logging.getLogger("user_level_log").warning(
                    "[COLLECT] Heat Absorber Closed"
                )

            self.aem = PyTango.DeviceProxy("b311a/xbpm/02")
            if self.aem.S < 1e-7:
                checkbeam = False
                logging.getLogger("HWR").warning("[COLLECT] No beam measured")
                logging.getLogger("user_level_log").warning(
                    "[COLLECT] No beam measured"
                )

        except Exception as ex:
            logging.getLogger("HWR").error(
                "[COLLECT] Cannot prepare_set_energy,checkbeam: %s, error was: %s"
                % (checkbeam, ex)
            )

        return checkbeam

    def _update_image_to_display(self):
        fname1 = "/mxn/groups/biomax/wmxsoft/auto_load_img_cc/to_display"
        fname2 = "/mxn/groups/biomax/ctrl_soft/auto_load_img_cc/to_display"
        time.sleep(self.display["delay"] + 3)
        frequency = 5
        step = int(math.ceil(frequency / self.display["exp"]))
        if step == 1:
            frequency = self.display["exp"]
        for i in range(1, self.display["nimages"] + 1, step):
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
        files = []

        # Get the data and proposal number
        collection = self.current_dc_parameters
        proposal_number = self.session_hwobj.proposal_number

        # Create the files variable as an array like ["/data/biomax/proposal1/file1.txt","/data/biomax/proposal1/file2.txt"]
        try:
            # Default of 100 images per h5 file.
            num_files = int(
                math.ceil(
                    collection["oscillation_sequence"][0]["number_of_images"] / 100.0
                )
            )
            template = collection.get("fileinfo").get("template")
            directory = collection.get("fileinfo").get("directory")
            filename = template.replace("%06d", "%s") % "master"
            # Master file
            files.append(os.path.join(directory, filename))
            # Data files
            for num in range(1, num_files + 1):
                files.append(os.path.join(directory, template % num))
        except Exception as ex:
            logging.getLogger("HWR").error("[HWR] Error during data catalog: %s" % ex)

        # Create dict of required data for SciCat
        try:
            msg["creationTime"] = time.time()
            msg["proposalId"] = proposal_number
            msg["uuid"] = self.collection_uuid
            msg["event"] = "biomax-experiment-began"
            msg["sourceFolder"] = directory
            msg["scientificMetadata"] = dict()
            msg["dataFormat"] = "HDF5 / NeXus"
            msg["files"] = files
            msg["datasetName"] = filename
            msg["description"] = "%s collection in Biomax for Sample %s" % (
                collection.get("experiment_type"),
                collection.get("blSampleId"),
            )
            msg["sampleId"] = collection.get("blSampleId")
        except Exception as ex:
            logging.getLogger("HWR").error(
                "[HWR] Error during data catalog, cannot create initial message: %s"
                % ex
            )

        logging.getLogger("HWR").info(
            "[HWR] Sending collection started info to the data catalog: %s" % msg
        )

        headers = {
            "content-type": "application/json",
            "api-key": self.datacatalog_token,
        }

        if self.datacatalog_url:
            try:
                requests.post(
                    self.datacatalog_url, data=json.dumps(msg), headers=headers
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
            msg = {
                "uuid": "f5ed1b14-3e70-43ce-b561-8902e5e31422",
                "event": "biomax-experiment-ended",

               # scientific data relevant to the experiment
               "scientificMetadata": {
                   "some_energy": {value: "4.2", unit: "eV"},
                   "some_distance": {value: "42", unit: "um"},
                   "some_time": {value: "300", unit: "ms"},
                },
            }
        """
        msg = {}
        collection = self.current_dc_parameters

        skip_values = ["fileinfo", "auto_dir", "EDNA_files_dir", "xds_dir"]
        scientificMetadata = dict()

        for item in collection:
            if item in skip_values:
                continue

            elif type(collection[item]) is dict or type(collection[item]) is list:
                for subitem in collection[item]:
                    if type(subitem) is dict:
                        for subsubitem in subitem:
                            title = "%s: %s" % (item, subsubitem)
                            smd = self._scientificmetadatawriter(
                                title, subsubitem, subitem[subsubitem]
                            )
                            scientificMetadata.update(smd)
                    else:
                        title = "%s: %s" % (item, subitem)
                        smd = self._scientificmetadatawriter(
                            title, subitem, collection[item][subitem]
                        )
                        scientificMetadata.update(smd)

            else:
                smd = self._scientificmetadatawriter(item, item, collection[item])
                scientificMetadata.update(smd)

        msg["event"] = "biomax-experiment-ended"
        msg["uuid"] = self.collection_uuid
        msg["scientificMetadata"] = scientificMetadata

        logging.getLogger("HWR").info(
            "[HWR] Sending collection info to the data catalog: %s" % msg
        )

        headers = {
            "content-type": "application/json",
            "api-key": self.datacatalog_token,
        }

        if self.datacatalog_url:
            try:
                requests.post(
                    self.datacatalog_url, data=json.dumps(msg), headers=headers
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

    def _scientificmetadatawriter(self, title, label, value):
        units = {
            "energy": "keV",
            "sampx": "mm",
            "sampy": "mm",
            "focus": "mm",
            "phi": "deg",
            "kappa": "deg",
            "kappa_phi": "deg",
            "phiz": "deg",
            "phiy": "deg",
            "wavelength": "angstrom",
            "slitGapHorizontal": "mm",
            "detectorDistance": "mm",
            "undulatorGap1": "mm",
            "beamSizeAtSampleX": "mm",
            "beamSizeAtSampleY": "mm",
            "resolution": "angstrom",
            # "flux": "ph/s"
        }

        unit = ""
        if label in units:
            unit = units[label]

        smd = {title: {"value": value, "unit": unit}}

        return smd

    def get_resolution_at_corner(self):
        return self.resolution_hwobj.get_value_at_corner()

    def update_data_collection_in_lims(self):
        """
        Descript. :
        """
        if self.lims_client_hwobj:
            # flux = self.get_flux()
            self.current_dc_parameters["flux"] = self.flux_before_collect
            if self.flux_after_collect is not None:
                self.current_dc_parameters["flux_end"] = self.flux_after_collect
            self.current_dc_parameters["wavelength"] = self.get_wavelength()
            self.current_dc_parameters[
                "detectorDistance"
            ] = self.get_detector_distance()
            self.current_dc_parameters["resolution"] = self.get_resolution()
            self.current_dc_parameters["transmission"] = self.get_transmission()
            beam_centre_x, beam_centre_y = self.get_beam_centre()
            self.current_dc_parameters["xBeam"] = beam_centre_x
            self.current_dc_parameters["yBeam"] = beam_centre_y
            und = self.get_undulators_gaps()
            self.current_dc_parameters["undulatorGap1"] = und
            self.current_dc_parameters[
                "resolutionAtCorner"
            ] = self.get_resolution_at_corner()
            beam_size_x, beam_size_y = self.get_beam_size()
            self.current_dc_parameters["beamSizeAtSampleX"] = beam_size_x
            self.current_dc_parameters["beamSizeAtSampleY"] = beam_size_y
            self.current_dc_parameters["beamShape"] = self.get_beam_shape()
            hor_gap, vert_gap = self.get_slit_gaps()
            self.current_dc_parameters["slitGapHorizontal"] = hor_gap
            self.current_dc_parameters["slitGapVertical"] = vert_gap
            self.current_dc_parameters["oscillation_sequence"][0][
                "kappaStart"
            ] = self.current_dc_parameters["motors"].get("kappa", 0)
            self.current_dc_parameters["oscillation_sequence"][0][
                "phiStart"
            ] = self.current_dc_parameters["motors"].get("kappa_phi", 0)
            try:
                self.lims_client_hwobj.update_data_collection(
                    self.current_dc_parameters
                )
            except:
                logging.getLogger("HWR").exception(
                    "Could not update data collection in LIMS"
                )

    def correct_omega_in_master_file(self, filename, overlap):
        script = "/mxn/groups/biomax/wmxsoft/scripts_mxcube/omega_correction/correct_omega.py"
        cmd = "ssh b-biomax-eiger-dc-1 python %s -f %s -o %f &" % (
            script,
            filename,
            -overlap,
        )
        logging.getLogger("HWR").info(" the cmd going to run is %s " % cmd)
        os.system(cmd)
