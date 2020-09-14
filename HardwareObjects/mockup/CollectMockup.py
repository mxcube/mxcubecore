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

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import os
import time
from HardwareRepository.TaskUtils import task
from HardwareRepository.HardwareObjects.abstract import AbstractCollect
from HardwareRepository import HardwareRepository as HWR


__credits__ = ["MXCuBE collaboration"]


class CollectMockup(AbstractCollect.AbstractCollect):

    def __init__(self, name):
        """

        :param name: name of the object
        :type name: string
        """

        AbstractCollect.AbstractCollect.__init__(self, name)

        self.aborted_by_user = False

    def init(self):
        """Main init method
        """

        AbstractCollect.AbstractCollect.init(self)

        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True,))

    def _execute(self, cp):
        """Main collection hook
        """
        self.emit("collectStarted", (None, 1))
        self.emit("fsmConditionChanged", "data_collection_started", True)
        self._store_image_in_lims(cp, 1)
        number_of_images = cp["oscillation_sequence"][0][
            "number_of_images"
        ]

        for image in range(
            cp["oscillation_sequence"][0]["number_of_images"]
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
                cp["oscillation_sequence"][0]["exposure_time"]
            )
            self.emit("collectImageTaken", image)
            self.emit("progressStep", (int(float(image) / number_of_images * 100)))
        self.emit_collection_finished(cp)

    def emit_collection_finished(self, cp):
        """Collection finished beahviour
        """
        if cp["experiment_type"] != "Collect - Multiwedge":
            self._update_data_collection_in_lims(cp)

            last_frame = cp["oscillation_sequence"][0][
                "number_of_images"
            ]
            if last_frame > 1:
                self._store_image_in_lims(cp, last_frame)
            if (
                cp["experiment_type"] in ("OSC", "Helical")
                and cp["oscillation_sequence"][0]["overlap"]
                == 0
                and last_frame > 19
            ):
                self.trigger_auto_processing(cp, "after", 0)

        success_msg = "Data collection successful"
        cp.dangerously_set("status", success_msg)
        self.emit(
            "collectOscillationFinished",
            (
                None,
                True,
                success_msg,
                cp.get("collection_id"),
                None,
                cp,
            ),
        )
        self.emit("collectEnded", None, success_msg)
        self.emit("collectReady", (True,))
        self.emit("progressStop", ())
        self.emit("fsmConditionChanged", "data_collection_successful", True)
        self.emit("fsmConditionChanged", "data_collection_started", False)
        self._collecting = False
        self.ready_event.set()

    def trigger_auto_processing(self, cp, process_event, frame_number):
        """
        Descript. :
        """
        if HWR.beamline.offline_processing is not None:
            HWR.beamline.offline_processing.execute_autoprocessing(
                process_event,
                cp,
                frame_number,
                self.run_offline_processing,
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
        HWR.beamline.sample_view.save_scene_snapshot(filename)

    @task
    def _take_crystal_animation(self, animation_filename, duration_sec=1):
        """Rotates sample by 360 and composes a gif file
           Animation is saved as the fourth snapshot
        """
        HWR.beamline.sample_view.save_scene_animation(animation_filename, duration_sec)

    @task
    def move_motors(self, motor_position_dict):
        HWR.beamline.diffractometer.move_motors(motor_position_dict)

    def prepare_input_files(self, cp):

        i = 1
        while True:
            xds_input_file_dirname = "xds_%s_%s_%d" % (
                cp["fileinfo"]["prefix"],
                cp["fileinfo"]["run_number"],
                i,
            )
            xds_directory = os.path.join(
                cp["fileinfo"]["process_directory"],
                xds_input_file_dirname,
            )
            if not os.path.exists(xds_directory):
                break
            i += 1

        mosflm_input_file_dirname = "mosflm_%s_run%s_%d" % (
            cp["fileinfo"]["prefix"],
            cp["fileinfo"]["run_number"],
            i,
        )
        mosflm_directory = os.path.join(
            cp["fileinfo"]["process_directory"],
            mosflm_input_file_dirname,
        )

        return xds_directory, mosflm_directory, ""
