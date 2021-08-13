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

"""EMBLCollect - defines osc, helical and mesh collections"""

import os

from mxcubecore.TaskUtils import task
from mxcubecore.HardwareObjects.abstract.AbstractCollect import AbstractCollect

from mxcubecore import HardwareRepository as HWR


__credits__ = ["EMBL Hamburg"]
__category__ = "General"


class EMBLCollect(AbstractCollect):
    """Main data collection class. Inherited from AbstractCollect.
       Collection is done by setting collection parameters and
       executing collect command
    """

    def __init__(self, name):

        AbstractCollect.__init__(self, name)
        self._previous_collect_status = None
        self._actual_collect_status = None

        self._collect_frame = None
        self._exp_type_dict = {}
        self.break_bragg_released = False

        self.aborted_by_user = None
        self.run_autoprocessing = None

        self.chan_collect_status = None
        self.chan_collect_frame = None
        self.chan_collect_error = None
        self.chan_undulator_gap = None

        self.cmd_collect_compression = None
        self.cmd_collect_description = None
        self.cmd_collect_detector = None
        self.cmd_collect_directory = None
        self.cmd_collect_energy = None
        self.cmd_collect_exposure_time = None
        self.cmd_collect_helical_position = None
        self.cmd_collect_in_queue = None
        self.cmd_collect_images_per_trigger = None
        self.cmd_collect_num_images = None
        self.cmd_collect_overlap = None
        self.cmd_collect_processing = None
        self.cmd_collect_range = None
        self.cmd_collect_raster_lines = None
        self.cmd_collect_raster_range = None
        self.cmd_collect_resolution = None
        self.cmd_collect_scan_type = None
        self.cmd_collect_shutter = None
        self.cmd_collect_shutterless = None
        self.cmd_collect_start_angle = None
        self.cmd_collect_start_image = None
        self.cmd_collect_template = None
        self.cmd_collect_transmission = None
        self.cmd_collect_space_group = None
        self.cmd_collect_unit_cell = None
        self.cmd_collect_start = None
        self.cmd_collect_abort = None
        self.cmd_collect_xds_data_range = None

    def init(self):
        """Main init method"""

        AbstractCollect.init(self)

        self._exp_type_dict = {"Mesh": "raster", "Helical": "Helical"}

        self.chan_collect_status = self.get_channel_object("collectStatus")
        self._actual_collect_status = self.chan_collect_status.get_value()
        self.chan_collect_status.connect_signal("update", self.collect_status_update)
        self.chan_collect_frame = self.get_channel_object("collectFrame")
        self.chan_collect_frame.connect_signal("update", self.collect_frame_update)
        self.chan_collect_error = self.get_channel_object("collectError")
        self.chan_collect_error.connect_signal("update", self.collect_error_update)
        self.cmd_collect_compression = self.get_command_object("collectCompression")
        self.cmd_collect_description = self.get_command_object("collectDescription")
        self.cmd_collect_detector = self.get_command_object("collectDetector")
        self.cmd_collect_directory = self.get_command_object("collectDirectory")
        self.cmd_collect_energy = self.get_command_object("collectEnergy")
        self.cmd_collect_exposure_time = self.get_command_object("collectExposureTime")
        self.cmd_collect_images_per_trigger = self.get_command_object(
            "collectImagesPerTrigger"
        )
        self.cmd_collect_helical_position = self.get_command_object(
            "collectHelicalPosition"
        )
        self.cmd_collect_in_queue = self.get_command_object("collectInQueue")
        self.cmd_collect_num_images = self.get_command_object("collectNumImages")
        self.cmd_collect_overlap = self.get_command_object("collectOverlap")
        self.cmd_collect_processing = self.get_command_object("collectProcessing")
        self.cmd_collect_range = self.get_command_object("collectRange")
        self.cmd_collect_raster_lines = self.get_command_object("collectRasterLines")
        self.cmd_collect_raster_range = self.get_command_object("collectRasterRange")
        self.cmd_collect_resolution = self.get_command_object("collectResolution")
        self.cmd_collect_scan_type = self.get_command_object("collectScanType")
        self.cmd_collect_shutter = self.get_command_object("collectShutter")
        self.cmd_collect_shutterless = self.get_command_object("collectShutterless")
        self.cmd_collect_start_angle = self.get_command_object("collectStartAngle")
        self.cmd_collect_start_image = self.get_command_object("collectStartImage")
        self.cmd_collect_template = self.get_command_object("collectTemplate")
        self.cmd_collect_transmission = self.get_command_object("collectTransmission")
        self.cmd_collect_space_group = self.get_command_object("collectSpaceGroup")
        self.cmd_collect_unit_cell = self.get_command_object("collectUnitCell")
        self.cmd_collect_xds_data_range = self.get_command_object("collectXdsDataRange")

        self.cmd_collect_nexp_frame = self.get_command_object("collectImagesPerTrigger")

        self.cmd_collect_start = self.get_command_object("collectStart")
        self.cmd_collect_abort = self.get_command_object("collectAbort")

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True,))

    def data_collection_hook(self):
        """Main collection hook"""

        if self.aborted_by_user:
            self.collection_failed("Aborted by user")
            self.aborted_by_user = False
            return

        if self._actual_collect_status in [
            "ready",
            "unknown",
            "error",
            "not available",
        ]:
            HWR.beamline.diffractometer.save_centring_positions()
            comment = "Comment: %s" % str(
                self.current_dc_parameters.get("comments", "")
            )
            self._error_msg = ""
            self._collecting = True
            self._collect_frame = None

            osc_seq = self.current_dc_parameters["oscillation_sequence"][0]
            file_info = self.current_dc_parameters["fileinfo"]
            sample_ref = self.current_dc_parameters["sample_reference"]

            if HWR.beamline.image_tracking is not None:
                HWR.beamline.image_tracking.set_image_tracking_state(True)

            if self.cmd_collect_compression is not None:
                self.cmd_collect_compression(file_info["compression"])

            self.cmd_collect_description(comment)
            self.cmd_collect_detector(HWR.beamline.detector.get_collect_name())
            self.cmd_collect_directory(str(file_info["directory"]))
            self.cmd_collect_exposure_time(osc_seq["exposure_time"])
            self.cmd_collect_in_queue(self.current_dc_parameters["in_queue"] != False)
            self.cmd_collect_nexp_frame(1)
            self.cmd_collect_overlap(osc_seq["overlap"])

            shutter_name = HWR.beamline.detector.get_shutter_name()
            if shutter_name is not None:
                self.cmd_collect_shutter(shutter_name)

            if osc_seq["overlap"] == 0:
                self.cmd_collect_shutterless(1)
            else:
                self.cmd_collect_shutterless(0)

            self.cmd_collect_range(osc_seq["range"])
            if self.current_dc_parameters["experiment_type"] != "Mesh":
                self.cmd_collect_num_images(osc_seq["number_of_images"])

            if self.cmd_collect_processing is not None:
                self.cmd_collect_processing(True)
                # GB 2019030: no idea why this could be unset.....
                #    self.current_dc_parameters["processing_parallel"]
                #    in (True, "MeshScan", "XrayCentering")
                #

            #if self.current_dc_parameters["processing_online"] is False:
            #    self.cmd_collect_processing(False)

            # GB 2018-05-16 : Workaround a fuzzy mesh scan interface of MD3
            # if self.current_dc_parameters['experiment_type'] == 'Mesh':
            #   _do_start = osc_seq['start'] - 0.5 * osc_seq['range']*
            # osc_seq['number_of_images']/float(osc_seq['number_of_lines'])
            #   print _do_start, ' Here'
            # else:
            #   _do_start = osc_seq['start']

            self.cmd_collect_start_angle(osc_seq["start"])
            # self.cmd_collect_start_angle(_do_start)

            self.cmd_collect_start_image(osc_seq["start_image_number"])
            self.cmd_collect_template(str(file_info["template"]))
            space_group = str(sample_ref["spacegroup"])
            if len(space_group) == 0:
                space_group = " "
            self.cmd_collect_space_group(space_group)
            unit_cell = list(eval(sample_ref["cell"]))
            self.cmd_collect_unit_cell(unit_cell)

            if self.current_dc_parameters["experiment_type"] == "OSC":
                xds_range = (
                    osc_seq["start_image_number"],
                    osc_seq["start_image_number"] + osc_seq["number_of_images"] - 1,
                )
                self.cmd_collect_xds_data_range(xds_range)
            elif (
                self.current_dc_parameters["experiment_type"] == "Collect - Multiwedge"
            ):
                xds_range = self.current_dc_parameters["in_interleave"]
                self.cmd_collect_xds_data_range(xds_range)

            if osc_seq["num_triggers"] and osc_seq["num_images_per_trigger"]:
                self.cmd_collect_scan_type("still")
                self.cmd_collect_images_per_trigger(osc_seq["num_images_per_trigger"])
            else:
                self.cmd_collect_scan_type(
                    self._exp_type_dict.get(
                        self.current_dc_parameters["experiment_type"], "OSC"
                    )
                )
            self.cmd_collect_start()
        else:
            self.collection_failed(
                "Unable to start collection. "
                + "Detector server is in %s state" % self._actual_collect_status
            )

    def collect_status_update(self, status):
        """Status event that controls execution

        :param status: collection status
        :type status: string
        """
        if status != self._actual_collect_status:
            self._previous_collect_status = self._actual_collect_status
            self._actual_collect_status = status
            if self._collecting:
                if self._actual_collect_status == "error":
                    self.collection_failed()
                elif self._actual_collect_status == "collecting":
                    self.store_image_in_lims_by_frame_num(1)
                if self._previous_collect_status is None:
                    if self._actual_collect_status == "busy":
                        self.print_log("HWR", "info", "Collection: Preparing ...")
                elif self._previous_collect_status == "busy":
                    if self._actual_collect_status == "collecting":
                        self.emit("collectStarted", (None, 1))
                elif self._previous_collect_status == "collecting":
                    if self._actual_collect_status == "ready":
                        self.collection_finished()
                    elif self._actual_collect_status == "aborting":
                        self.print_log("HWR", "info", "Collection: Aborting...")
                        self.collection_failed()

    def collect_error_update(self, error_msg):
        """Collect error behaviour

        :param error_msg: error message
        :type error_msg: string
        """

        if self._collecting and len(error_msg) > 0:
            self._error_msg = error_msg
            self.print_log(
                "GUI", "error", "Collection: Error from detector server: %s" % error_msg
            )

    def collection_finished(self):
        """Additionaly sets break bragg if it was previously released"""
        AbstractCollect.collection_finished(self)
        if (
            self.current_dc_parameters["in_queue"] is False
            and self.break_bragg_released
        ):
            self.break_bragg_released = False
            HWR.beamline.energy.set_break_bragg()

    def collect_frame_update(self, frame):
        """Image frame update

        :param frame: frame num
        :type frame: int
        """
        if self._collecting:
            if self.current_dc_parameters["in_interleave"]:
                number_of_images = self.current_dc_parameters["in_interleave"][1]
            else:
                number_of_images = self.current_dc_parameters["oscillation_sequence"][
                    0
                ]["number_of_images"]
            if self._collect_frame != frame:
                self._collect_frame = frame
                self.emit("progressStep", (int(float(frame) / number_of_images * 100)))
                self.emit("collectImageTaken", frame)

    def store_image_in_lims_by_frame_num(self, frame_number):
        """Store image in lims

        :param frame: dict with frame parameters
        :type frame: dict
        :param motor_position_id: position id
        :type motor_position_id: int
        """
        self.trigger_auto_processing("image", frame_number)
        return self.store_image_in_lims(frame_number)

    def trigger_auto_processing(self, process_event, frame_number):
        """Starts autoprocessing"""
        HWR.beamline.offline_processing.execute_autoprocessing(
            process_event,
            self.current_dc_parameters,
            frame_number,
            self.current_dc_parameters["processing_offline"],
        )

    def stop_collect(self):
        """Stops collect"""

        AbstractCollect.stop_collect(self)

        self.cmd_collect_abort()
        HWR.beamline.detector.close_cover()

    def set_helical_pos(self, arg):
        """Sets helical positions
           8 floats describe:
             p1AlignmY, p1AlignmZ, p1CentrX, p1CentrY
             p2AlignmY, p2AlignmZ, p2CentrX, p2CentrY
        """
        helical_positions = [
            arg["1"]["phiy"],
            arg["1"]["phiz"],
            arg["1"]["sampx"],
            arg["1"]["sampy"],
            arg["2"]["phiy"],
            arg["2"]["phiz"],
            arg["2"]["sampx"],
            arg["2"]["sampy"],
        ]
        self.cmd_collect_helical_position(helical_positions)

    def set_mesh_scan_parameters(
        self, num_lines, num_total_frames, mesh_center, mesh_range
    ):
        """Sets mesh parameters"""
        self.cmd_collect_raster_lines(num_lines)
        self.cmd_collect_num_images(num_total_frames / num_lines)
        # GB collection server interface assumes the order: fast, slow for mesh
        # range. Need reversal at P14:
        if HWR.beamline.session.beamline_name == "P13":
            self.cmd_collect_raster_range(mesh_range)
        else:
            self.cmd_collect_raster_range(mesh_range[::-1])

    @task
    def _take_crystal_snapshot(self, snapshot_filename):
        """Saves crystal snapshot"""
        HWR.beamline.sample_view.save_scene_snapshot(snapshot_filename)

    @task
    def _take_crystal_animation(self, animation_filename, duration_sec=1):
        """Rotates sample by 360 and composes a gif file
           Animation is saved as the fourth snapshot
        """

        HWR.beamline.sample_view.save_scene_animation(animation_filename, duration_sec)

    # def set_energy(self, value):
    #     """Sets energy"""
    #     """
    #     if abs(value - self.get_energy()) > 0.005 and not self.break_bragg_released:
    #         self.break_bragg_released = True
    #         if hasattr(HWR.beamline.energy, "release_break_bragg"):
    #             HWR.beamline.energy.release_break_bragg()
    #         self.cmd_collect_energy(value * 1000.0)
    #     else:
    #     """
    #     self.cmd_collect_energy(self.get_energy() * 1000)

    def set_resolution(self, value):
         """Sets resolution in A"""
         if not value:
             value = self.get_resolution()
         self.cmd_collect_resolution(value)

    def set_transmission(self, value):
         """Sets transmission in %"""
         self.cmd_collect_transmission(value)

    @task
    def move_motors(self, motor_position_dict):
        """Move to centred position"""
        HWR.beamline.diffractometer.move_motors(motor_position_dict)

    def prepare_input_files(self):
        """Prepares xds directory"""
        i = 1
        while True:
            xds_input_file_dirname = "xds_%s_%s_%d" % (
                self.current_dc_parameters["fileinfo"]["prefix"],
                self.current_dc_parameters["fileinfo"]["run_number"],
                i,
            )
            xds_directory = os.path.join(
                self.current_dc_parameters["fileinfo"]["process_directory"],
                xds_input_file_dirname,
            )
            if not os.path.exists(xds_directory):
                break
            i += 1

        self.current_dc_parameters["xds_dir"] = xds_directory

        return xds_directory, ""

    def get_undulators_gaps(self):
        """Return triplet with gaps. In our case we have one gap,
        """
        und_gaps = {}
        if self.chan_undulator_gap:
            und_gaps = self.chan_undulator_gap.get_value()
            if not isinstance(und_gaps, (list, tuple)):
                und_gaps = list(und_gaps)
        return und_gaps

    def get_machine_current(self):
        """Returns flux"""
        return HWR.beamline.machine_info.get_current()

    def get_machine_message(self):
        """Returns machine message"""
        return HWR.beamline.machine_info.get_message()

    def get_machine_fill_mode(self):
        """Returns machine filling mode"""
        fill_mode = str(HWR.beamline.machine_info.get_message())
        return fill_mode[:20]

    def get_beamline_configuration(self, *args):
        """Returns beamline config"""
        return self.bl_config._asdict()

    def get_total_absorbed_dose(self):
        return float("%.3e" % HWR.beamline.flux.get_value())

    def set_run_autoprocessing(self, status):
        """Enables or disables autoprocessing after a collection"""
        self.run_autoprocessing = status

    def create_file_directories(self):
        self.prepare_input_files()
