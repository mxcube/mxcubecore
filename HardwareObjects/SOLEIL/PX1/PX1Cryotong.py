from __future__ import print_function
import logging
import gevent
import time

from HardwareRepository.Command.Tango import DeviceProxy


from HardwareRepository.HardwareObjects.Cats90 import (
    Cats90,
    SampleChangerState,
    BASKET_UNIPUCK,
)

from PX1Environment import EnvironmentPhase


class PX1Cryotong(Cats90):

    __TYPE__ = "CATS"

    default_no_lids = 1
    baskets_per_lid = 3

    default_basket_type = BASKET_UNIPUCK

    def __init__(self, *args, **kwargs):

        super(PX1Cryotong, self).__init__(*args, **kwargs)

        self._safeNeeded = None
        self._homeOpened = None
        self.dry_and_soak_needed = False
        self.count_down = None

        self.soft_auth = None
        self.incoherent_state = None

    def init(self):

        super(PX1Cryotong, self).init()

        self.cats_device = DeviceProxy(self.getProperty("cats_device"))

        self.environment = self.getObjectByRole("environment")

        if self.environment is None:
            logging.error(
                "PX1Cats. environment object not available. Sample changer cannot operate. Info.mode only"
            )
            self.infomode = True
        else:
            self.infomode = False

        for channel_name in (
            "_chnSoftAuth",
            "_chnHomeOpened",
            "_chnDryAndSoakNeeded",
            "_chnIncoherentGonioSampleState",
            "_chnSampleIsDetected",
            "_chnCountDown",
        ):
            setattr(self, channel_name, self.get_channel_object(channel_name))

        self._chnSoftAuth.connectSignal("update", self._software_authorization)
        self._chnHomeOpened.connectSignal("update", self._update_home_opened)
        self._chnIncoherentGonioSampleState.connectSignal(
            "update", self._update_ack_sample_memory
        )
        self._chnDryAndSoakNeeded.connectSignal("update", self._dry_and_soak_needed)
        self._chnSampleIsDetected.connectSignal("update", self._update_sample_is_detected)
        self._chnCountDown.connectSignal("update", self._update_count_down)

        self._cmdDrySoak = self.add_command(
            {"type": "tango", "name": "_cmdDrySoak", "tangoname": self.tangoname},
            "DryAndSoak",
        )

    # ## CRYOTONG SPECIFIC METHODS ###

    def _software_authorization(self, value):
        if value != self.soft_auth:
            self.soft_auth = value
            self.emit("softwareAuthorizationChanged", (value,))

    def _update_home_opened(self, value=None):
        if self._homeOpened != value:
            self._homeOpened = value
            self.emit("homeOpened", (value,))

    def _update_sample_is_detected(self, value):
        self.emit("sampleIsDetected", (value,))

    def _update_ack_sample_memory(self, value=None):
        if value is None:
            value = self._chnIncoherentGonioSampleState.getValue()

        if value != self.incoherent_state:
            # automatically acknowledge the error. send a warning to the GUI
            if self.incoherent_state is not None:
                logging.getLogger("user_level_log").warning(
                    "CATS: Requested Sample could not be loaded."
                )
                self.emit("loadError", value)
                try:
                    self._cmdAckSampleMemory()
                except BaseException:
                    """ do nothing if cmd not to acknowledge not in xml """
                    pass
            self.incoherent_state = value

    def _dry_and_soak_needed(self, value=None):
        self.dry_and_soak_needed = value

    def do_dry_and_soak(self):
        homeOpened = self._chnHomeOpened.getValue()

        if not homeOpened:
            self._do_dry_soak()
        else:
            logging.getLogger("user_level_log").warning(
                "CATS: You must Dry_and_Soak the gripper."
            )

    def _update_count_down(self, value=None):
        if value is None:
            value = self._chnCountDown.getValue()

        if value != self.count_down:
            logging.getLogger("HWR").info(
                "PX1Cats. CountDown changed. Now is: %s" % value
            )
            self.count_down = value
            self.emit("countdownSignal", value)

    def _do_dry_soak(self):
        """
        Launch the "DrySoak" command on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        if self.infomode:
            logging.warning("PX1Cats. It is in info mode only. DrySoak command ignored")
            return

        self._cmdDrySoak()

    def _do_safe(self):
        """
        Launch the "safe" trajectory on the CATS Tango DS

        :returns: None
        :rtype: None
        """
        if self.infomode:
            logging.warning(
                "PX1Cryotong. It is in info mode only. Command 'safe' ignored"
            )
            return

        ret = self.env_send_transfer()

        if not ret:
            logging.getLogger("user_level_log").error(
                "PX1 Environment cannot set transfer phase"
            )
            raise Exception(
                "Cryotong cannot get to transfer phase. Aborting sample changer operation"
            )

        self._execute_server_task(
            self._cmdSafe,
            "Safe",
            states=[SampleChangerState.Ready, SampleChangerState.Alarm],
        )

    # ## (END) CRYOTONG SPECIFIC METHODS ###

    # ## OVERLOADED CATS90 methods ####
    def cats_pathrunning_changed(self, value):
        Cats90.cats_pathrunning_changed(self, value)
        if self.cats_running is False and self.dry_and_soak_needed:
            self.do_dry_and_soak()

    def _do_load(self, sample=None, wash=None):

        ret = self.check_power_on()
        if ret is False:
            logging.getLogger("user_level_log").error("CRYOTONG Cannot be powered")
            raise Exception(
                "CRYOTONG Cannot be powered. Aborting sample changer operation"
            )

        ret = self.check_drysoak()
        if ret is False:
            logging.getLogger("user_level_log").error(
                "CRYOTONG Home Open / DryAndSoak not valid for loading"
            )
            raise Exception("CRYOTONG Home Open / DryAndSoak not valid for loading")

        ret = self.env_send_transfer()
        if ret is False:
            logging.getLogger("user_level_log").error(
                "PX1 Environment cannot set transfer phase"
            )
            raise Exception(
                "Cryotong cannot get to transfer phase. Aborting sample changer operation"
            )

        self._do_loadOperation(sample)

        # Check the value of the CATSCRYOTONG attribute dryAndSoakNeeded to warn
        # user if it is True
        dryAndSoak = self._chnDryAndSoakNeeded.getValue()
        if dryAndSoak:
            logging.getLogger("user_level_log").warning(
                "CATS: It is recommended to Dry_and_Soak the gripper."
            )

        incoherentSample = self._chnIncoherentGonioSampleState.getValue()
        if incoherentSample:
            logging.getLogger("user_level_log").info(
                "CATS: Load/Unload Error. Please try again."
            )
            self.emit("loadError", incoherentSample)

    def _do_unload(self, sample=None, wash=None):

        ret = self.check_power_on()
        if ret is False:
            logging.getLogger("user_level_log").error("CRYOTONG Cannot be powered")
            raise Exception(
                "CRYOTONG Cannot be powered. Aborting sample changer operation"
            )

        ret = self.env_send_transfer()

        if ret is False:
            logging.getLogger("user_level_log").error(
                "PX1 Environment cannot set transfer phase"
            )
            raise Exception(
                "Cryotong cannot get to transfer phase. Aborting sample changer operation"
            )

        self._do_unloadOperation(sample)

    def check_power_on(self):
        if self._chnPowered.getValue():
            return True

        self._cmdPowerOn()

        timeout = 3
        t0 = time.time()

        while not self._chnPowered.getValue():
            gevent.sleep(0.3)
            if time.time() - t0 > timeout:
                logging.getLogger("HWR").warning(
                    "CRYOTONG: timeout waiting for power on"
                )
                break

        if self._chnPowered.getValue():
            return False

        return True

    def check_drysoak(self):
        if self._chnHomeOpened.getValue() is False:
            return True

        #
        self._cmdDrySoak()

        time.sleep(3)
        t0 = time.time()
        wait_n = 0
        while self._is_device_busy():
            if wait_n % 10 == 3:
                logging.getLogger("HWR").warning(
                    "CRYOTONG: waiting for dry and soak to complete"
                )
            gevent.sleep(0.3)
            wait_n += 1

        if self._is_device_ready() and self._chnHomeOpened.getValue() is False:
            return True
        else:
            return False

    def env_send_transfer(self):
        if self.environment.readyForTransfer():
            return True

        logging.getLogger("user_level_log").warning(
            "CRYOTONG: Not ready for transfer. sending it"
        )
        self.environment.setPhase(EnvironmentPhase.TRANSFER)

        timeout = 10
        t0 = time.time()
        while not self.environment.readyForTransfer():
            gevent.sleep(0.3)
            if time.time() - t0 > timeout:
                logging.getLogger("HWR").warning(
                    "CRYOTONG: timeout waiting for transfer phase"
                )
                break
            logging.getLogger("HWR").warning(
                "CRYOTONG: waiting for transfer phase to be set"
            )

        if not self.environment.readyForTransfer():
            return False

        logging.getLogger("HWR").warning("CRYOTONG: ready for transfer now")
        return True

    # ## (END) OVERLOADED CATS90 methods ####


def test_hwo(hwo):
    import gevent

    basket_list = hwo.get_basket_list()
    sample_list = hwo.get_sample_list()
    print("Baskets/Samples in CATS: %s/%s" % (len(basket_list), len(sample_list)))
    gevent.sleep(2)
    sample_list = hwo.get_sample_list()
    print("No of samples is ", len(sample_list))

    for s in sample_list:
        if s.is_loaded():
            print("Sample %s loaded" % s.get_address())
            break

    if hwo.has_loaded_sample():
        print(
            "Currently loaded (%s): %s"
            % (hwo.has_loaded_sample(), hwo.get_loaded_sample().get_address())
        )

    print("\nCATS model is: ", hwo.cats_model)
    print("CATS state is: ", hwo.state)
    print("Sample on Magnet : ", hwo.cats_sample_on_diffr())
    print("All lids closed: ", hwo._chnAllLidsClosed.getValue())

    print("Sample Changer State is: ", hwo.get_status())
    for basketno in range(hwo.number_of_baskets):
        no = basketno + 1
        print("Tool for basket %d is: %d" % (no, hwo.tool_for_basket(no)))
