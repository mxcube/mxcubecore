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

"""
AbstractMulticollect
Defines a sequence how data collection is executed.
"""

import os
import sys
import logging
import time
import errno
import abc
import collections
import gevent
import gevent.event
from mxcubecore.TaskUtils import task
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR


__credits__ = ["MXCuBE collaboration"]


BeamlineConfig = collections.namedtuple(
    "BeamlineConfig",
    [
        "synchrotron_name",
        "directory_prefix",
        "default_exposure_time",
        "minimum_exposure_time",
        "detector_fileext",
        "detector_type",
        "detector_manufacturer",
        "detector_model",
        "detector_px",
        "detector_py",
        "detector_binning_mode",
        "undulators",
        "focusing_optic",
        "monochromator_type",
        "beam_divergence_vertical",
        "beam_divergence_horizontal",
        "polarisation",
        "input_files_server",
    ],
)


class AbstractCollect(HardwareObject, object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.bl_config = BeamlineConfig(*[None] * 18)

        self._collecting = False
        self._error_msg = ""
        self.exp_type_dict = {}

        self.collection_id = None
        self.data_collect_task = None
        self.current_dc_parameters = None
        self.current_lims_sample = {}
        self.run_offline_processing = None
        self.run_online_processing = None
        self.ready_event = None

    def init(self):
        self.ready_event = gevent.event.Event()

        undulators = []
        try:
            for undulator in self["undulators"]:
                undulators.append(undulator)
        except BaseException:
            pass

        beam_div_hor, beam_div_ver = HWR.beamline.beam.get_beam_divergence()

        self.set_beamline_configuration(
            synchrotron_name=HWR.beamline.session.synchrotron_name,
            directory_prefix=self.get_property("directory_prefix"),
            default_exposure_time=HWR.beamline.detector.get_property(
                "default_exposure_time"
            ),
            minimum_exposure_time=HWR.beamline.detector.get_property(
                "minimum_exposure_time"
            ),
            detector_fileext=HWR.beamline.detector.get_property("fileSuffix"),
            detector_type=HWR.beamline.detector.get_property("type"),
            detector_manufacturer=HWR.beamline.detector.get_property("manufacturer"),
            detector_model=HWR.beamline.detector.get_property("model"),
            detector_px=HWR.beamline.detector.get_property("px"),
            detector_py=HWR.beamline.detector.get_property("py"),
            detector_binning_mode=HWR.beamline.detector.get_binning_mode(),
            undulators=undulators,
            focusing_optic=self.get_property("focusing_optic"),
            monochromator_type=self.get_property("monochromator"),
            beam_divergence_vertical=beam_div_hor,
            beam_divergence_horizontal=beam_div_ver,
            polarisation=self.get_property("polarisation"),
            input_files_server=self.get_property("input_files_server"),
        )

    def set_beamline_configuration(self, **configuration_parameters):
        """Sets beamline configuration

        :param configuration_parameters: dict with config param.
        :type configuration_parameters: dict
        """
        self.bl_config = BeamlineConfig(**configuration_parameters)

    def collect(self, owner, dc_parameters_list):
        """
        Main collect method.
        """
        self.ready_event.clear()
        self.current_dc_parameters = dc_parameters_list[0]
        self.data_collect_task = gevent.spawn(self.do_collect, owner)
        self.ready_event.wait()
        self.ready_event.clear()
        return self.data_collect_task

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
                "Collection parameters: %s" % str(self.current_dc_parameters)
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

        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            failed_msg = "Data collection failed!\n%s" % exc_value
            self.collection_failed(failed_msg)
        else:
            self.collection_finished()
        finally:
            self.data_collection_cleanup()

    def data_collection_cleanup(self):
        """
        Method called when at end of data collection, successful or not.
        """
        self.close_fast_shutter()
        self.close_safety_shutter()
        self.close_detector_cover()

    def collection_failed(self, failed_msg=None):
        """Collection failed method"""

        if not failed_msg:
            failed_msg = "Data collection failed!"
        self.current_dc_parameters["status"] = "Failed"
        self.current_dc_parameters["comments"] = "%s\n%s" % (
            failed_msg,
            self._error_msg,
        )
        self.emit(
            "collectOscillationFailed",
            (
                None,
                False,
                failed_msg,
                self.current_dc_parameters.get("collection_id"),
                None,
            ),
        )
        self.emit("progressStop", ())
        self._collecting = False
        self.update_data_collection_in_lims()
        self.ready_event.set()

    def collection_stopped(self):
        """Collection stopped method"""

        self.current_dc_parameters["status"] = "Stopped"
        self.current_dc_parameters["comments"] = "Stopped by the user"
        self.emit("progressStop", ())
        self._collecting = False
        self.update_data_collection_in_lims()
        self.ready_event.set()
        if self.data_collect_task is not None:
            self.data_collect_task.kill(block=False)

    def collection_finished(self):
        """Collection finished beahviour"""

        success_msg = "Data collection successful"
        self.current_dc_parameters["status"] = success_msg

        if self.current_dc_parameters["experiment_type"] != "Collect - Multiwedge":
            self.update_data_collection_in_lims()

            last_frame = self.current_dc_parameters["oscillation_sequence"][0][
                "number_of_images"
            ]
            if (
                last_frame > 1
                and self.current_dc_parameters["experiment_type"] != "Mesh"
            ):
                # We do not store first and last frame for mesh
                self.store_image_in_lims_by_frame_num(last_frame)
            if (
                self.current_dc_parameters["experiment_type"] in ("OSC", "Helical")
                and self.current_dc_parameters["oscillation_sequence"][0]["overlap"]
                == 0
                and last_frame > 19
            ):
                self.trigger_auto_processing("after", 0)

        self.emit(
            "collectOscillationFinished",
            (
                None,
                True,
                success_msg,
                self.current_dc_parameters.get("collection_id"),
                None,
                self.current_dc_parameters,
            ),
        )
        self.emit("progressStop", ())
        self._collecting = False
        self.ready_event.set()

    def store_image_in_lims_by_frame_num(self, frame_number):
        pass

    def stop_collect(self):
        """
        Stops data collection
        """
        if self.data_collect_task is not None:
            self.data_collect_task.kill(block=False)

    def open_detector_cover(self):
        """
        Descript. :
        """
        pass

    def open_safety_shutter(self):
        """
        Descript. :
        """
        pass

    def open_fast_shutter(self):
        """
        Descript. :
        """
        pass

    def close_fast_shutter(self):
        """
        Descript. :
        """
        pass

    def close_safety_shutter(self):
        """
        Descript. :
        """
        pass

    def close_detector_cover(self):
        """
        Descript. :
        """
        pass

    def set_transmission(self, value):
        """def get_beam_
        Descript. :
        """
        pass

    def set_wavelength(self, value):
        """
        Descript. :
        """
        pass

    def set_energy(self, value):
        """
        Descript. :
        """
        pass

    def set_resolution(self, value):
        """
        Descript. :
        """
        pass

    def move_detector(self, value):
        """
        Descript. :
        """
        pass

    def get_total_absorbed_dose(self):
        return

    def get_wavelength(self):
        """
        Descript. :
        """
        if HWR.beamline.energy is not None:
            return HWR.beamline.energy.get_wavelength()

    def get_detector_distance(self):
        """
        Descript. :
        """
        if HWR.beamline.detector is not None:
            return HWR.beamline.detector.distance.get_value()

    def get_resolution(self):
        """
        Descript. :
        """
        if HWR.beamline.resolution is not None:
            return HWR.beamline.resolution.get_value()

    def get_transmission(self):
        """
        Descript. :
        """
        if HWR.beamline.transmission is not None:
            return HWR.beamline.transmission.get_value()

    def get_beam_size(self):
        """
        Descript. :
        """
        if HWR.beamline.beam is not None:
            return HWR.beamline.beam.get_beam_size()
        else:
            return None, None

    def get_slit_gaps(self):
        """
        Descript. :
        """
        if HWR.beamline.beam is not None:
            return HWR.beamline.beam.get_slits_gap()
        return None, None

    def get_undulators_gaps(self):
        """
        Descript. :
        """
        return {}
        # return HWR.beamline.energy.get_undulator_gaps()

    def get_machine_current(self):
        """
        Descript. :
        """
        if HWR.beamline.machine_info:
            return HWR.beamline.machine_info.get_current()
        else:
            return 0

    def get_machine_message(self):
        """
        Descript. :
        """
        if HWR.beamline.machine_info:
            return HWR.beamline.machine_info.get_message()
        else:
            return ""

    def get_machine_fill_mode(self):
        """
        Descript. :
        """
        if HWR.beamline.machine_info:
            fill_mode = str(HWR.beamline.machine_info.get_message())
            return fill_mode[:20]
        else:
            return ""

    def get_measured_intensity(self):
        """
        Descript. :
        """
        return

    def get_cryo_temperature(self):
        """
        Descript. :
        """
        return

    def create_file_directories(self):
        """
        Method create directories for raw files and processing files.
        Directorie names for xds, mosflm and hkl are created
        """
        self.create_directories(
            self.current_dc_parameters["fileinfo"]["directory"],
            self.current_dc_parameters["fileinfo"]["process_directory"],
            self.current_dc_parameters["fileinfo"]["archive_directory"],
        )
        xds_directory, mosflm_directory, hkl2000_directory = self.prepare_input_files()
        if xds_directory:
            self.current_dc_parameters["xds_dir"] = xds_directory

    def create_directories(self, *args):
        """
        Descript. :
        """
        for directory in args:
            try:
                os.makedirs(directory)
            except os.error as e:
                if e.errno != errno.EEXIST:
                    raise

    def prepare_input_files(self):
        """
        Prepares input files for xds, mosflm and hkl2000
        returns: 3 strings
        """

        return None, None, None

    def store_data_collection_in_lims(self):
        """
        Descript. :
        """
        lims = HWR.beamline.lims
        if lims and lims.is_connected() and not self.current_dc_parameters["in_interleave"]:
            try:
                self.current_dc_parameters[
                    "synchrotronMode"
                ] = self.get_machine_fill_mode()
                (collection_id, detector_id,) = HWR.beamline.lims.store_data_collection(
                    self.current_dc_parameters, self.bl_config
                )
                self.current_dc_parameters["collection_id"] = collection_id
                self.collection_id = collection_id
                if detector_id:
                    self.current_dc_parameters["detector_id"] = detector_id
            except BaseException:
                logging.getLogger("HWR").exception(
                    "Could not store data collection in LIMS"
                )

    def update_data_collection_in_lims(self):
        """
        Descript. :
        """
        params = self.current_dc_parameters
        if HWR.beamline.lims and not params["in_interleave"]:
            params["flux"] = HWR.beamline.flux.get_value()
            params["flux_end"] = params["flux"]
            params["totalAbsorbedDose"] = self.get_total_absorbed_dose()
            params["wavelength"] = HWR.beamline.energy.get_wavelength()
            params["detectorDistance"] = HWR.beamline.detector.distance.get_value()
            params["resolution"] = HWR.beamline.resolution.get_value()
            params["transmission"] = HWR.beamline.transmission.get_value()
            beam_centre_x, beam_centre_y = HWR.beamline.detector.get_beam_position()
            pixel_x, pixel_y = HWR.beamline.detector.get_pixel_size()
            params["xBeam"] = beam_centre_x * pixel_x
            params["yBeam"] = beam_centre_y * pixel_y
            und = self.get_undulators_gaps()
            i = 1
            for jj in self.bl_config.undulators:
                key = jj.type
                if key in und:
                    params["undulatorGap%d" % (i)] = und[key]
                    i += 1
            params["resolutionAtCorner"] = HWR.beamline.resolution.get_value_at_corner()
            beam_size_x, beam_size_y = HWR.beamline.beam.get_beam_size()
            params["beamSizeAtSampleX"] = beam_size_x
            params["beamSizeAtSampleY"] = beam_size_y
            params["beamShape"] = HWR.beamline.beam.get_beam_shape()
            hor_gap, vert_gap = self.get_slit_gaps()
            params["slitGapHorizontal"] = hor_gap
            params["slitGapVertical"] = vert_gap
            try:
                HWR.beamline.lims.update_data_collection(params)
            except BaseException:
                logging.getLogger("HWR").exception(
                    "Could not update data collection in LIMS"
                )

    def store_sample_info_in_lims(self):
        """
        Descript. :
        """
        lims = HWR.beamline.lims
        if lims and lims.is_connected() and not self.current_dc_parameters["in_interleave"]:
            HWR.beamline.lims.update_bl_sample(self.current_lims_sample)

    def store_image_in_lims(self, frame_number, motor_position_id=None):
        """
        Descript. :
        """
        lims = HWR.beamline.lims
        if lims and lims.is_connected() and not self.current_dc_parameters["in_interleave"]:
            file_location = self.current_dc_parameters["fileinfo"]["directory"]
            image_file_template = self.current_dc_parameters["fileinfo"]["template"]
            filename = image_file_template % frame_number
            lims_image = {
                "dataCollectionId": self.current_dc_parameters.get("collection_id"),
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
                jpeg_filename = "%s.jpeg" % os.path.splitext(image_file_template)[0]
                thumb_filename = (
                    "%s.thumb.jpeg" % os.path.splitext(image_file_template)[0]
                )
                jpeg_file_template = os.path.join(
                    archive_directory, jpeg_filename
                ).replace("cbf.jpeg", "jpeg")
                jpeg_thumbnail_file_template = os.path.join(
                    archive_directory, thumb_filename
                ).replace("cbf.thumb", "thumb")
                jpeg_full_path = jpeg_file_template % frame_number
                jpeg_thumbnail_full_path = jpeg_thumbnail_file_template % frame_number
                lims_image["jpegFileFullPath"] = jpeg_full_path
                lims_image["jpegThumbnailFileFullPath"] = jpeg_thumbnail_full_path
            if motor_position_id:
                lims_image["motorPositionId"] = motor_position_id
            image_id = HWR.beamline.lims.store_image(lims_image)
            return image_id

    def update_lims_with_workflow(self, workflow_id, grid_snapshot_filename):
        """Updates collection with information about workflow

        :param workflow_id: workflow id
        :type workflow_id: int
        :param grid_snapshot_filename: grid snapshot file path
        :type grid_snapshot_filename: string
        """
        lims = HWR.beamline.lims
        if lims and lims.is_connected():
            try:
                self.current_dc_parameters["workflow_id"] = workflow_id
                if grid_snapshot_filename:
                    self.current_dc_parameters[
                        "xtalSnapshotFullPath3"
                    ] = grid_snapshot_filename
                HWR.beamline.lims.update_data_collection(self.current_dc_parameters)
            except BaseException:
                logging.getLogger("HWR").exception(
                    "Could not store data collection into ISPyB"
                )

    def get_sample_info(self):
        """
        Descript. :
        """
        sample_info = self.current_dc_parameters.get("sample_reference")
        try:
            sample_id = int(sample_info["blSampleId"])
        except BaseException:
            sample_id = None

        self.current_dc_parameters["blSampleId"] = sample_id

        if HWR.beamline.diffractometer.in_plate_mode():
            # TODO store plate location in lims
            pass
        elif HWR.beamline.sample_changer:
            try:
                self.current_dc_parameters[
                    "actualSampleBarcode"
                ] = HWR.beamline.sample_changer.getLoadedSample().getID()
                self.current_dc_parameters["actualContainerBarcode"] = (
                    HWR.beamline.sample_changer.getLoadedSample().getContainer().getID()
                )

                logging.getLogger("user_level_log").info("Getting loaded sample coords")
                basket, vial = HWR.beamline.sample_changer.getLoadedSample().getCoords()

                self.current_dc_parameters["actualSampleSlotInContainer"] = vial
                self.current_dc_parameters["actualContainerSlotInSC"] = basket
            except BaseException:
                self.current_dc_parameters["actualSampleBarcode"] = None
                self.current_dc_parameters["actualContainerBarcode"] = None
        else:
            self.current_dc_parameters["actualSampleBarcode"] = None
            self.current_dc_parameters["actualContainerBarcode"] = None

    def move_to_centered_position(self):
        """
        Descript. :
        """
        positions_str = ""
        for motor, position in self.current_dc_parameters["motors"].items():
            if position:
                if isinstance(motor, str):
                    positions_str += " %s=%f" % (motor, position)
                else:
                    positions_str += " %s=%f" % (motor.getMotorMnemonic(), position)
        self.current_dc_parameters["actualCenteringPosition"] = positions_str
        self.move_motors(self.current_dc_parameters["motors"])

    @abc.abstractmethod
    @task
    def move_motors(self, motor_position_dict):
        """
        Descript. :
        """
        return

    def take_crystal_snapshots(self):
        """
        Descript. :
        """
        number_of_snapshots = self.current_dc_parameters["take_snapshots"]
        if self.current_dc_parameters["experiment_type"] == "Mesh":
            number_of_snapshots = 1

        snapshot_directory = self.current_dc_parameters["fileinfo"]["archive_directory"]
        if number_of_snapshots > 0 or self.current_dc_parameters.get("take_video"):
            if not os.path.exists(snapshot_directory):
                try:
                    self.create_directories(snapshot_directory)
                except BaseException:
                    logging.getLogger("HWR").exception(
                        "Collection: Error creating snapshot directory"
                    )
        if number_of_snapshots > 0 and not self.current_dc_parameters["in_interleave"]:

            logging.getLogger("user_level_log").info(
                "Collection: Taking %d sample snapshot(s)" % number_of_snapshots
            )
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
                if number_of_snapshots > 1:
                    HWR.beamline.diffractometer.move_omega_relative(90)

        if (
            not HWR.beamline.diffractometer.in_plate_mode()
            and self.current_dc_parameters.get("take_video")
        ):
            # Add checkbox to allow enable/disable creation of gif
            logging.getLogger("user_level_log").info("Collection: Saving animated gif")
            animation_filename = os.path.join(
                snapshot_directory,
                "%s_%s_animation.gif"
                % (
                    self.current_dc_parameters["fileinfo"]["prefix"],
                    self.current_dc_parameters["fileinfo"]["run_number"],
                ),
            )
            self.current_dc_parameters["xtalSnapshotFullPath2"] = animation_filename
            self._take_crystal_animation(animation_filename, duration_sec=1)

    @abc.abstractmethod
    @task
    def _take_crystal_snapshot(self, snapshot_filename):
        """
        Depends on gui version how this method is implemented.
        In Qt3 diffractometer has a function,
        In Qt4 graphics_manager is making crystal snapshots
        """
        pass

    def _take_crystal_animation(self, animation_filename, duration_sec=1):
        """Rotates sample by 360 and composes a gif file"""
        pass

    @abc.abstractmethod
    def data_collection_hook(self):
        """
        Descript. :
        """
        pass

    @abc.abstractmethod
    def trigger_auto_processing(self, process_event, frame_number):
        """
        Descript. :
        """
        pass

    def set_helical(self, arg):
        """
        Descript. :
        """
        pass

    def set_helical_pos(self, arg):
        """
        Descript. :
        """
        pass

    def set_fast_characterisation(self, arg):
        """
        Descript. :
        """
        pass

    def setCentringStatus(self, status):
        """
        Descript. :
        """
        pass

    def prepare_interleave(self, data_model, param_list):
        self.current_dc_parameters = param_list[0]
        self.current_dc_parameters["status"] = "Running"
        self.current_dc_parameters["collection_start_time"] = time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        self.take_crystal_snapshots()

        self.store_data_collection_in_lims()
        self.current_dc_parameters["status"] = "Data collection successful"
        self.update_data_collection_in_lims()

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
        return

        # self.mesh_num_lines = num_lines
        # self.mesh_total_nb_frames = total_nb_frames
        # self.mesh_range = mesh_range_param
        # self.mesh_center = mesh_center_param
