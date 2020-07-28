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

import os
import time
import gevent
import logging
import tempfile
from datetime import datetime

from HardwareRepository.HardwareObjects.abstract import AbstractSampleChanger
from HardwareRepository.HardwareObjects.abstract.sample_changer import (
    Container,
    Crims,
    Sample,
)

from HardwareRepository import HardwareRepository as HWR


POSITION_DESC = {
    "Park": "Parked",
    "PickDew": "Pick from dewar",
    "PutDew": "Put in the dewar",
    "DewToMD": "On the way from dewar to MD",
    "MD": "MD",
    "Dryer": "Dryer",
    "CTB": "Center to base",
    "BTC": "Base to center",
    "CTEject": "Center puck eject",
    "EjectTC": "Put to cener puck",
}

STATUS_DESC = {
    "idl": "Idle",
    "bsy": "Busy",
    "err": "Error",
    "opn": "Opened",
    "on": "On",
    "off": "Off",
}

STATUS_STR_DESC = {
    "Sys": "Controller",
    "Rob": "Robot",
    "Grp": "Gripper",
    "Lid": "Dewar Lid",
    "Mag": "MD smart magnet",
    "Cry": "Cryo stream position",
    "Gui": "Guillotine",
    "Trsf": "Sample transfer state",
    "MD": "MD transfer state",
    "CDor": "Robot cage door",
    "CPuck": "Central puck",
    "VDet": "Vial in gripper detected",
    "Dry": "Dry gripper routine",
    "Prgs": "Progress bar",
    "PSw": "Puck switches",
    "SDet": "Sample detected on MD",
    "RPos": "Robot positions",
    "SPNr": "Sample puck in operation",
    "Err": "Error",
    "LErr": "Last 5 errors",
    "LSPmnt": "Last sample mounted",
    "CMD": "Command in progress",
    "MntPos": "MD mounting position",
    "Vial": "Vial detected",
}

CMD_STR_DESC = {
    "IDL": "Idle",
    "Nxt": "Nxt ?",
    "Mnt": "Mount sample",
    "Dis": "Dismount sample",
    "Tst": "Test ?",
    "Dry": "Dry",
}

ERROR_STR_DESC = {
    0: "No Error",
    1: "Guillotine valve 1",
    2: "Guillotine valve 2",
    3: "Puck switches",
    4: "Gripper",
    5: "Air pressure",
    6: "Lid valve 1",
    7: "Lid valve 2",
    8: "Crash",
    9: "Magnet",
    10: "Transfer",
    11: "Communication with diffractometer",
}


