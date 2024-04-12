# encoding: utf-8
#
#  Project: MXCuBE
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
import time
import logging
import gevent

from mxcubecore.TaskUtils import task

from mxcubecore.HardwareObjects import EMBLFlexHCD


class EMBLFlexHarvester(EMBLFlexHCD):
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

    def get_room_temperature_mode(self):
        return self._execute_cmd_exporter("getRoomTemperatureMode", attribute=True)

    def set_room_temperature_mode(self, value):
        self._execute_cmd_exporter("setRoomTemperatureMode", value, command=True)
        logging.getLogger("user_level_log").info(
            f"setting Robot Room temperature to {value}"
        )
        return self.get_room_temperature_mode()

    def mount_from_harvester(self):
        return True

    def get_sample_list(self) -> list:
        """
        Get Sample List related to the Harvester content/processing Plan
        """
        sample_list = super().get_sample_list()
        present_sample_list = []
        ha_sample_lists = self._harvester_hwo.get_crystal_uuids()
        ha_sample_names = self._harvester_hwo.get_sample_names()
        ha_sample_acronyms = self._harvester_hwo.get_sample_acronyms()

        if ha_sample_lists:
            for i in range(len(ha_sample_lists)):
                sample = sample_list[i]
                sample.id = ha_sample_lists[i]
                sample._name = ha_sample_names[i]
                # if all sample come with proteinAcronym
                if len(ha_sample_acronyms) > 0 and len(ha_sample_acronyms) == len(
                    ha_sample_lists
                ):
                    sample.proteinAcronym = ha_sample_acronyms[i]
                else:
                    # if all sample does not have proteinAcronym
                    # we set first proteinAcronym to all if exist at least one
                    sample.proteinAcronym = (
                        ha_sample_acronyms[0] if len(ha_sample_acronyms) > 0 else ""
                    )
                present_sample_list.append(sample)

        return present_sample_list

    def _hw_get_mounted_sample(self) -> str:
        loaded_sample = self._loaded_sample
        return (
            str(loaded_sample[0])
            + ":"
            + str(loaded_sample[1])
            + ":"
            + "%02d" % loaded_sample[2]
        )

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
                    gevent.sleep(2)

            with gevent.Timeout(600, RuntimeError(err_msg)):
                while True:
                    is_safe = self._execute_cmd_exporter(
                        "getRobotIsSafe", attribute=True
                    )
                    if is_safe:
                        break
                    gevent.sleep(2)
            return True
        except Exception:
            return False

    def _do_load(self, sample=None):
        """
        Load a Sample from Harvester
        """
        self._update_state()

        # We wait for the sample changer if its already doing something, like defreezing
        # wait for 10 minutes then timeout !
        self._wait_ready(600)

        previous_sample = self._loaded_sample
        # Start loading from harvester
        load_task = gevent.spawn(
            self._execute_cmd_exporter,
            "loadSampleFromHarvester",
            self.pin_cleaning,
            command=True,
        )

        # Wait for sample changer to start activity
        try:
            _tt = time.time()
            self._wait_busy(300)
            logging.getLogger("HWR").info(f"Waited SC activity {time.time() - _tt}")
        except Exception:
            logging.getLogger("user_level_log").error(
                "ERROR While Waited SC activity to start"
            )
            for msg in self.get_robot_exceptions():
                logging.getLogger("user_level_log").error(msg)
            raise

        # Wait for the sample to be loaded, (put on the goniometer)
        err_msg = "Timeout while waiting to sample to be loaded"
        with gevent.Timeout(600, RuntimeError(err_msg)):
            while not load_task.ready():
                gevent.sleep(2)

        with gevent.Timeout(600, RuntimeError(err_msg)):
            while True:
                is_safe = self._execute_cmd_exporter("getRobotIsSafe", attribute=True)

                if is_safe:
                    break

                gevent.sleep(2)

        for msg in self.get_robot_exceptions():
            if msg is not None:
                logging.getLogger("user_level_log").error(
                    "ERROR While SC activity After Loaded Sample "
                )
                logging.getLogger("HWR").error(msg)
                logging.getLogger("user_level_log").error(msg)
                # Temp: In Harvester mode any robot Exception is consider as Loading failed
                # Except Pin Cleaning Station Exception
                if "Pin Cleaning Station" not in msg:
                    return False

        loaded_sample = (
            sample.get_cell_no(),
            sample.get_basket_no(),
            sample.get_vial_no(),
        )
        self._loaded_sample = loaded_sample

        return self._set_loaded_sample_and_prepare(loaded_sample, previous_sample)
