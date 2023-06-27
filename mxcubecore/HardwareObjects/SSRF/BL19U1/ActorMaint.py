"""
CATS maintenance mockup.
待解决：
此处命令产生的error没有提示，只有数字errorcode
"""
import logging

from mxcubecore.TaskUtils import task
from mxcubecore.BaseHardwareObjects import Equipment

from mxcubecore.HardwareObjects.abstract import AbstractSampleChanger
from mxcubecore import HardwareRepository as HWR

import gevent
import time


__author__ = "Mikel Eguiraun"
__credits__ = ["The MxCuBE collaboration"]


TOOL_FLANGE, TOOL_UNIPUCK, TOOL_SPINE, TOOL_PLATE, TOOL_LASER, TOOL_DOUBLE_GRIPPER = (
    0,
    1,
    2,
    3,
    4,
    5,
)

TOOL_TO_STR = {
    "Flange": TOOL_FLANGE,
    "Unipuck": TOOL_UNIPUCK,
    "Rotat": TOOL_SPINE,
    "Plate": TOOL_PLATE,
    "Laser": TOOL_LASER,
    "Double": TOOL_DOUBLE_GRIPPER,
}



def set_running(func):
    """
    装饰器函数，在机械手dry，initialize，clear memory 的时候设置self._running为1
    """
    def wrapper(self):
        self._running=1
        self._update_global_state()

        ret = func(self)  # command的返回值ret,命令运行成功应该会返回机械手的返回信息，如果没有连通机械手返回False

        self._running = 0
        self._update_global_state()
        if ret:
            print("scmaint command return:",ret)
        # ret == False
        else:
            logging.getLogger("HWR").error(
                "socket timeout, please check the network connection"
            )
            raise Exception("socket timeout, please check the network connection")
    return wrapper

def if_running(func):
    """
    装饰器函数，可以用于dry，initialize，clear memory, 判断机械手在运行时不操作直接返回
    但实际只用在了clear memory（因为前端界面没有禁用按钮）
    """
    def wrapper(self):
        if self._running==1:
            logging.getLogger("HWR").debug(
                "机械手正在运动，请稍后操作" % (1)
            )
            return
        func(self)
    return wrapper

def set_running_closelid(func):
    """
    装饰器函数，在机械手close lid的时候设置self._running为1
    """
    def wrapper(self,state=True):
        self._running=1
        self._update_global_state()

        ret = func(self,state) #command的返回值ret,命令运行成功应该会返回机械手的返回信息，如果没有连通机械手返回False

        # try:
        #     res = func(self,state)  # command的返回值ret,命令运行成功应该会返回机械手的返回信息，如果没有连通机械手返回False
        # except Exception as e:
        #     print("type(e):", type(e))
        #     print("e:", e)
        #     errorCode = e
        #     self._running = 0
        #     self._update_global_state()
        #     return errorCode

        self._running = 0
        self._update_global_state()
        if ret:
            print(ret)
        # ret == False
        else:
            logging.getLogger("HWR").error(
                "socket timeout, please check the network connection"
            )
            raise Exception("socket timeout, please check the network connection")
    return wrapper


def if_running_closelid(func):
    """
    装饰器函数，用于close and open lid, 判断机械手在运行时不操作直接返回（因为前端界面没有禁用按钮）
    """
    def wrapper(self,state=True):
        if self._running==1:
            logging.getLogger("HWR").debug(
                "机械手正在运动，请稍后开关lid %d" % (1)
            )
            return
        return func(self,state)
    return wrapper


# 待添加给函数
def if_ErrorCode(func):
    """
    装饰器函数，用于当发送机械手命令，机械手返回报错时，获取报错信息，
    """
    def wrapper(self,*args):
        try:
            res = func(self,*args)
        except Exception as e:
            print("type(e):",type(e))
            print("e:",e)
            errorCode = e
            return errorCode
        else:
            return res
    return wrapper







