import gevent
from datetime import datetime
import time
import logging

from mxcubecore.HardwareObjects.abstract import AbstractSampleChanger
from mxcubecore.HardwareObjects.abstract.sample_changer import Container
from mxcubecore import HardwareRepository as HWR

# MD2 = HWR.beamline.diffractometer

# print(HWR.beamline.sample_changer_maintenance.running)

def if_running_sc(func):
    """
    装饰器函数，用于取样上样时，进行判断，如果机械手在运行，则不操作直接返回（因为前端界面没有禁用按钮）
    """
    def wrapper(self,sample,wait=False):
        if HWR.beamline.sample_changer_maintenance.running == 1:
            logging.getLogger("HWR").debug(
                "机械手正在运动，请稍后操作"
            )
            return
        return func(self,sample,wait)
    return wrapper

def set_running_sc(func):
    """
    装饰器函数，在机械手通过此py文件运动时，设置CatsMaintMockup.py 中的 CatsMaintMockup类 的 self._running为1
    """
    def wrapper(self,sample,wait):
        #设置机械手在运动
        HWR.beamline.sample_changer_maintenance.change_running_state(1)
        HWR.beamline.sample_changer_maintenance._update_global_state()
        # print("设置完running状态：",HWR.beamline.sample_changer_maintenance.running)

        res = func(self,sample,wait) #command的返回值ret,命令运行成功应该会返回机械手的返回信息，如果没有连通机械手返回False


        # 结束机械手运动状态
        HWR.beamline.sample_changer_maintenance._running = 0
        HWR.beamline.sample_changer_maintenance._update_global_state()
        if self._ifcmdSucceeded:
            self._ifcmdSucceeded = False
            return res
        else:
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
    def wrapper(self,magazine,position,*args):
        try:
            print()
            res = func(self,magazine,position,*args)
        except Exception as e:
            print("type(e):",type(e))
            print("e:",e)
            errorCode = e
            return errorCode
        else:
            return res
    return wrapper