class Marvin(AbstractSampleChanger.SampleChanger):

    __TYPE__ = "Marvin"

    def __init__(self, *args, **kwargs):
        super(Marvin, self).__init__(self.__TYPE__, False, *args, **kwargs)
        self._selected_sample = None
        self._selected_basket = None

        self._num_baskets = None
        self._status_list = []
        self._state_string = None
        self._puck_switches = None
        self._centre_puck = None
        self._mounted_puck = None
        self._mounted_sample = None
        self._action_started = None
        self._progress = None
        self._veto = None
        self._sample_detected = None
        self._focusing_mode = None
        self._process_step_info = None
        self._command_list = None
        self._info_dict = {}
        self._in_error_state = False
        self._was_mount_error = False
        self._command_acknowledgement = False

        self.chan_status = None
        self.chan_sample_is_loaded = None
        self.chan_puck_switched = None
        self.chan_mounted_sample_puck = None
        self.chan_process_step_info = None

        self.cmd_mount_sample = None
        self.cmd_unmount_sample = None
        self.cmd_open_lid = None
        self.cmd_close_lid = None
        self.cmd_base_to_center = None
        self.cmd_center_to_base = None
        self.cmd_dry_gripper = None

        self.beam_focusing_hwobj = None

    def init(self):
        self._puck_switches = 0
        self._num_basket = self.get_property("numBaskets")
        if not self._num_basket:
            self._num_basket = 17

        for i in range(self._num_basket):
            basket = Container.Basket(self, i + 1)
            self._add_component(basket)

        self.chan_mounted_sample_puck = self.get_channel_object("chanMountedSamplePuck")
        self.chan_mounted_sample_puck.connect_signal(
            "update", self.mounted_sample_puck_changed
        )

        self.chan_process_step_info = self.get_channel_object(
            "chanProcessStepInfo", optional=True
        )
        if self.chan_process_step_info is not None:
            self.chan_process_step_info.connect_signal(
                "update", self.process_step_info_changed
            )

        self.chan_command_list = self.get_channel_object(
            "chanCommandList", optional=True
        )
        if self.chan_command_list is not None:
            self.chan_command_list.connect_signal("update", self.command_list_changed)

        self.chan_puck_switches = self.get_channel_object("chanPuckSwitches")
        self.chan_puck_switches.connect_signal("update", self.puck_switches_changed)

        self.chan_status = self.get_channel_object("chanStatusList")
        self.chan_status.connect_signal("update", self.status_list_changed)

        self.chan_sample_is_loaded = self.get_channel_object("chanSampleIsLoaded")
        self.chan_sample_is_loaded.connect_signal(
            "update", self.sample_is_loaded_changed
        )

        self.chan_veto = self.get_channel_object("chanVeto", optional=True)
        if self.chan_veto is not None:
            self.chan_veto.connect_signal("update", self.veto_changed)

        self.cmd_mount_sample = self.get_command_object("cmdMountSample")
        self.cmd_unmount_sample = self.get_command_object("cmdUnmountSample")
        self.cmd_open_lid = self.get_command_object("cmdOpenLid")
        self.cmd_close_lid = self.get_command_object("cmdCloseLid")
        self.cmd_base_to_center = self.get_command_object("cmdBaseToCenter")
        self.cmd_center_to_base = self.get_command_object("cmdCenterToBase")
        self.cmd_dry_gripper = self.get_command_object("cmdDryGripper")

        self.beam_focusing_hwobj = self.get_object_by_role("beam_focusing")
        if self.beam_focusing_hwobj is not None:
            self.connect(
                self.beam_focusing_hwobj,
                "focusingModeChanged",
                self.focusing_mode_changed,
            )
            (
                self._focusing_mode,
                beam_size,
            ) = self.beam_focusing_hwobj.get_active_focus_mode()
            self.focusing_mode_changed(self._focusing_mode, beam_size)
        else:
            self._focusing_mode = "P13mode"

        self._init_sc_contents()
        self._update_state()
        self._updateSCContents()
        self._update_loaded_sample()

        self.log_filename = self.get_property("log_filename")
        if self.log_filename is None:
            self.log_filename = os.path.join(
                tempfile.gettempdir(), "mxcube", "marvin.log"
            )
        logging.getLogger("HWR").debug("Marvin log filename: %s" % self.log_filename)
        AbstractSampleChanger.SampleChanger.init(self)

        self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
        self.status_list_changed(self.chan_status.get_value())
        self.puck_switches_changed(self.chan_puck_switches.get_value())
        self.mounted_sample_puck_changed(self.chan_mounted_sample_puck.get_value())
        self.sample_is_loaded_changed(self.chan_sample_is_loaded.get_value())

    def get_status_str_desc(self):
        return STATUS_STR_DESC

    def get_log_filename(self):
        """Returns log filename"""
        return self.log_filename

    def run_test(self):
        """Test method mounts/dismounts samples """
        samples_mounted = 0
        for cycle in range(5):
            for sample_index in range(1, 11):
                logging.getLogger("GUI").info(
                    "Sample changer: Mounting sample 1:%d" % sample_index
                )
                self.load("1:%02d" % sample_index, wait=True)
                logging.getLogger("GUI").info(
                    "Sample changer: Total mounts done: %d" % (samples_mounted + 1)
                )
                samples_mounted += 1
                gevent.sleep(1)

    def puck_switches_changed(self, puck_switches):
        """Updates puck switches"""
        self._puck_switches = int(puck_switches)
        self._info_dict["puck_switches"] = int(puck_switches)
        self._updateSCContents()

    def sample_is_loaded_changed(self, sample_detected):
        """Updates sample is loaded"""
        if self._sample_detected != sample_detected:

            if sample_detected:
                logging.getLogger("HWR").debug("Sample changer: sample re-appeared")
            else:
                logging.getLogger("HWR").debug("Sample changer: sample disappeared")

            self._sample_detected = sample_detected
            self._info_dict["sample_detected"] = sample_detected
            self._update_loaded_sample()
            self.update_info()

    def wait_command_acknowledgement(self, timeout):
        with gevent.Timeout(
            timeout, Exception("Timeout waiting for command acknowldegement")
        ):
            logging.getLogger("HWR").debug(
                "Sample changer: start waiting command acknowldegement"
            )
            while not self._command_acknowledgement:
                gevent.sleep(0.05)
            logging.getLogger("HWR").debug(
                "Sample changer: done waiting command acknowldegement"
            )

    def wait_sample_to_disappear(self, timeout):
        with gevent.Timeout(
            timeout, Exception("Timeout waiting for sample to disappear")
        ):
            logging.getLogger("HWR").debug(
                "Sample changer: start waiting sample to disappear"
            )
            while self._sample_detected:
                if self._was_mount_error:
                    self._was_mount_error = False
                    return
                gevent.sleep(0.05)
            logging.getLogger("HWR").debug(
                "Sample changer: done  waiting sample to disappear"
            )

    def wait_sample_to_appear(self, timeout):
        with gevent.Timeout(timeout, Exception("Timeout waiting for sample to appear")):
            logging.getLogger("HWR").debug(
                "Sample changer: start waiting sample to appear"
            )
            while not self._sample_detected:
                if self._was_mount_error:
                    self._was_mount_error = False
                    return
                gevent.sleep(0.05)
            logging.getLogger("HWR").debug(
                "Sample changer: done  waiting sample to appear"
            )

    def wait_sample_on_gonio(self, timeout):
        # with gevent.Timeout(timeout, Exception("Timeout waiting for sample on gonio")):
        #    while not self._sample_detected:
        #        gevent.sleep(0.05)
        with gevent.Timeout(timeout, Exception("Timeout waiting for centring phase")):
            while (
                HWR.beamline.diffractometer.get_current_phase()
                != HWR.beamline.diffractometer.PHASE_CENTRING
            ):
                if not self._is_device_busy():
                    return
                gevent.sleep(0.05)

    def is_sample_on_gonio(self):
        return self.chan_sample_is_loaded.get_value()
        # logging.getLogger("GUI").info("Sample on gonio check 1: %s" %first_try)
        # gevent.sleep(1.0)
        # second_try = self.chan_sample_is_loaded.get_value()
        # logging.getLogger("GUI").info("Sample on gonio check 2: %s" %second_try)
        # return first_try and second_try

    def mounted_sample_puck_changed(self, mounted_sample_puck):
        """Updates mounted puck index"""
        mounted_sample = mounted_sample_puck[0] - 1
        mounted_puck = mounted_sample_puck[1] - 1

        if mounted_puck != self._mounted_puck:
            self._mounted_puck = mounted_puck
            if self._focusing_mode == "P13mode":
                self._info_dict["mounted_puck"] = mounted_puck
            else:
                self._info_dict["mounted_puck"] = mounted_puck + 1
            self._updateSCContents()

        if mounted_sample != self._mounted_sample:
            self._mounted_sample = mounted_sample
            if self._focusing_mode == "P13mode":
                self._info_dict["mounted_sample"] = mounted_sample
            else:
                self._info_dict["mounted_sample"] = mounted_sample + 1
            self._update_loaded_sample()

    def veto_changed(self, status):
        """Veto changed callback. Used to wait for ready"""
        self._veto = status
        self._info_dict["veto"] = self._veto

    def focusing_mode_changed(self, focusing_mode, beam_size):
        """Sets CRL combination based on the focusing mode"""
        self._focusing_mode = focusing_mode
        self._info_dict["focus_mode"] = self._focusing_mode

    def process_step_info_changed(self, process_step_info):
        self._process_step_info = process_step_info.replace("\n", " ")
        self._command_acknowledgement = True
        if "error" in process_step_info.lower():
            self._was_mount_error = True
            logging.getLogger("GUI").error(
                "Sample changer: %s" % self._process_step_info
            )
            # GB: 20190304: this seemd to lock mxcube forever on any marvin error
            # self._in_error_state = True
            # self._set_state(AbstractSampleChanger.SampleChangerState.Alarm)

        else:
            logging.getLogger("GUI").info(
                "Sample changer: %s" % self._process_step_info
            )
        self._info_dict["process_step"] = self._process_step_info

    def command_list_changed(self, cmd_list):
        self._command_list = cmd_list.replace("\n", "")
        logging.getLogger("GUI").info(
            "Sample changer: Last command - %s" % self._command_list
        )
        self._info_dict["command_list"] = self._command_list

    def open_lid(self):
        self.cmd_open_lid(1)

    def close_lid(self):
        self.cmd_close_lid(1)

    def base_to_center(self):
        return
        # self.cmd_base_to_center(1)

    def center_to_base(self):
        return
        # self.cmd_center_to_base(1)

    def dry_gripper(self):
        self.cmd_dry_gripper(1)

    def get_sample_properties(self):
        """Gets sample properties """
        return (Container.Pin.__HOLDER_LENGTH_PROPERTY__,)

    def assert_can_execute_task(self):
        return

    def _do_update_info(self):
        """Updates the sample changers status: mounted pucks, state,
           currently loaded sample
        """
        # self._update_state()
        # self._updateSCContents()
        # call this method if status string changed
        # self._update_loaded_sample()

    def _directly_update_selected_component(self, basket_no, sample_no):
        """Directly updates necessary sample"""
        basket = None
        sample = None
        if basket_no is not None and basket_no > 0 and basket_no <= self._num_basket:
            basket = self.get_component_by_address(
                Container.Basket.get_basket_address(basket_no)
            )
            if (
                sample_no is not None
                and sample_no > 0
                and sample_no <= len(basket.get_sample_list())
            ):
                sample = self.get_component_by_address(
                    Container.Pin.get_sample_address(basket_no, sample_no)
                )
        self._set_selected_component(basket)
        self._set_selected_sample(sample)

    def _do_select(self, component):
        """Selects a new component (basket or sample).
           Uses method >_directly_update_selected_component< to actually
           search and select the corrected positions.
        """
        if type(component) in (Container.Pin, Sample.Sample):
            selected_basket_no = component.get_basket_no()
            selected_sample_no = component.get_index() + 1
        elif isinstance(component, Container.Container) and (
            component.get_type() == Container.Basket.__TYPE__
        ):
            selected_basket_no = component.get_index() + 1
            selected_sample_no = None

        self._directly_update_selected_component(selected_basket_no, selected_sample_no)

    def _do_scan(self, component, recursive):
        """Scans the barcode of a single sample, puck or recursively even the
           complete sample changer.
           Not implemented
        """
        print("_do_scan TODO")

    def _do_load(self, sample=None):
        """Loads a sample on the diffractometer. Performs a simple put operation
           if the diffractometer is empty, and a sample exchange (unmount of
           old + mount of  new sample) if a sample is already mounted on
           the diffractometer.
        """
        # self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
        log = logging.getLogger("GUI")

        if self._focusing_mode not in (
            "Collimated",
            "Double",
            "Imaging",
            "TREXX",
            "P13mode",
        ):
            error_msg = "Focusing mode is undefined. Sample loading is disabled"
            log.error(error_msg)
            return

        # if self._focusing_mode in ("Collimated", "Double") and not self._centre_puck:
        #    log.error("No center puck detected. Please do Base-to-Center with any puck.")
        #    return

        if self._in_error_state:
            log.error(
                "Sample changer is in error state. "
                + "All commands are disabled."
                + "Fix the issue and reset sample changer in MXCuBE"
            )
            return

        start_time = datetime.now()
        selected = self.get_selected_sample()

        if sample is not None:
            if sample != selected:
                self._do_select(sample)
                selected = self.get_selected_sample()
        else:
            if selected is not None:
                sample = selected
            else:
                raise Exception("No sample selected")

        basket_index = selected.get_basket_no()
        sample_index = selected.get_vial_no()

        # 1. Check if sample is on gonio. This should never happen
        # because if mount is requested and on gonio is sample then
        # first sample is dismounted
        if self._focusing_mode == "P13mode":
            if self.is_sample_on_gonio():
                if selected == self.get_loaded_sample():
                    msg = (
                        "The sample "
                        + str(self.get_loaded_sample().get_address())
                        + " is already loaded"
                    )
                    raise Exception(msg)
                else:
                    self._do_unload()

        msg = "Sample changer: Loading sample %d:%d" % (
            int(basket_index),
            int(sample_index),
        )
        log.warning(msg + " Please wait...")
        self.emit("progressInit", (msg, 100, False))

        # 2. Set diffractometer transfer phase
        logging.getLogger("HWR").debug(
            "%s %s"
            % (
                HWR.beamline.diffractometer.get_current_phase(),
                HWR.beamline.diffractometer.PHASE_TRANSFER,
            )
        )
        if (
            HWR.beamline.diffractometer.get_current_phase()
            != HWR.beamline.diffractometer.PHASE_TRANSFER
        ):
            logging.getLogger("HWR").debug("set transfer")
            HWR.beamline.diffractometer.set_phase(
                HWR.beamline.diffractometer.PHASE_TRANSFER, 60.0
            )
            time.sleep(2)
            if (
                HWR.beamline.diffractometer.get_current_phase()
                != HWR.beamline.diffractometer.PHASE_TRANSFER
            ):
                log.error(
                    "Diffractometer is not in the transfer phase. "
                    + "Sample will not be mounted"
                )
                raise Exception("Unable to set Transfer phase")

        # logging.getLogger("HWR").debug("Sample changer: Closing guillotine...")
        # HWR.beamline.detector.close_cover()
        # logging.getLogger("HWR").debug("Sample changer: Guillotine closed")
        # 3. If necessary move detector to save position
        if self._focusing_mode == "P13mode":
            if HWR.beamline.detector.distance.get_value() < 399.0:
                log.info("Sample changer: Moving detector to save position...")
                self._veto = 1
                HWR.beamline.detector.distance.set_value(400, timeout=45)
                time.sleep(1)
                self.waitVeto(20.0)
                log.info("Sample changer: Detector moved to save position")
        else:
            pass
            # logging.getLogger("HWR").debug("Sample changer: Closing guillotine...")
            # HWR.beamline.detector.close_cover()
            ##logging.getLogger("HWR").debug("Sample changer: Guillotine closed")

        # 4. Executed command and wait till device is ready
        if self._focusing_mode == "P13mode":
            self._execute_server_task(
                self.cmd_mount_sample, int(sample_index), int(basket_index)
            )
        else:
            if (
                self._focusing_mode == "Collimated"
                or self._focusing_mode == "Imaging"
                or self._focusing_mode == "TREXX"
            ):
                self._execute_server_task(
                    self.cmd_mount_sample, int(sample_index), int(basket_index), 1
                )
            elif self._focusing_mode == "Double":
                self._execute_server_task(
                    self.cmd_mount_sample, int(sample_index), int(basket_index), 3
                )

        self.emit("progressStop", ())

        if self.is_sample_on_gonio():
            log.info(
                "Sample changer: Sample %d:%d loaded"
                % (int(basket_index), int(sample_index))
            )
            if self._focusing_mode == "P13mode":
                HWR.beamline.diffractometer.set_phase(
                    HWR.beamline.diffractometer.PHASE_CENTRING, 60.0
                )
                # HWR.beamline.diffractometer.close_kappa()
        else:
            log.error(
                "Sample changer: Failed to load sample %d:%d"
                % (int(basket_index), int(sample_index))
            )
            raise Exception("Sample not loaded!")

    def load(self, sample=None, wait=True):
        """ Load a sample"""
        # self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
        if self._focusing_mode == "P13mode":
            AbstractSampleChanger.SampleChanger.load(self, sample, wait)
        else:
            sample = self._resolve_component(sample)
            self.assert_not_charging()
            return self._execute_task(
                AbstractSampleChanger.SampleChangerState.Loading,
                wait,
                self._do_load,
                sample,
            )

    def _do_unload(self, sample_slot=None):
        """Unloads a sample from the diffractometer"""
        log = logging.getLogger("GUI")

        # self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
        if self._focusing_mode not in (
            "Collimated",
            "Double",
            "Imaging",
            "TREXX",
            "P13mode",
        ):
            error_msg = "Focusing mode is undefined. Sample loading is disabled"
            log.error(error_msg)
            return

        if self._in_error_state:
            log.error(
                "Sample changer is in error state. "
                + "All commands are disabled."
                + "Fix the issue and reset sample changer in MXCuBE"
            )
            return

        if self._focusing_mode == "P13mode":
            sample_index = self._mounted_sample
            basket_index = self._mounted_puck
        else:
            sample_index = self._mounted_sample + 1
            basket_index = self._mounted_puck + 1

        msg = "Sample changer: Unloading sample %d:%d" % (basket_index, sample_index)
        log.warning(msg + ". Please wait...")
        self.emit("progressInit", (msg, 100, False))

        if (
            HWR.beamline.diffractometer.get_current_phase()
            != HWR.beamline.diffractometer.PHASE_TRANSFER
        ):
            HWR.beamline.diffractometer.set_phase(
                HWR.beamline.diffractometer.PHASE_TRANSFER, 60
            )
            if (
                HWR.beamline.diffractometer.get_current_phase()
                != HWR.beamline.diffractometer.PHASE_TRANSFER
            ):
                log.error(
                    "Diffractometer is not in the transfer phase. "
                    + "Sample will not be mounted"
                )
                raise Exception("Unable to set Transfer phase")

        # HWR.beamline.detector.close_cover()
        if self._focusing_mode == "P13mode":
            if HWR.beamline.detector.distance.get_value() < 399.0:
                log.info("Sample changer: Moving detector to save position ...")
                self._veto = 1
                HWR.beamline.detector.distance.set_value(400, timeout=45)
                time.sleep(1)
                self.waitVeto(20.0)
                log.info("Sample changer: Detector moved to save position")
        else:
            pass
            # HWR.beamline.detector.close_cover()

        start_time = datetime.now()

        if self._focusing_mode == "P13mode":
            self._execute_server_task(
                self.cmd_unmount_sample, sample_index, basket_index
            )
        else:
            if (
                self._focusing_mode == "Collimated"
                or self._focusing_mode == "Imaging"
                or self._focusing_mode == "TREXX"
            ):

                self._execute_server_task(
                    self.cmd_unmount_sample, sample_index, basket_index, 1
                )
            elif self._focusing_mode == "Double":
                self._execute_server_task(
                    self.cmd_unmount_sample, sample_index, basket_index, 3
                )

        self.emit("progressStop", ())

        if self.is_sample_on_gonio():
            log.error(
                "Sample changer: Failed to unload sample %d:%d"
                % (basket_index, sample_index)
            )
            raise Exception("Sample not unloaded!")
        else:
            log.info(
                "Sample changer: Sample %d:%d unloaded" % (basket_index, sample_index)
            )

    def clear_basket_info(self, basket):
        """Clears information about basket"""
        # TODO
        return

    def _do_change_mode(self, mode):
        """Changes the mode of sample changer"""
        return

    def _do_abort(self):
        """Aborts the sample changer"""
        return

    def _do_reset(self):
        """Clean all sample info, move sample to his position and move puck
           from center to base"""
        self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
        self._init_sc_contents()
        self._in_error_state = False

    def _execute_server_task(self, method, *args):
        """Executes called cmd, waits until sample changer is ready and
           updates loaded sample info
        """
        # self.wait_ready(60.0)
        self._state_string = "Bsy"
        self._progress = 5

        arg_arr = []
        for arg in args:
            arg_arr.append(arg)

        logging.getLogger("HWR").debug(
            "Sample changer: Sending cmd with arguments: %s..." % str(arg_arr)
        )

        self._command_acknowledgement = False

        method(arg_arr)
        logging.getLogger("HWR").debug("Sample changer: Waiting ready...")
        self.wait_command_acknowledgement(5.0)
        self._action_started = True
        gevent.sleep(5)
        if method == self.cmd_mount_sample:
            # self.wait_sample_on_gonio(120.0)
            self._was_mount_error = False
            self.wait_sample_to_disappear(40.0)
            self.wait_sample_to_appear(60.0)
        else:
            self.wait_ready(120.0)
        logging.getLogger("HWR").debug("Sample changer: Ready")
        logging.getLogger("HWR").debug("Sample changer: Waiting veto...")
        self.waitVeto(20.0)
        logging.getLogger("HWR").debug("Sample changer: Veto ready")
        # if self._is_device_busy():
        #    raise Exception("Action finished to early. Sample changer is not ready!!!")
        self.sample_is_loaded_changed(self.chan_sample_is_loaded.get_value())
        self._update_state()
        self._update_loaded_sample()
        self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
        self._action_started = False

    def _update_state(self):
        state = self._read_state()
        if (
            state == AbstractSampleChanger.SampleChangerState.Moving
            and self._is_device_busy(self.get_state())
        ):
            return
        self._set_state(state)

    def _read_state(self):
        """Converts state string to defined state"""
        state_converter = {
            "ALARM": AbstractSampleChanger.SampleChangerState.Alarm,
            "Err": AbstractSampleChanger.SampleChangerState.Fault,
            "Idl": AbstractSampleChanger.SampleChangerState.Ready,
            "Bsy": AbstractSampleChanger.SampleChangerState.Moving,
        }
        return state_converter.get(
            self._state_string, AbstractSampleChanger.SampleChangerState.Unknown
        )

    def _is_device_busy(self, state=None):
        """Checks whether Sample changer is busy"""
        if state is None:
            state = self._read_state()
        if self._progress >= 100 and state in (
            AbstractSampleChanger.SampleChangerState.Ready,
            AbstractSampleChanger.SampleChangerState.Loaded,
            AbstractSampleChanger.SampleChangerState.Alarm,
            AbstractSampleChanger.SampleChangerState.Disabled,
            AbstractSampleChanger.SampleChangerState.Fault,
            AbstractSampleChanger.SampleChangerState.StandBy,
        ):
            return False
        else:
            return True

    def _is_device_ready(self):
        """Checks whether Sample changer is ready"""
        state = self._read_state()
        return state in (
            AbstractSampleChanger.SampleChangerState.Ready,
            AbstractSampleChanger.SampleChangerState.Charging,
        )

    def wait_ready(self, timeout=None):
        """Waits until the samle changer is ready"""
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while self._is_device_busy():
                gevent.sleep(0.05)

    def waitVeto(self, timeout=20):
        with gevent.Timeout(timeout, Exception("Timeout waiting for veto")):
            while self._veto == 1:
                self.veto_changed(self.chan_veto.get_value)
                gevent.sleep(0.1)

    def _update_selection(self):
        """Updates selected basked and sample"""

        basket = None
        sample = None
        try:
            basket_no = self._selected_basket
            if (
                basket_no is not None
                and basket_no > 0
                and basket_no <= self._num_basket
            ):
                basket = self.get_component_by_address(
                    Container.Basket.get_basket_address(basket_no)
                )
                sample_no = self._selected_sample
                if (
                    sample_no is not None
                    and sample_no > 0
                    and sample_no <= Container.Basket.NO_OF_SAMPLES_PER_PUCK
                ):
                    sample = self.get_component_by_address(
                        Container.Pin.get_sample_address(basket_no, sample_no)
                    )
        except BaseException:
            pass
        self._set_selected_component(basket)
        self._set_selected_sample(sample)

    def _update_loaded_sample(self):
        """
        Updates loaded sample
        """

        if (
            self._sample_detected
            and self._mounted_sample > -1
            and self._mounted_puck > -1
            and self._centre_puck
        ):
            if self._focusing_mode == "P13mode":
                new_sample = self.get_component_by_address(
                    Container.Pin.get_sample_address(
                        self._mounted_puck, self._mounted_sample
                    )
                )
            else:
                new_sample = self.get_component_by_address(
                    Container.Pin.get_sample_address(
                        self._mounted_puck + 1, self._mounted_sample + 1
                    )
                )
        else:
            new_sample = None

        if self.get_loaded_sample() != new_sample:
            old_sample = self.get_loaded_sample()
            if old_sample is not None:
                # there was a sample on the gonio
                loaded = False
                has_been_loaded = True
                old_sample._set_loaded(loaded, has_been_loaded)
            if new_sample is not None:
                self._update_sample_barcode(new_sample)
                loaded = True
                has_been_loaded = True
                new_sample._set_loaded(loaded, has_been_loaded)

    def _update_sample_barcode(self, sample):
        """
        Updates the barcode of >sample< in the local database
        after scanning with the barcode reader.
        """
        datamatrix = "NotAvailable"
        scanned = len(datamatrix) != 0
        if not scanned:
            datamatrix = "----------"
        sample._set_info(sample.is_present(), datamatrix, scanned)

    def _init_sc_contents(self):
        """
        Initializes the sample changer content with default values.
        """
        basket_list = [("", 4)] * self._num_basket
        for basket_index in range(self._num_basket):
            basket = self.get_components()[basket_index]
            datamatrix = None
            present = scanned = True
            basket._set_info(present, datamatrix, scanned)

        # create temporary list with default sample information and indices
        sample_list = []
        for basket_index in range(self._num_basket):
            for sample_index in range(10):
                sample_list.append(
                    (
                        "",
                        basket_index + 1,
                        sample_index + 1,
                        1,
                        Container.Pin.STD_HOLDERLENGTH,
                    )
                )
        # write the default sample information into permanent Pin objects
        for spl in sample_list:
            sample = self.get_component_by_address(
                Container.Pin.get_sample_address(spl[1], spl[2])
            )
            datamatrix = None
            present = scanned = loaded = _has_been_loaded = False
            sample._set_info(present, datamatrix, scanned)
            sample._set_loaded(loaded, has_been_loaded)
            sample._set_holder_length(spl[4])

    def _updateSCContents(self):
        """
        Updates sample changer content
        """
        for basket_index in range(self._num_basket):
            basket = self.get_components()[basket_index]

            if self._focusing_mode == "P13mode":
                bsk_index = basket_index + 1
            else:
                bsk_index = basket_index

            if (
                (int(self._puck_switches) & pow(2, basket_index) > 0)
                or (self._mounted_puck == bsk_index)
                and self._centre_puck
            ):
                # f puck_switches & (1 << basket_index):
                # basket was mounted
                present = True
                scanned = False
                datamatrix = None
            else:
                # basket was removed
                present = False
                scanned = False
                datamatrix = None

            basket._set_info(present, datamatrix, scanned)
            # set the information for all dependent samples
            """
            for sample_index in range(10):
                sample = self.get_component_by_address(Pin.get_sample_address(\
                    (basket_index + 1), (sample_index + 1)))
                present = sample.get_container().is_present()
                if present:
                    datamatrix = '%d:%d - Not defined' % \
                       (bsk_index, sample_index)
                else:
                    datamatrix = None
                datamatrix = None
                scanned = False
                sample._set_info(present, datamatrix, scanned)
                # forget about any loaded state in newly mounted or removed basket)
                loaded = _has_been_loaded = False
                sample._set_loaded(loaded, has_been_loaded)
            """

        self._trigger_selection_changed_event()

    def status_list_changed(self, status_string):
        tmp_string = status_string.replace(" ", "")
        tmp_string1 = tmp_string.replace("On\r", "On")
        status_string = tmp_string1.replace("\rSys", ";Sys")
        self._status_list = status_string.split(";")

        for status in self._status_list:
            property_status_list = status.split(":")
            if len(property_status_list) < 2:
                continue

            prop_name = property_status_list[0]
            prop_value = property_status_list[1]

            if prop_name == "Rob":
                if (
                    self._state_string != prop_value
                    and prop_value in ("Idl", "Bsy", "Err")
                    and self._action_started
                ):
                    self._state_string = prop_value
                    logging.getLogger("HWR").debug(
                        "Sample changer: status changed: %s" % self._state_string
                    )
                    self._update_state()
            elif prop_name == "Prgs":
                try:
                    if int(prop_value) != self._progress and self._action_started:
                        self._progress = int(prop_value)
                        self.emit("progressStep", self._progress)
                        self._info_dict["progress"] = self._progress
                except BaseException:
                    pass
            elif prop_name == "CPuck":
                if prop_value == "1":
                    centre_puck = True
                elif prop_value == "0":
                    centre_puck = False

                if centre_puck != self._centre_puck:
                    self._centre_puck = centre_puck
                    self._info_dict["centre_puck"] = self._centre_puck
                    self._updateSCContents()
                    self._update_loaded_sample()
            elif prop_name == "Lid":
                self._info_dict["lid_opened"] = prop_value == "Opn"
            elif prop_name == "Err":
                logging.getLogger("GUI").error(
                    "Sample changer: Error (%s)" % prop_value
                )
                logging.getLogger("GUI").error("Details: ")

                for status in self._status_list:
                    property_status_list = status.split(":")
                    if len(property_status_list) < 2:
                        continue

                    prop_name = property_status_list[0]
                    prop_value = property_status_list[1]

                    if prop_name in STATUS_STR_DESC:
                        logging.getLogger("GUI").error(
                            " - %s: %s " % (STATUS_STR_DESC[prop_name], prop_value)
                        )

        self.emit("statusListChanged", self._status_list)
        self.emit("infoDictChanged", self._info_dict)

    def re_emit_values(self):
        self.emit("statusListChanged", self._status_list)
        self.emit("infoDictChanged", self._info_dict)
        self._trigger_info_changed_event()
        self._trigger_selection_changed_event()