class ActorMaint(Equipment):

    __TYPE__ = "CATS"
    NO_OF_LIDS = 3

    """
    Actual implementation of the CATS Sample Changer, MAINTENANCE COMMANDS ONLY
    BESSY BL14.1 installation with 3 lids
    """

    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)

        self._state = "READY"
        self._running = 0
        self._powered = 0
        self._toolopen = 0
        self._message = ["1. ","Nothing to report. ","   2. current sample: ","None"]
        # self._message = [" ","1. current sample: ","None"]
        self._regulating = 0
        self._lid1state = 1
        self._lid2state = 0
        self._lid3state = 0
        self._charging = 0
        self._currenttool = 1

        self._socket_addr = '10.30.61.73:10100'

        self._ifcmdSucceeded = False


    def init(self):

        try:
            self.cats_model = self.cats_device.read_attribute("CatsModel").value
        except Exception:
            self.cats_model = "CATS"


        self._cmdDry = self.add_command(
            {"type": "socketrobot", "socket_address":self._socket_addr, "name": '_cmdDry'}, 'Dry Wait = ON'
        )
        self._cmdHome = self.add_command(
            {"type": "socketrobot", "socket_address": self._socket_addr, "name": '_cmdHome'}, 'RobotInitialize'
        )
        self._cmdClearMemory = self.add_command(
            {"type": "socketrobot", "socket_address": self._socket_addr, "name": '_cmdClearMemory'}, 'SetMountedPin Dewar = 1 Magazine = 0 Position = 0'
        )
        self._cmdCloselid = self.add_command(
            {"type": "socketrobot", "socket_address": self._socket_addr, "name": '_cmdCloselid'}, 'Dewar Open = OFF Dewar = 1'
        )
        self._cmdOpenlid = self.add_command(
            {"type": "socketrobot", "socket_address": self._socket_addr, "name": '_cmdOpenlid'}, 'Dewar Open = ON Dewar = 1'
        )

        self._cmdAbort = self.add_command(
            {"type": "socketrobot", "socket_address": self._socket_addr, "name": '_cmdAbort'}, 'Abort'
        )

        # add_channel会在初始化时被测试能不能连通，add_command不会
        # self._test = self.add_channel(
        #     {"type": "exporter", "exporter_address": '10.30.63.67:9002', "name": '_test'}, 'ZoomPosition'
        # )
        # self._test = self.add_command(
        #     {"type": "exporter", "exporter_address": '10.30.63.67:9002', "name": '_test'}, 'ZoomPosition'
        # )


        # print("初始化时被调用")
    @property
    def running(self):
        return self._running


    # 不知道为什么这个函数没有用
    @running.setter
    def running(self,state):
        print("设置_running为:",state)
        if state in [0,1]:
            self._running = state
            print("设置_running成功")
    # 用这个函数代替上面的setter函数
    def change_running_state(self,state):
        if state in [0,1]:
            self._running = state

    def change_message_sampleState(self,msg):
        self._message[3] = msg
    def change_message_error(self,msg):
        self._message[1] = msg

    def get_current_tool(self):
        return self._currenttool


    def _do_abort(self):
        """
        abort作用，
        1. 会让系统的一些参数变为初始参数，以便继续操作
        2. 向机械手发送abort命令
        """
        self._running=0
        HWR.beamline.sample_changer._set_state(AbstractSampleChanger.SampleChangerState.Ready)
        self._update_global_state()     #其实不用update，这里update一下只是为了刷新一下界面
        self._cmdAbort()

    def _do_reset(self):
        """
        Launch the "reset" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        self._running = 0
        HWR.beamline.sample_changer._set_state(AbstractSampleChanger.SampleChangerState.Ready)










    @set_running
    def _do_dry_gripper(self):
        """
        Launch the "dry" command


        :returns: None
        :rtype: None
        """
        return self._cmdDry()
        # return self._do_dry0()
    @set_running
    def _do_home(self):
        """
        robot initialize
        会将是否close lid的flag恢复为false
        """
        HWR.beamline.sample_changer.change_ifcloseLid_inBeginning_state(False)
        return self._cmdHome()

    @if_running
    @set_running
    def _do_clear_memory(self):
        """
        clear robot memory
        """
        # 清除系统存储的上样样品
        HWR.beamline.sample_changer.clear_memory()
        # 清除机械手存储的上样样品
        return self._cmdClearMemory()


    @if_ErrorCode
    def _do_cmdOpenlid(self):
        return self._cmdOpenlid()

    @if_ErrorCode
    def _do_cmdCloselid(self):
        return self._cmdCloselid()

    @if_running_closelid
    @set_running_closelid
    def _do_lid1_state(self, state):
        """
        Opens lid 1 if >state< == True, closes the lid otherwise
        when close：
                会将是否close lid的flag设置为True
        """
        print("open or close lid function")
        if state:
            self._ifcmdSucceeded = self._do_cmdOpenlid()


        elif state == False:
            HWR.beamline.sample_changer.change_ifcloseLid_inBeginning_state(True)
            self.change_message_error("Nothing to report")
            self._ifcmdSucceeded  = self._do_cmdCloselid()

        print("self._ifcmdSucceeded:", self._ifcmdSucceeded, type(self._ifcmdSucceeded))
        if (type(self._ifcmdSucceeded) is Exception) or (type(self._ifcmdSucceeded) is OSError) or (
                type(self._ifcmdSucceeded) is TimeoutError) or (type(self._ifcmdSucceeded) is KeyError):
            # 在发生错误后恢复机械手的各种状态
            self._do_reset()
            self._update_global_state()
            # 翻译来自机械手的errorCode
            if type(self._ifcmdSucceeded) is Exception:
                self._ifcmdSucceeded = str(self._ifcmdSucceeded)
                self._ifcmdSucceeded = HWR.beamline.sample_changer._paraphrase_errorCode(self._ifcmdSucceeded)
            logging.getLogger("user_level_log").error(
                "ErrorCode from robot: %s, please contact the teacher on duty" % self._ifcmdSucceeded)
            raise Exception(f"ErrorCode from robot: {self._ifcmdSucceeded}, please contact the teacher on duty")

        else:
            print("res,与__call__的返回值信息应该一样",self._ifcmdSucceeded)
            self._lid1state = state
            self._update_lid1_state(state)
        return self._ifcmdSucceeded
        # if res:
        #     print("res,与__call__的返回值信息应该一样",res)
        #     self._lid1state = state
        #     self._update_lid1_state(state)
        # return res




    def _do_set_on_diff(self, sample):
        """
        Launch the "setondiff" command on the CATS Tango DS, an example of sample value is 2:05

        :returns: None
        :rtype: None
        """

        if sample is None:
            raise Exception("No sample selected")
        else:
            str_tmp = str(sample)
            sample_tmp = str_tmp.split(":")
            # calculate CATS specific lid/sample number
            lid = (int(sample_tmp[0]) - 1) / 3 + 1
            puc_pos = ((int(sample_tmp[0]) - 1) % 3) * 10 + int(sample_tmp[1])
            argin = [str(lid), str(puc_pos), "0"]
            logging.getLogger().info("to SetOnDiff %s", argin)
            # self._execute_server_task(self._cmdSetOnDiff,argin)

    def _do_power_state(self, state=False):
        """
        Switch on CATS power if >state< == True, power off otherwise

        :returns: None
        :rtype: None
        """
        self._powered = state
        self._update_powered_state(state)

    def _do_enable_regulation(self):
        """
        Switch on CATS regulation

        :returns: None
        :rtype: None
        """
        self._regulating = True
        self._update_regulation_state(True)

    def _do_disable_regulation(self):
        """
        Switch off CATS regulation

        :returns: None
        :rtype: None
        """
        self._regulating = False
        self._update_regulation_state(False)





    # def _do_lid2_state(self, state=True):
    #     """
    #     Opens lid 2 if >state< == True, closes the lid otherwise
    #
    #     :returns: None
    #     :rtype: None
    #     """
    #     self._lid2state = state
    #     self._update_lid2_state(state)
    #
    # def _do_lid3_state(self, state=True):
    #     """
    #     Opens lid 3 if >state< == True, closes the lid otherwise
    #
    #     :returns: None
    #     :rtype: None
    #     """
    #     self._lid3state = state
    #     self._update_lid3_state(state)

    #########################          PROTECTED          #########################

    def _execute_task(self, wait, method, *args):
        ret = self._run(method, *args)
        if wait:
            return ret.get()
        else:
            return ret

    @task
    def _run(self, method, *args):
        exception = None
        ret = None
        try:
            ret = method(*args)
        except Exception as ex:
            exception = ex
        if exception is not None:
            raise exception  # pylint: disable-msg=E0702
        return ret

    #########################           PRIVATE           #########################

    def _update_running_state(self, value):
        self._running = value
        self.emit("runningStateChanged", (value,))
        self._update_global_state()

    def _update_powered_state(self, value):
        self._powered = value
        self.emit("powerStateChanged", (value,))
        self._update_global_state()

    def _update_tool_state(self, value):
        self._toolopen = value
        self.emit("toolStateChanged", (value,))
        self._update_global_state()

    def _update_message(self, value):
        self._message = value
        self.emit("messageChanged", (value,))
        self._update_global_state()

    def _update_regulation_state(self, value):
        self._regulating = value
        self.emit("regulationStateChanged", (value,))
        self._update_global_state()

    def _update_state(self, value):
        self._state = value
        self._update_global_state()

    def _update_lid1_state(self, value):
        self._lid1state = value
        # self.emit("lid1StateChanged", (value,))
        # self.emit("lid1StateChanged12345", (value,))
        self._update_global_state()

    # def _update_lid2_state(self, value):
    #     self._lid2state = value
    #     self.emit("lid2StateChanged", (value,))
    #     self._update_global_state()
    #
    # def _update_lid3_state(self, value):
    #     self._lid3state = value
    #     self.emit("lid3StateChanged", (value,))
    #     self._update_global_state()

    def _update_operation_mode(self, value):
        self._charging = not value

    def _update_global_state(self):
        # print("进入_update_global_state函数")
        state_dict, cmd_state, message = self.get_global_state()
        self.emit("globalStateChanged", (state_dict, cmd_state, message))

    def get_global_state(self):
        """
        Update clients with a global state that
        contains different:

        - first param (state_dict):
            collection of state bits

        - second param (cmd_state):
            list of command identifiers and the
            status of each of them True/False
            representing whether the command is
            currently available or not

        - message
            a message describing current state information
            as a string
        """
        _ready = str(self._state) in ("READY", "ON")

        if self._running:
            state_str = "MOVING"
        elif not (self._powered) and _ready:
            state_str = "DISABLED"
        elif _ready:
            state_str = "READY"
        else:
            state_str = str(self._state)

        state_dict = {
            "toolopen": self._toolopen,
            "powered": self._powered,
            "running": self._running,
            "regulating": self._regulating,
            "lid1": self._lid1state,
            "lid2": self._lid2state,
            "lid3": self._lid3state,
            "state": state_str,
        }

        cmd_state = {
            "powerOn": (not self._powered) and _ready,
            "powerOff": (self._powered) and _ready,
            "regulon": (not self._regulating) and _ready,
            "openlid1": (not self._lid1state) and self._powered and _ready,
            "closelid1": self._lid1state and self._powered and _ready,
            "dry": (not self._running) and self._powered and _ready,
            "soak": (not self._running) and self._powered and _ready,
            "home": (not self._running) and self._powered and _ready,
            "back": (not self._running) and self._powered and _ready,
            "safe": (not self._running) and self._powered and _ready,
            "clear_memory": True,
            "reset": True,
            "abort": self._running,
        }

        message = self._message

        return state_dict, cmd_state, message

    def get_cmd_info(self):
        """return information about existing commands for this object
        the information is organized as a list
        with each element contains
        [ cmd_name,  display_name, category ]
        """
        """ [cmd_id, cmd_display_name, nb_args, cmd_category, description ] """
        # cmd_list = [
        #     [
        #         "Power",
        #         [
        #             ["powerOn", "PowerOn", "Switch Power On"],
        #             ["powerOff", "PowerOff", "Switch Power Off"],
        #             ["regulon", "Regulation On", "Swich LN2 Regulation On"],
        #         ],
        #     ],
        #     [
        #         "Lid",
        #         [
        #             ["openlid1", "Open Lid", "Open Lid"],
        #             ["closelid1", "Close Lid", "Close Lid"],
        #         ],
        #     ],
        #     [
        #         "Actions",
        #         [
        #             ["home", "Home", "Actions", "Home (trajectory)"],
        #             ["dry", "Dry", "Actions", "Dry (trajectory)"],
        #             ["soak", "Soak", "Actions", "Soak (trajectory)"],
        #         ],
        #     ],
        #     [
        #         "Recovery",
        #         [
        #             [
        #                 "clear_memory",
        #                 "Clear Memory",
        #                 "Clear Info in Robot Memory "
        #                 " (includes info about sample on Diffr)",
        #             ],
        #             ["reset", "Reset Message", "Reset Cats State"],
        #             ["back", "Back", "Reset Cats State"],
        #             ["safe", "Safe", "Reset Cats State"],
        #         ],
        #     ],
        #     ["Abort", [["abort", "Abort", "Abort Execution of Command"]]],
        # ]
        cmd_list = [
            [
                "Power",
                [
                    ["powerOn", "PowerOn", "Switch Power On"],
                    ["powerOff", "PowerOff", "Switch Power Off"],
                    # ["regulon", "Regulation On", "Swich LN2 Regulation On"],
                ],
            ],
            [
                "Lid",
                [
                    ["openlid1", "Open Lid", "Open Lid"],
                    ["closelid1", "Close Lid", "Close Lid"],
                ],
            ],
            [
                "Actions",
                [
                    ["home", "Home", "Actions", "Home (trajectory)"],
                    ["dry", "Dry", "Actions", "Dry (trajectory)"],
                    # ["soak", "Soak", "Actions", "Soak (trajectory)"],
                ],
            ],
            [
                "Recovery",
                [
                    [
                        "clear_memory",
                        "Clear Memory",
                        "Clear Info in Robot Memory "
                        " (includes info about sample on Diffr)",
                    ],
                    # ["reset", "Reset Message", "Reset Cats State"],
                    # ["back", "Back", "Reset Cats State"],
                    # ["safe", "Safe", "Reset Cats State"],
                ],
            ],
            ["Abort", [["abort", "Abort", "Abort Execution of Command"]]],
        ]
        return cmd_list

    def _execute_server_task(self, method, *args):
        task_id = method(*args)
        ret = None
        # introduced wait because it takes some time before the attribute PathRunning is set
        # after launching a transfer
        # after setting refresh in the Tango DS to 0.1 s a wait of 1s is enough
        time.sleep(1.0)
        while str(self._chnPathRunning.get_value()).lower() == "true":
            gevent.sleep(0.1)
        ret = True
        return ret

    def send_command(self, cmd_name, args=None):

        #
        lid = 1
        toolcal = 0
        tool = self.get_current_tool()

        if cmd_name == "dry":

            self._do_dry_gripper()
        if cmd_name == "home":
            self._do_home()
        if cmd_name == "safe":
            pass



        if cmd_name == "soak":
            if tool in [TOOL_DOUBLE_GRIPPER, TOOL_UNIPUCK]:
                args = [str(tool), str(lid)]
            else:
                raise Exception("Can SOAK only when UNIPUCK tool is mounted")

        if cmd_name == "back":
            if tool is not None:
                args = [tool, toolcal]
            else:
                raise Exception("Cannot detect type of TOOL in Cats. Command ignored")

        if cmd_name == "powerOn":
            logging.getLogger("HWR").debug(
                "powerOn命令 %d" % (1)
            )
            self._do_power_state(True)

        if cmd_name == "powerOff":
            self._do_power_state(False)

        # if cmd_name == "regulon":
        #     self._do_enable_regulation()
        # if cmd_name == "reguloff":
        #     self._do_disable_regulation()
        if cmd_name == "openlid1":
            self._do_lid1_state(True)

        if cmd_name == "closelid1":
            self._do_lid1_state(False)
        if cmd_name == "clear_memory":
            self._do_clear_memory()
        if cmd_name == "abort":
            print("abort")
            self._do_abort()
        # if cmd_name == "safe":
        #     print("abort")
        #     self._do_abort()

        return True


def test_hwo(hwo):
    print((hwo.get_current_tool()))
