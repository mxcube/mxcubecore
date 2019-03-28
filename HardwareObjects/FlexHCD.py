import base64
import cPickle
from HardwareRepository.HardwareObjects.abstract.AbstractSampleChanger import *
from PyTango.gevent import DeviceProxy


class Pin(Sample):
    def __init__(self, basket, cell_no, basket_no, sample_no):
        super(Pin, self).__init__(
            basket, Pin.getSampleAddress(cell_no, basket_no, sample_no), True
        )
        self._setHolderLength(22.0)
        self.present = True

    def getBasketNo(self):
        return self.getContainer().getIndex() + 1

    def getVialNo(self):
        return self.getIndex() + 1

    def getCellNo(self):
        return self.getContainer().getContainer().getIndex() + 1

    def getCell(self):
        return self.getContainer().getContainer()

    @staticmethod
    def getSampleAddress(cell_number, basket_number, sample_number):
        return (
            str(cell_number) + ":" + str(basket_number) + ":" + "%02d" % sample_number
        )


class Basket(Container):
    __TYPE__ = "Puck"

    def __init__(self, container, cell_no, basket_no, unipuck=False):
        super(Basket, self).__init__(
            self.__TYPE__, container, Basket.getBasketAddress(cell_no, basket_no), True
        )
        for i in range(16 if unipuck else 10):
            slot = Pin(self, cell_no, basket_no, i + 1)
            self._addComponent(slot)
        self.present = True

    @staticmethod
    def getBasketAddress(cell_number, basket_number):
        return str(cell_number) + ":" + str(basket_number)

    def getCellNo(self):
        return self.getContainer().getIndex() + 1

    def getCell(self):
        return self.getContainer()

    def clearInfo(self):
        self.getContainer()._reset_basket_info(self.getIndex() + 1)
        self.getContainer()._triggerInfoChangedEvent()


class Cell(Container):
    __TYPE__ = "Cell"

    def __init__(self, container, number, sc3_pucks=True):
        super(Cell, self).__init__(
            self.__TYPE__, container, Cell.getCellAddress(number), True
        )
        self.present = True
        if sc3_pucks:
            for i in range(3):
                self._addComponent(
                    Basket(self, number, i + 1, unipuck=1 - (number % 2))
                )
        else:
            for i in range(3):
                self._addComponent(Basket(self, number, i + 1, unipuck=True))

    @staticmethod
    def getCellAddress(cell_number):
        return str(cell_number)

    def _reset_basket_info(self, basket_no):
        pass

    def clearInfo(self):
        self.getContainer()._reset_cell_info(self.getIndex() + 1)
        self.getContainer()._triggerInfoChangedEvent()

    def getCell(self):
        return self


