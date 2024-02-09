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

"""FlexHCD Linux Java implementation of sample changer.
Example xml file:
<object class = "EMBLFlexHCD">
  <username>Sample Changer</username>
  <exporter_address>lid231flex1:9001</exporter_address>
  <object role="controller" href="/bliss"/>
  <puck_configuration>["SC3", "UNI", "SC3", "UNI", "UNI", "UNI", "UNI", "UNI"]<
/puck_configuration>
</object>
"""
import time
import ast
import base64
import pickle
import logging
import gevent

from mxcubecore import HardwareRepository as HWR

from mxcubecore.TaskUtils import task
from mxcubecore.HardwareObjects.abstract.AbstractSampleChanger import (
    SampleChanger,
    SampleChangerState,
)
from mxcubecore.HardwareObjects.abstract.sample_changer.Container import (
    Container,
    Sample,
)
from PyTango.gevent import DeviceProxy


class Pin(Sample):
    def __init__(self, basket, cell_no, basket_no, sample_no):
        super(Pin, self).__init__(
            basket, Pin.get_sample_address(cell_no, basket_no, sample_no), True
        )
        self._set_holder_length(22.0)
        self.present = True

    def get_basket_no(self):
        return self.get_container().get_index() + 1

    def get_vial_no(self):
        return self.get_index() + 1

    def get_cell_no(self):
        return self.get_container().get_container().get_index() + 1

    def get_cell(self):
        return self.get_container().get_container()

    @staticmethod
    def get_sample_address(cell_number, basket_number, sample_number):
        return (
            str(cell_number) + ":" + str(basket_number) + ":" + "%02d" % sample_number
        )


class Basket(Container):
    __TYPE__ = "Puck"

    def __init__(self, container, cell_no, basket_no, unipuck=False):
        super(Basket, self).__init__(
            self.__TYPE__,
            container,
            Basket.get_basket_address(cell_no, basket_no),
            True,
        )
        for i in range(16 if unipuck else 10):
            slot = Pin(self, cell_no, basket_no, i + 1)
            self._add_component(slot)
        self.present = True

    @staticmethod
    def get_basket_address(cell_number, basket_number):
        return str(cell_number) + ":" + str(basket_number)

    def get_cell_no(self):
        return self.get_container().get_index() + 1

    def get_cell(self):
        return self.get_container()

    def clear_info(self):
        self.get_container()._reset_basket_info(self.get_index() + 1)
        self.get_container()._trigger_info_changed_event()


class Cell(Container):
    __TYPE__ = "Cell"

    def __init__(self, container, number, puck_type="SC3"):
        super(Cell, self).__init__(
            self.__TYPE__, container, Cell.get_cell_address(number), True
        )
        self.present = True

        if puck_type == "SC3":
            for i in range(3):
                self._add_component(Basket(self, number, i + 1, unipuck=False))
        else:
            for i in range(3):
                self._add_component(Basket(self, number, i + 1, unipuck=True))

    @staticmethod
    def get_cell_address(cell_number):
        return str(cell_number)

    def _reset_basket_info(self, basket_no):
        pass

    def clear_info(self):
        self.get_container()._reset_cell_info(self.get_index() + 1)
        self.get_container()._trigger_info_changed_event()

    def get_cell(self):
        return self


