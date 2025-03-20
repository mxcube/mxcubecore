import gevent
import time
import logging

from mxcubecore.HardwareObjects.abstract import AbstractSampleChanger
from mxcubecore.HardwareObjects.abstract.sample_changer import Container
from mxcubecore import HardwareRepository as HWR

class PlateManipulator(AbstractSampleChanger.SampleChanger):

    __TYPE__ = "PlateManipulator"
    NO_OF_BASKETS = 8
    NO_OF_SAMPLES_IN_BASKET = 12
    PLATE_MODE_CHANGED_EVENT = "plateModeChanged"

    def __init__(self, *args, **kwargs):
        super(PlateManipulator, self).__init__(self.__TYPE__, False, *args, **kwargs)

    def init(self):
        self.plate_mode_on = False
        self.exporter_addr = '10.30.61.67:9002'

        self._cmdgetPlateLocation = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "getPlateLocation",
            },
            "getPlateLocation",
        )

        self._cmdstartMovePlateToLocation = self.add_command(
            {
                "type": "exporter",
                "exporter_address": self.exporter_addr,
                "name": "startMovePlateToLocation",
            },
            "startMovePlateToLocation",
        )

        gevent.spawn(self.check_plate_location_set_loaded_sample)

    def get_if_plate_mode(self):
        return self.plate_mode_on

    def check_plate_location_set_loaded_sample(self):
        """


                        puck_pin_index = old_loaded_sample.address.find(':')
                        puck_id = old_loaded_sample.address[0:puck_pin_index]
                        pin_id = old_loaded_sample.address[puck_pin_index+1:]
                        print('old_loaded_sample.address: ',puck_id,pin_id)
        """
        SC = HWR.beamline.sample_changer
        while True:
            # time.sleep(0.05)
            time.sleep(1)
            if self.plate_mode_on:
                print("plate_mode_on")
                currentPlateLocation =  self._do_getPlateLocation()
                if currentPlateLocation:
                    old_loaded_sample = SC.get_loaded_sample()      #没有的时候为None,手动上的样也是None， 机械手上样是一个Contanier.Pin 的object，其中address是'1:01'这样格式的地质
                    if old_loaded_sample is not None and (old_loaded_sample.address == currentPlateLocation):
                        # print("old_loaded_sample is not None and (old_loaded_sample.address == currentPlateLocation)")
                        pass
                    else:
                        # print('change loaded sample to this currentPlateLocation,currentPlateLoaction: ',currentPlateLocation,"。")
                        SC.change_load_sample(currentPlateLocation)





    def _set_plate_mode(self,mode_on=None):
        SC = HWR.beamline.sample_changer
        if mode_on is not None:
            if mode_on != self.plate_mode_on:
                self.plate_mode_on = mode_on
                print('change plate mode: ',self.plate_mode_on)
                SC._trigger_plate_mode_changed_event(mode_on)




    def _do_getPlateLocation(self):
        """

        实际应该发送exporter请求，获取实时location，此处返回固定值作为模拟
        """
        # return '1:03'
        MD2 = HWR.beamline.diffractometer
        MD2_current_phase = MD2.get_current_phase()
        if MD2_current_phase == 'Centring':
            res = self._cmdgetPlateLocation()
            # print("res of _cmdgetPlateLocation: ",res)
            row = res[0] +1
            col = res[1] +1
            row = str(int(row))
            if col>=10:
                col = str(int(col))
            else:
                col = '0' +str(int(col))
            # print('str res of _cmdgetPlateLocation: ',row+':'+col)
            return row+':'+col

        else:
            return None



    def do_startMovePlateToLocation(self,sample):
        print(sample)
        row,col = sample.split(':')
        row = int(row)-1
        col = int(col)-1
        self._cmdstartMovePlateToLocation(row,col,0.5,0.5)






    def exchange(self,newsample,wait=False):
        # raise Exception("test exception")
        logging.getLogger("HWR").debug("get in exchange method")
        self.load(newsample,wait)


    def load(self, sample, wait=False):
        logging.getLogger("HWR").debug("get in load smaple in SampleChangerMockup.py")
        # self.emit("fsmConditionChanged", "sample_mounting_sample_changer", True)



        previous_sample = self.get_loaded_sample()
        self._set_state(AbstractSampleChanger.SampleChangerState.Loading)   # 此处好像也传递给了前端状态，调用了signals中的sc_state_changed()
        self._reset_loaded_sample()

        if isinstance(sample, tuple):
            basket, sample = sample
        else:
            basket, sample = sample.split(":")

        self._selected_basket = basket = int(basket)
        self._selected_sample = sample = int(sample)

        msg = "Loading sample %d:%d" % (basket, sample)
        logging.getLogger("user_level_log").info(
            "Sample changer: %s. Please wait..." % msg
        )

        # self.emit("progressInit", (msg, 100))
        # for step in range(2 * 100):
        #     self.emit("progressStep", int(step / 2.0))
        #     time.sleep(0.01)

        mounted_sample = self.get_component_by_address(
            Container.Pin.get_sample_address(basket, sample)
        )

        print("start time sleep 5")
        time.sleep(5)

        print("end time sleep 5")


        self._set_state(AbstractSampleChanger.SampleChangerState.Ready)

        if mounted_sample is not previous_sample:
            self._trigger_loaded_sample_changed_event(mounted_sample)
        self.update_info()
        logging.getLogger("user_level_log").info("Sample changer: Sample loaded")
        self.emit("progressStop", ())

        self.emit("fsmConditionChanged", "sample_is_loaded", True)
        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", False)

        # try:
        #     raise Exception("test exception")
        # finally:
        #     HWR.beamline.sample_changer_maintenance._running = 0
        #     HWR.beamline.sample_changer_maintenance._update_global_state()
        #     self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
        return self.get_loaded_sample()

    def unload(self, sample_slot=None, wait=None):
        logging.getLogger("user_level_log").info("Unloading sample")
        sample = self.get_loaded_sample()
        sample._set_loaded(False, True)
        self._selected_basket = -1
        self._selected_sample = -1
        self._trigger_loaded_sample_changed_event(self.get_loaded_sample())
        self.emit("fsmConditionChanged", "sample_is_loaded", False)

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

