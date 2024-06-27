# encoding: utf-8
#
#  Project: MXCuBE
#  https://github.com/mxcube
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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

__copyright__ = """ Copyright © 2010 - 2024 by MXCuBE Collaboration """
__license__ = "LGPLv3+"


import time
import logging

from mxcubecore.HardwareObjects.abstract.AbstractSampleChanger import (
    SampleChanger,
    SampleChangerState,
)
from mxcubecore.HardwareObjects.abstract.sample_changer import Container
from mxcubecore.TaskUtils import task
from mxcubecore import HardwareRepository as HWR


class P11SampleChanger(SampleChanger):
    __TYPE__ = "P11SC"
    NO_OF_BASKETS = 23
    NO_OF_SAMPLES_IN_BASKET = 16

    def __init__(self, *args, **kwargs):
        super().__init__(self.__TYPE__, False, *args, **kwargs)

    def init(self):
        self._selected_sample = -1
        self._selected_basket = -1
        self._scIsCharging = None

        self.no_of_baskets = self.get_property(
            "no_of_baskets", P11SampleChanger.NO_OF_BASKETS
        )

        self.no_of_samples_in_basket = self.get_property(
            "no_of_samples_in_basket", P11SampleChanger.NO_OF_SAMPLES_IN_BASKET
        )

        for i in range(self.no_of_baskets):
            basket = Container.Basket(
                self, i + 1, samples_num=self.no_of_samples_in_basket
            )
            self._add_component(basket)

        self.load_cmd = self.get_command_object("mount")
        self.unload_cmd = self.get_command_object("unmount")
        self.wash_cmd = self.get_command_object("wash")
        self.home_cmd = self.get_command_object("home")
        self.cool_cmd = self.get_command_object("cool")
        self.deice_cmd = self.get_command_object("deice")

        self.chan_current_sample = self.get_channel_object("current_sample")
        self.chan_current_sample.connect_signal("update", self.current_sample_changed)

        self.chan_state = self.get_channel_object("state")
        self.chan_state.connect_signal("update", self.state_channel_changed)

        self.chan_powered = self.get_channel_object("powered")
        self.chan_powered.connect_signal("update", self.powered_changed)

        self.chan_condition_dict = {}
        self.condition_list = [
            "cond_interlock",
            "cond_collimator",
            "cond_goniopos",
            "cond_guillotine",
            "cond_collision",
            "cond_screen",
        ]

        self.chan_cryoswitch = self.get_channel_object("cryoswitch")

        self.chan_cond_cryo = self.get_channel_object("cond_cryo")
        self.chan_cond_cryo.connect_signal("update", self.cryopos_changed)

        for condition in self.condition_list:
            self.chan_condition_dict[condition] = self.get_channel_object(condition)
            self.chan_condition_dict[condition].connect_signal(
                "update",
                lambda value, cond=condition, this=self: P11SampleChanger.condition_changed(
                    this, cond, value
                ),
            )

        # channels
        self._init_sc_contents()
        self.signal_wait_task = None
        SampleChanger.init(self)

        self.log_filename = self.get_property("log_filename")

        contents = self.get_components()
        basket_list = self.get_basket_list()

        self._update_selection()

    def get_log_filename(self):
        return self.log_filename

    def is_powered(self):
        return True

    def load_sample(self, holder_length, sample_location=None, wait=False):
        self.load(sample_location, wait)

    def home(self):
        self.wait_sc_ready()
        self.log.debug("OPERATING SC NOW (HOME) sample_changer")
        self._set_state(SampleChangerState.Moving)
        self.home_cmd()
        self.wait_sc_ready()
        self.emit("progressStop", ())

    def cool(self):
        self.wait_sc_move()
        self.log.debug("OPERATING SC NOW (COOL) sample_changer")
        self._set_state(SampleChangerState.Moving)
        self.cool_cmd()
        self.wait_sc_move()
        self.emit("progressStop", ())

    def deice(self):
        self.wait_sc_move()
        self.log.debug("OPERATING SC NOW (DE-ICING) sample_changer")
        self._set_state(SampleChangerState.Moving)
        self.deice_cmd()
        self.wait_sc_move()
        self.emit("progressStop", ())

    def wash(self, wait=False):
        if not self.has_loaded_sample():
            self.user_log.debug("No sample is mounted. Wash command not possible")
            raise RuntimeWarning("There is no sample to wash")

        sample_no = self.chan_current_sample.get_value()

        self.prepare_load(wash=True)
        self._set_state(SampleChangerState.Moving)
        self._unload()
        self._load(sample_no)
        self.cleanup_load()

    def load(self, sample=None, wait=True):
        """
        Load a sample.

        Args:
            sample (tuple): sample address on the form
                            (component1, ... ,component_N-1, component_N)
            wait (boolean): True to wait for load to complete False otherwise

        Returns
            (Object): Value returned by _execute_task either a Task or result of the
                      operation
        """
        # sample = self._resolve_component(sample)
        self.assert_not_charging()

        self._set_state(SampleChangerState.Moving)

        self._start_load = time.time()
        # self._reset_loaded_sample()

        if isinstance(sample, tuple):
            basket, sample = sample
        else:
            basket, sample = sample.split(":")

        self.log.debug(" loading basket %s - sample %s" % (basket, sample))
        self._selected_basket = basket = int(basket)
        self._selected_sample = sample = int(sample)
        sample_no = (basket - 1) * self.NO_OF_SAMPLES_IN_BASKET + sample

        self._selected_sample_no = sample_no

        msg = "Loading sample %d:%d (sample number=%d)" % (basket, sample, sample_no)

        logging.getLogger("user_level_log").info(
            "Sample changer: %s. Please wait..." % msg
        )

        self.emit("progressInit", (msg, 100))

        # for step in range(2 * 100):
        #    self.emit("progressStep", int(step / 2.0))
        #    time.sleep(0.01)

        # Do a chained load in this case
        if self.has_loaded_sample():
            # Do first an unload in this case
            if (sample is None) or (sample == self.get_loaded_sample()):
                raise Exception(
                    "The sample "
                    + str(self.get_loaded_sample().get_address())
                    + " is already loaded"
                )

            self.log.debug("A sample is mounted. Doing a chained unload/load")
            self.prepare_load()
            self._set_state(SampleChangerState.Moving)
            self._unload()
            self._load(sample_no)
        else:
            self.log.debug("No sample is mounted. Doing a simple load")
            self.prepare_load()
            self._load(sample_no)

        self.cleanup_load()

        logging.getLogger("user_level_log").info(
            "Sample changer: Sample loaded (total time: %s)"
            % (time.time() - self._start_load)
        )

        self.emit("progressStop", ())

        return self.get_loaded_sample()

    def _load(self, sample_no):
        self.log.debug("   - checking if conditions (except cryo) are all fulfilled")
        if not self.check_pre_conditions():
            raise Exception("conditions for loading not met")

        self.wait_sc_ready()
        self.retract_cryo()

        self.log.debug("OPERATING SC NOW (LOAD) sample_changer: %s" % sample_no)
        self._set_state(SampleChangerState.Moving)
        self.load_cmd(sample_no)
        self.wait_sc_ready()
        self.insert_cryo()

    @task
    def unload(self, sample=None, wait=True):
        self._start_load = time.time()
        self.log.debug("Unload called with sample = %s" % sample)

        if not self.has_loaded_sample():
            raise Exception("Trying to unmount sample without any sample mounted")

        self.prepare_load()
        self._unload()
        self.cleanup_load()
        logging.getLogger("user_level_log").info(
            "Sample changer: Sample unloaded (total time: %s)"
            % (time.time() - self._start_load)
        )

    def _unload(self):
        self.log.debug("   - checking if conditions (except cryo) are all fulfilled")
        if not self.check_pre_conditions():
            raise Exception("conditions for loading not met")

        self.wait_sc_ready()
        self.retract_cryo()

        self._set_state(SampleChangerState.Moving)
        self.unload_cmd()
        self.wait_sc_ready()
        self.insert_cryo()

    def prepare_load(self, wash=False):
        self.log.debug("Preparing load")
        self.log.debug("   - asking diffractometer to save state")

        HWR.beamline.diffractometer.save_position("mount")

        self.log.debug("   - asking diffractometer to go to transfer phase")

        try:
            HWR.beamline.diffractometer.goto_transfer_phase()
            HWR.beamline.diffractometer.wait_phase()

            if not wash:
                self.log.debug("  setting zoom to 0  before loading")
                HWR.beamline.diffractometer.zoom.set_zoom_value(0)
                self.log.debug("  clearing images ")
                HWR.beamline.sample_view.clear_all_shapes()
                self.log.debug("  done")

        except Exception as e:
            self.cleanup_load()
            raise (e)

        return

    def cleanup_load(self):
        self.log.debug("Loading finished. Restoring previous conditions")
        HWR.beamline.diffractometer.restore_position("mount")
        # TODO: state handling. for now. this should be update automatically
        self._set_state(SampleChangerState.Ready)

    def check_pre_conditions(self):
        all_good = True

        self.log.debug("Checking pre-condtions for load/unload")
        for cond_name, cond_chan in self.chan_condition_dict.items():
            if not cond_chan.get_value():
                self.log.debug(" Condition %s for mounting not met" % cond_name)
                all_good = False

        self.log.debug(
            "   - conditions for mounting are %s met" % (all_good and "now" or "not")
        )

        return all_good

    def retract_cryo(self):
        self.log.debug("Retracting cryo")
        self.chan_cryoswitch.set_value(1)
        self.wait_cryo_condition(True)

    def insert_cryo(self):
        self.log.debug("Inserting cryo")
        self.chan_cryoswitch.set_value(0)
        self.wait_cryo_condition(False)

    def wait_cryo_condition(self, condition, timeout=1):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.chan_cond_cryo.get_value() == condition:
                break
            time.sleep(0.03)
        else:
            raise Exception("Cryo retract/insert failed")

    def sample_no_to_address(self, sample_no):
        if sample_no == 0:
            return (-1, -1)

        basket = int((sample_no - 1) / self.no_of_samples_in_basket) + 1
        sample = (sample_no - 1) % self.no_of_samples_in_basket + 1
        return (basket, sample)

    def sample_address_to_no(self, sample_address):
        basket, sample = sample_address
        sample_no = (basket - 1) * self.no_of_samples_in_basket + sample
        return sample_no

    def current_sample_changed(self, sample_no):
        self.log.debug(
            "P11SampleChanger -  current sample changed. now is: %s" % sample_no
        )
        self._update_selection()

    def read_current_sample(self):
        sample_no = self.chan_current_sample.get_value()
        self.log.debug("P11SampleChanger -  loaded sample no is: %s" % sample_no)
        return self.sample_no_to_address(sample_no)

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
        self.log.debug("- send unmount command")
        self.log.debug("- wait to finish")

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

        self._set_state(SampleChangerState.Ready)

    def wait_sc_move(self):
        while True:
            state = str(self.chan_state.get_value())
            if state == "ON":
                self._set_state(SampleChangerState.Ready)
                break
            time.sleep(0.05)

    def wait_sc_ready(self):
        t0 = last_printed = time.time()

        self.emit("progressStep", 20)

        last_elapsed = 0

        while True:
            elapsed = round(time.time() - t0)
            if elapsed != last_elapsed:
                self.emit("progressStep", 30 + elapsed * 5)
                last_elapsed = elapsed
            state = str(self.chan_state.get_value())
            if time.time() - last_printed > 2:
                self.log.debug("current state is %s" % state)
                last_printed = time.time()
            if state == "ON":
                break
            time.sleep(0.05)

    def state_channel_changed(self, value):
        self.log.debug(" - P11SampleChanger state changed. now is %s" % (value))
        if str(value) == "ON" or value == SampleChangerState.Ready:
            self._set_state(SampleChangerState.Ready)
        elif str(value) == "MOVING" or value == SampleChangerState.Moving:
            self._set_state(SampleChangerState.Moving)
        else:
            self._set_state(SampleChangerState.Unknown)

    def powered_changed(self, value):
        self.log.debug(" - P11SampleChanger powered changed. now is %s" % (value))

    def cryopos_changed(self, value):
        self.log.debug(" - P11SampleChanger cryopos changed. now is %s" % (value))

    def condition_changed(self, condition, value):
        self.log.debug(
            " - P11SampleChanger condition %s changed. now is %s" % (condition, value)
        )

    def update_enable_state(self, condition, value):
        self.log.debug(
            " - P11SampleChanger condition %s changed. now is %s" % (condition, value)
        )

    def _update_selection(self):
        self.log.debug(" updating selection")
        basket, sample = self.read_current_sample()

        self.log.debug(" looking for sample %s" % str((basket, sample)))

        for c in self.get_components():
            i = c.get_index()
            if basket == i + 1:
                self._set_selected_component(c)
                break

        # find sample
        for s in self.get_sample_list():
            # print(f"Sample coords = {s.get_coords()}")
            if s.get_coords() == (basket, sample):
                self.log.debug("      -   sample found")
                self._set_loaded_sample(s)
                self._set_selected_sample(s)
            else:
                s._set_loaded(False)

        self._set_selected_sample(None)

    def _set_loaded_sample(self, sample):
        previous_loaded = None

        for smp in self.get_sample_list():
            if smp.is_loaded():
                previous_loaded = smp
                break

        for smp in self.get_sample_list():
            if smp != sample:
                smp._set_loaded(False)
            else:
                self.log.debug(f" Found sample {smp} is loaded")
                self.log.debug(f"   getting loaded {self.get_loaded_sample()}")
                smp._set_loaded(True)