class EMBLFlexHCD(SampleChanger):
    __TYPE__ = "Flex Sample Changer"

    def __init__(self, *args, **kwargs):
        super(EMBLFlexHCD, self).__init__(self.__TYPE__, True, *args, **kwargs)

    def init(self):
        _pucks = '["UNI", "UNI", "UNI", "UNI", "UNI", "UNI", "UNI", "UNI"]'
        pucks = ast.literal_eval(self.get_property("puck_configuration", _pucks))

        for i in range(8):
            cell = Cell(self, i + 1, pucks[i])
            self._add_component(cell)

        self.robot = self.get_property("tango_device")
        if self.robot:
            self.robot = DeviceProxy(self.robot)

        self.exporter_addr = self.get_property("exporter_address")

        self.swstate_attr = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "swstate",
            },
            "State",
        )

        self.controller = self.get_object_by_role("controller")
        self.prepareLoad = self.get_command_object("moveToLoadingPosition")
        self.timeout = 3
        self.gripper_types = {
            -1: "No Gripper",
            1: "UNIPUCK",
            2: "MINISPINE",
            3: "FLIPPING",
            4: "UNIPUCK_DOUBLE",
            5: "PLATE",
        }

        SampleChanger.init(self)
        # self._set_state(SampleChangerState.Disabled)
        self._update_selection()
        self.state = self._read_state()

    def get_sample_list(self):
        sample_list = super().get_sample_list()

        sc_present_sample_list = self._execute_cmd_exporter(
            "getPresentSamples", attribute=True
        )

        if sc_present_sample_list:
            sc_present_sample_list = sc_present_sample_list.split(":")
        else:
            sc_present_sample_list = []

        present_sample_list = []

        for sample in sample_list:
            for present_sample_str in sc_present_sample_list:
                present_sample = present_sample_str.split(",")
                if sample.get_address() == (
                    str(present_sample[0])
                    + ":"
                    + str(present_sample[1])
                    + ":"
                    + "%02d" % int(present_sample[4])
                ):
                    present_sample_list.append(sample)

        return present_sample_list

    @task
    def prepare_load(self):
        if self.controller:
            self.controller.hutch_actions(enter=True, hutch_trigger=True)
        else:
            self.prepareLoad()

    @task
    def _prepare_centring_task(self):
        if self.controller:
            self.controller.hutch_actions(enter=False, sc_loading=True)
        else:
            gevent.sleep(2)
            self.get_command_object("unlockMinidiffMotors")(wait=True)
            self.get_command_object("prepareCentring")(wait=True)

    def prepare_centring(self):
        self._prepare_centring_task()

    def get_sample_properties(self):
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)

    def get_basket_list(self):
        basket_list = []
        # put here only the baskets that exist, not all the possible ones
        for cell in self.get_components():
            for basket in cell.get_components():
                if isinstance(basket, Basket):
                    basket_list.append(basket)

        return basket_list

    def _do_change_mode(self, *args, **kwargs):
        return

    def _do_update_info(self):
        self._update_selection()
        self._update_state()

    def _do_scan(self, component, recursive=True, saved={"barcodes": None}):
        return

    def _execute_cmd(self, cmd, *args, **kwargs):
        timeout = kwargs.pop("timeout", None)
        if args:
            cmd_str = "flex.%s(%s)" % (cmd, ",".join(map(repr, args)))
        else:
            cmd_str = "flex.%s()" % cmd
        cmd_id = self.robot.eval(cmd_str)

        if not cmd_id:
            cmd_id = self.robot.eval(cmd_str)
        with gevent.Timeout(
            timeout, RuntimeError("Timeout while executing %s" % repr(cmd_str))
        ):
            while True:
                if self.robot.is_finished(cmd_id):
                    break
                gevent.sleep(0.2)

        res = self.robot.get_result(cmd_id)
        if res:
            res = pickle.loads(base64.b64decode(res))
            if isinstance(res, Exception):
                raise res
            return res

    def _execute_cmd_exporter(self, cmd, *args, **kwargs):
        ret = None
        timeout = kwargs.pop("timeout", 900)
        if args:
            args_str = "%s" % "\t".join(map(repr, args))
        if kwargs.pop("command", None):
            exp_cmd = self.add_command(
                {
                    "type": "exporter",
                    "exporter_address": self.exporter_addr,
                    "name": "%s" % cmd,
                },
                "%s" % cmd,
            )
            if args:
                ret = exp_cmd(args_str)
            else:
                ret = exp_cmd()
        if kwargs.pop("attribute", None):
            exp_attr = self.add_channel(
                {
                    "type": "exporter",
                    "exporter_address": self.exporter_addr,
                    "name": "%s" % cmd,
                },
                "%s" % cmd[3:],
            )
            if cmd.startswith("get"):
                return exp_attr.get_value()
            if cmd.startswith("set"):
                ret = exp_attr.set_value(args_str)

        self._wait_ready(timeout=timeout)
        return ret

    def _assert_ready(self):
        if not self._ready():
            raise RuntimeError("Sample changer is busy cant mount/unmount")

    def _ready(self):
        return self._execute_cmd_exporter("getState", attribute=True) == "Ready"

    def _busy(self):
        return self._execute_cmd_exporter("getState", attribute=True) != "Ready"

    def _wait_ready(self, timeout=None):
        # None means wait forever timeout <=0 use default timeout
        if timeout is not None and timeout <= 0:
            timeout = self.timeout

        err_msg = "Timeout waiting for sample changer to be ready"

        with gevent.Timeout(timeout, RuntimeError(err_msg)):
            while not self._ready():
                gevent.sleep(0.5)

    def _wait_busy(self, timeout=None):
        # None means wait forever timeout <=0 use default timeout
        if timeout is not None and timeout <= 0:
            timeout = self.timeout

        err_msg = "Timeout waiting for sample changer action to start"

        with gevent.Timeout(timeout, RuntimeError(err_msg)):
            while not self._busy():
                gevent.sleep(0.5)

    def _do_select(self, component):
        if isinstance(component, Cell):
            cell_pos = component.get_index() + 1
        elif isinstance(component, (Basket, Pin)):
            cell_pos = component.get_cell_no()

        self._execute_cmd_exporter("moveDewar", cell_pos, command=True)

        self._update_selection()

    @task
    def load_sample(
        self,
        holderLength,
        sample_id=None,
        sample_location=None,
        sampleIsLoadedCallback=None,
        failureCallback=None,
        prepareCentring=True,
    ):
        # self._assert_ready()
        cell, basket, sample = sample_location
        sample = self.get_component_by_address(
            Pin.get_sample_address(cell, basket, sample)
        )
        return self.load(sample)

    def chained_load(self, old_sample, sample):
        return self._do_load(sample)

    def _set_loaded_sample_and_prepare(self, sample, previous_sample):
        res = False

        if not -1 in sample and sample != previous_sample:
            self._set_loaded_sample(self.get_sample_with_address(sample))
            self._prepare_centring_task()
            res = True

        return res

    def _hw_get_mounted_sample(self):
        loaded_sample = tuple(
            self._execute_cmd_exporter("getMountedSamplePosition", attribute=True)
        )

        return (
            str(loaded_sample[0])
            + ":"
            + str(loaded_sample[1])
            + ":"
            + "%02d" % loaded_sample[2]
        )

    def get_loaded_sample(self):
        sample = None

        loaded_sample_addr = self._hw_get_mounted_sample()

        for s in self.get_sample_list():
            if s.get_address() == loaded_sample_addr:
                sample = s

        return sample

    def get_sample_with_address(self, address):
        sample = None
        address = str(address[0]) + ":" + str(address[1]) + ":" + "%02d" % address[2]

        for s in self.get_sample_list():
            if s.get_address() == address:
                sample = s

        return sample

    def reset_loaded_sample(self):
        self._execute_cmd_exporter("resetLoadedPosition", command=True)
        self._reset_loaded_sample()

    def get_robot_exceptions(self):
        return [self._execute_cmd_exporter("getLastTaskException", attribute=True)] or [
            ""
        ]

    @task
    def load(self, sample):
        self.prepare_load()
        self.enable_power()

        try:
            res = SampleChanger.load(self, sample)
        finally:
            for msg in self.get_robot_exceptions():
                if msg is not None:
                    logging.getLogger("HWR").error(msg)

        # if res:
        #    self.prepare_centring()

        return res

    @task
    def unload_sample(
        self,
        holderLength,
        sample_id=None,
        sample_location=None,
        successCallback=None,
        failureCallback=None,
    ):
        self._assert_ready()
        cell, basket, sample = sample_location
        sample = self.get_component_by_address(
            Pin.get_sample_address(cell, basket, sample)
        )
        return self.unload(sample)

    @task
    def unload(self, sample):
        self.prepare_load()
        self.enable_power()

        if not sample:
            sample = self._hw_get_mounted_sample()

        try:
            SampleChanger.unload(self, sample)
        finally:
            for msg in self.get_robot_exceptions():
                if msg is not None:
                    logging.getLogger("HWR").error(msg)

    def get_gripper(self):
        gripper_type = self._execute_cmd_exporter("get_gripper_type", attribute=True)

        return self.gripper_types.get(gripper_type, "?")

    def get_available_grippers(self):
        grippers = []
        try:
            ret = sorted(
                self._execute_cmd_exporter("getSupportedGrippers", attribute=True)
            )
            for gripper in ret:
                grippers.append(self.gripper_types[gripper])
        except Exception:
            grippers = [-1]

        return grippers

    @task
    def change_gripper(self, gripper=None):
        self.prepare_load()
        self.enable_power()

        if gripper:
            self._execute_cmd_exporter("setGripper", gripper, command=True)
        else:
            self._execute_cmd_exporter("changeGripper", command=True)

    @task
    def home(self):
        self.prepare_load()
        self.enable_power()
        self._execute_cmd_exporter("homeClear", command=True)

    @task
    def enable_power(self):
        if not self.exporter_addr:
            self._execute_cmd("enablePower", 1)

    @task
    def defreeze(self):
        self.prepare_load()
        self.enable_power()
        self._execute_cmd_exporter("defreezeGripper", command=True)

    def _do_load(self, sample=None):
        self._update_state()
        previous_sample = tuple(
            self._execute_cmd_exporter("getMountedSamplePosition", attribute=True)
        )

        # We wait for the sample changer if its already doing something, like defreezing
        # wait for 10 minutes then timeout !
        self._wait_ready(600)

        # Start loading
        load_task = gevent.spawn(
            self._execute_cmd_exporter,
            "loadSample",
            sample.get_cell_no(),
            sample.get_basket_no(),
            sample.get_vial_no(),
            command=True,
        )

        # Wait for sample changer to start activity
        try:
            _tt = time.time()
            self._wait_busy(300)
            logging.getLogger("HWR").info(f"Waited SC activity {time.time() - _tt}")
        except:
            for msg in self.get_robot_exceptions():
                logging.getLogger("user_level_log").error(msg)
            raise

        # Wait for the sample to be loaded, (put on the goniometer)
        err_msg = "Timeout while waiting to sample to be loaded"
        with gevent.Timeout(600, RuntimeError(err_msg)):
            while not load_task.ready():
                loaded_sample = tuple(
                    self._execute_cmd_exporter(
                        "getMountedSamplePosition", attribute=True
                    )
                )

                if loaded_sample == (
                    sample.get_cell_no(),
                    sample.get_basket_no(),
                    sample.get_vial_no(),
                ):
                    break

                gevent.sleep(2)

        with gevent.Timeout(600, RuntimeError(err_msg)):
            while True:
                is_safe = self._execute_cmd_exporter("getRobotIsSafe", attribute=True)

                if is_safe:
                    break

                gevent.sleep(2)

        for msg in self.get_robot_exceptions():
            if msg is not None:
                logging.getLogger("HWR").error(msg)
                logging.getLogger("user_level_log").error(msg)

        return self._set_loaded_sample_and_prepare(loaded_sample, previous_sample)

    def _do_unload(self, sample=None):
        self._execute_cmd_exporter(
            "unloadSample",
            sample.get_cell_no(),
            sample.get_basket_no(),
            sample.get_vial_no(),
            command=True,
        )

        loaded_sample = tuple(
            self._execute_cmd_exporter("getMountedSamplePosition", attribute=True)
        )

        for msg in self.get_robot_exceptions():
            if msg is not None:
                logging.getLogger("HWR").error(msg)
                logging.getLogger("user_level_log").error(msg)

        if loaded_sample == (-1, -1, -1):
            self._reset_loaded_sample()

            if self.controller:
                self.controller.hutch_actions(release_interlock=True)

            return True

        return False

    def _do_abort(self):
        self._execute_cmd_exporter("abort", command=True)

    def _do_trash(self):
        self.prepare_load()
        self._execute_cmd_exporter("trashMountedSample", command=True)
        self._reset_loaded_sample()

    def _do_reset(self):
        self._execute_cmd_exporter("homeClear", command=True)

    def clear_basket_info(self, basket):
        return self._reset_basket_info(basket)

    def _reset_basket_info(self, basket):
        pass

    def clear_cell_info(self, cell):
        return self._reset_cell_info(cell)

    def _reset_cell_info(self, cell):
        pass

    def _update_state(self):
        try:
            state = self._read_state()
            status = self._execute_cmd_exporter("getStatus", attribute=True)
        except Exception:
            state = SampleChangerState.Unknown
            status = "Unknown"

        self._set_state(state, status)

    def is_sequencer_ready(self):
        if self.prepareLoad:
            cmdobj = self.get_command_object
            return all(
                [cmd.isSpecReady() for cmd in (cmdobj("moveToLoadingPosition"),)]
            )
        return True

    def _read_state(self):
        state = self._execute_cmd_exporter("getState", attribute=True).upper()

        state_converter = {
            "ALARM": SampleChangerState.Alarm,
            "FAULT": SampleChangerState.Fault,
            "RUNNING": SampleChangerState.Moving,
            "READY": SampleChangerState.Ready,
            "STANDBY": SampleChangerState.Ready,
        }

        return state_converter.get(state, SampleChangerState.Unknown)

    def _is_device_busy(self, state=None):
        if state is None:
            state = self._read_state()
        return state not in (
            SampleChangerState.Ready,
            SampleChangerState.Loaded,
            SampleChangerState.Alarm,
            SampleChangerState.Disabled,
            SampleChangerState.Fault,
            SampleChangerState.StandBy,
        )

    def _is_device_ready(self):
        state = self._read_state()
        return state in (SampleChangerState.Ready, SampleChangerState.Charging)

    def _wait_device_ready(self, timeout=None):
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self._is_device_ready():
                gevent.sleep(0.01)

    def _update_selection(self):
        sample_cell, sample_puck, sample = self._execute_cmd_exporter(
            "getMountedSamplePosition", attribute=True
        )

        cell = sample_cell

        for cmp in self.get_components():
            idx = cmp.get_index()
            if cell == idx + 1:
                self._set_selected_component(cmp)
                break

        # find sample
        for samp in self.get_sample_list():
            if samp.get_coords() == (sample_cell, sample_puck, sample):
                self._set_loaded_sample(samp)
                self._set_selected_sample(samp)
            else:
                samp._set_loaded(False)

        self._set_selected_sample(None)

    def prepare_hutch(self, **kwargs):
        return
