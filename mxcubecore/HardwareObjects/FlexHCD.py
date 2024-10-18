import base64
import logging
import pickle

import gevent
from PyTango.gevent import DeviceProxy

from mxcubecore.HardwareObjects.abstract.AbstractSampleChanger import (
    SampleChanger,
    SampleChangerState,
)
from mxcubecore.HardwareObjects.abstract.sample_changer.Container import (
    Container,
    Sample,
)
from mxcubecore.TaskUtils import task


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

    def __init__(self, container, number, sc3_pucks=True):
        super(Cell, self).__init__(
            self.__TYPE__, container, Cell.get_cell_address(number), True
        )
        self.present = True
        if sc3_pucks:
            for i in range(3):
                self._add_component(
                    Basket(self, number, i + 1, unipuck=1 - (number % 2))
                )
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


class FlexHCD(SampleChanger):
    __TYPE__ = "HCD"

    def __init__(self, *args, **kwargs):
        super(FlexHCD, self).__init__(self.__TYPE__, True, *args, **kwargs)

    def init(self):
        sc3_pucks = self.get_property("sc3_pucks", True)

        for i in range(8):
            cell = Cell(self, i + 1, sc3_pucks)
            self._add_component(cell)

        self.robot = self.get_property("tango_device")
        if self.robot:
            self.robot = DeviceProxy(self.robot)

        self.exporter_addr = self.get_property("exporter_address")

        if self.exporter_addr:
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

    @task
    def prepare_load(self):
        if self.controller:
            self.controller.hutch_actions(enter=True)
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
        # if self.exporter_addr:
        #    basket_list =
        for cell in self.get_components():
            for basket in cell.get_components():
                if isinstance(basket, Basket):
                    basket_list.append(basket)

        return basket_list

    def _do_change_mode(self, *args, **kwargs):
        return

    def _do_update_info(self):
        # self._update_selection()
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
            else:
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
        if self.exporter_addr:
            if not self._ready():
                raise RuntimeError("Sample changer is busy cant mount/unmount")

    def _ready(self):
        return self.swstate_attr.get_value() == "Ready"

    def _wait_ready(self, timeout=None):
        err_msg = "Timeout waiting for sample changer to be ready"
        # None means infinite timeout <=0 means default timeout
        if timeout is not None and timeout <= 0:
            timeout = self.timeout
        with gevent.Timeout(timeout, RuntimeError(err_msg)):
            while not self._ready():
                gevent.sleep(0.5)

    def _do_select(self, component):
        if isinstance(component, Cell):
            cell_pos = component.get_index() + 1
        elif isinstance(component, Basket) or isinstance(component, Pin):
            cell_pos = component.get_cell_no()

        if self.exporter_addr:
            self._execute_cmd_exporter("moveDewar", cell_pos, command=True)
        else:
            self._execute_cmd("moveDewar", cell_pos)

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
        self._assert_ready()
        cell, basket, sample = sample_location
        sample = self.get_component_by_address(
            Pin.get_sample_address(cell, basket, sample)
        )
        return self.load(sample)

    def chained_load(self, old_sample, sample):
        self._assert_ready()
        if self.exporter_addr:
            unload_load_task = gevent.spawn(
                self._execute_cmd_exporter,
                "loadSample",
                sample.get_cell_no(),
                sample.get_basket_no(),
                sample.get_vial_no(),
                command=True,
            )
        else:
            unload_load_task = gevent.spawn(
                self._execute_cmd,
                "chainedUnldLd",
                [
                    old_sample.get_cell_no(),
                    old_sample.get_basket_no(),
                    old_sample.get_vial_no(),
                ],
                [sample.get_cell_no(), sample.get_basket_no(), sample.get_vial_no()],
            )

        gevent.sleep(10)

        err_msg = "Timeout waiting for sample changer to be in safe position"
        while not unload_load_task.ready():
            if self.exporter_addr:
                loading_state = self._execute_cmd_exporter(
                    "getCurrentLoadSampleState", attribute=True
                )
                if "on_gonio" in loading_state:
                    self._set_loaded_sample(sample)
                    with gevent.Timeout(60, RuntimeError(err_msg)):
                        logging.getLogger("HWR").info(err_msg)
                        while not self._execute_cmd_exporter(
                            "getRobotIsSafe", attribute=True
                        ):
                            gevent.sleep(0.5)
                    return True
            else:
                loading_state = str(
                    self._execute_cmd("get_robot_cache_variable", "LoadSampleStatus")
                )
                if "on_gonio" in loading_state:
                    self._set_loaded_sample(sample)
                    with gevent.Timeout(60, RuntimeError(err_msg)):
                        logging.getLogger("HWR").info(err_msg)
                        while (
                            not self._execute_cmd(
                                "get_robot_cache_variable", "data:dioRobotIsSafe"
                            )
                            == "true"
                        ):
                            gevent.sleep(0.5)
                    return True
            gevent.sleep(2)

        logging.getLogger("HWR").info("unload load task done")
        for msg in self.get_robot_exceptions():
            logging.getLogger("HWR").error(msg)

        return self._check_pin_on_gonio()

    def _check_pin_on_gonio(self):
        if self.exporter_addr:
            _on_gonio = self._execute_cmd_exporter("pin_on_gonio", command=True)
        else:
            _on_gonio = self._execute_cmd("pin_on_gonio")

        if _on_gonio:
            # finish the loading actions
            self._prepare_centring_task()
            return True
        else:
            logging.getLogger("HWR").info("reset loaded sample")
            self._reset_loaded_sample()
            # if self.controller:
            #    self.controller.hutch_actions(release_interlock=True)
            return False

    def reset_loaded_sample(self):
        if self.exporter_addr:
            self._execute_cmd_exporter("resetLoadedPosition", command=True)
        else:
            self._execute_cmd("reset_loaded_position")
        self._reset_loaded_sample()

    def get_robot_exceptions(self):
        if self.exporter_addr:
            """
            return self._execute_cmd_exporter('getRobotExceptions',
                                              attribute=True)
            """
            return ""
        else:
            return self._execute_cmd("getRobotExceptions")

    @task
    def load(self, sample):
        self.prepare_load(wait=True)
        self.enable_power()
        try:
            res = SampleChanger.load(self, sample)
        finally:
            for msg in self.get_robot_exceptions():
                logging.getLogger("HWR").error(msg)
        if res:
            self.prepare_centring()
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
        self.prepare_load(wait=True)
        self.enable_power()

        if not sample:
            sample = self.get_loaded_sample().get_address()

        try:
            SampleChanger.unload(self, sample)
        finally:
            for msg in self.get_robot_exceptions():
                logging.getLogger("HWR").error(msg)

    def get_gripper(self):
        if self.exporter_addr:
            gripper_type = self._execute_cmd_exporter(
                "get_gripper_type", attribute=True
            )
        else:
            gripper_type = self._execute_cmd("get_gripper_type")

        return self.gripper_types.get(gripper_type, "?")

    def get_available_grippers(self):
        grippers = []

        try:

            if self.exporter_addr:
                ret = sorted(
                    self._execute_cmd_exporter("getSupportedGrippers", attribute=True)
                )
                for gripper in ret:
                    grippers.append(self.gripper_types[gripper])
            else:
                ret = [1, 3]  # self._execute_cmd("get_supported_grippers")

                for gripper in ret:
                    grippers.append(self.gripper_types[gripper])
        except Exception:
            grippers = [-1]

        return grippers

    @task
    def change_gripper(self, gripper=None):
        self.prepare_load(wait=True)
        self.enable_power()
        if self.exporter_addr:
            if gripper:
                self._execute_cmd_exporter("setGripper", gripper, command=True)
            else:
                self._execute_cmd_exporter("changeGripper", command=True)
        else:
            self._execute_cmd("changeGripper")

    @task
    def home(self):
        self.prepare_load(wait=True)
        self.enable_power()
        if self.exporter_addr:
            self._execute_cmd_exporter("homeClear", command=True)
        else:
            self._execute_cmd("homeClear")

    @task
    def enable_power(self):
        if not self.exporter_addr:
            self._execute_cmd("enablePower", 1)

    @task
    def defreeze(self):
        self.prepare_load(wait=True)
        self.enable_power()
        if self.exporter_addr:
            self._execute_cmd_exporter("defreezeGripper", command=True)
        else:
            self._execute_cmd("defreezeGripper")

    def _do_load(self, sample=None):
        self._update_state()

        if self.exporter_addr:
            load_task = gevent.spawn(
                self._execute_cmd_exporter,
                "loadSample",
                sample.get_cell_no(),
                sample.get_basket_no(),
                sample.get_vial_no(),
                command=True,
            )
        else:
            load_task = gevent.spawn(
                self._execute_cmd,
                "loadSample",
                sample.get_cell_no(),
                sample.get_basket_no(),
                sample.get_vial_no(),
            )

        gevent.sleep(10)
        err_msg = "Timeout waiting for sample changer to be in safe position"
        while not load_task.ready():
            if self.exporter_addr:
                loading_state = self._execute_cmd_exporter(
                    "getCurrentLoadSampleState", attribute=True
                )

                if "on_gonio" in loading_state:
                    self._set_loaded_sample(sample)
                    with gevent.Timeout(20, RuntimeError(err_msg)):
                        while not self._execute_cmd_exporter(
                            "getRobotIsSafe", attribute=True
                        ):
                            gevent.sleep(0.5)
                    return True
            else:
                loading_state = str(
                    self._execute_cmd("get_robot_cache_variable", "LoadSampleStatus")
                )
                if "on_gonio" in loading_state:
                    self._set_loaded_sample(sample)
                    with gevent.Timeout(20, RuntimeError(err_msg)):
                        while (
                            not self._execute_cmd(
                                "get_robot_cache_variable", "data:dioRobotIsSafe"
                            )
                            == "true"
                        ):
                            gevent.sleep(0.5)
                    return True
            gevent.sleep(2)

        if self.exporter_addr:
            loaded_sample = self._execute_cmd_exporter(
                "get_loaded_sample", attribute=True
            )
        else:
            loaded_sample = self._execute_cmd("get_loaded_sample")
        if loaded_sample == (
            sample.get_cell_no(),
            sample.get_basket_no(),
            sample.get_vial_no(),
        ):
            self._set_loaded_sample(sample)
            return True
        return self._check_pin_on_gonio()

    def _do_unload(self, sample=None):
        loaded_sample = self.get_loaded_sample()
        if loaded_sample is not None and loaded_sample != sample:
            raise RuntimeError("Cannot unload another sample")

        if self.exporter_addr:
            self._execute_cmd_exporter(
                "unloadSample",
                sample.get_cell_no(),
                sample.get_basket_no(),
                sample.get_vial_no(),
                command=True,
            )
            loaded_sample = self._execute_cmd_exporter(
                "getLoadedSample", attribute=True
            )
        else:
            self._execute_cmd(
                "unloadSample",
                sample.get_cell_no(),
                sample.get_basket_no(),
                sample.get_vial_no(),
            )
            loaded_sample = self._execute_cmd("get_loaded_sample")
        if loaded_sample == (-1, -1, -1):
            self._reset_loaded_sample()
            if self.controller:
                self.controller.hutch_actions(release_interlock=True)
            return True

        return False

    def _do_abort(self):
        if self.exporter_addr:
            self._execute_cmd_exporter("abort", command=True)
        else:
            self._execute_cmd("abort")

    def _do_reset(self):
        if self.controller:
            self.controller.hutch_actions(enter=True)
        if self.exporter_addr:
            self._execute_cmd_exporter("homeClear", command=True)
        else:
            self._execute_cmd("homeClear")

    def clear_basket_info(self, basket):
        return self._reset_basket_info(basket)

    def _reset_basket_info(self, basket):
        pass

    def clear_cell_info(self, cell):
        return self._reset_cell_info(cell)

    def _reset_cell_info(self, cell):
        pass

    def _update_state(self):
        # see if the command exists for exporter
        if not self.exporter_addr:
            pass
            # defreezing = self._execute_cmd("isDefreezing")

            # if defreezing:
            #    self._set_state(SampleChangerState.Moving)

        try:
            state = self._read_state()
        except Exception:
            state = SampleChangerState.Unknown

        self._set_state(state)

    def is_sequencer_ready(self):
        if self.prepareLoad:
            cmdobj = self.get_command_object
            return all(
                [cmd.isSpecReady() for cmd in (cmdobj("moveToLoadingPosition"),)]
            )
        return True

    def _read_state(self):
        # should read state from robot
        if self.exporter_addr:
            state = self.swstate_attr.get_value().upper()
        else:
            state = "RUNNING" if self._execute_cmd("robot.isBusy") else "STANDBY"
            if state == "STANDBY" and not self.is_sequencer_ready():
                state = "RUNNING"

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
        if self.exporter_addr:
            sample_cell, sample_puck, sample = self._execute_cmd_exporter(
                "get_loaded_sample", attribute=True
            )
            cell = sample_cell
            puck = sample_puck
        else:
            cell, puck = self._execute_cmd("get_cell_position")
            sample_cell, sample_puck, sample = self._execute_cmd("get_loaded_sample")

        for c in self.get_components():
            i = c.get_index()
            if cell == i + 1:
                self._set_selected_component(c)
                break

        # find sample
        for s in self.get_sample_list():
            if s.get_coords() == (sample_cell, sample_puck, sample):
                self._set_loaded_sample(s)
                self._set_selected_sample(s)
                return

        for s in self.get_sample_list():
            s._set_loaded(False)
        self._set_selected_sample(None)

    def prepare_hutch(self, **kwargs):
        if self.exporter_addr:
            return

        user_port = kwargs.get("user_port")
        robot_port = kwargs.get("robot_port")
        if user_port is not None:
            self._execute_cmd("robot.user_port(user_port)")

        if robot_port is not None:
            self._execute_cmd("robot.robot_port(robot_port)")
