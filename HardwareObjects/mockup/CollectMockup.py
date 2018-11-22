#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import os
import time
import logging
import gevent
from HardwareRepository.TaskUtils import task
from AbstractCollect import AbstractCollect


__credits__ = ["MXCuBE colaboration"]


class CollectMockup(AbstractCollect):
    """
    """

    def __init__(self, name):
        """

        :param name: name of the object
        :type name: string
        """

        AbstractCollect.__init__(self, name)

        self.aborted_by_user = False
        self.graphics_manager_hwobj = None

    def init(self):
        """Main init method
        """

        AbstractCollect.init(self)

        self.graphics_manager_hwobj = self.getObjectByRole("graphics_manager")

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True,))

    def data_collection_hook(self):
        """Main collection hook
        """
        self.emit("collectStarted", (None, 1))
        self.emit("fsmConditionChanged", "data_collection_started", True)
        self.store_image_in_lims_by_frame_num(1)
        number_of_images = self.current_dc_parameters["oscillation_sequence"][0][
            "number_of_images"
        ]
        for image in range(
            self.current_dc_parameters["oscillation_sequence"][0]["number_of_images"]
        ):
            if self.aborted_by_user:
                self.ready_event.set()
                self.aborted_by_user = False
                return

            # Uncomment to test collection failed
            # if image == 5:
            #    self.emit("collectOscillationFailed", (self.owner, False,
            #       "Failed on 5", self.current_dc_parameters.get("collection_id")))
            #    self.ready_event.set()
            #    return

            time.sleep(
                self.current_dc_parameters["oscillation_sequence"][0]["exposure_time"]
            )
            self.emit("collectImageTaken", image)
            self.emit("progressStep", (int(float(image) / number_of_images * 100)))
        self.emit_collection_finished()

    def emit_collection_finished(self):
        """Collection finished beahviour
        """
        if self.current_dc_parameters["experiment_type"] != "Collect - Multiwedge":
            self.update_data_collection_in_lims()

            last_frame = self.current_dc_parameters["oscillation_sequence"][0][
                "number_of_images"
            ]
            if last_frame > 1:
                self.store_image_in_lims_by_frame_num(last_frame)
            if (
                self.current_dc_parameters["experiment_type"] in ("OSC", "Helical")
                and self.current_dc_parameters["oscillation_sequence"][0]["overlap"]
                == 0
                and last_frame > 19
            ):
                self.trigger_auto_processing("after", self.current_dc_parameters, 0)

        success_msg = "Data collection successful"
        self.current_dc_parameters["status"] = success_msg
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
        self.emit("collectEnded", None, success_msg)
        self.emit("collectReady", (True,))
        self.emit("progressStop", ())
        self.emit("fsmConditionChanged", "data_collection_successful", True)
        self.emit("fsmConditionChanged", "data_collection_started", False)
        self._collecting = False
        self.ready_event.set()

    def store_image_in_lims_by_frame_num(self, frame, motor_position_id=None):
        """
        Descript. :
        """
        self.trigger_auto_processing("image", self.current_dc_parameters, frame)
        image_id = self.store_image_in_lims(frame)
        return image_id

    def trigger_auto_processing(self, process_event, params_dict, frame_number):
        """
        Descript. : 
        """
        if self.autoprocessing_hwobj is not None:
            self.autoprocessing_hwobj.execute_autoprocessing(
                process_event,
                self.current_dc_parameters,
                frame_number,
                self.run_processing_after,
            )

    def stopCollect(self, owner="MXCuBE"):
        """
        Descript. :
        """
        self.aborted_by_user = True
        self.cmd_collect_abort()
        self.emit_collection_failed("Aborted by user")

    @task
    def _take_crystal_snapshot(self, filename):
        self.graphics_manager_hwobj.save_scene_snapshot(filename)

    @task
    def _take_crystal_animation(self, animation_filename, duration_sec=1):
        """Rotates sample by 360 and composes a gif file
           Animation is saved as the fourth snapshot
        """
        self.graphics_manager_hwobj.save_scene_animation(
            animation_filename, duration_sec
        )

    # @task
    # def move_motors(self, motor_position_dict):
    #     """
    #     Descript. :
    #     """
    #     return

    @task
    def move_motors(self, motor_position_dict):
        # TODO We copy, as dictionary is reset in move_motors. CLEAR UP!!
        # TODO clear up this confusion between move_motors and moveMotors
        self.diffractometer_hwobj.move_motors(motor_position_dict.copy())

    def prepare_input_files(self):
        """
        Descript. : 
        """
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

        mosflm_input_file_dirname = "mosflm_%s_run%s_%d" % (
            self.current_dc_parameters["fileinfo"]["prefix"],
            self.current_dc_parameters["fileinfo"]["run_number"],
            i,
        )
        mosflm_directory = os.path.join(
            self.current_dc_parameters["fileinfo"]["process_directory"],
            mosflm_input_file_dirname,
        )

        return xds_directory, mosflm_directory, ""

    # rhfogh Added to improve interaction with UI and persistence of values
    def set_wavelength(self, wavelength):
        self.energy_hwobj.move_wavelength(wavelength)

    def set_energy(self, energy):
        self.energy_hwobj.move_energy(energy)

    def set_resolution(self, new_resolution):
        self.resolution_hwobj.move(new_resolution)

    def set_transmission(self, transmission):
        self.transmission_hwobj.set_value(transmission)

    def move_detector(self, detector_distance):
        self.detector_hwobj.set_distance(detector_distance)
