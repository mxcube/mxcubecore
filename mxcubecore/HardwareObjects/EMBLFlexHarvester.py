# encoding: utf-8
#
#  Project name: MXCuBE
#  https://github.com/mxcube.
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""FlexHarvester Linux Java implementation of the Flex sample changer for Harvester Use.
Example xml file:
<object class = "EMBLFlexHarvester">
  <username>Sample Changer</username>
  <exporter_address>lid231flex1:9001</exporter_address>
</object>
"""

from __future__ import annotations

import logging
import time
from typing import (
    Any,
    List,
)

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.EMBLFlexHCD import EMBLFlexHCD
from mxcubecore.model import queue_model_objects as qmo
from mxcubecore.queue_entry.base_queue_entry import (
    CENTRING_METHOD,
    QueueExecutionException,
)
from mxcubecore.TaskUtils import task


class EMBLFlexHarvester(EMBLFlexHCD):
    """EMBLFlexHarvester is the Hardware Object interface for the EMBL Flex Sample Changer
    It inherits from EMBLFlexHCD and implements the Harvester interface.
    """

    __TYPE__ = "Flex Sample Changer"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._harvester_hwo = None
        self.pin_cleaning = None
        self._loaded_sample = None

    def init(self):
        self.pin_cleaning = self.get_property("pin_cleaning")

        self._loaded_sample = (-1, -1, -1)
        self._harvester_hwo = self.get_object_by_role("harvester")

        EMBLFlexHCD.init(self)

    def get_room_temperature_mode(self) -> bool:
        """Get the Harvester Room Temperature Mode"""
        return self._execute_cmd_exporter("getRoomTemperatureMode", attribute=True)

    def set_room_temperature_mode(self, value) -> bool:
        """Set the Harvester Room Temperature Mode"""
        self._execute_cmd_exporter("setRoomTemperatureMode", value, command=True)
        logging.getLogger("user_level_log").info(
            "setting Robot Room temperature to %s", value
        )
        return self.get_room_temperature_mode()

    def mount_from_harvester(self):
        """This enable Mounting a sample from Harvester"""
        return True

    def get_sample_list(self) -> List[Any]:
        """
        Get Sample List related to the Harvester content/processing Plan
        """
        sample_list = super().get_sample_list()
        present_sample_list = []

        # Retrieve metadata lists from harvester HWO
        try:
            ha_sample_lists = self._harvester_hwo.get_crystal_uuids()
            ha_sample_names = self._harvester_hwo.get_sample_names()
            ha_sample_states = self._harvester_hwo.get_samples_state()
        except Exception as e:
            self.user_log.error(
                "Failed retrieving sample metadata from Harvester: %s", e
            )
            return present_sample_list

        ha_sample_acronyms = self._harvester_hwo.get_sample_acronyms()

        # If no samples reported by Harvester
        if not ha_sample_lists:
            self.user_log.warning("No samples reported by Harvester")
            return present_sample_list

        # Process each sample independently to avoid global failure
        for index, x_tal_uuid in enumerate(ha_sample_lists):
            sample = sample_list[index]
            img_url = self._harvester_hwo.get_crystal_images_urls(x_tal_uuid)
            img_target_x = self._harvester_hwo.get_image_target_x(x_tal_uuid)
            img_target_y = self._harvester_hwo.get_image_target_y(x_tal_uuid)

            # Enrich sample object in MXCuBE
            sample.id = x_tal_uuid
            sample.container_info = {"state": ha_sample_states[index]}

            sample._set_image_url(img_url)
            sample._set_image_x(img_target_x)
            sample._set_image_y(img_target_y)
            sample._name = ha_sample_names[index]

            # Protein acronym logic (fallback-safe)
            if ha_sample_acronyms and len(ha_sample_acronyms) == len(ha_sample_lists):
                sample.proteinAcronym = ha_sample_acronyms[index]
            else:
                sample.proteinAcronym = (
                    ha_sample_acronyms[0] if ha_sample_acronyms else ""
                )

            present_sample_list.append(sample)

        self.user_log.info("Loaded %d samples from Harvester", len(present_sample_list))
        return present_sample_list

    def _hw_get_mounted_sample(self) -> str:
        """Get the currently mounted sample location string
        Exporter Does not know the loaded sample location
        we get it from our own tracking
        """
        loaded_sample = self._loaded_sample
        return (
            str(loaded_sample[0])
            + ":"
            + str(loaded_sample[1])
            + ":"
            + "%02d" % loaded_sample[2]
        )

    def _hw_get_mounted_crystal_id(self) -> str:
        """Get the currently mounted crystal UUID"""
        return self._execute_cmd_exporter("getMountedCrystalId", attribute=True)

    @task
    def load_a_pin_for_calibration(self):
        """
        Load a Pin from Harvester
        """
        try:
            self.prepare_load()
            self.enable_power()

            load_task = gevent.spawn(
                self._execute_cmd_exporter,
                "loadSampleFromHarvester",
                self.pin_cleaning,
                command=True,
            )

            self._wait_busy(30)
            err_msg = "Timeout while waiting to sample to be loaded"
            with gevent.Timeout(600, RuntimeError(err_msg)):
                while not load_task.ready():
                    logging.getLogger("user_level_log").info("wait loading task")
                    gevent.sleep(2)

            with gevent.Timeout(600, RuntimeError(err_msg)):
                while True:
                    logging.getLogger("user_level_log").info("Wait Robot Safe position")
                    is_safe = self._execute_cmd_exporter(
                        "getRobotIsSafe", attribute=True
                    )
                    if is_safe:
                        break
                    gevent.sleep(2)
            return True
        except RuntimeError:
            return False

    def start_harvester_centring(self):
        try:
            dm = HWR.beamline.diffractometer

            logging.getLogger("user_level_log").info("Start Auto Harvesting Centring")

            computed_offset = HWR.beamline.harvester.get_offsets_for_sample_centering()
            dm.start_harvester_centring(computed_offset)

        except Exception as exc:
            logging.getLogger("user_level_log").exception(
                "Could not center sample, skipping"
            )
            raise QueueExecutionException(
                "Could not center sample, skipping", self
            ) from exc

    def _set_loaded_sample_and_prepare(self, loaded_sample_tup, previous_sample_tup):
        res = False

        loaded_sample = self.get_sample_with_address(loaded_sample_tup)

        if -1 not in loaded_sample_tup and loaded_sample_tup != previous_sample_tup:
            self._set_loaded_sample(loaded_sample)
            self._prepare_centring_task()
            res = True

        if res:
            if not self._harvester_hwo.get_room_temperature_mode():
                self.queue_harvest_next_sample(loaded_sample.get_address())

            # we expect CENTRING_METHOD to be None
            # NB: move this call to base_queue_entry mount_sample and add Harvester Centering METHOD
            HWR.beamline.queue_manager.centring_method = CENTRING_METHOD.NONE
            self.start_harvester_centring()

        return res

    def _do_load(self, sample=None) -> bool:
        """
        Load a Sample from Harvester
        """
        # 1. Initial setup and harvesting
        harvesting_result = self.queue_harvest_sample(sample.get_address())
        if not harvesting_result:
            raise QueueExecutionException("Harvester could not Harvest sample", self)

        self._update_state()
        self._wait_ready(600)

        sample_uuid = self.get_sample_uuid(sample.get_address())
        previous_sample = self._loaded_sample

        # 2. Main loading sequence
        if not self._perform_loading_sequence(sample_uuid):
            return False

        # 3 Finalization
        loaded_sample = (
            sample.get_cell_no(),
            sample.get_basket_no(),
            sample.get_vial_no(),
        )
        # Flex/Exporter Does not know the loaded sample location we keep track of it ourselfs
        self._loaded_sample = loaded_sample
        return self._set_loaded_sample_and_prepare(loaded_sample, previous_sample)

    def _perform_loading_sequence(self, sample_uuid) -> bool:
        """Start loading from harvester"""
        logging.getLogger("user_level_log").info(
            "Start loading from harvester SAMPLE_UUID %s", sample_uuid
        )
        load_task = gevent.spawn(
            self._execute_cmd_exporter,
            sample_uuid,
            self.pin_cleaning,
            command=True,
        )

        # Wait for sample changer to start activity
        try:
            _tt = time.time()
            self._wait_busy(300)
            logging.getLogger("HWR").info("Waited SC activity %s", time.time() - _tt)
        except Exception:
            logging.getLogger("user_level_log").error(
                "ERROR While Waited SC activity to start"
            )
            for msg in self.get_robot_exceptions():
                logging.getLogger("user_level_log").error(msg)
            raise

        #  Wait for sample to be loaded
        err_msg = "Timeout while waiting to sample to be loaded"
        try:
            with gevent.Timeout(600, RuntimeError(err_msg)):
                while not load_task.ready():
                    logging.getLogger("user_level_log").info("Wait loading task")
                    loaded_sample = self._hw_get_mounted_crystal_id()
                    if loaded_sample == sample_uuid:
                        break
                    gevent.sleep(2)
        except RuntimeError:
            logging.getLogger("user_level_log").error(err_msg)
            return False

        return self._finalize_loading_sequence()

    def _finalize_loading_sequence(self) -> bool:
        """Finalize loading sequence"""
        #  Wait for robot to be in safe state
        err_msg = "Timeout while waiting for robot to be in safe state"
        try:
            with gevent.Timeout(600, RuntimeError(err_msg)):
                while True:
                    is_safe = self._execute_cmd_exporter(
                        "getRobotIsSafe", attribute=True
                    )
                    if is_safe:
                        break
                    gevent.sleep(2)
        except RuntimeError:
            logging.getLogger("user_level_log").error(err_msg)
            return False

        # Check for robot exceptions
        for msg in self.get_robot_exceptions():
            if msg is not None and "Pin Cleaning Station" not in msg:
                logging.getLogger("user_level_log").error(
                    "ERROR While SC activity After Loaded Sample"
                )
                logging.getLogger("HWR").error(msg)
                logging.getLogger("user_level_log").error(msg)
                return False

        return True

    def harvest_and_mount_sample(self, xtal_uuid: str, sample) -> bool:
        """
        return (Bool) : whether the crystal has been Harvest then mount

        """
        try:
            self._harvester_hwo.harvest_crystal(xtal_uuid)
            self._harvester_hwo._wait_sample_transfer_ready(None)

            self._do_load(sample)
        except Exception:
            logging.getLogger("user_level_log").exception("Could not Harvest Crystal")
            return "Could not Harvest Crystal"

    def queue_list(self) -> List[str]:
        """
        builds a List representation of the queue based.
        """

        node = HWR.beamline.queue_model.get_model_root()

        result = []

        if isinstance(node, List):
            node_list = node
        else:
            node_list = node.get_children()

        for node in node_list:
            if isinstance(node, qmo.Sample):
                result.append(node.loc_str)

        return result

    def get_sample_uuid(self, sample_loc_str: str) -> str | None:
        """
        Get Sample UUID of the sample_loc_str from Sample List
        """
        samples_list = self.get_sample_list()
        sample_uuid = None
        for s in samples_list:
            # it seems get_id() was broken
            if s.get_address() == sample_loc_str or s.id == sample_loc_str:
                sample_uuid = s.id

                return sample_uuid
        return sample_uuid

    def queue_harvest_sample(self, sample_loc_str: str) -> bool:
        """
        While queue execution send harvest request
        """
        current_queue = self.queue_list()

        sample_uuid = self.get_sample_uuid(sample_loc_str)

        return self._harvester_hwo.queue_harvest_sample(
            sample_loc_str, sample_uuid, current_queue
        )

    def queue_harvest_next_sample(self, sample_loc_str) -> None:
        """
        While queue execution send harvest request
        on next sample of the queue list
        """

        current_queue_list = self.queue_list()

        next_sample = None
        try:
            next_sample = current_queue_list[
                current_queue_list.index(sample_loc_str) + 1
            ]
        except (ValueError, IndexError):
            next_sample = None

        sample_uuid = self.get_sample_uuid(next_sample)

        self._harvester_hwo.queue_harvest_next_sample(next_sample, sample_uuid)
