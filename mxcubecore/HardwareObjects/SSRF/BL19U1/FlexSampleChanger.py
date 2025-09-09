import gevent
from datetime import datetime
import time
import logging
import traceback

from mxcubecore.HardwareObjects.abstract import AbstractSampleChanger
from mxcubecore.HardwareObjects.abstract.sample_changer import Container
from mxcubecore import HardwareRepository as HWR
from mxcubecore.queue_entry.base_queue_entry import CENTRING_METHOD





def if_running_sc(func):
    """
    装饰器函数，用于取样上样时，进行判断，如果机械手在运行，则不操作直接返回（因为前端界面没有禁用按钮）
    """

    def wrapper(self, sample, wait=False):
        if HWR.beamline.sample_changer_maintenance.running == 1:
            logging.getLogger("user_level_log").info(
                "机械手正在运动，请稍后操作"
            )
            return
        return func(self, sample, wait)

    return wrapper


def set_running_sc(func):
    """
    装饰器函数，在机械手通过此py文件运动时，设置CatsMaintMockup.py 中的 CatsMaintMockup类 的 self._running为1
    """

    def wrapper(self, sample, wait):
        # 设置机械手在运动
        HWR.beamline.sample_changer_maintenance.change_running_state(1)
        HWR.beamline.sample_changer_maintenance._update_global_state()
        # print("设置完running状态：",HWR.beamline.sample_changer_maintenance.running)

        try:
            res = func(self, sample, wait)  # command的返回值ret,命令运行成功应该会返回机械手的返回信息，如果没有连通机械手返回False
        except Exception as e:
            raise e
        finally:
            # 结束机械手运动状态
            HWR.beamline.sample_changer_maintenance._running = 0
            HWR.beamline.sample_changer_maintenance._update_global_state()
        if self._ifcmdSucceeded:
            self._ifcmdSucceeded = False
            return res
        else:
            print('self._ifcmdSucceeded in wrapper')
            logging.getLogger("HWR").error(
                "socket timeout, please check the network connection"
            )
            # 这个raise Exception要加，因为samplechanger.py的mount_sample_clean_up有个try判断
            raise Exception("socket timeout, please check the network connection")

    return wrapper


def if_ErrorCode(func):
    """
    装饰器函数，用于当发送机械手命令，机械手返回报错时，获取报错信息，返回给load或者unload
    """

    def wrapper(self, *args):
        try:
            res = func(self, *args)
        except Exception as e:
            print("type(e) from if_ErrorCode:", type(e))
            print("e from if_ErrorCode::", e)
            errorCode = e
            return errorCode
        else:
            return res

    return wrapper


