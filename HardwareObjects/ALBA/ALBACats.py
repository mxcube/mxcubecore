from __future__ import print_function

from HardwareRepository.HardwareObjects.Cats90 import (
    Cats90,
    SampleChangerState,
    TOOL_SPINE,
)

import logging
import time
import gevent

TIMEOUT = 3


class ALBACats(Cats90):
    """
    Main class used @ ALBA to integrate the CATS-IRELEC sample changer.
    """

    def __init__(self, *args):
        Cats90.__init__(self, *args)

    def init(self):
        Cats90.init(self)

        self.shifts_channel = self.get_channel_object("shifts")
        self.phase_channel = self.get_channel_object("phase")

        self.go_transfer_cmd = self.get_command_object("go_transfer")
        self.go_sampleview_cmd = self.get_command_object("go_sampleview")
        self.super_abort_cmd = self.get_command_object("super_abort")
        self.super_state_channel = self.get_channel_object("super_state")

        self.auto_prepare_diff = self.get_property("auto_prepare_diff")
        self.detdist_position_channel = self.get_channel_object("detdist_position")
        self.detdist_saved = None

        self._cmdLoadHT = self.get_command_object("_cmdLoadHT")
        self._cmdChainedLoadHT = self.get_command_object("_cmdChainedLoadHT")
        self._cmdUnloadHT = self.get_command_object("_cmdUnloadHT")

        self._chnPathSafe = self.get_channel_object("_chnPathSafe")

        if self._chnPathRunning is not None:
            self._chnPathRunning.connect_signal("update", self._update_running_state)

        if self._chnPowered is not None:
            self._chnPowered.connect_signal("update", self._update_powered_state)

    def is_ready(self):
        """
        Returns a boolean value indicating is the sample changer is ready for operation.

        @return: boolean
        """
        return (
            self.state == SampleChangerState.Ready
            or self.state == SampleChangerState.Loaded
            or self.state == SampleChangerState.Charging
            or self.state == SampleChangerState.StandBy
            or self.state == SampleChangerState.Disabled
        )

    def diff_send_transfer(self):
        """
        Checks if beamline supervisor is in TRANSFER phase (i.e. sample changer in TRANSFER phase too).
        If is not the case, It sends the sample changer to TRANFER phase.
        Returns a boolean value indication if the sample changer is in TRANSFER phase.

        @return: boolean
        """
        if self.read_super_phase().upper() == "TRANSFER":
            logging.getLogger("user_level_log").error(
                "Supervisor is already in transfer phase"
            )
            return True

        self.go_transfer_cmd()
        ret = self._wait_phase_done("TRANSFER")
        return ret

    def diff_send_sampleview(self):
        """
        Checks if beamline supervisor is in SAMPLE phase (i.e. sample changer in SAMPLE phase too).
        If is not the case, It sends the sample changer to SAMPLE phase.
        Returns a boolean value indication if the sample changer is in SAMPLE phase.

        @return: boolean
        """
        if self.read_super_phase().upper() == "SAMPLE":
            logging.getLogger("user_level_log").error(
                "Supervisor is already in sample view phase"
            )
            return True

        t0 = time.time()
        while True:
            state = str(self.super_state_channel.get_value())
            if str(state) == "ON":
                break

            if (time.time() - t0) > TIMEOUT:
                logging.getLogger("user_level_log").error(
                    "Supervisor timeout waiting for ON state. Returning"
                )
                return False

            time.sleep(0.1)

        self.go_sampleview_cmd()
        ret = self._wait_phase_done("SAMPLE")
        return ret

    def _wait_super_ready(self):
        while True:
            state = str(self.super_state_channel.get_value())
            if state == "ON":
                logging.getLogger("user_level_log").error(
                    "Supervisor is in ON state. Returning"
                )
                break

    def _wait_phase_done(self, final_phase):
        """
        Method to wait a phase change. When supervisor reaches the final phase, the diffracometer
        returns True.

        @final_phase: target phase
        @return: boolean
        """
        while True:
            state = str(self.super_state_channel.get_value())
            if state == "ON":
                logging.getLogger("user_level_log").error(
                    "Supervisor is in ON state. Returning"
                )
                break
            elif str(state) != "MOVING":
                logging.getLogger("user_level_log").error(
                    "Supervisor is in a funny state %s" % str(state)
                )
                return False

            logging.getLogger("HWR").debug("Supervisor waiting to finish phase change")
            time.sleep(0.2)

        time.sleep(0.1)

        if self.read_super_phase().upper() != final_phase:
            logging.getLogger("user_level_log").error(
                "Supervisor is not yet in %s phase. Aborting load" % final_phase
            )
            return False
        else:
            return True

    def save_detdist_position(self):
        self.detdist_saved = self.detdist_position_channel.get_value()
        logging.getLogger("user_level_log").error(
            "Saving current det.distance (%s)" % self.detdist_saved
        )

    def restore_detdist_position(self):
        if abs(self.detdist_saved - self.detdist_position_channel.get_value()) >= 0.1:
            logging.getLogger("user_level_log").error(
                "Restoring det.distance to %s" % self.detdist_saved
            )
            self.detdist_position_channel.set_value(self.detdist_saved)
            time.sleep(0.4)
            self._wait_super_ready()

    def read_super_phase(self):
        """
        Returns supervisor phase (CurrentPhase attribute from Beamline Supervisor Tango DS)

        @return: str
        """
        return self.phase_channel.get_value()

    def load(self, sample=None, wait=False, wash=False):
        """
        Loads a sample. Overides to include ht basket.

        @sample: sample to load.
        @wait:
        @wash: wash dring the load opearation.
        @return:
        """

        logging.getLogger("HWR").debug(
            "Loading sample %s / type(%s)" % (sample, type(sample))
        )

        ret, msg = self._check_coherence()
        if not ret:
            raise Exception(msg)

        sample_ht = self.is_ht_sample(sample)

        if not sample_ht:
            sample = self._resolve_component(sample)
            self.assert_not_charging()
            use_ht = False
        else:
            sample = sample_ht
            use_ht = True

        if self.has_loaded_sample():
            if (wash is False) and self.get_loaded_sample() == sample:
                raise Exception(
                    "The sample " + sample.get_address() + " is already loaded"
                )
            else:
                # Unload first / do a chained load
                pass

        return self._execute_task(
            SampleChangerState.Loading, wait, self._do_load, sample, None, use_ht
        )

    def unload(self, sample_slot=None, wait=False):
        """
        Unload the sample. If sample_slot=None, unloads to the same slot the sample was loaded from.

        @sample_slot:
        @wait:
        @return:
        """
        sample_slot = self._resolve_component(sample_slot)

        self.assert_not_charging()

        # In case we have manually mounted we can command an unmount
        if not self.has_loaded_sample():
            raise Exception("No sample is loaded")

        return self._execute_task(
            SampleChangerState.Unloading, wait, self._do_unload, sample_slot
        )

    # TODO: this overides identical method from Cats90
    def is_powered(self):
        return self._chnPowered.get_value()

    # TODO: this overides identical method from Cats90
    def is_path_running(self):
        return self._chnPathRunning.get_value()

    # TODO: this overides method from AbstractSampleChanger
    # def has_loaded_sample(self):  # not used.  to use it remove _
    #   return self._chnSampleIsDetected.get_value()

    def _update_running_state(self, value):
        """
        Emits signal with new Running State

        @value: New running state
        """
        self.emit("runningStateChanged", (value,))

    def _update_powered_state(self, value):
        """
        Emits signal with new Powered State

        @value: New powered state
        """
        self.emit("powerStateChanged", (value,))

    def _do_load(self, sample=None, shifts=None, use_ht=False):
        """
        Loads a sample on the diffractometer. Performs a simple put operation if the diffractometer is empty, and
        a sample exchange (unmount of old + mount of new sample) if a sample is already mounted on the diffractometer.
        Overides Cats90 method.

        @sample: sample to load.
        @shifts: mounting point offsets.
        @use_ht: mount a sample from hot tool.
        """
        if not self._chnPowered.get_value():
            self._cmdPowerOn()  # try switching power on

        current_tool = self.get_current_tool()

        self.save_detdist_position()
        ret = self.diff_send_transfer()

        if ret is False:
            logging.getLogger("user_level_log").error(
                "Supervisor cmd transfer phase returned an error."
            )
            self._update_state()  # remove transient states like Loading. Reflect hardware state
            raise Exception(
                "CATS cannot get to transfer phase. Aborting sample changer operation."
            )

        gevent.sleep(3)
        if not self._chnPowered.get_value():
            raise Exception(
                "CATS power is not enabled. Please switch on arm power before transferring samples."
            )

        # obtain mounting offsets from diffr
        shifts = self._get_shifts()

        if shifts is None:
            xshift, yshift, zshift = ["0", "0", "0"]
        else:
            xshift, yshift, zshift = map(str, shifts)

        # get sample selection
        selected = self.get_selected_sample()

        logging.getLogger("HWR").debug(
            "  ==========CATS=== selected sample is %s (prev %s)"
            % (str(selected), str(sample))
        )

        if not use_ht:
            if sample is not None:
                if sample != selected:
                    self._do_select(sample)
                    selected = self.get_selected_sample()
            else:
                if selected is not None:
                    sample = selected
                else:
                    raise Exception("No sample selected")
        else:
            selected = None

        # some cancel cases
        if (
            not use_ht
            and self.has_loaded_sample()
            and selected == self.get_loaded_sample()
        ):
            self._update_state()  # remove transient states like Loading. Reflect hardware state
            raise Exception(
                "The sample "
                + str(self.get_loaded_sample().get_address())
                + " is already loaded"
            )

        if not self.has_loaded_sample() and self.cats_sample_on_diffr() == 1:
            logging.getLogger("HWR").warning(
                "  ==========CATS=== sample on diffr, loading aborted"
            )
            self._update_state()  # remove transient states like Loading. Reflect hardware state
            raise Exception(
                "The sample "
                + str(self.get_loaded_sample().get_address())
                + " is already loaded"
            )
            return

        if self.cats_sample_on_diffr() == -1:
            self._update_state()  # remove transient states like Loading. Reflect hardware state
            raise Exception(
                "Conflicting info between diffractometer and on-magnet detection. Consider 'Clear'"
            )
            return

        # end some cancel cases

        # if load_ht
        loaded_ht = self.is_loaded_ht()

        #
        # Loading HT sample
        #
        if use_ht:  # loading HT sample

            if loaded_ht == -1:  # has loaded but it is not HT
                # first unmount (non HT)
                logging.getLogger("HWR").warning(
                    "  ==========CATS=== mix load/unload dewar vs HT (NOT IMPLEMENTED YET)"
                )
                return

            argin = ["2", str(sample), "0", "0", xshift, yshift, zshift]
            logging.getLogger("HWR").warning(
                "  ==========CATS=== about to load HT. %s" % str(argin)
            )
            if loaded_ht == 1:  # has ht loaded
                cmd_ok = self._execute_server_task(
                    self._cmdChainedLoadHT, argin, waitsafe=True
                )
            else:
                cmd_ok = self._execute_server_task(
                    self._cmdLoadHT, argin, waitsafe=False
                )

        #
        # Loading non HT sample
        #
        else:
            if loaded_ht == 1:  # has an HT sample mounted
                # first unmount HT
                logging.getLogger("HWR").warning(
                    "  ==========CATS=== mix load/unload dewar vs HT (NOT IMPLEMENTED YET)"
                )
                return

            # calculate CATS specific lid/sample number
            # lid = ((selected.get_basket_no() - 1) / 3) + 1
            # sample = (((selected.get_basket_no() - 1) % 3) * 10) + selected.get_vial_no()

            basketno = selected.get_basket_no()
            sampleno = selected.get_vial_no()

            lid, sample = self.basketsample_to_lidsample(basketno, sampleno)
            tool = self.tool_for_basket(basketno)
            stype = self.get_cassette_type(basketno)

            if tool != current_tool:
                logging.getLogger("HWR").warning(
                    "  ==========CATS=== changing tool from %s to %s"
                    % (current_tool, tool)
                )
                changing_tool = True
            else:
                changing_tool = False

            # we should now check basket type on diffr to see if tool is different...
            # then decide what to do

            if shifts is None:
                xshift, yshift, zshift = ["0", "0", "0"]
            else:
                xshift, yshift, zshift = map(str, shifts)

            # prepare argin values
            argin = [
                str(tool),
                str(lid),
                str(sample),
                str(stype),
                "0",
                xshift,
                yshift,
                zshift,
            ]

            if tool == 2:
                read_barcode = (
                    self.read_datamatrix and self._cmdChainedLoadBarcode is not None
                )
            else:
                if self.read_datamatrix:
                    logging.getLogger("HWR").warning(
                        "  ==========CATS=== reading barcode only possible with spine pucks"
                    )
                read_barcode = False

            if loaded_ht == -1:  # has a loaded but it is not an HT

                if changing_tool:
                    raise Exception(
                        "This operation requires a tool change. You should unload sample first"
                    )

                if read_barcode:
                    logging.getLogger("HWR").warning(
                        "  ==========CATS=== chained load sample (barcode), sending to cats:  %s"
                        % argin
                    )
                    cmd_ok = self._execute_server_task(
                        self._cmdChainedLoadBarcode, argin, waitsafe=True
                    )
                else:
                    logging.getLogger("HWR").warning(
                        "  ==========CATS=== chained load sample, sending to cats:  %s"
                        % argin
                    )
                    cmd_ok = self._execute_server_task(
                        self._cmdChainedLoad, argin, waitsafe=True
                    )
            elif loaded_ht == 0:
                if read_barcode:
                    logging.getLogger("HWR").warning(
                        "  ==========CATS=== load sample (barcode), sending to cats:  %s"
                        % argin
                    )
                    cmd_ok = self._execute_server_task(
                        self._cmdLoadBarcode, argin, waitsafe=True
                    )
                else:
                    logging.getLogger("HWR").warning(
                        "  ==========CATS=== load sample, sending to cats:  %s" % argin
                    )
                    cmd_ok = self._execute_server_task(
                        self._cmdLoad, argin, waitsafe=True
                    )

        if not cmd_ok:
            logging.getLogger("HWR").info("  LOAD Command failed on device server")
        elif self.auto_prepare_diff and not changing_tool:
            logging.getLogger("HWR").info(
                "  AUTO_PREPARE_DIFF (On) sample changer is in safe state... preparing diff now"
            )
            # ret = self.diff_send_sampleview()
            self.go_sampleview_cmd()
            logging.getLogger("HWR").info("     restoring detector distance")
            self.restore_detdist_position()
            self._wait_phase_done("SAMPLE")
        else:
            logging.getLogger("HWR").info(
                "  AUTO_PREPARE_DIFF (Off) sample loading done / or changing tool (%s)"
                % changing_tool
            )

        # load commands are executed until path is safe. Then we have to wait for
        # path to be finished
        self._wait_device_ready()

    def _do_unload(self, sample_slot=None, shifts=None):
        """
        Unloads a sample from the diffractometer.
        Overides Cats90 method.

        @sample_slot:
        @shifts: mounting position
        """
        if not self._chnPowered.get_value():
            self._cmdPowerOn()  # try switching power on

        ret = self.diff_send_transfer()

        if ret is False:
            logging.getLogger("user_level_log").error(
                "Supervisor cmd transfer phase returned an error."
            )
            return

        shifts = self._get_shifts()

        if sample_slot is not None:
            self._do_select(sample_slot)

        loaded_ht = self.is_loaded_ht()

        if shifts is None:
            xshift, yshift, zshift = ["0", "0", "0"]
        else:
            xshift, yshift, zshift = map(str, shifts)

        loaded_lid = self._chnLidLoadedSample.get_value()
        loaded_num = self._chnNumLoadedSample.get_value()

        if loaded_lid == -1:
            logging.getLogger("HWR").warning(
                "  ==========CATS=== unload sample, no sample mounted detected"
            )
            return

        loaded_basket, loaded_sample = self.lidsample_to_basketsample(
            loaded_lid, loaded_num
        )

        tool = self.tool_for_basket(loaded_basket)

        argin = [str(tool), "0", xshift, yshift, zshift]

        logging.getLogger("HWR").warning(
            "  ==========CATS=== unload sample, sending to cats:  %s" % argin
        )
        if loaded_ht == 1:
            cmd_ret = self._execute_server_task(self._cmdUnloadHT, argin)
        else:
            cmd_ret = self._execute_server_task(self._cmdUnload, argin)

    def _do_abort(self):
        """
        Aborts a running trajectory on the sample changer.

        :returns: None
        :rtype: None
        """
        if self.super_abort_cmd is not None:
            self.super_abort_cmd()  # stops super
        self._cmdAbort()
        self._update_state()  # remove software flags like Loading.. reflects current hardware state

    def _check_coherence(self):
        detected = self._chnSampleIsDetected.get_value()
        loaded_lid = self._chnLidLoadedSample.get_value()
        loaded_num = self._chnNumLoadedSample.get_value()

        if -1 in [loaded_lid, loaded_num] and detected:
            return False, "Sample detected on Diffract. but there is no info about it"

        return True, ""

    def _get_shifts(self):
        """
        Get the mounting position from the Diffractometer DS.

        @return: 3-tuple
        """
        if self.shifts_channel is not None:
            shifts = self.shifts_channel.get_value()
        else:
            shifts = None
        return shifts

    # def path_running(self):
    # """
    # Overides Cats90 method.
    #
    # @return:
    # """
    # return (self._chnPathSafe.get_value() is not True)

    # TODO: fix return type
    def is_ht_sample(self, address):
        """
        Returns is sample address belongs to hot tool basket.

        @address: sample address
        @return: int or boolean
        """
        basket, sample = address.split(":")
        try:
            if int(basket) >= 100:
                return int(sample)
            else:
                return False
        except Exception:
            return False

    def tool_for_basket(self, basketno):
        """
        Returns the tool corresponding to the basket.

        @basketno: basket number
        @return: int
        """
        if basketno == 100:
            return TOOL_SPINE

        return Cats90.tool_for_basket(self, basketno)

    def is_loaded_ht(self):
        """
           1 : has loaded ht
           0 : nothing loaded
          -1 : loaded but not ht
        """
        sample_lid = self._chnLidLoadedSample.get_value()

        if self.has_loaded_sample():
            if sample_lid == 100:
                return 1
            else:
                return -1
        else:
            return 0


def test_hwo(hwo):
    hwo._update_cats_contents()
    print(" Is path running? ", hwo.is_path_running())
    print(" Loading shifts:  ", hwo._get_shifts())
    print(" Sample on diffr :  ", hwo.cats_sample_on_diffr())
    print(" Baskets :  ", hwo.basket_presence)
    print(" Baskets :  ", hwo.get_basket_list())
    if hwo.has_loaded_sample():
        print(" Loaded is: ", hwo.get_loaded_sample().get_coords())
    print(" Is mounted sample: ", hwo.is_mounted_sample((1, 1)))


if __name__ == "__main__":
    test()