class ActorSampleChanger(AbstractSampleChanger.SampleChanger):

    __TYPE__ = "Actor"
    NO_OF_BASKETS = 5
    NO_OF_SAMPLES_IN_BASKET = 16

    def __init__(self, *args, **kwargs):
        super(ActorSampleChanger, self).__init__(self.__TYPE__, False, *args, **kwargs)

    def init(self):
        self._selected_sample = -1
        self._selected_basket = -1
        self._scIsCharging = None


        self.no_of_baskets = self.get_property(
            "no_of_baskets", ActorSampleChanger.NO_OF_BASKETS
        )

        self.no_of_samples_in_basket = self.get_property(
            "no_of_samples_in_basket", ActorSampleChanger.NO_OF_SAMPLES_IN_BASKET
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



        self._dewar=1
        self.socket_addr = '10.30.61.73:10100'
        self._ifcloseLid_inBeginning = False
        self.count = 14

        self._cmdMount = self.add_command(
            {"type": "socketrobot", "socket_address": self.socket_addr, "name": '_cmdMount'},
            'Mount'
        )
        self._cmdUnMount = self.add_command(
            {"type": "socketrobot", "socket_address": self.socket_addr, "name": '_cmdMount'},
            'Dismount'
        )
        self._cmdExchange = self.add_command(
            {"type": "socketrobot", "socket_address": self.socket_addr, "name": '_cmdExchange'},
            'Exchange'
        )

        self._ifcmdSucceeded = False

    # def load_sample(self, holder_length, sample_location=None, wait=False):
    #     if Microdiff.get_current_phase() != "Transfer:
    #         Microdiff.set_phase("Transfer",wait=True,timeout=500)
    #     self.load(sample_location, wait)

    @if_ErrorCode
    def _do_mount(self,magazine,position):
        return self._cmdMount(magazine=magazine,position=position)
    @if_ErrorCode
    def _do_unmount(self,magazine,position):
        return self._cmdUnMount(magazine=magazine,position=position)
    @if_ErrorCode
    def _do_exchange(self,oldMagazine,oldPosition,newMagazine,newPosition):
        print("oldMagazine,oldPosition,NewMagazine,NewPosition:",oldMagazine,oldPosition,newMagazine,newPosition)
        return self._cmdExchange(oldMagazine=oldMagazine,oldPosition=oldPosition,newMagazine=newMagazine,newPosition=newPosition)

    def get_log_filename(self):
        return self.log_filename


    def load_sample(self, holder_length, sample_location=None, wait=False):
        print("进入ActorSampleChanger.py的load_sample函数")
        self.load(sample_location, wait)

    @property
    def ifcloseLid_inBeginning(self):
        return self._ifcloseLid_inBeginning

    def change_ifcloseLid_inBeginning_state(self,state:bool):
        self._ifcloseLid_inBeginning = state


    @if_running_sc
    @set_running_sc
    def exchange(self,newsample,wait=False):
        print("进入exchange函数")

        #检查md2
        self.check_MD2_state()



        oldsample = self.get_loaded_sample().get_address()
        print("oldsample: ",oldsample,"newsample: ",newsample)
        # print(type(oldsample),type(newsample)) # 两个str
        oldBasket, oldSample = oldsample.split(":")
        newBasket, newSample = newsample.split(":")

        # 清除oldsample 的 loaded属性
        self.get_loaded_sample()._set_loaded(False, True)     #    def _set_loaded(self, loaded, has_been_loaded=None):


        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", True)

        newBasket = int(newBasket)
        newSample = int(newSample)
        oldBasket = int(oldBasket)
        oldSample = int(oldSample)


        msg = "Exchanging sample %d:%d" % (newBasket, newSample)
        logging.getLogger("user_level_log").info(
            "Sample changer: %s. Please wait..." % msg
        )

        self.emit("progressInit", (msg, 100))
        for step in range(2 * 100):
            self.emit("progressStep", int(step / 2.0))
            time.sleep(0.01)

        print("oldSample!=newSample or oldBasket != newSample:",oldSample!=newSample or oldBasket != newBasket)
        if oldSample!=newSample or oldBasket != newBasket:
            # 判断真实命令是否发送成功,_ifcmdSucceeded可能是机械手的返回信息，或者是因为socket连接问题所返回的False,
            # 如果机械手返回信息有报错，在cmd函数中就会raise exception,然后会在if_ErrorCode函数中(转换为int?)传递过来
            self._ifcmdSucceeded = self._do_exchange(oldBasket, oldSample,newBasket,newSample)
            print("self._ifcmdSucceeded:", self._ifcmdSucceeded, type(self._ifcmdSucceeded))

            #处理返回的_ifcmdSucceeded信息
                # 如果命令返回False说明是socket连接没有连上
            if self._ifcmdSucceeded == False:
                self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
                return
            # 如果命令返回的类型是Exception，说明是机械手有报错
            elif (type(self._ifcmdSucceeded) is Exception) or (type(self._ifcmdSucceeded) is OSError) or (type(self._ifcmdSucceeded) is TimeoutError) or (type(self._ifcmdSucceeded) is KeyError):
                # 在发生错误后恢复机械手的各种状态
                self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
                HWR.beamline.sample_changer_maintenance._running = 0
                HWR.beamline.sample_changer_maintenance._update_global_state()
                # 翻译来自机械手的errorCode
                if type(self._ifcmdSucceeded) is Exception:
                    self._ifcmdSucceeded = str(self._ifcmdSucceeded)
                    self._ifcmdSucceeded = self._paraphrase_errorCode(self._ifcmdSucceeded)
                logging.getLogger("user_level_log").error(
                    "ErrorCode from robot:"+ self._ifcmdSucceeded+",please contact the teacher on duty")
                raise Exception(f"ErrorCode from robot: {self._ifcmdSucceeded}, please contact the teacher on duty")

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
        print("self.get_loaded_sample().get_address()",self.get_loaded_sample().get_address())
        #计数
        self.count += 1

        # 上完样品，md2 变为centering
        HWR.beamline.diffractometer.set_phase("Centring")

        return self.get_loaded_sample()



    def change_MD2_state(self,timeout=3):
        MD2 = HWR.beamline.diffractometer
        if MD2.get_current_phase() != "Transfer":
            MD2.set_phase("Transfer", wait=True)
            print("切换完成")
        gevent.sleep(timeout)
        if MD2.get_current_phase() == "Transfer":
            return True
        else:
            return False

    def check_MD2_state(self):
        if not self.change_MD2_state():
            raise Exception("please check the status of MD2")
        else:
            print("进入安全等待时间5s")
            time.sleep(5)

    @if_running_sc
    @set_running_sc
    def load(self, sample, wait=False):
        print("进入load函数")

        # 先判断是否closelid了
        if not self._ifcloseLid_inBeginning:
            # 恢复各种状态
            HWR.beamline.sample_changer_maintenance._running = 0
            HWR.beamline.sample_changer_maintenance._update_global_state()

            logging.getLogger("user_level_log").error("please close the lid first")# doesn't work,can show on log message, don't know why
            logging.getLogger("HWR").debug("please close the lid first")
            self.send_msg_to_statemessage("please close the lid first")
            HWR.beamline.sample_changer_maintenance._update_global_state()
            raise Exception("please close the lid first")

        # 判断md2
        self.check_MD2_state()

        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", True)
        previous_sample = self.get_loaded_sample()

        #原来的位置,为了显示abort按钮和提示栏，把这两行注释掉 self._reset_loaded_sample() 应该是把所有sample执行sample._set_loaded(False)
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

        self.emit("progressInit", (msg, 100))
        for step in range(2 * 100):
            self.emit("progressStep", int(step / 2.0))
            time.sleep(0.01)

        mounted_sample = self.get_component_by_address(
            Container.Pin.get_sample_address(basket, sample)
        )
        # self._set_state(AbstractSampleChanger.SampleChangerState.Ready) #原来的位置

        if mounted_sample is not previous_sample:
            # 判断真实命令是否发送成功,_ifcmdSucceeded可能是机械手的返回信息，或者是因为socket连接问题所返回的False,
            # 如果机械手返回信息有报错，在cmd函数中就会raise exception,然后会在if_ErrorCode函数中(转换为int?)传递过来
            self._ifcmdSucceeded = self._do_mount(basket,sample)
            print("self._ifcmdSucceeded:",self._ifcmdSucceeded,type(self._ifcmdSucceeded))

            #处理返回的_ifcmdSucceeded信息
                # 如果命令返回False说明是socket连接没有连上
            if self._ifcmdSucceeded == False:
                self._selected_sample = -1
                self._selected_basket = -1
                self.send_sample_address_to_statemessage()

                self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
                return

            # 如果命令返回的类型是Exception，说明是机械手有报错
            elif (type(self._ifcmdSucceeded) is Exception) or (type(self._ifcmdSucceeded) is OSError) or (type(self._ifcmdSucceeded) is TimeoutError):
                # 在发生错误后恢复机械手的各种状态
                self._selected_sample = -1
                self._selected_basket = -1
                self.send_sample_address_to_statemessage()


                self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
                HWR.beamline.sample_changer_maintenance._running = 0
                HWR.beamline.sample_changer_maintenance._update_global_state()

                #翻译来自机械手的errorCode
                if type(self._ifcmdSucceeded) is Exception:
                    self._ifcmdSucceeded = str(self._ifcmdSucceeded)
                    self._ifcmdSucceeded = self._paraphrase_errorCode(self._ifcmdSucceeded)
                logging.getLogger("user_level_log").error("ErrorCode from robot: %s, please contact the teacher on duty" % self._ifcmdSucceeded)
                raise Exception(f"ErrorCode from robot: {self._ifcmdSucceeded}, please contact the teacher on duty")

            self._trigger_loaded_sample_changed_event(mounted_sample)

        self.send_sample_address_to_statemessage()

        self.update_info()
        logging.getLogger("user_level_log").info("Sample changer: Sample loaded")
        self.emit("progressStop", ())

        self.emit("fsmConditionChanged", "sample_is_loaded", True)
        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", False)

        self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
        print("self.get_loaded_sample().get_address()",self.get_loaded_sample().get_address())
        #计数
        self.count += 1

        # 上完样品，md2 变为centering
        HWR.beamline.diffractometer.set_phase("Centring")
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
            logging.getLogger("user_level_log").info("即将把样品下到的位置:"+sample_slot+",已上样样品本来所处的位置:"+self.get_loaded_sample().get_address())
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
        self.check_MD2_state()

        if sample_slot==self.get_loaded_sample().get_address():
            logging.getLogger("user_level_log").info("即将把样品下到的位置与已上样样品本来所处的位置一致，开始下样")
        else:
            logging.getLogger("user_level_log").error("即将把样品下到的位置与已上样样品本来所处的位置不一致")

            self.unload_error_recover()
            raise Exception("the location selected is not the same as the location where the mounted sample was taken")


        sample = self.get_loaded_sample()
        sample._set_loaded(False, True)     #    def _set_loaded(self, loaded, has_been_loaded=None):


        if self._selected_sample > 0 and self._selected_sample <= 16:
            self._ifcmdSucceeded =  self._do_unmount(self._selected_basket,self._selected_sample)
            # 如果命令返回False说明是socket连接没有连上
            if self._ifcmdSucceeded == False:
                self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
                return
            # 如果命令返回的类型是Exception，说明是机械手有报错
            elif (type(self._ifcmdSucceeded) is Exception) or (type(self._ifcmdSucceeded) is OSError) or (type(self._ifcmdSucceeded) is TimeoutError):

                self.unload_error_recover()
                self._ifcmdSucceeded  = str(self._ifcmdSucceeded)
                raise Exception(f"ErrorCode from robot: {self._ifcmdSucceeded}, please contact the teacher on duty")

            self._selected_basket = -1
            self._selected_sample = -1

            self._trigger_loaded_sample_changed_event(self.get_loaded_sample())
            self.send_sample_address_to_statemessage()

            self.emit("fsmConditionChanged", "sample_is_loaded", False)
        else:
            logging.getLogger("HWR").debug("cannot unload, the location is wrong")

    def _paraphrase_errorCode(self,errorCode):
        if errorCode == "62":
            return "Dewar plug not in correct location when dewar open or close program called, usually caused by the insensitivty of the sensor beneath the lid"
        elif errorCode == "24":
            return "Pin already mounted, (if there is no Pin mounted, then it could be the incorrect judge from infrared senor)"
        elif errorCode == "31":
            return "Pin is not sensored on goniometer after mounting, (maybe caused by there's no pin in that postion)"
        else:
            return errorCode

    def get_loaded_sample(self):
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

    def send_msg_to_statemessage(self,msg):
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