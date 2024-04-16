"""
  File:  MICROMAXCollect.py

  Description:  This module implements the hardware object for the
  Biomax data collection
"""

import os
import logging
import json
import gevent
import time
import math
import PyTango
import sys

from mxcubecore import HardwareRepository as HWR
from mxcubecore.TaskUtils import task
from mxcubecore.HardwareObjects.GenericDiffractometer import GenericDiffractometer
from mxcubecore.HardwareObjects.MAXIV.DataCollect import DataCollect
from mxcubecore.HardwareObjects.MAXIV.SciCatPlugin import SciCatPlugin
from abstract.AbstractCollect import AbstractCollect
from mxcubecore.BaseHardwareObjects import HardwareObject


DET_SAFE_POSITION = 500


class MICROMAXCollect(DataCollect):
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
        self.in_interleave = False
        self.exp_type_dict = None
        self.display = {}
        self.stop_display = False
        self.interleaved_energies = []
        self.collection_dictionaries = []
        self.scicat_enabled = False
        self.collection_uuid = ""

        self.flux_before_collect = None
        self.estimated_flux_before_collect = None
        self.flux_after_collect = None
        self.estimated_flux_after_collect = None
        self.ssx_mode = False

    def init(self):
        """
        Descript. :
        """
        self.ready_event = gevent.event.Event()
        self.diffractometer_hwobj = self.get_object_by_role("diffractometer")
        self.lims_client_hwobj = self.get_object_by_role("dbserver")
        self.machine_info_hwobj = self.get_object_by_role("mach_info")
        self.energy_hwobj = self.get_object_by_role("energy")
        self.resolution_hwobj = self.get_object_by_role("resolution")
        self.detector_hwobj = HWR.beamline.detector
        self.flux_hwobj = self.get_object_by_role("flux")
        self.autoprocessing_hwobj = self.get_object_by_role("auto_processing")
        # self.autoprocessing_hwobj.lims_client_hwobj = self.lims_client_hwobj
        self.autoprocessing_hwobj.NIMAGES_TRIGGER_AUTO_PROC = (
            self.NIMAGES_TRIGGER_AUTO_PROC
        )
        self.beam_info_hwobj = self.get_object_by_role("beam_info")
        self.transmission_hwobj = self.get_object_by_role("transmission")
        # self.sample_changer_hwobj = self.getObjectByRole("sample_changer")
        # self.sample_changer_maint_hwobj = self.getObjectByRole("sample_changer_maintenance")
        self.dtox_hwobj = self.detector_hwobj.get_object_by_role("detector_distance")
        # self.detector_cover_hwobj = self.getObjectByRole("detector_cover")
        self.session_hwobj = self.get_object_by_role("session")
        self.shape_history_hwobj = HWR.beamline.sample_view
        self.dozor_hwobj = self.get_object_by_role("dozor")
        self.scicat_enabled = self.get_property("scicat_enabled", False)
        if self.scicat_enabled:
            self.scicat_hwobj = SciCatPlugin()
            self.log.info("[COLLECT] SciCat Datacatalog enabled")
        else:
            self.scicat_hwobj = None
            self.log.warning("[COLLECT] SciCat Datacatalog not enabled")
        self.polarisation = float(self.get_property("polarisation", 0.99))
        self.gen_thumbnail_script = self.get_property(
            "gen_thumbnail_script",
            "/mxn/groups/sw/mxsw/mxcube_scripts/generate_thumbnail",
        )

        self.log = logging.getLogger("HWR")
        self.user_log = logging.getLogger("user_level_log")

        self.safety_shutter_hwobj = self.get_object_by_role("safety_shutter")
        # todo
        # self.fast_shutter_hwobj = self.getObjectByRole("fast_shutter")
        # self.cryo_stream_hwobj = self.getObjectByRole("cryo_stream")

        self.exp_type_dict = {"Mesh": "Mesh", "Helical": "Helical"}
        try:
            min_exp = self.detector_hwobj.get_minimum_exposure_time()
        except Exception:
            self.log.exception("Detector min exposure not available, set to 0.1")
            min_exp = 0.1

        try:
            pix_x = self.detector_hwobj.get_pixel_size_x()
        except Exception:
            self.log.exception("Detector X pixel size not available, set to 7-5e5")
            pix_x = 7.5e-5

        try:
            pix_y = self.detector_hwobj.get_pixel_size_y()
        except Exception:
            self.log.exception("Detector Y pixel size not available, set to 7-5e5")
            pix_y = 7.5e-5

        if self.beam_info_hwobj is None:
            self.log.error("Beam Info hwobj not defined, this will cause troubles")

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
            detector_binning_mode="",
            undulators=self.get_property("undulator"),
            focusing_optic=self.get_property("focusing_optic"),
            monochromator_type=self.get_property("monochromator"),
            beam_divergence_vertical=None,  # self.beam_info_hwobj.get_beam_divergence_hor(),
            beam_divergence_horizontal=None,  # self.beam_info_hwobj.get_beam_divergence_ver(),
            polarisation=self.polarisation,
            input_files_server=self.get_property("input_files_server"),
        )

        # self.add_channel({"type": "tango",
        #                  "name": 'undulator_gap',
        #                  "tangoname": self.get_property('undulator_gap'),
        #                  "timeout": 10000,
        #                  },
        #                 'Position'
        #                 )

        self.emit("collectReady", (True,))

    def do_collect(self, owner):
        """
        Actual collect sequence
        """
        self.user_log.info("Collection: Preparing to collect")
        # todo, add more exceptions and abort
        try:
            self.emit("collectReady", (False,))
            self.emit("collectStarted", (owner, 1))

            self.current_dc_parameters["status"] = "Running"
            self.current_dc_parameters["collection_start_time"] = time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            self.current_dc_parameters["synchrotronMode"] = self.get_machine_fill_mode()

            self.user_log.info("Collection: Storing data collection in LIMS")
            self.store_data_collection_in_lims()

            self.user_log.info(
                "Collection: Creating directories for raw images and processing files"
            )
            self.create_file_directories()

            self.user_log.info("Collection: Getting sample info from parameters")
            self.get_sample_info()

            # log.info("Collect: Storing sample info in LIMS")
            # self.store_sample_info_in_lims()

            if all(
                item is None for item in self.current_dc_parameters["motors"].values()
            ):
                # No centring point defined
                # create point based on the current position
                current_diffractometer_position = (
                    self.diffractometer_hwobj.get_positions()
                )
                for motor in self.current_dc_parameters["motors"].keys():
                    self.current_dc_parameters["motors"][
                        motor
                    ] = current_diffractometer_position[motor]

            # todo, self.move_to_centered_position() should go inside take_crystal_snapshots,
            # which makes sure it move motors to the correct positions and move back
            # if there is a phase change
            self.user_log.debug("Collection: going to take snapshots...")
            self.take_crystal_snapshots()
            self.user_log.debug("Collection: snapshots taken")

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
                    except Exception:
                        self.log.exception(
                            "Collection: Error creating archive directory"
                        )

                os.chmod(archive_directory, 0o777)
                for file in snapshots_files:
                    os.chmod(file, 0o777)
            except Exception as ex:
                msg = (
                    "[COLLECT] Archive directory preparation failed. Data collection continues. Error was: %s"
                    % str(ex)
                )
                self.user_log.error(msg)

            self.close_fast_shutter()
            self.close_detector_cover()
            self.open_safety_shutter()

            # prepare beamline for data acquisiion
            self.prepare_acquisition()
            self.emit(
                "collectOscillationStarted",
                (owner, None, None, None, self.current_dc_parameters, None),
            )
            # Main data collection method
            self.data_collection_hook()

            # correct the omega values in the master file for characterization
            if self.char:
                self.autoprocessing_hwobj.correct_omega_in_master_file(
                    self.current_dc_parameters
                )

            self.emit_collection_finished()

        except Exception as ex:
            self.log.exception("[COLLECT] Data collection failed: %s" % ex)
            self.user_log.error("[COLLECT] Data collection failed: %s" % ex)
            self.emit_collection_failed()
            self.close_fast_shutter()

    def prepare_acquisition(self):
        """
        Prepare the beamline for the data collection
        """
        self.log.info(
            "[COLLECT] Preparing data collection with parameters: %s"
            % self.current_dc_parameters
        )

        self.stop_display = False

        if "wavelength" in self.current_dc_parameters:
            wavelength = self.current_dc_parameters["wavelength"]
            self.user_log.info("Collection: Setting wavelength to %.3f", wavelength)
            try:
                self.set_wavelength(wavelength)
            except Exception as ex:
                self.user_log.error("Collection: cannot set beamline wavelength")
                msg = "[COLLECT] Error setting wavelength: %s" % ex
                self.log.error(msg)
                raise Exception(msg)

        elif "energy" in self.current_dc_parameters:
            energy = self.current_dc_parameters["energy"]
            self.user_log.info("Collection: Setting energy to %.3f", energy)

            try:
                self.set_energy(energy)
            except Exception as ex:
                self.user_log.exception("Collection: cannot set beamline energy.")
                msg = "[COLLECT] Error setting energy: %s" % ex
                self.log.error(msg)
                raise Exception(msg)

        if "detroi" in self.current_dc_parameters:
            try:
                detroi = self.current_dc_parameters["detroi"]
                self.user_log.info("Collection: Setting detector ROI to %s", detroi)
                self.set_detector_roi(detroi)
            except Exception as ex:
                self.user_log.error("Collection: cannot set detector roi.")
                msg = "[COLLECT] Error setting detector roi: %s" % ex
                self.log.error(msg)
                raise Exception(msg)

        if "resolution" in self.current_dc_parameters:
            try:
                resolution = self.current_dc_parameters["resolution"]["upper"]
                self.user_log.info("Collection: Setting resolution to %.3f", resolution)
                self.set_resolution(resolution)
            except Exception as ex:
                self.user_log.error("Collection: cannot set resolution.")
                msg = "[COLLECT] Error setting resolution: %s" % ex
                self.log.error(msg)
                raise Exception(msg)

        elif "detdistance" in self.current_dc_parameters:
            try:
                detdistance = self.current_dc_parameters["detdistance"]
                self.user_log.info("Collection: Moving detector to %f", detdistance)
                self.move_detector(detdistance)
            except Exception as ex:
                self.user_log.error("Collection: cannot set detector distance.")
                msg = "[COLLECT] Error setting detector distance: %s" % ex
                self.log.error(msg)
                raise Exception(msg)

        if "transmission" in self.current_dc_parameters:
            transmission = self.current_dc_parameters["transmission"]
            self.user_log.info("Collection: Setting transmission to %.3f", transmission)
            try:
                self.set_transmission(transmission)
            except Exception as ex:
                self.user_log.error("Collection: cannot set beamline transmission.")
                msg = "[COLLECT] Error setting transmission: %s" % ex
                self.log.error(msg)
                raise Exception(msg)

        self.triggers_to_collect = self.prepare_triggers_to_collect()

        # create a list with all the interleaved energies
        # and save all the collection parameters
        if self.in_interleave:
            self.autoprocessing_hwobj.interleaved_energies.append(
                self.current_dc_parameters["energy"]
            )
            self.autoprocessing_hwobj.collection_dictionaries.append(
                self.current_dc_parameters
            )

        if self.scicat_enabled:
            try:
                proposalId = self.session_hwobj.proposal_number
                self.scicat_hwobj.start_scan(proposalId, self.current_dc_parameters)
            except Exception as ex:
                self.log.exception(
                    "[COLLECT] Error sending uuid to data catalog: %s" % ex
                )

        try:
            self.prepare_detector()
        except Exception as ex:
            self.user_log.exception("Collection: cannot set prepare detector.")
            msg = "[COLLECT] Error preparing detector: %s" % ex
            self.log.error(msg)
            raise Exception(msg)

        # move MD3 to DataCollection phase if it's not
        if self.diffractometer_hwobj.get_current_phase() != "DataCollection":
            self.user_log.info("Moving Diffractometer to Data Collection")
            self.diffractometer_hwobj.set_phase("DataCollection")

        self.flux_before_collect = 0  # self.get_instant_flux()
        self.estimated_flux_before_collect = 0  # self.get_estimated_flux()
        # flux value is a string
        if float(self.flux_before_collect) < 1:
            self.user_log.error("Collection: Flux is 0, please check the beam!!")

        self.diffractometer_hwobj.wait_ready(20)
        self.move_to_centered_position()
        self.diffractometer_hwobj.wait_ready(20)

        self.log.info(
            "Updating data collection in LIMS with data: %s"
            % self.current_dc_parameters
        )
        self.update_data_collection_in_lims()

    def prepare_triggers_to_collect(self):
        """
        Prepare number of triggers for the detector
        """
        oscillation_parameters = self.current_dc_parameters["oscillation_sequence"][0]
        osc_start = oscillation_parameters["start"]
        osc_range = oscillation_parameters["range"]
        nframes = oscillation_parameters["number_of_images"]
        overlap = oscillation_parameters["overlap"]
        triggers_to_collect = []

        if overlap > 0 or overlap < 0:
            # currently for characterization, only collect one image at each omega position
            ntriggers = nframes
            nframes_per_trigger = 1
            for trigger_num in range(1, ntriggers + 1):
                triggers_to_collect.append(
                    (osc_start, trigger_num, nframes_per_trigger, osc_range)
                )
                osc_start += osc_range * nframes_per_trigger - overlap
            self.char = True
        elif self.current_dc_parameters["experiment_type"] == "Mesh":
            msg = "osc_start %s, nframes %s, osc_range %s num_lines %s" % (
                osc_start,
                nframes,
                osc_range,
                self.get_mesh_num_lines(),
            )
            self.log.info(msg)
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
            self.log.debug("data_collection_hook {}".format(oscillation_parameters))
            # TODO: investigate gevent.timeout exception handing, this wait is
            # to ensure that configuration is done before arming
            time.sleep(2)
            try:
                self.detector_hwobj.wait_config_done()
                self.detector_hwobj.start_acquisition()
                self.detector_hwobj.wait_ready()
            except Exception as ex:
                self.log.error("[COLLECT] Detector Error: %s" % ex)
                raise RuntimeError("[COLLECT] Detector error while arming.")

            self.log.debug("data_collection_hook detector ready")

            try:
                shutterless_exptime = self.detector_hwobj.get_acquisition_time()
            except Exception as ex:
                self.log.exception(
                    "[COLLECT] Detector error getting acquisition time: %s" % ex
                )
                shutterless_exptime = 0.01

            for (
                osc_start,
                trigger_num,
                nframes_per_trigger,
                osc_range,
            ) in self.triggers_to_collect:
                osc_end = osc_start + osc_range * nframes_per_trigger
                # self.display_task = gevent.spawn(self._update_image_to_display)
                self.progress_task = gevent.spawn(self._update_task_progress)

                # Actual MD3 oscillation launched here
                self.oscillation_task = self.oscil(
                    osc_start, osc_end, shutterless_exptime, 1, wait=True
                )
            self.log.debug("data_collection_hook OSC Done")

            try:
                self.detector_hwobj.stop_acquisition()
            except Exception as ex:
                self.log.error("[COLLECT] Detector error stopping acquisition: %s" % ex)

            self.emit("collectImageTaken", oscillation_parameters["number_of_images"])
        except RuntimeError as ex:
            self.data_collection_cleanup()
            self.log.error("[COLLECT] Runtime Error: %s" % ex)
            raise Exception("data collection hook failed... ", str(ex))
        except Exception:
            self.log.exception("Unexpected error")
            self.data_collection_cleanup()
            raise Exception("data collection hook failed... ", sys.exc_info()[0])
        finally:
            self.close_detector_cover()

    def get_mesh_num_lines(self):
        return self.mesh_num_lines

    def get_mesh_total_nb_frames(self):
        return self.mesh_total_nb_frames

    def get_current_shape(self):
        shape_id = self.current_dc_parameters["shape"]
        if shape_id != "":
            shape = self.shape_history_hwobj.get_shape(shape_id).as_dict()
        else:
            shape = None
        return shape

    def oscil(self, start, end, exptime, npass, wait=True):
        time.sleep(1)
        oscillation_parameters = self.current_dc_parameters["oscillation_sequence"][0]
        msg = (
            "[MICROMAXCOLLECT] Oscillation requested oscillation_parameters: %s"
            % oscillation_parameters
        )
        self.log.info(msg)

        if self.helical:
            self.diffractometer_hwobj.osc_scan_4d(
                start, end, exptime, self.helical_pos, wait=wait
            )
        elif self.current_dc_parameters["experiment_type"] == "Mesh":
            self.log.info(
                "Mesh oscillation requested: number of lines %s"
                % self.get_mesh_num_lines()
            )
            self.log.info(
                "Mesh oscillation requested: total number of frames %s"
                % self.get_mesh_total_nb_frames()
            )

            shape = self.get_current_shape()
            if shape is None:
                raise RuntimeError("Mesh oscillation failed, no shape defined")

            range_x = (shape.get("num_cols") - 1) * shape.get("cell_width") / 1000.0
            range_y = (shape.get("num_rows") - 1) * shape.get("cell_height") / 1000.0

            # the MD3 raster scan command is relative to the currently saved centered position,
            # calculate and save this mesh's center position
            self.move_to_mesh_center(shape)

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
            self.diffractometer_hwobj.do_oscillation_scan(start, end, exptime, wait)

    def move_to_mesh_center(self, shape):
        """
        move to the mesh center and invoke 'save centered position' command
        """
        range_x = shape.get("num_cols") * shape.get("cell_width") / 1000.0
        range_y = shape.get("num_rows") * shape.get("cell_height") / 1000.0

        self.diffractometer_hwobj.phiy_motor_hwobj.set_value_relative(range_y / 2.0)
        self.diffractometer_hwobj.move_cent_vertical_relative(-range_x / 2.0)

        self.diffractometer_hwobj.save_centered_position()

    def _update_task_progress(self):
        """
        Emit signals to follow the acquisition progress
        """
        self.log.info("[MICROMAXCOLLECT] update task progress launched")
        num_images = self.current_dc_parameters["oscillation_sequence"][0][
            "number_of_images"
        ]
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
            self.log.info(
                "[MICROMAXCOLLECT] collectImageTaken %s (%s, %s, %s)"
                % (current_frame, num_images, step_size, step_count)
            )
            self.emit("collectImageTaken", current_frame)
            step_count += 1

    def emit_collection_failed(self):
        """
        Handle failure messages and cleanup
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
            self.char = False
        if self.current_dc_parameters["experiment_type"] == "Mesh" or self.hve:
            self.detector_hwobj.disable_stream()

        self.emit("collectEnded", self.owner, False, failed_msg)
        self.emit("collectReady", (True,))
        self._collecting = None
        self.ready_event.set()

        self.log.error(
            "[COLLECT] COLLECTION FAILED, self.current_dc_parameters: %s"
            % self.current_dc_parameters
        )

        self.update_data_collection_in_lims()

    def emit_collection_finished(self):
        """
        Handle finish messages and autoprocessing
        """
        exp_type = self.current_dc_parameters["experiment_type"]
        overlap = self.current_dc_parameters["oscillation_sequence"][0]["overlap"]
        num_images = self.current_dc_parameters["oscillation_sequence"][0][
            "number_of_images"
        ]
        if (
            exp_type in ("OSC", "Helical")
            and overlap == 0
            and num_images >= self.NIMAGES_TRIGGER_AUTO_PROC
            and not self.in_interleave
        ):
            gevent.spawn(self.trigger_auto_processing, "after", 0)

        if not self.in_interleave:
            gevent.spawn(self.post_collection_store_image)

        if self.current_dc_parameters["experiment_type"] == "Mesh" or self.hve:
            # disable stream interface
            self.detector_hwobj.disable_stream()
        if self.char:
            # stop char converter
            self.char = False
        self.diffractometer_hwobj.wait_ready(5)

        # estimate the flux at sample position
        self.estimated_flux_after_collect = self.get_estimated_flux()
        if self.estimated_flux_before_collect > 0:
            self.flux_after_collect = str(
                float(self.estimated_flux_after_collect)
                * float(self.flux_before_collect)
                / float(self.estimated_flux_before_collect)
            )
        self.log.info(
            "[COLLECT] flux before and after collection are: {} {} estimated values are {} {}, beam_size is {}".format(
                self.flux_before_collect,
                self.flux_after_collect,
                self.estimated_flux_before_collect,
                self.estimated_flux_after_collect,
                self.current_dc_parameters["beamSizeAtSampleX"],
            )
        )

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

        self.log.debug(
            "[COLLECT] COLLECTION FINISHED, self.current_dc_parameters: %s"
            % self.current_dc_parameters
        )

        if self.scicat_enabled:
            self.scicat_hwobj.end_scan(self.current_dc_parameters)

    def post_collection_store_image(self, collection=None):
        """
        Generate and store ijn ispyb thumbnail images
        """
        # only store the first image
        self.log.info("Storing images in lims, frame number: 1")
        if collection is None:
            collection = self.current_dc_parameters
        try:
            self.store_image_in_lims(1, collection=collection)
            self.generate_and_copy_thumbnails(collection["fileinfo"]["filename"], 1)
        except Exception as ex:
            self.log.error("Could not store images in lims, error was {}".format(ex))

    def store_image_in_lims_by_frame_num(self, frame, motor_position_id=None):
        """
        Descript. :
        """
        # Dont save mesh first and last images
        # Mesh images (best positions) are stored after data analysis
        self.log.info("TODO: fix store_image_in_lims_by_frame_num method for nimages>1")
        return

    def generate_and_copy_thumbnails(self, data_path, frame_number):
        if self.gen_thumbnail_script is None:
            self.log.warning(
                "[COLLECT] Generating thumbnail script is not defined, no thumbnails will be created!!"
            )
            return
        #  generare diffraction thumbnails
        image_file_template = self.current_dc_parameters["fileinfo"]["template"]
        archive_directory = self.current_dc_parameters["fileinfo"]["archive_directory"]
        thumb_filename = "%s.thumb.jpeg" % os.path.splitext(image_file_template)[0]
        jpeg_thumbnail_file_template = os.path.join(archive_directory, thumb_filename)
        jpeg_thumbnail_full_path = jpeg_thumbnail_file_template % frame_number

        self.log.info(
            "[COLLECT] Generating thumbnails, output filename: %s"
            % jpeg_thumbnail_full_path
        )
        self.log.info("[COLLECT] Generating thumbnails, data path: %s" % data_path)
        cmd = "ssh clu0-fe-0 %s  %s  %d  %s &" % (
            self.gen_thumbnail_script,
            data_path,
            frame_number,
            jpeg_thumbnail_full_path,
        )
        self.log.info(cmd)
        os.system(cmd)

    def store_image_in_lims(
        self, frame_number, motor_position_id=None, collection=None
    ):
        """
        Descript. :
        """
        if collection is None:
            collection = self.current_dc_parameters
        if self.lims_client_hwobj:
            file_location = collection["fileinfo"]["directory"]
            image_file_template = collection["fileinfo"]["template"]
            filename = image_file_template % frame_number
            lims_image = {
                "dataCollectionId": collection["collection_id"],
                "fileName": filename,
                "fileLocation": file_location,
                "imageNumber": frame_number,
                "measuredIntensity": self.get_measured_intensity(),
                "synchrotronCurrent": self.get_machine_current(),
                "machineMessage": self.get_machine_message(),
                "temperature": self.get_cryo_temperature(),
            }
            archive_directory = collection["fileinfo"]["archive_directory"]

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
                lims_image["fileLocation"] = collection["fileinfo"]["directory"]
            if motor_position_id:
                lims_image["motorPositionId"] = motor_position_id
            self.log.info(
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
                self.log.error(
                    "Could not store images in lims, error was {}".format(ex)
                )

            # temp fix for ispyb permission issues
            try:
                session_dir = os.path.join(archive_directory, "../../../")
                os.system("chmod -R 777 %s" % (session_dir))
            except Exception as ex:
                self.log.warning(
                    "Could not change permissions on ispyb storage, error was {}".format(
                        ex
                    )
                )

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
                except Exception:
                    self.log.exception("Collection: Error creating snapshot directory")

            # for plate head, takes only one image
            if (
                self.diffractometer_hwobj.head_type
                == GenericDiffractometer.HEAD_TYPE_PLATE
            ):
                number_of_snapshots = 1
            else:
                number_of_snapshots = 4  # 4 take only one image for the moment
            self.user_log.info(
                "Collection: Taking %d sample snapshot(s)" % number_of_snapshots
            )
            if self.diffractometer_hwobj.get_current_phase() != "Centring":
                self.user_log.info("Moving Diffractometer to CentringPhase")
                self.diffractometer_hwobj.set_phase("Centring")
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
        self.log.info(
            "[COLLECT] triggering auto processing, self.current_dc_parameters: %s"
            % self.current_dc_parameters
        )
        self.log.info("[COLLECT] Launching MAXIV Autoprocessing")
        if self.autoprocessing_hwobj is not None:
            try:
                self.autoprocessing_hwobj.execute_autoprocessing(
                    process_event, self.current_dc_parameters, frame_number
                )
            except Exception as ex:
                self.log.error(
                    "[COLLECT] Cannot execute autoprocessing: error was: %s" % ex
                )

    def get_beam_centre(self):
        """
        Descript. :
        """
        if self.detector_hwobj is not None:
            return self.detector_hwobj.get_beam_position()
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
            self.log.info("Openning the detector cover.")
            plc = PyTango.DeviceProxy("b312a/vac/plc-01")
            plc.B312A_E06_DIA_DETC01_ENAC = 1
            plc.B312A_E06_DIA_DETC01_OPC = 1
            time.sleep(1)  # make sure the cover is up before the data collection stars
        except Exception:
            self.log.exception("Could not open the detector cover")
            raise RuntimeError("[COLLECT] Could not open the detector cover.")

    def close_detector_cover(self):
        """
        Descript. :
        """
        try:
            self.log.info("Closing the detector cover")
            plc = PyTango.DeviceProxy("b312a/vac/plc-01")
            plc.B312A_E06_DIA_DETC01_ENAC = 1
            plc.B312A_E06_DIA_DETC01_CLC = 1
        except Exception:
            self.log.exception("Could not close the detector cover")

    def open_fast_shutter(self):
        """
        Descript. : important to make sure it's passed, as we
                    don't open the fast shutter in MXCuBE
        """
        self.diffractometer_hwobj.open_fast_shutter()

    def close_fast_shutter(self):
        """
        Descript. :
        """
        # to do, close the fast shutter as early as possible in case
        # MD3 fails to do so
        self.diffractometer_hwobj.close_fast_shutter()

    @task
    def _take_crystal_snapshot(self, filename):
        """
        Descript. :
        """
        # take image from server
        self.diffractometer_hwobj.camera.take_snapshot(filename)

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
        new_distance = self.resolution_hwobj.resolution_to_distance(value)
        self.move_detector(new_distance)

    def set_energy(self, value):
        self.log.info("[COLLECT] Setting beamline energy to %s" % value)
        self.energy_hwobj.start_move_energy(value, True, False)  # keV
        self.log.info(
            "[COLLECT] Updating wavelength parameter to %s" % (12.3984 / value)
        )
        self.current_dc_parameters["wavelength"] = 12.3984 / value
        self.log.info("[COLLECT] Setting detector energy")
        self.detector_hwobj.set_photon_energy(value * 1000)  # ev

    def set_wavelength(self, value):
        self.log.info("[COLLECT] Setting beamline wavelength to %s" % value)
        self.energy_hwobj.startMoveWavelength(value)
        current_energy = self.energy_hwobj.getCurrentEnergy()
        self.detector_hwobj.set_photon_energy(current_energy * 1000)

    @task
    def move_motors(self, motor_position_dict):
        """
        Descript. :
        """
        self.diffractometer_hwobj.move_to_motors_positions(motor_position_dict)

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
        self.user_log.info(
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
        self.log.info(
            "[COLLECT] Processing input file directories: XDS: %s, AUTO: %s"
            % (xds_directory, auto_directory)
        )
        return xds_directory, auto_directory

    def move_detector(self, value):
        """
        Descript. : move detector to the set distance
        """
        lower_limit, upper_limit = self.get_detector_distance_limits()
        self.log.info(
            "...................value %s, detector movement start..... %s"
            % (value, self.dtox_hwobj.get_value())
        )
        if upper_limit is not None and lower_limit is not None:
            if value >= upper_limit or value <= lower_limit:
                self.log.exception("Can't move detector, the value is out of limits")
                self.stop_collect()
            else:
                try:
                    if self.dtox_hwobj is not None:
                        self.dtox_hwobj.set_value(value)
                        self.dtox_hwobj.wait_end_of_move(50)
                except Exception:
                    self.user_log.error("Cannot move detector.")
                    self.log.exception("Problems when moving detector!!")
                    self.stop_collect()
        else:
            self.log.exception("Can't get distance limits, not moving detector!!")
        self.log.info(
            "....................value %s detector movement finished.....%s"
            % (value, self.dtox_hwobj.get_value())
        )

        current_pos = self.dtox_hwobj.get_value()
        if abs(current_pos - value) > 0.05:
            self.user_log.exception("Detector didn't go to the set position")
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

        config["OmegaStart"] = osc_start  # oscillation_parameters['start']
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
        except Exception:
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
        config["FilenamePattern"] = name_pattern

        # make sure the filewriter is enabled
        self.detector_hwobj.enable_filewriter()
        self.detector_hwobj.enable_stream()
        dozor_dict = self.detector_hwobj.prepare_acquisition(config)

        # set image appendix, used by online analysis
        target_beam_size_factor = 2.0  # this value should be from x-ray centering
        collect_dict = {
            "exp_type": self.current_dc_parameters["experiment_type"],
            "ssx_mode": self.ssx_mode,
            "row": ntrigger,
            "col": nframes_per_trigger,
            "target_beam_size_factor": target_beam_size_factor,
            "col_id": self.current_dc_parameters["collection_id"],
            "process_dir": self.current_dc_parameters["auto_dir"],
            "shape_id": self.current_dc_parameters["shape"],
            "mxcube_server": self.get_mxcube_server_ip(),
        }
        header_appendix = {
            "dozor_dict": dozor_dict,
            "collect_dict": collect_dict,
        }
        self.detector_hwobj.set_header_appendix(json.dumps(header_appendix))

    def stop_collect(self):
        """
        Stops data collection
        """
        self.log.error("Stopping collection ....")
        self.close_detector_cover()
        self.diffractometer_hwobj.abort()
        self.detector_hwobj.abort()
        self.detector_hwobj.disarm()
        try:
            self.progress_task.kill(block=False)
        except Exception:
            pass
        if self.data_collect_task is not None:
            self.data_collect_task.kill(block=False)
        self.log.error("Collection stopped")
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
            chan = self.getChannelObject("undulator_gap")
            gap = "{:.2f}".format(chan.get_value())
            return gap
        except Exception:
            return None

    def get_slit_gaps(self):
        """
        Descript. :
        """
        try:
            return self.beam_info_hwobj.get_beam_size()
        except Exception:
            return None

    def get_machine_current(self):
        """
        Descript. :
        """
        try:
            return self.machine_info_hwobj.getCurrent()
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
            return self.machine_info_hwobj.getFillingMode()
        except Exception:
            return ""

    def get_flux(self):
        """
        Descript. :
        """
        try:
            flux = self.flux_hwobj.get_flux()
        except Exception as ex:
            self.log.error("[HWR] Cannot retrieve flux value. Error was {}".format(ex))
            flux = -1
        return flux

    def get_instant_flux(self, keep_position=False):
        """
        Descript. : get the instant flux value, w/o checking beamstability
        this method assuming that the MD3 is already in datacollection phase
        """
        try:
            ori_motors, ori_phase = self.diffractometer_hwobj.set_calculate_flux_phase()
            flux = self.flux_hwobj.get_instant_flux()
        except Exception as ex:
            self.log.error(
                "[COLLECT] Cannot get the current flux value. Error was {}".format(ex)
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

    def get_estimated_flux(self):
        """
        Descript. : Read the flux from BCU, no attenuation, no collimator
        """

        flux = 0
        try:
            flux = self.flux_hwobj.estimate_flux()
        except Exception:
            self.log.error("[COLLECT] Cannot estimate flux from BCU")
        return flux

    def get_measured_intensity(self):
        return float(self.get_flux())

    def prepare_for_new_sample(self, manual_mode=True):
        """
        Descript.: prepare beamline for a new sample,
        """
        self.log.info("[HWR] Preparing beamline for a new sample.")
        if manual_mode:
            self.close_detector_cover()
            self.diffractometer_hwobj.set_phase("Transfer")
            self.close_safety_shutter()

        self.move_detector(DET_SAFE_POSITION)

    def _update_image_to_display(self):
        fname1 = "/mxn/groups/sw/mxsw/albula_autoload/to_display"
        time.sleep(self.display["delay"] + 3)
        frequency = 5
        step = int(math.ceil(frequency / self.display["exp"]))
        if step == 1:
            frequency = self.display["exp"]
        for i in range(1, self.display["nimages"] + 1, step):
            try:
                os.system("echo %s, %s > %s" % (self.display["file_name1"], i, fname1))
            except Exception:
                pass
            if self.stop_display:
                break
            time.sleep(frequency)

    def enable_scicat(self, enable):
        self.scicat_enabled = enable
        if self.scicat_enabled:
            self.scicat_hwobj = SciCatPlugin()
            self.log.info("[COLLECT] SciCat Datacatalog enabled")
        else:
            self.scicat_hwobj = None
            self.log.warning("[COLLECT] SciCat Datacatalog not enabled")

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
            except Exception:
                self.log.exception("Could not update data collection in LIMS")

    def start_dataset_repacking(self):
        self.autoprocessing_hwobj.start_dataset_repacking(
            self.current_dc_parameters, self.bl_config
        )

    def set_interleave(self, in_interleave):
        self.in_interleave = in_interleave