class FlexHCD(SampleChanger):
    __TYPE__ = "HCD"

    def __init__(self, *args, **kwargs):
        super(FlexHCD, self).__init__(self.__TYPE__, True, *args, **kwargs)

    def init(self):
        sc3_pucks = self.getProperty("sc3_pucks", True)

        for i in range(8):
            cell = Cell(self, i + 1, sc3_pucks)
            self._addComponent(cell)

        self.robot = self.getProperty("tango_device")
        if self.robot:
            self.robot = DeviceProxy(self.robot)

        self.exporter_addr = self.getProperty("exporter_address")
        if self.exporter_addr:
            self.swstate_attr = self.addChannel(
                {
                    "type": "exporter",
                    "exporter_address": self.exporter_addr,
                    "name": "swstate",
                },
                "State",
            )

        self.controller = self.getObjectByRole("controller")
        self.prepareLoad = self.getCommandObject("moveToLoadingPosition")
        self.timeout = 3
        self.gripper_types = {
            -1: "No Gripper",
            1: "UNIPUCK",
            2: "MINISPINE",
            3: "FLIPPING",
            4: "UNIPUCK_DOUBLE",
            5: "PLATE",
        }

        return SampleChanger.init(self)

    @task
    def prepare_load(self):
        if self.controller:
            self.controller.hutch_actions(condition=True)
        else:
            self.prepareLoad()

    @task
    def prepare_centring(self):
        if self.controller:
            self.controller.hutch_actions(condition=False, sc_loading=True)
        else:
            gevent.sleep(2)
            self.getCommandObject("unlockMinidiffMotors")(wait=True)
            self.getCommandObject("prepareCentring")(wait=True)

    def prepareCentring(self):
        self.prepare_centring()

    def getSampleProperties(self):
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)

    def getBasketList(self):
        basket_list = []
        # put here only the baskets that exist, not all the possible ones
        # if self.exporter_addr:
        #    basket_list =
        for cell in self.getComponents():
            for basket in cell.getComponents():
                if isinstance(basket, Basket):
                    basket_list.append(basket)

        return basket_list

    def _doChangeMode(self, *args, **kwargs):
        return

    def _doUpdateInfo(self):
        # self._updateSelection()
        self._updateState()

    def _doScan(self, component, recursive=True, saved={"barcodes": None}):
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
            res = cPickle.loads(base64.decodestring(res))
            if isinstance(res, Exception):
                raise res
            else:
                return res

    def _execute_cmd_exporter(self, cmd, *args, **kwargs):
        timeout = kwargs.pop("timeout", 900)
        if args:
            args_str = "%s" % "\t".join(map(repr, args))
        if kwargs.pop("command", None):
            exp_cmd = self.addCommand(
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
            exp_attr = self.addChannel(
                {
                    "type": "exporter",
                    "exporter_address": self.exporter_addr,
                    "name": "%s" % cmd,
                },
                "%s" % cmd[3:],
            )
            if cmd.startswith("get"):
                return exp_attr.getValue()
            if cmd.startswith("set"):
                ret = exp_attr.setValue(args_str)

        self._wait_ready(timeout=timeout)
        return ret

    def _ready(self):
        return self.swstate_attr.getValue() == "Ready"

    def _wait_ready(self, timeout=None):
        err_msg = "Timeout waiting for sample changer to be ready"
        # None means infinite timeout <=0 means default timeout
        if timeout is not None and timeout <= 0:
            timeout = self.timeout
        with gevent.Timeout(timeout, RuntimeError(err_msg)):
            while not self._ready():
                time.sleep(0.5)

    def _doSelect(self, component):
        if isinstance(component, Cell):
            cell_pos = component.getIndex() + 1
        elif isinstance(component, Basket) or isinstance(component, Pin):
            cell_pos = component.getCellNo()

        if self.exporter_addr:
            self._execute_cmd_exporter("moveDewar", cell_pos, command=True)
        else:
            self._execute_cmd("moveDewar", cell_pos)

        self._updateSelection()

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
        cell, basket, sample = sample_location
        sample = self.getComponentByAddress(Pin.getSampleAddress(cell, basket, sample))
        return self.load(sample)

    def chained_load(self, old_sample, sample):
        if self.exporter_addr:
            unload_load_task = gevent.spawn(
                self._execute_cmd_exporter,
                "loadSample",
                sample.getCellNo(),
                sample.getBasketNo(),
                sample.getVialNo(),
                command=True,
            )
        else:
            unload_load_task = gevent.spawn(
                self._execute_cmd,
                "chainedUnldLd",
                [
                    old_sample.getCellNo(),
                    old_sample.getBasketNo(),
                    old_sample.getVialNo(),
                ],
                [sample.getCellNo(), sample.getBasketNo(), sample.getVialNo()],
            )

        gevent.sleep(15)

        err_msg = "Timeout waiting for sample changer to be in safe position"
        while not unload_load_task.ready():
            if self.exporter_addr:
                loading_state = self._execute_cmd_exporter(
                    "getCurrentLoadSampleState", attribute=True
                )
                if "on_gonio" in loading_state:
                    self._setLoadedSample(sample)
                    with gevent.Timeout(20, RuntimeError(err_msg)):
                        while not self._execute_cmd_exporter(
                            "getRobotIsSafe", attribute=True
                        ):
                            gevent.sleep(0.5)
                    return True
            else:
                loading_state = str(
                    self._execute_cmd("sampleStatus", "LoadSampleStatus")
                )
                if "on_gonio" in loading_state:
                    self._setLoadedSample(sample)
                    with gevent.Timeout(20, RuntimeError(err_msg)):
                        while (
                            not self._execute_cmd(
                                "get_robot_cache_variable", "data:dioRobotIsSafe"
                            )
                            == "true"
                        ):
                            gevent.sleep(0.5)
                    return True
            gevent.sleep(1)

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
            self.prepare_centring()
            return True
        else:
            logging.getLogger("HWR").info("reset loaded sample")
            self._resetLoadedSample()
            # if self.controller:
            #    self.controller.hutch_actions(release_interlock=True)
            return False

    def reset_loaded_sample(self):
        if self.exporter_addr:
            self._execute_cmd_exporter("reset_loaded_position", command=True)
        else:
            self._execute_cmd("reset_loaded_position")
        self._resetLoadedSample()

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
            self.prepareCentring()
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
        cell, basket, sample = sample_location
        sample = self.getComponentByAddress(Pin.getSampleAddress(cell, basket, sample))
        return self.unload(sample)

    @task
    def unload(self, sample):
        self.prepare_load(wait=True)
        self.enable_power()
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
        if self.exporter_addr:
            ret = sorted(
                self._execute_cmd_exporter("getSupportedGrippers", attribute=True)
            )
            for gripper in ret:
                grippers.append(self.gripper_types[gripper])
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

    def _doLoad(self, sample=None):
        self._updateState()
        if self.exporter_addr:
            load_task = gevent.spawn(
                self._execute_cmd_exporter,
                "loadSample",
                sample.getCellNo(),
                sample.getBasketNo(),
                sample.getVialNo(),
                command=True,
            )
        else:
            load_task = gevent.spawn(
                self._execute_cmd,
                "loadSample",
                sample.getCellNo(),
                sample.getBasketNo(),
                sample.getVialNo(),
            )
        gevent.sleep(5)

        err_msg = "Timeout waiting for sample changer to be in safe position"
        while not load_task.ready():
            if self.exporter_addr:
                loading_state = self._execute_cmd_exporter(
                    "getCurrentLoadSampleState", attribute=True
                )
                if "on_gonio" in loading_state:
                    self._setLoadedSample(sample)
                    with gevent.Timeout(20, RuntimeError(err_msg)):
                        while not self._execute_cmd_exporter(
                            "getRobotIsSafe", attribute=True
                        ):
                            gevent.sleep(0.5)
                    return True
            else:
                loading_state = str(
                    self._execute_cmd("sampleStatus", "LoadSampleStatus")
                )
                if "on_gonio" in loading_state:
                    self._setLoadedSample(sample)
                    with gevent.Timeout(20, RuntimeError(err_msg)):
                        while (
                            not self._execute_cmd(
                                "get_robot_cache_variable", "data:dioRobotIsSafe"
                            )
                            == "true"
                        ):
                            gevent.sleep(0.5)
                    return True
            gevent.sleep(1)

        if self.exporter_addr:
            loaded_sample = self._execute_cmd_exporter(
                "get_loaded_sample", attribute=True
            )
        else:
            loaded_sample = self._execute_cmd("get_loaded_sample")
        if loaded_sample == (
            sample.getCellNo(),
            sample.getBasketNo(),
            sample.getVialNo(),
        ):
            self._setLoadedSample(sample)
            return True
        return self._check_pin_on_gonio()

    def _doUnload(self, sample=None):
        loaded_sample = self.getLoadedSample()
        if loaded_sample is not None and loaded_sample != sample:
            raise RuntimeError("Cannot unload another sample")

        if self.exporter_addr:
            self._execute_cmd_exporter(
                "unloadSample",
                sample.getCellNo(),
                sample.getBasketNo(),
                sample.getVialNo(),
                command=True,
            )
            loaded_sample = self._execute_cmd_exporter(
                "get_loaded_sample", attribute=True
            )
        else:
            self._execute_cmd(
                "unloadSample",
                sample.getCellNo(),
                sample.getBasketNo(),
                sample.getVialNo(),
            )
            loaded_sample = self._execute_cmd("get_loaded_sample")
        if loaded_sample == (-1, -1, -1):
            self._resetLoadedSample()
            if self.controller:
                self.controller.hutch_actions(release_interlock=True)
            return True
        return False

    def _doAbort(self):
        if self.exporter_addr:
            self._execute_cmd_exporter("abort", command=True)
        else:
            self._execute_cmd("abort")

    def _doReset(self):
        if self.exporter_addr:
            self._execute_cmd_exporter("homeClear", command=True)
        else:
            self._execute_cmd("homeClear")

    def clearBasketInfo(self, basket):
        return self._reset_basket_info(basket)

    def _reset_basket_info(self, basket):
        pass

    def clearCellInfo(self, cell):
        return self._reset_cell_info(cell)

    def _reset_cell_info(self, cell):
        pass

    def _updateState(self):
        # see if the command exists for exporter
        if not self.exporter_addr:
            defreezing = self._execute_cmd("isDefreezing")
            if defreezing:
                self._setState(SampleChangerState.Ready)

        try:
            state = self._readState()
        except Exception:
            state = SampleChangerState.Unknown

        self._setState(state)

    def isSequencerReady(self):
        if self.prepareLoad:
            cmdobj = self.getCommandObject
            return all(
                [cmd.isSpecReady() for cmd in (cmdobj("moveToLoadingPosition"),)]
            )
        return True

    def _readState(self):
        # should read state from robot
        if self.exporter_addr:
            state = self.swstate_attr.getValue().upper()
        else:
            state = "RUNNING" if self._execute_cmd("robot.isBusy") else "STANDBY"
            if state == "STANDBY" and not self.isSequencerReady():
                state = "RUNNING"

        state_converter = {
            "ALARM": SampleChangerState.Alarm,
            "FAULT": SampleChangerState.Fault,
            "RUNNING": SampleChangerState.Moving,
            "READY": SampleChangerState.Ready,
            "STANDBY": SampleChangerState.Ready,
        }

        return state_converter.get(state, SampleChangerState.Unknown)

    def _isDeviceBusy(self, state=None):
        if state is None:
            state = self._readState()
        return state not in (
            SampleChangerState.Ready,
            SampleChangerState.Loaded,
            SampleChangerState.Alarm,
            SampleChangerState.Disabled,
            SampleChangerState.Fault,
            SampleChangerState.StandBy,
        )

    def _isDeviceReady(self):
        state = self._readState()
        return state in (SampleChangerState.Ready, SampleChangerState.Charging)

    def _waitDeviceReady(self, timeout=None):
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self._isDeviceReady():
                gevent.sleep(0.01)

    def _updateSelection(self):
        if self.exporter_addr:
            sample_cell, sample_puck, sample = self._execute_cmd_exporter(
                "get_loaded_sample", attribute=True
            )
            cell = sample_cell
            puck = sample_puck
        else:
            cell, puck = self._execute_cmd("get_cell_position")
            sample_cell, sample_puck, sample = self._execute_cmd("get_loaded_sample")

        for c in self.getComponents():
            i = c.getIndex()
            if cell == i + 1:
                self._setSelectedComponent(c)
                break

        # find sample
        for s in self.getSampleList():
            if s.getCoords() == (sample_cell, sample_puck, sample):
                self._setLoadedSample(s)
                # self._setSelectedSample(s)
                return

        for s in self.getSampleList():
            s._setLoaded(False)
        self._setSelectedSample(None)

    def prepare_hutch(self, **kwargs):
        if self.exporter_addr:
            return

        user_port = kwargs.get("user_port")
        robot_port = kwargs.get("robot_port")
        if user_port is not None:
            self._execute_cmd("robot.user_port(user_port)")

        if robot_port is not None:
            self._execute_cmd("robot.robot_port(robot_port)")
