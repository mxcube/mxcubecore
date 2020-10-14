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
AbstractCollect defines a sequence how data collection is executed.
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

from HardwareRepository.TaskUtils import task  # , cleanup_and_handle_error
from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.ConvertUtils import string_types
from HardwareRepository import HardwareRepository as HWR

from HardwareRepository.utils.dataobject import DataObject


__credits__ = ["MXCuBE collaboration"]


log = logging.getLogger("user_level_log")


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
        self.bl_config = BeamlineConfig(*[None] * 17)

        self._collecting = False
        self._error_msg = ""
        self.exp_type_dict = {}

        self._execute_task = None
        self.run_offline_processing = None
        self.run_online_prcessing = None
        self.ready_event = None

    def init(self):
        self.ready_event = gevent.event.Event()

        undulators = []
        try:
            for undulator in self["undulators"]:
                undulators.append(undulator)
        except Exception:
            pass

        session = HWR.beamline.session
        if session:
            synchrotron_name = session.get_property("synchrotron_name")
        else:
            synchrotron_name = "UNKNOWN"


        beam_div_hor, beam_div_ver = HWR.beamline.beam.get_beam_divergence()

        self.set_beamline_configuration(
            synchrotron_name=synchrotron_name,
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
            undulators=undulators,
            focusing_optic=self.get_property("focusing_optic"),
            monochromator_type=self.get_property("monochromator"),
            beam_divergence_vertical=beam_divergence_ver,
            beam_divergence_horizontal=beam_divergence_hor,
            polarisation=self.get_property("polarisation"),
            input_files_server=self.get_property("input_files_server"),
        )

    def set_beamline_configuration(self, **configuration_parameters):
        """Sets beamline configuration

        :param configuration_parameters: dict with config param.
        :type configuration_parameters: dict
        """
        self.bl_config = BeamlineConfig(**configuration_parameters)

    def collect(self, owner, cp_dict):
        """
        Main collect method.
        """
        self.ready_event.clear()
        self._execute_task = gevent.spawn(
            self._start, owner, DataObject(cp_dict[0])
        )
        self.ready_event.wait()
        self.ready_event.clear()

    def _start(self, owner, cp):
        """
        Actual collect sequence
        """
        log.info("Collection: Preparing to collect")
        self.emit("collectReady", (False,))
        self.emit("collectOscillationStarted", (owner, None, None, None, cp, None))
        self.emit("progressInit", ("Collection", 100, False))

        try:
            # Prepare data collection
            self._pre_execute(cp)
            logging.getLogger("HWR").info("Collection parameters: %s" % str(cp))

            # Create directories and input files for processing, XDS, mossflm etc
            self._create_files_and_directories(cp)
            self._get_sample_info(cp)

            # Store information in LIMS
            self._store_data_collection_in_lims(cp)
            self._store_sample_info_in_lims(cp)

            # if there is no centered position create one based on the current
            # position of the goniometer
            if all(item is None for item in cp["motors"].values()):
                positions = HWR.beamline.diffractometer.get_positions()

                for motor in cp["motors"].keys():
                    cp["motors"][motor] = positions.get(motor)

            # Move to the centered position and take crystal snapshots
            log.info("Collection: Moving to centred position")
            self._move_to_centered_position(cp)
            self._take_crystal_snapshots(cp)
            self._move_to_centered_position(cp)

            # Set beamline parameters, transmission, energy and detector distance
            if "transmission" in cp:
                log.info("Collection: Setting transmission to %.2f", cp["transmission"])
                HWR.beamline.transmission.set_value(cp["transmission"])

            if "wavelength" in cp:
                log.info("Collection: Setting wavelength to %.4f", cp["wavelength"])
                HWR.beamline.energy.set_wavelength(cp["wavelength"])
            elif "energy" in cp:
                log.info("Collection: Setting energy to %.4f", cp["energy"])
                HWR.beamline.energy.set_value(cp["energy"])

            dd0 = cp.get("resolution")

            if dd0 and dd0.get("upper"):
                resolution = dd0["upper"]
                log.info("Collection: Setting resolution to %.3f", resolution)
                HWR.beamline.resolution.set_value(resolution)
            elif "detector_distance" in cp:
                log.info("Collection: Moving detector to %.2f", cp["detector_distance"])
                HWR.beamline.detector.distance.set_value(cp["detector_distance"])

            # Method to be overridden for the actual image acquisition
            self._execute(cp)

            # Update information in LIMS
            self._update_data_collection_in_lims(cp)
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            self._execute_failed(cp, exc_type, exc_value, exc_tb)
        else:
            self._post_execute(cp)
        finally:
            self._post_execute_cleanup()
            self.ready_event.set()

        return cp

    def _pre_execute(self, cp):
        cp.dangerously_set("status", "Running")
        cp.dangerously_set("collection_start_time", time.strftime("%Y-%m-%d %H:%M:%S"))

    @abc.abstractmethod
    def _execute(self, cp):
        """Site specific execution method

        Args:
            cp ([type]): [description]
        """

    def _post_execute(self, cp):
        """Collection finished beahviour"""
        cp.dangerously_set("status", "Data collection successful")

        if cp["experiment_type"] != "Collect - Multiwedge":
            self._update_data_collection_in_lims(cp)

            last_frame = cp["oscillation_sequence"][0]["number_of_images"]
            if last_frame > 1 and cp["experiment_type"] != "Mesh":
                # We do not store first and last frame for mesh
                self._store_image_in_lims(cp, last_frame)
            if (
                cp["experiment_type"] in ("OSC", "Helical")
                and cp["oscillation_sequence"][0]["overlap"] == 0
                and last_frame > 19
            ):
                self.trigger_auto_processing("after", 0)

        self.emit(
            "collectOscillationFinished",
            (
                None,
                True,
                "Data collection successful",
                cp.get("collection_id"),
                None,
                cp,
            ),
        )
        self.emit("progressStop", ())

    def _post_execute_cleanup(self):
        """
        Method called when at end of data collection, successful or not.
        """
        pass
        #self.close_fast_shutter()
        #self.close_safety_shutter()
        #self.close_detector_cover()

    def _execute_failed(self, cp, ex_type, ex_value, ex_stacktrace):
        """Collection failed method"""
        failed_msg = "Data collection failed!\n%s" % ex_value

        cp.dangerously_set("status", "Failed")
        cp.dangerously_set("comments", "%s\n%s" % (failed_msg, self._error_msg))

        self.emit(
            "collectOscillationFailed",
            (None, False, failed_msg, cp.get("collection_id"), None),
        )

        self.emit("progressStop", ())
        self._update_data_collection_in_lims(cp)

    def _create_files_and_directories(self, cp):
        """
        Method create directories for raw files and processing files.
        Directorie names for xds, mosflm and hkl are created
        """
        log.info("Collection: Creating directories for raw images and processing files")

        self.create_directories(
            cp["fileinfo"]["directory"],
            cp["fileinfo"]["process_directory"],
            cp["fileinfo"]["archive_directory"],
        )

        xds_directory, mosflm_directory, hkl2000_directory = self.prepare_input_files(cp)

        if xds_directory:
            cp.dangerously_set("xds_dir", xds_directory)

    def prepare_input_files(self, cp):
        return None, None, None

    def create_directories(self, *args):
        """Creates file directories"""

        for directory in args:
            try:
                os.makedirs(directory)
            except os.error as e:
                if e.errno != errno.EEXIST:
                    raise

    def _get_sample_info(self, cp):
        """Returns sample info

        Args:
            cp (imutable): [description]
        """

        log.info("Getting sample information from lims and sample changer")

        sample_info = cp.get("sample_reference")
        sample_changer = HWR.beamline.sample_changer

        try:
            sample_id = int(sample_info["blSampleId"])
        except Exception:
            sample_id = None

        cp.dangerously_set("blSampleId", sample_id)

        if HWR.beamline.diffractometer.in_plate_mode():
            # TODO store plate location in lims
            pass
        elif sample_changer:
            try:
                basket, vial = sample_changer.get_loaded_sample().get_coords()

                cp.dangerously_set(
                    "actualSampleBarcode", sample_changer.get_loaded_sample().get_id()
                )
                cp.dangerously_set(
                    "actualContainerBarcode",
                    sample_changer.get_loaded_sample().get_container().get_id(),
                )
                cp.dangerously_set("actualSampleSlotInContainer", vial)
                cp.dangerously_set("actualContainerSlotInSC", basket)
            except Exception:
                cp.dangerously_set("actualSampleBarcode", None)
                cp.dangerously_set("actualContainerBarcode", None)
        else:
            cp.dangerously_set("actualSampleBarcode", None)
            cp.dangerously_set("actualContainerBarcode", None)

    def _store_data_collection_in_lims(self, cp):
        """
        Descript. :
        """
        log.info("Collection: Storing data collection in LIMS")

        if HWR.beamline.lims and not cp["in_interleave"]:
            try:
                cp.dangerously_set("synchrotronMode", self.get_machine_fill_mode())
                (collection_id, detector_id) = HWR.beamline.lims.store_data_collection(
                    cp, self.bl_config
                )

                cp.dangerously_set(collection_id, collection_id)

                if detector_id:
                    cp.dangerously_set("detector_id", detector_id)

            except Exception:
                logging.getLogger("HWR").exception(
                    "Could not store data collection in LIMS"
                )

    def _store_sample_info_in_lims(self, cp):
        """
        Descript. :
        """
        log.info("Collect: Storing sample info in LIMS")
        if HWR.beamline.lims and not cp["in_interleave"]:
            HWR.beamline.lims.update_bl_sample(cp)

    def _move_to_centered_position(self, cp):
        """
        Descript. :
        """
        dd0 = HWR.beamline.diffractometer.get_positions()

        logging.getLogger("HWR").debug(
            "MOTORS-premove " + ", ".join("%s:%s" % tt0 for tt0 in sorted(dd0.items()))
        )
        dd0 = cp["motors"]
        logging.getLogger("HWR").debug(
            "MOTORS-target " + ", ".join("%s:%s" % tt0 for tt0 in sorted(dd0.items()))
        )
        positions_str = ""
        for motor, position in cp["motors"].items():
            if position:
                if isinstance(motor, string_types):
                    positions_str += " %s=%f" % (motor, position)
                else:
                    positions_str += " %s=%f" % (motor.get_motor_mnemonic(), position)
        cp["actualCenteringPosition"] = positions_str
        self.move_motors(cp["motors"])
        dd0 = HWR.beamline.diffractometer.get_positions()
        logging.getLogger("HWR").debug(
            "MOTORS-postmove " + ", ".join("%s:%s" % tt0 for tt0 in sorted(dd0.items()))
        )

    def _take_crystal_snapshots(self, cp):
        """
        Descript. :
        """
        number_of_snapshots = cp["take_snapshots"]
        snapshot_directory = cp["fileinfo"]["archive_directory"]
        if number_of_snapshots > 0 or cp.get("take_video"):
            if not os.path.exists(snapshot_directory):
                try:
                    self.create_directories(snapshot_directory)
                except Exception:
                    logging.getLogger("HWR").exception(
                        "Collection: Error creating snapshot directory"
                    )

        if number_of_snapshots > 0 and not cp["in_interleave"]:
            logging.getLogger("user_level_log").info(
                "Collection: Taking %d sample snapshot(s)" % number_of_snapshots
            )
            for snapshot_index in range(number_of_snapshots):
                snapshot_filename = os.path.join(
                    snapshot_directory,
                    "%s_%s_%s.snapshot.jpeg"
                    % (
                        cp["fileinfo"]["prefix"],
                        cp["fileinfo"]["run_number"],
                        (snapshot_index + 1),
                    ),
                )
                cp.dangerously_set(
                    "xtalSnapshotFullPath%i" % (snapshot_index + 1), snapshot_filename
                )
                self._take_crystal_snapshot(snapshot_filename)
                if number_of_snapshots > 1:
                    HWR.beamline.diffractometer.move_omega_relative(90)

        if not HWR.beamline.diffractometer.in_plate_mode() and cp.get("take_video"):
            # Add checkbox to allow enable/disable creation of gif
            logging.getLogger("user_level_log").info("Collection: Saving animated gif")
            animation_filename = os.path.join(
                snapshot_directory,
                "%s_%s_animation.gif"
                % (cp["fileinfo"]["prefix"], cp["fileinfo"]["run_number"]),
            )
            cp.dangerously_set("xtalSnapshotFullPath2", animation_filename)
            self._take_crystal_animation(animation_filename, duration_sec=1)

    def _update_data_collection_in_lims(self, cp):
        """
        Descript. :
        """
        log.info("Collection: Updating data collection in LIMS")

        if HWR.beamline.lims and not cp["in_interleave"]:
            cp.dangerously_set("flux", HWR.beamline.flux.get_value())
            cp.dangerously_set("flux_end", HWR.beamline.flux.get_value())
            cp.dangerously_set("wavelength", HWR.beamline.energy.get_wavelength())
            cp.dangerously_set(
                "detectorDistance", HWR.beamline.detector.distance.get_value()
            )

            cp.dangerously_set("resolution", HWR.beamline.resolution.get_value())
            cp.dangerously_set("transmission", HWR.beamline.transmission.get_value())

            # This is in pix or mm?s
            #beam_centre_x, beam_centre_y = HWR.beamline.detector.get_beam_centre()
            #cp.dangerously_set("xBeam", beam_centre_x)
            #cp.dangerously_set("yBeam", beam_centre_y)

            und = HWR.beamline.energy.get_undulator_gaps()
            i = 1
            for jj in self.bl_config.undulators:
                key = jj.type
                if key in und:
                    cp["undulatorGap%d" % (i)] = und[key]
                    i += 1

            #TODO check if this is used
            #cp.dangerously_set("resolutionAtCorner", HWR.beamline.resolution.get_value())

            beam_size_x, beam_size_y = HWR.beamline.beam.get_beam_size()
            cp.dangerously_set("beamSizeAtSampleX", beam_size_x)
            cp.dangerously_set("beamSizeAtSampleY", beam_size_y)
            cp.dangerously_set("beamShape", HWR.beamline.beam.get_beam_shape())

            try:
                hor_gap, vert_gap = HWR.beamline.beam.slits.get_gaps()
                cp.dangerously_set("slitGapHorizontal", hor_gap)
                cp.dangerously_set("slitGapVertical", vert_gap)
            except BaseException:
                pass

            try:
                HWR.beamline.lims.update_data_collection(cp)
            except Exception:
                logging.getLogger("HWR").exception(
                    "Could not update data collection in LIMS"
                )

    def _store_image_in_lims(self, cp, frame_number, motor_position_id=None):
        """
        Descript. :
        """
        #TODO where to get cryo temp?
        cryo_temp = None

        if HWR.beamline.lims and not cp["in_interleave"]:
            file_location = cp["fileinfo"]["directory"]
            image_file_template = cp["fileinfo"]["template"]
            filename = image_file_template % frame_number
            lims_image = {
                "dataCollectionId": cp.get("collection_id"),
                "fileName": filename,
                "fileLocation": file_location,
                "imageNumber": frame_number,
                "measuredIntensity": HWR.beamline.flux.get_value(),
                "synchrotronCurrent": HWR.beamline.machine_info.get_current(),
                "machineMessage": HWR.beamline.machine_info.get_message(),
                "temperature": cryo_temp,
            }
            archive_directory = cp["fileinfo"]["archive_directory"]
            if archive_directory:
                jpeg_filename = "%s.jpeg" % os.path.splitext(image_file_template)[0]
                thumb_filename = (
                    "%s.thumb.jpeg" % os.path.splitext(image_file_template)[0]
                )
                jpeg_file_template = os.path.join(
                    archive_directory, jpeg_filename
                ).replace("cbf.thumb", "thumb")
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

    def _update_lims_with_workflow(self, cp, workflow_id, grid_snapshot_filename):
        """Updates collection with information about workflow

        :param workflow_id: workflow id
        :type workflow_id: int
        :param grid_snapshot_filename: grid snapshot file path
        :type grid_snapshot_filename: string
        """
        if HWR.beamline.lims is not None:
            try:
                cp.dangerously_set("workflow_id", workflow_id)
                if grid_snapshot_filename:
                    cp.dangerously_set("xtalSnapshotFullPath3", grid_snapshot_filename)
                HWR.beamline.lims.update_data_collection(cp)
            except Exception:
                logging.getLogger("HWR").exception(
                    "Could not store data collection into ISPyB"
                )

    #TODO rename to stop_execute
    def stop_collect(self):
        """
        Stops data collection
        """
        if self._execute_task is not None:
            self._execute_task.kill(block=False)

    def set_helical(self, arg):
        pass

    def set_helical_pos(self, arg):
        pass

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