class FlexSampleChanger(AbstractSampleChanger.SampleChanger):
    __TYPE__ = "Flex"
    NO_OF_BASKETS = 37
    NO_OF_SAMPLES_IN_BASKET = 16

    def __init__(self, *args, **kwargs):
        super(FlexSampleChanger, self).__init__(self.__TYPE__, False, *args, **kwargs)

    def init(self):
        self._selected_sample = -1
        self._selected_basket = -1
        self._scIsCharging = None
        self.centring_method = "AUTO_LOOP"
        # self.use_magnet = self.getproperty("")

        self.no_of_baskets = self.get_property(
            "no_of_baskets", FlexSampleChanger.NO_OF_BASKETS
        )

        self.no_of_samples_in_basket = self.get_property(
            "no_of_samples_in_basket", FlexSampleChanger.NO_OF_SAMPLES_IN_BASKET
        )

        for i in range(self.no_of_baskets):
            basket = Container.Basket(
                self, i + 1, samples_num=self.no_of_samples_in_basket
            )
            self._add_component(basket)

        self._init_sc_contents()
        self.signal_wait_task = None
        AbstractSampleChanger.SampleChanger.init(self)

        self.log_filename = self.get_property("log_filename")

        self._dewar = 1
        # self.socket_addr = '10.30.61.73:10100'
        self.exporter_addr = '10.30.61.74:9001'
        self._ifcloseLid_inBeginning = True
        self.count = 1
        self.pulling_state_flex_flag = True



        # self._cmdExchange = self.add_command(
        #     {"type": "socketrobot", "socket_address": self.socket_addr, "name": '_cmdExchange'},
        #     'Exchange'
        # )
        #
        self._cmdExchange = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "chainedUnldLd",
            },
            "chainedUnldLd",
        )
        self._cmdLoadSample = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "loadSample",
            },
            "loadSample",
        )
        self._cmdUnLoadSample = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "unloadSample",
            },
            "unloadSample",
        )
        self._cmdGetState = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "getState",
            },
            "getState",
        )
        self._cmdGetStatus = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "getStatus",
            },
            "getStatus",
        )

        self._cmdGetSamplePoolLN2Level = self.add_command(
            {
              "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "getSamplePoolLN2Level",
            },
            "getSamplePoolLN2Level"
        )

        self._cmdGetMountedSamplePosition = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "getMountedSamplePosition",
            },
            "getMountedSamplePosition",
        )
        self._cmdGetPresentSamples = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "getPresentSamples",
            },
            "getPresentSamples",
        )

        self._cmdCheckTaskResult=self.add_command(
              {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "checkTaskResult",
            },
            "checkTaskResult",
        )

        self._cmdGetLastTaskException = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "getLastTaskException",
            },
            "getLastTaskException",
        )

        self._cmdGetCurrentLoadSampleState =self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "getCurrentLoadSampleState",
            },
            "getCurrentLoadSampleState",
        )



        self._ifcmdSucceeded = False
        self.first_launch_mxcube = True  # 添加
        self.if_check_mountedPin_from_camerman = False
        self.write_sample_dir()  # 加载sample的prefix和subdir
        self.get_loaded_sample_fromstart()

    def pulling_state_flex(self):
        while self.pulling_state_flex_flag:
            time.sleep(0.05)
            try:
                if self._ready():
                    self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
                    if HWR.beamline.sample_changer_maintenance._running != 0:
                        HWR.beamline.sample_changer_maintenance._update_running_state(0)
                else:
                    self._set_state(AbstractSampleChanger.SampleChangerState.Moving)
                    if HWR.beamline.sample_changer_maintenance._running != 1:
                        HWR.beamline.sample_changer_maintenance._update_running_state(1)
            except Exception:
                pass

            try:
                current_status = self._do_getStatus()
                self._set_status(current_status)
            except Exception:
                pass

            try:
                current_sample_pool_LN2_level = self._do_getSamplePoolLN2Level()
                self._set_sampleLN2Level(current_sample_pool_LN2_level)
            except Exception:
                pass



    def write_sample_dir(self):  # 添加
        """
        将目录从sc.xml写入二维列表
        self.proteinAcronym与
        self.default_pre_cmdGetMountedSamplePositionfix
        """
        self.proteinAcronym = [["0" for j in range(self.no_of_samples_in_basket)] for i in range(self.no_of_baskets)]
        for i in range(len(self.proteinAcronym)):
            for j in range(self.no_of_samples_in_basket):
                xmlName = "subdir" + str(i + 1) + "-" + str(j + 1)  # "subdir5-2"
                self.proteinAcronym[i][j] = self.get_property(xmlName)

        self.default_prefix = [["0" for j in range(self.no_of_samples_in_basket)] for i in range(self.no_of_baskets)]
        for i in range(len(self.default_prefix)):
            for j in range(self.no_of_samples_in_basket):
                xmlName = "prefix" + str(i + 1) + "-" + str(j + 1)  # "subdir5-2"
                self.default_prefix[i][j] = self.get_property(xmlName)

    def change_load_sample(self,sample):
        """
        change load_sample without actual move the robot, just change the setting in mxcube inside
        sample should be '1:01'
        """
        previous_sample = self.get_loaded_sample()
        self._reset_loaded_sample()
        puck,pin = sample.split(":")
        self._selected_basket = puck = int(puck)
        self._selected_sample = pin = int(pin)

        mounted_sample = self.get_component_by_address(
            Container.Pin.get_sample_address(puck, pin)
        )

        if mounted_sample is not previous_sample:
            self._trigger_loaded_sample_changed_event(mounted_sample)
        self.update_info()
        self.emit("fsmConditionChanged", "sample_is_loaded", True)
        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", False)



    def checkTaskResult(self,task_id):
        print('task_id in checkTaskResult: ',task_id,type(task_id))
        taskRes = self._cmdCheckTaskResult(task_id)    #id
        print('taskRes: ',taskRes)
        if taskRes < 0  :
            taskExceptionRes = self._cmdGetLastTaskException()
            print('taskExceptionRes: ',taskExceptionRes)
            raise Exception("error in task: "+taskExceptionRes)

    @if_ErrorCode
    def _do_mount(self, magazine, position,wait=True,timeout=None):
        # return self._cmdMount(magazine=magazine, position=position)
        # print('type o_cmdGetMountedSamplePositionf magazion and position: ',type(magazine),type(position))
        parm = '1\t'+str(magazine)+'\t'+str(position)
        # print('load parameter: ',parm)
        res = self._cmdLoadSample(parm)
        if wait:

            self.wait_centring_ready_when_load(magazine,position,res,timeout)
        return res

    @if_ErrorCode
    def _do_unmount(self, magazine, position,wait=True,timeout=None):
        # return self._cmdUnMount(magazine=magazine, position=position)
        parm = '1\t' + str(magazine) + '\t' + str(position)
        res = self._cmdUnLoadSample(parm)
        if wait:
            self.wait_ready(timeout)
            self.checkTaskResult(res)
        return res
    @if_ErrorCode
    def _do_exchange(self, oldMagazine, oldPosition, newMagazine, newPosition,wait=True,timeout = None):
        print("oldMagazine,oldPosition,NewMagazine,NewPosition:", oldMagazine, oldPosition, newMagazine, newPosition)
        # parm = [1,oldMagazine,oldPosition,1,newMagazine,newPosition]
        parm = '1\t' + str(newMagazine) + '\t' + str(newPosition)
        print("parm in exchange method and typeof(parm): ",parm,type(parm))
        res = self._cmdLoadSample(parm)
        MD2 = HWR.beamline.diffractometer
        print('current phase and state of md2: ', MD2.get_current_phase(), MD2.get_state())
        if wait:
            print("waiting the return message")
            self.wait_centring_ready_when_load(newMagazine, newPosition, res, timeout)
        return res



    @if_ErrorCode
    def _do_getMountedSamplePosition(self,wait=True,timeout=None):
        res = self._cmdGetMountedSamplePosition()
        # no wait no task
        return res

    @if_ErrorCode
    def _do_getState(self):
        """
        获取机械手状态，只有moving and ready
        """
        res = self._cmdGetState()
        # print('get status of flex robot: ',res)
        return res
    @if_ErrorCode
    def _do_getStatus(self):
        """
        获取机械手各种状态
        """
        res = self._cmdGetStatus()
        return res
    @if_ErrorCode
    def _do_getSamplePoolLN2Level(self):
        res = self._cmdGetSamplePoolLN2Level()
        return res

    def _ready(self):
        """
        判断是否ready
        return: True / False
        """
        state = self._do_getState()
        if state == 'Ready':
            return True
        else:
            return False

    def wait_ready(self, timeout=None):
        # None means infinite timeout
        # <=0 means default timeout
        if timeout is not None and timeout <= 0:
            logging.getLogger("HWR").warning(
                "DEBUG: Strange timeout value passed %s" % str(timeout)
            )
            timeout = 30
        with gevent.Timeout(
            timeout, RuntimeError("Timeout waiting for FlexRobot to be ready")
        ):
            while not self._ready():
                time.sleep(0.5)

    def wait_centring_ready_when_load(self,puck_num,pin_num,task_id,timeout=None):
        MD2 = HWR.beamline.diffractometer
        timeout = 300
        if timeout is not None and timeout <= 0:
            logging.getLogger("HWR").warning(
                "DEBUG: Strange timeout value passed %s" % str(timeout)
            )
            print("set timeout = 30 in wait_centring_ready_when_load")
            timeout = 30
        with gevent.Timeout(
                timeout, RuntimeError("Timeout waiting for FlexRobot to be ready")
        ):
            print('current phase and state of md2 in wait centring ready: ',MD2.get_current_phase(),MD2.get_state())

            # while MD2.get_current_phase() != "Transfer":
            #     time.sleep(0.5)
            # print('current phase and state of md2: ', MD2.get_current_phase(), MD2.get_state())
            # while MD2.get_current_phase() != "Centring" or MD2.get_state() =='Running':
            #     print("MD2.get_current_phase() and MD2.get_state(): ",MD2.get_current_phase(),MD2.get_state())
            #     time.sleep(0.5)

            while True:
                load_sample_state = self._cmdGetCurrentLoadSampleState()
                # print("in while true, load_sample_state: ")
                time.sleep(0.3)
                if load_sample_state == 'on_gonio' and MD2.get_state() =='Ready':
                    break
                if self._ready():
                    self.checkTaskResult(task_id)

            res = self._do_getMountedSamplePosition()
            if res[1]==puck_num and res[2]==pin_num:
                print("sample is ready to centring")
            else:
                self.checkTaskResult(task_id)



    def get_log_filename(self):
        return self.log_filename

    def load_sample(self, holder_length, sample_location=None, wait=False):
        print("进入ActorSampleChanger.py的load_sample函数")
        self.load(sample_location, wait)

    @property
    def ifcloseLid_inBeginning(self):
        return self._ifcloseLid_inBeginning

    def change_ifcloseLid_inBeginning_state(self, state: bool):
        self._ifcloseLid_inBeginning = state

    def MD2_Centring(self):
        # pass
        HWR.beamline.diffractometer.set_phase("Centring")
        HWR.beamline.diffractometer._wait_ready(30000)
        if self.centring_method == "AUTO_LOOP":
            logging.getLogger("HWR").info("CENTRING_METHOD: auto LOOP CENTRING")
            HWR.beamline.diffractometer.start_auto_sample_centring("LOOP_CENTRING_ONLY")
        elif self.centring_method == "MANUAL":
            logging.getLogger("HWR").info("CENTRING_METHOD: MANUAL CENTRING")

    def test_exception(self):
        try:
            raise ConnectionRefusedError
        except Exception as e:
            return e

    @if_running_sc
    @set_running_sc
    def exchange(self, newsample, wait=False):
        print("进入exchange函数")

        # 检查md2
        # self.check_MD2_state()
        # self.check_MD2_Magnet()

        oldsample = self.get_loaded_sample().get_address()
        print("oldsample: ", oldsample, "newsample: ", newsample)
        # print(type(oldsample),type(newsample)) # 两个str
        oldBasket, oldSample = oldsample.split(":")
        newBasket, newSample = newsample.split(":")

        # 清除oldsample 的 loaded属性
        self.get_loaded_sample()._set_loaded(False, True)  # def _set_loaded(self, loaded, has_been_loaded=None):


        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", True)



        newBasket = int(newBasket)
        newSample = int(newSample)
        oldBasket = int(oldBasket)
        oldSample = int(oldSample)

        msg = "Exchanging sample %d:%d" % (newBasket, newSample)
        logging.getLogger("user_level_log").info(
            "Sample changer: %s. Please wait..." % msg
        )
        # print("before self.emit(progressInit, (msg, 100))")
        self.emit("progressInit", (msg, 100))
        # print("self.emit(progressInit, (msg, 100)) ended")
        print("before self.emit(progressStep,int(step/2))")
        for step in range(2 * 100):
            self.emit("progressStep", int(step / 2.0))
            # time.sleep(0.001)      #不知道为什么要有这行，但这行原来是time.sleep(0.01)拖漫了大概有14s的时间,改成0.001从2s变到5s左右
        print("self.emit(progressStep,int(step/2)) ended")




        print("oldSample!=newSample or oldBasket != newSample:", oldSample != newSample or oldBasket != newBasket)
        if oldSample != newSample or oldBasket != newBasket:
            # 判断真实命令是否发送成功,_ifcmdSucceeded可能是机械手的返回信息，或者是因为socket连接问题所返回的False,
            # 如果机械手返回信息有报错，在cmd函数中就会raise exception,然后会在if_ErrorCode函数中(转换为int?)传递过来
            self._ifcmdSucceeded = self._do_exchange(oldBasket, oldSample, newBasket, newSample)
            print("DEBUG!!!self._ifcmdSucceeded:", self._ifcmdSucceeded, type(self._ifcmdSucceeded))


            # self._ifcmdSucceeded = self.test_exception() #测试bug用

            # 处理返回的_ifcmdSucceeded信息
            # 如果命令返回False说明是socket连接没有连上
            if self._ifcmdSucceeded == False:
                print('_ifcmdSucceeded is false.')
                self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
                return
            # 如果命令返回的类型是Exception，说明是机械手有报错
            # 20230714 添加新异常：<ConnectionRefusedError>
            elif (type(self._ifcmdSucceeded) is Exception) or (type(self._ifcmdSucceeded) is OSError) or (
                    type(self._ifcmdSucceeded) is TimeoutError) or (type(self._ifcmdSucceeded) is KeyError) or (
                    type(self._ifcmdSucceeded) is ConnectionRefusedError) or (
                    type(self._ifcmdSucceeded) is ConnectionAbortedError) or (
                    type(self._ifcmdSucceeded) is ConnectionResetError) or (
                    type(self._ifcmdSucceeded) is BrokenPipeError) or(
                    type(self._ifcmdSucceeded) is RuntimeError):
                # 在发生错误后恢复机械手的各种状态
                print("there is some error with exchange command, start try to restore status")
                # 20240101 add x 3
                self.update_info()
                self.emit("progressStop", ())
                self.emit("fsmConditionChanged", "sample_mounting_sample_changer", True)

                self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
                HWR.beamline.sample_changer_maintenance._running = 0
                HWR.beamline.sample_changer_maintenance._update_global_state()


                self._ifcmdSucceeded = str(self._ifcmdSucceeded)
                logging.getLogger("user_level_log").error(
                    "ErrorCode from robot: %s,  " % self._ifcmdSucceeded)
                raise Exception(f"ErrorCode from robot: {self._ifcmdSucceeded},  ")


            # 命令完成
            mounted_sample = self.get_component_by_address(
                Container.Pin.get_sample_address(newBasket, newSample)
            )
            self._trigger_loaded_sample_changed_event(mounted_sample)
            self._selected_basket = newBasket
            self._selected_sample = newSample
            self.send_sample_address_to_statemessage()
        # exchange的是同一个或者exchange完成
        self.update_info()
        logging.getLogger("user_level_log").info("Sample changer: Sample loaded")
        self.emit("progressStop", ())

        self.emit("fsmConditionChanged", "sample_is_loaded", True)
        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", False)

        self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
        print("self.get_loaded_sample().get_address()", self.get_loaded_sample().get_address())
        # 计数
        self.count += 1

        # 上完样品，md2 变为centering
        self.MD2_Centring()

        return self.get_loaded_sample()

    def change_MD2_state(self, timeout=3):
        MD2 = HWR.beamline.diffractometer
        if MD2.get_current_phase() != "Transfer":
            MD2.set_phase("Transfer", wait=True)
            time.sleep(0.5)
            print("切换完成")
        gevent.sleep(timeout)
        if MD2.get_current_phase() == "Transfer":
            return True
        else:
            return False

    def change_Cryo_state(self, timeout=1):
        MD2 = HWR.beamline.diffractometer
        MD2.Cryo_Is_Back.set_value(True)

    def check_MD2_state(self):
        MD2 = HWR.beamline.diffractometer
        # 判断是否在对的phase
        if not self.change_MD2_state():
            logging.getLogger("user_level_log").error(
                "The MD2 seems cannot change to sample change status while mounting, please try again first.")
            raise Exception(
                "The MD2 seems cannot change to sample change status while mounting, please try again first.")
        # 判断cryo是否在对的位置
        # self.change_Cryo_state()
        # logging.getLogger("HWR").info("Cryo state: %s ", str(MD2.Cryo_Is_Back.get_value()))
        # if MD2.Cryo_Is_Back.get_value() != True:
        #     logging.getLogger("user_level_log").error(
        #         "The cryo seems cannot change to back position while mounting, ")
        #     raise Exception(
        #         "The cryo seems cannot change to back position while mounting, ")
        # else:
        #     print("get into safe waiting time for 0.5 second")
        #     time.sleep(0.5)
        #     print("safe waiting time ended")

    def check_MD2_Magnet(self):
        MD2 = HWR.beamline.diffractometer
        # print("smart magnet: "+str(MD2.sample_isloaded_magnet.get_value()))
        logging.getLogger("HWR").info("smart magnet state: %s", str(MD2.sample_isloaded_magnet.get_value()))
        if MD2.sample_isloaded_magnet.get_value():
            logging.getLogger("user_level_log").error(
                "The smart magnet says there's a sample already been mounted, if there's not, please contact the teacher on duty")
            raise Exception(
                "The smart magnet says there's a sample already been mounted, if there's not, please contact the teacher on duty")

    @if_running_sc
    @set_running_sc
    def load(self, sample, wait=False):
        print("进入load函数")


        #
        # 如果在dwear里，就可以直接设置为已经closelid了 (代码以删除)
        # 先判断是否closelid了，flex不需要类似于 close lid 的操作，注释
        # if not self._ifcloseLid_inBeginning:
        #     # 恢复各种状态
        #     HWR.beamline.sample_changer_maintenance._running = 0
        #     HWR.beamline.sample_changer_maintenance._update_global_state()
        #
        #     logging.getLogger("user_level_log").error(
        #         "please close the lid first")  # doesn't work,can show on log message, don't know why
        #     logging.getLogger("HWR").debug("please close the lid first")
        #     self.send_msg_to_statemessage("please close the lid first")
        #     HWR.beamline.sample_changer_maintenance._update_global_state()
        #     raise Exception("please close the lid first")


        # 判断md2 flex do not need
        # self.check_MD2_state()
        # self.check_MD2_Magnet()

        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", True)
        previous_sample = self.get_loaded_sample()

        # 原来的位置,为了显示abort按钮和提示栏，把这两行注释掉 self._reset_loaded_sample() 应该是把所有sample执行sample._set_loaded(False)
        # self._set_state(AbstractSampleChanger.SampleChangerState.Loading)   #把 abort按钮给消失了
        # self._reset_loaded_sample()     # 把提示栏消失了

        if isinstance(sample, tuple):
            basket, sample = sample
        else:
            basket, sample = sample.split(":")

        self._selected_basket = basket = int(basket)
        self._selected_sample = sample = int(sample)
        self.send_sample_address_to_statemessage()

        msg = "Loading sample %d:%d" % (basket, sample)
        logging.getLogger("user_level_log").info(
            "Sample changer: %s. Please wait..." % msg
        )
        time_before_emit_progressInit = time.time()
        self.emit("progressInit", (msg, 100))
        time_after_emit_progressInit = time.time()
        for step in range(2 * 100):
            self.emit("progressStep", int(step / 2.0))
            # time.sleep(0.01)            #不知道为什么要有这行，但这行原来是time.sleep(0.01)拖漫了大概有14s的时间,改成0.001从2s变到5s左右
        time_after_emit_progressStep = time.time()
        logging.getLogger("HWR").info("the time cost by emit progressInit and progressStrp: %s,%s",
                                      str(time_after_emit_progressInit - time_before_emit_progressInit)
                                      , str(time_after_emit_progressStep - time_after_emit_progressInit))

        mounted_sample = self.get_component_by_address(
            Container.Pin.get_sample_address(basket, sample)
        )
        # self._set_state(AbstractSampleChanger.SampleChangerState.Ready) #原来的位置

        if mounted_sample is not previous_sample:
            # 判断真实命令是否发送成功,_ifcmdSucceeded可能是机械手的返回信息，或者是因为socket连接问题所返回的False,
            # 如果机械手返回信息有报错，在cmd函数中就会raise exception,然后会在if_ErrorCode函数中(转换为int?)传递过来

            self._ifcmdSucceeded = self._do_mount(basket, sample)
            print("self._ifcmdSucceeded:", self._ifcmdSucceeded, type(self._ifcmdSucceeded))

            # 处理返回的_ifcmdSucceeded信息
            # 如果命令返回False说明是socket连接没有连上
            if self._ifcmdSucceeded == False:
                self._selected_sample = -1
                self._selected_basket = -1
                self.send_sample_address_to_statemessage()

                self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
                return

            # 如果命令返回的类型是Exception，说明是机械手有报错
            elif (type(self._ifcmdSucceeded) is Exception) or (type(self._ifcmdSucceeded) is OSError) or (
                    type(self._ifcmdSucceeded) is TimeoutError) or (type(self._ifcmdSucceeded) is KeyError) or (
                    type(self._ifcmdSucceeded) is ConnectionRefusedError) or (
                    type(self._ifcmdSucceeded) is ConnectionAbortedError) or (
                    type(self._ifcmdSucceeded) is ConnectionResetError) or (
                    type(self._ifcmdSucceeded) is BrokenPipeError) or(
                    type(self._ifcmdSucceeded) is RuntimeError):
                # 在发生错误后恢复机械手的各种状态
                self._selected_sample = -1
                self._selected_basket = -1
                self.send_sample_address_to_statemessage()

                # 20240101 add x 3
                self.update_info()
                self.emit("progressStop", ())
                self.emit("fsmConditionChanged", "sample_mounting_sample_changer", False)

                self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
                HWR.beamline.sample_changer_maintenance._running = 0
                HWR.beamline.sample_changer_maintenance._update_global_state()


                self._ifcmdSucceeded = str(self._ifcmdSucceeded)
                logging.getLogger("user_level_log").error(
                    "ErrorCode from robot: %s,  " % self._ifcmdSucceeded)
                raise Exception(f"ErrorCode from robot: {self._ifcmdSucceeded},  ")

            self._trigger_loaded_sample_changed_event(mounted_sample)

        self.send_sample_address_to_statemessage()

        self.update_info()
        logging.getLogger("user_level_log").info("Sample changer: Sample loaded")
        self.emit("progressStop", ())

        self.emit("fsmConditionChanged", "sample_is_loaded", True)
        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", False)

        self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
        print("self.get_loaded_sample().get_address()", self.get_loaded_sample().get_address())
        # 计数
        self.count += 1

        # 上完样品，md2 变为centering
        self.MD2_Centring()

        return self.get_loaded_sample()

    def unload_error_recover(self):
        """
        在发生错误后恢复机械手的各种状态
        """
        self._trigger_loaded_sample_changed_event(self.get_loaded_sample())
        self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
        HWR.beamline.sample_changer_maintenance._running = 0
        HWR.beamline.sample_changer_maintenance._update_global_state()

    def clear_memory(self):
        """
        用来清除已经上样信息
        """
        # print(HWR.beamline.diffractometer.readPhase.get_value())
        if self.get_loaded_sample():
            sample = self.get_loaded_sample()
            sample._set_loaded(False, True)

        self._selected_basket = -1
        self._selected_sample = -1

        self._trigger_loaded_sample_changed_event(self.get_loaded_sample())
        self.send_sample_address_to_statemessage()

        self.emit("fsmConditionChanged", "sample_is_loaded", False)

    @if_running_sc
    @set_running_sc
    def unload(self, sample_slot=None, wait=None):
        """
        下样函数，（只有不是手动上样的样品点下样后才会进入此函数）
        1.需要先判断系统记录中是否有已经上样的样品，有才能下样
        2.判断需要下样的位置和已上样样品本来所处的位置，如果不一致，报错提示，避免冲突碰撞
        """

        logging.getLogger("user_level_log").info("Unloading sample")

        try:
            logging.getLogger("user_level_log").info(
                "即将把样品下到的位置:" + sample_slot + ",已上样样品本来所处的位置:" + self.get_loaded_sample().get_address())
        except AttributeError:
            logging.getLogger("user_level_log").error("还没有上样，无法取下样品")

            # print("当下样的报错的时候的self.get_loaded_sample()：",self.get_loaded_sample())
            # 下面这行函数会结束load sample，please wait的进度条,真正作用的是
            #         server.emit(
            #             "loaded_sample_changed",
            #             {"address": address, "barcode": barcode},
            #             namespace="/hwr",
            #         )
            #         源码在signals的loaded_sample_changed(sample)函数，传入的get_loaded_sample()为None，所以应该不影响

            # 在发生错误后恢复机械手的各种状态
            self.unload_error_recover()
            raise Exception("Can not unload since there has no sample was mounted")

        # 检查md2
        # self.check_MD2_state()

        if sample_slot == self.get_loaded_sample().get_address():
            logging.getLogger("user_level_log").info("即将把样品下到的位置与已上样样品本来所处的位置一致，开始下样")
        else:
            logging.getLogger("user_level_log").error("即将把样品下到的位置与已上样样品本来所处的位置不一致")

            self.unload_error_recover()
            raise Exception("the location selected is not the same as the location where the mounted sample was taken")

        sample = self.get_loaded_sample()
        sample._set_loaded(False, True)  # def _set_loaded(self, loaded, has_been_loaded=None):

        if self._selected_sample > 0 and self._selected_sample <= 16:
            self._ifcmdSucceeded = self._do_unmount(self._selected_basket, self._selected_sample)
            # 如果命令返回False说明是socket连接没有连上
            if self._ifcmdSucceeded == False:
                self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
                return
            # 如果命令返回的类型是Exception，说明是机械手有报错
            elif (type(self._ifcmdSucceeded) is Exception) or (type(self._ifcmdSucceeded) is OSError) or (
                    type(self._ifcmdSucceeded) is TimeoutError) or (type(self._ifcmdSucceeded) is KeyError) or (
                    type(self._ifcmdSucceeded) is ConnectionRefusedError) or (
                    type(self._ifcmdSucceeded) is ConnectionAbortedError) or (
                    type(self._ifcmdSucceeded) is ConnectionResetError) or (
                    type(self._ifcmdSucceeded) is BrokenPipeError) or(
                    type(self._ifcmdSucceeded) is RuntimeError):

                self.unload_error_recover()
                self._ifcmdSucceeded = str(self._ifcmdSucceeded)
                raise Exception(f"ErrorCode from robot: {self._ifcmdSucceeded},  ")

            self._selected_basket = -1
            self._selected_sample = -1

            self._trigger_loaded_sample_changed_event(self.get_loaded_sample())
            self.send_sample_address_to_statemessage()

            self.emit("fsmConditionChanged", "sample_is_loaded", False)

            # flex dont need make close lid state to false after unload.
            # self.change_ifcloseLid_inBeginning_state(False)
        else:
            logging.getLogger("HWR").debug("cannot unload, the location is wrong")

    def synchronize_with_flex(self):
        # 判断机械手当前状态，如果位置在dewar里，就不用判断close lid
        ret = self._do_getMountedSamplePosition()
        print("self._do_getMountedSamplePosition(): ",ret,type(ret))


        MountedPin = ret

        # # 有样品，相当于换样
        if MountedPin[0] != -1:                 #无样品： [-1,-1,-1]
            self._selected_basket = MountedPin[1]
            self._selected_sample = MountedPin[2]
            # 命令完成
            mounted_sample = self.get_component_by_address(
                Container.Pin.get_sample_address(self._selected_basket, self._selected_sample)
            )
            self._trigger_loaded_sample_changed_event(mounted_sample)

            self.send_sample_address_to_statemessage()
            # exchange的是同一个或者exchange完成
            self.update_info()
            logging.getLogger("user_level_log").info("Sample changer: Sample loaded")

            self.emit("fsmConditionChanged", "sample_is_loaded", True)
            self.emit("fsmConditionChanged", "sample_mounting_sample_changer", False)

        # # 没有样品，相当于下样
        else:
            self._selected_basket = MountedPin[1]   #-1
            self._selected_sample = MountedPin[2]   #-1

            self._trigger_loaded_sample_changed_event(self.get_loaded_sample())
            self.send_sample_address_to_statemessage()

            self.emit("fsmConditionChanged", "sample_is_loaded", False)

        return ret



    def get_loaded_sample_fromstart(self):
        try:
            if self.first_launch_mxcube:
                self.first_launch_mxcube = False
        except AttributeError:
            pass
        else:
            if not self.if_check_mountedPin_from_camerman:
                self.if_check_mountedPin_from_camerman = True
                # self.synchronize_with_camerman()
                # 判断机械手当前状态，如果位置在dewar里，就不用判断close lid

                # 代修改,(原先actor还要判断机械手在不在dwear里来判断要不要close lid)
                print("try to get loaded sample info from flex robot，if it stuck here for a long time, means there's problem of connection between mxcube and flex robot")
                ret = self._cmdGetMountedSamplePosition()
                # ret = self._cmdGetState()
                # print("self._cmdGetStatus")
                print("the result of loaded sample info: ",ret)
                MountedPin = ret
                #无样品： [-1,-1,-1]
                self._selected_basket = MountedPin[1]
                self._selected_sample = MountedPin[2]


    def get_loaded_sample(self):
        # 在mxcube内部查询已上样的样品信息

        return self.get_component_by_address(
            Container.Pin.get_sample_address(
                self._selected_basket, self._selected_sample
            )
        )

    def is_mounted_sample(self, sample):
        return (
                self.get_component_by_address(
                    Container.Pin.get_sample_address(sample[0], sample[1])
                )
                == self.get_loaded_sample()
        )

    def send_msg_to_statemessage(self, msg):
        HWR.beamline.sample_changer_maintenance.change_message_error(msg)

    def send_sample_address_to_statemessage(self):
        try:
            address = self.get_loaded_sample().get_address()
        except AttributeError:
            HWR.beamline.sample_changer_maintenance.change_message_sampleState("None")
        else:
            HWR.beamline.sample_changer_maintenance.change_message_sampleState(address)

    def _do_abort(self):
        return

    def _do_change_mode(self):
        return

    def _do_update_info(self):
        return

    def _do_select(self, component):
        return

    def _do_scan(self, component, recursive):
        return

    def _do_load(self, sample=None):
        return

    def _do_unload(self, sample_slot=None):
        return

    def _do_reset(self):
        return

    def _init_sc_contents(self):
        """
        Initializes the sample changer content with default values.

        :returns: None
        :rtype: None
        """
        named_samples = {}
        if self.has_object("test_sample_names"):
            for tag, val in self["test_sample_names"].get_properties().items():
                named_samples[val] = tag

        for basket_index in range(self.no_of_baskets):
            basket = self.get_components()[basket_index]
            datamatrix = None
            present = True
            scanned = False
            basket._set_info(present, datamatrix, scanned)

        sample_list = []
        for basket_index in range(self.no_of_baskets):
            for sample_index in range(self.no_of_samples_in_basket):
                sample_list.append(
                    (
                        "",
                        basket_index + 1,
                        sample_index + 1,
                        1,
                        Container.Pin.STD_HOLDERLENGTH,
                    )
                )
        for spl in sample_list:
            address = Container.Pin.get_sample_address(spl[1], spl[2])
            sample = self.get_component_by_address(address)
            sample_name = named_samples.get(address)
            if sample_name is not None:
                sample._name = sample_name
            datamatrix = "matr%d_%d" % (spl[1], spl[2])
            present = scanned = loaded = has_been_loaded = False
            sample._set_info(present, datamatrix, scanned)
            sample._set_loaded(loaded, has_been_loaded)
            sample._set_holder_length(spl[4])

        self._set_state(AbstractSampleChanger.SampleChangerState.Ready)



    def notice_for_developer(self):
        """
        1. samplechanger.py 中的 mount_sample_clean_up 与 unmount_sample_clean_up，try之后的exception中有个单独的“raise”,才能把这里raise的报错信息显示在ui界面上
        2. 要让ui界面出现abort按钮应该是要设置 Maint.py里的self._running为1
        """
        pass