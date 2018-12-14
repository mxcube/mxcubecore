#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import os
import time
import logging
import tempfile
from datetime import datetime
from abstract.AbstractSampleChanger import *


POSITION_DESC = {"Park" : "Parked",
                 "PickDew": "Pick from dewar",
                 "PutDew" : "Put in the dewar",
                 "DewToMD" : "On the way from dewar to MD",
                 "MD": "MD",
                 "Dryer": "Dryer",
                 "CTB": "Center to base",
                 "BTC": "Base to center",
                 "CTEject": "Center puck eject",
                 "EjectTC": "Put to cener puck"}

STATUS_DESC = {"idl": "Idle",
               "bsy": "Busy",
               "err": "Error",
               "opn": "Opened",
               "on": "On",
               "off": "Off"}

STATUS_STR_DESC = {"Sys": "Controller",
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
                   "Vial": "Vial detected"}

CMD_STR_DESC = {"IDL": "Idle",
                "Nxt": "Nxt ?",
                "Mnt": "Mount sample",
                "Dis": "Dismount sample",
                "Tst": "Test ?",
                "Dry": "Dry"}

ERROR_STR_DESC = {0: "No Error",
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
                  11: "Communication with diffractometer"}
   

class Marvin(SampleChanger):
    """
    """    
    __TYPE__ = "Marvin"    

    def __init__(self, *args, **kwargs):
        super(Marvin, self).__init__(self.__TYPE__,False, *args, **kwargs)
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

        self.detector_hwobj = None
        self.beam_focusing_hwobj = None
        self.diffractometer_hwobj = None
            
    def init(self):      
        self._puck_switches = 0
        self._num_basket = self.getProperty("numBaskets")
        if not self._num_basket:
            self._num_basket = 17

        for i in range(self._num_basket):
            basket = Basket(self, i + 1)
            self._addComponent(basket)

        self.chan_mounted_sample_puck = self.getChannelObject("chanMountedSamplePuck")
        self.chan_mounted_sample_puck.connectSignal("update", self.mounted_sample_puck_changed)

        self.chan_process_step_info = self.getChannelObject("chanProcessStepInfo",
                                                            optional=True)
        if self.chan_process_step_info is not None:
            self.chan_process_step_info.connectSignal("update", self.process_step_info_changed)

        self.chan_command_list = self.getChannelObject("chanCommandList",
                                                       optional=True)
        if self.chan_command_list is not None:
            self.chan_command_list.connectSignal("update", self.command_list_changed)

        self.chan_puck_switches = self.getChannelObject("chanPuckSwitches")
        self.chan_puck_switches.connectSignal("update", self.puck_switches_changed)
        
        self.chan_status = self.getChannelObject("chanStatusList")
        self.chan_status.connectSignal("update", self.status_list_changed)

        self.chan_sample_is_loaded = self.getChannelObject("chanSampleIsLoaded")
        self.chan_sample_is_loaded.connectSignal("update", self.sample_is_loaded_changed)

        self.chan_veto = self.getChannelObject("chanVeto", optional=True)
        if self.chan_veto is not None:
            self.chan_veto.connectSignal("update", self.veto_changed)

        self.cmd_mount_sample = self.getCommandObject("cmdMountSample")
        self.cmd_unmount_sample = self.getCommandObject("cmdUnmountSample")
        self.cmd_open_lid = self.getCommandObject("cmdOpenLid")
        self.cmd_close_lid = self.getCommandObject("cmdCloseLid")
        self.cmd_base_to_center = self.getCommandObject("cmdBaseToCenter")
        self.cmd_center_to_base = self.getCommandObject("cmdCenterToBase")
        self.cmd_dry_gripper = self.getCommandObject("cmdDryGripper")

        self.detector_hwobj = self.getObjectByRole('detector')
        self.beam_focusing_hwobj = self.getObjectByRole("beam_focusing")
        if self.beam_focusing_hwobj is not None:
            self.connect(self.beam_focusing_hwobj,
                         "focusingModeChanged",
                         self.focusing_mode_changed)
            self._focusing_mode, beam_size = self.beam_focusing_hwobj.get_active_focus_mode()
            self.focusing_mode_changed(self._focusing_mode, beam_size)
        else:
            self._focusing_mode = "P13mode"

        self.diffractometer_hwobj = self.getObjectByRole("diffractometer")

        self._initSCContents()
        self._updateState()
        self._updateSCContents()
        self._updateLoadedSample()

        self.log_filename = self.getProperty("log_filename")
        if self.log_filename is None:
            self.log_filename = os.path.join(tempfile.gettempdir(),
                                             "mxcube",
                                             "marvin.log")
        logging.getLogger("HWR").debug("Marvin log filename: %s" % self.log_filename)
        SampleChanger.init(self)

        self._setState(SampleChangerState.Ready)
        self.puck_switches_changed(self.chan_puck_switches.getValue())
        self.mounted_sample_puck_changed(self.chan_mounted_sample_puck.getValue())
        self.sample_is_loaded_changed(self.chan_sample_is_loaded.getValue())

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
                logging.getLogger("GUI").info("Sample changer: Mounting sample 1:%d" % sample_index)
                self.load("1:%02d" % sample_index, wait=True)
                logging.getLogger("GUI").info("Sample changer: Total mounts done: %d" % (samples_mounted + 1))
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
            self._sample_detected = sample_detected
            self._info_dict["sample_detected"] = sample_detected
            self._updateLoadedSample()
            self.updateInfo()

    def wait_sample_on_gonio(self, timeout):
        #with gevent.Timeout(timeout, Exception("Timeout waiting for sample on gonio")):
        #    while not self._sample_detected:
        #        gevent.sleep(0.05)
        with gevent.Timeout(timeout, Exception("Timeout waiting for centring phase")):
            while self.diffractometer_hwobj.get_current_phase() != \
                  self.diffractometer_hwobj.PHASE_CENTRING:
                if not self._isDeviceBusy():
                    return
                gevent.sleep(0.05)

    def is_sample_on_gonio(self):
        return self.chan_sample_is_loaded.getValue()
        #logging.getLogger("GUI").info("Sample on gonio check 1: %s" %first_try)
        #gevent.sleep(1.0)
        #second_try = self.chan_sample_is_loaded.getValue()
        #logging.getLogger("GUI").info("Sample on gonio check 2: %s" %second_try)
        #return first_try and second_try

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
            self._updateLoadedSample()

    def veto_changed(self, status):
        """Veto changed callback. Used to wait for ready"""
        self._veto = status
        self._info_dict["veto"] = self._veto

    def focusing_mode_changed(self, focusing_mode, beam_size):
        """Sets CRL combination based on the focusing mode"""
        self._focusing_mode = focusing_mode
        self._info_dict["focus_mode"] = self._focusing_mode

    def process_step_info_changed(self, process_step_info):
        self._process_step_info = process_step_info
        if "error" in process_step_info.lower():
            logging.getLogger("GUI").error("Sample changer: %s" % self._process_step_info)
            self._in_error_state = True
            self._setState(SampleChangerState.Alarm)
        else:
            logging.getLogger("GUI").info("Sample changer: %s" % self._process_step_info) 
        self._info_dict["process_step"] = self._process_step_info

    def command_list_changed(self, cmd_list):
        self._command_list = cmd_list
        logging.getLogger("GUI").info("Sample changer: Last command - %s" % self._command_list)
        self._info_dict["command_list"] = self._command_list

    def open_lid(self):
        self.cmd_open_lid(1)

    def close_lid(self):
        self.cmd_close_lid(1)

    def base_to_center(self):
        return
        #self.cmd_base_to_center(1)

    def center_to_base(self):
        return
        #self.cmd_center_to_base(1)
    
    def dry_gripper(self):
        self.cmd_dry_gripper(1)

    def getSampleProperties(self):
        """Gets sample properties """
        return (Pin.__HOLDER_LENGTH_PROPERTY__,)
        
    def _doUpdateInfo(self):       
        """Updates the sample changers status: mounted pucks, state, 
           currently loaded sample
        """
        pass
        #self._updateState()               
        #self._updateSCContents()
        #call this method if status string changed
        #self._updateLoadedSample()
                    
    def _directlyUpdateSelectedComponent(self, basket_no, sample_no):    
        """Directly updates necessary sample"""
        basket = None
        sample = None
        if basket_no is not None and basket_no>0 and \
           basket_no <=self._num_basket:
            basket = self.getComponentByAddress(Basket.getBasketAddress(basket_no))
            if sample_no is not None and sample_no>0 and \
               sample_no <= len(basket.getSampleList()):
                sample = self.getComponentByAddress(Pin.getSampleAddress(basket_no, sample_no))            
        self._setSelectedComponent(basket)
        self._setSelectedSample(sample)

    def _doSelect(self,component):
        """Selects a new component (basket or sample).
           Uses method >_directlyUpdateSelectedComponent< to actually 
           search and select the corrected positions.
        """
        if type(component) in (Pin, Sample):
            selected_basket_no = component.getBasketNo()
            selected_sample_no = component.getIndex()+1
        elif isinstance(component, Container) and ( component.getType() == Basket.__TYPE__):
            selected_basket_no = component.getIndex()+1
            selected_sample_no = None

        self._directlyUpdateSelectedComponent(selected_basket_no, selected_sample_no)
            
    def _doScan(self,component,recursive):
        """Scans the barcode of a single sample, puck or recursively even the 
           complete sample changer.
           Not implemented
        """
        print "_doScan TODO"
    
    def _doLoad(self,sample=None):
        """Loads a sample on the diffractometer. Performs a simple put operation
           if the diffractometer is empty, and a sample exchange (unmount of 
           old + mount of  new sample) if a sample is already mounted on 
           the diffractometer.
        """
        self._setState(SampleChangerState.Ready)
        log = logging.getLogger("GUI")

        if self._focusing_mode not in ("Collimated", "Double", "P13mode"):
            error_msg = "Focusing mode is undefined. Sample loading is disabled"
            log.error(error_msg)
            return

        #if self._focusing_mode in ("Collimated", "Double") and not self._centre_puck:
        #    log.error("No center puck detected. Please do Base-to-Center with any puck.")
        #    return

        if self._in_error_state:
            log.error("Sample changer is in error state. " + \
                      "All commands are disabled." + \
                      "Fix the issue and reset sample changer in MXCuBE")
            return
        
        start_time = datetime.now()
        selected = self.getSelectedSample()

        if sample is not None:
            if sample != selected:
                self._doSelect(sample)
                selected=self.getSelectedSample()
        else:
            if selected is not None:
                 sample = selected
            else:
               raise Exception("No sample selected")

        basket_index = selected.getBasketNo()
        sample_index = selected.getVialNo()

        # 1. Check if sample is on gonio. This should never happen
        # because if mount is requested and on gonio is sample then
        # first sample is dismounted
        if self._focusing_mode == "P13mode":
            if self.is_sample_on_gonio():
                if selected==self.getLoadedSample():
                    msg = "The sample " + \
                          str(self.getLoadedSample().getAddress()) + \
                          " is already loaded"
                    raise Exception(msg)
                else:
                    self._doUnload()

        msg = "Sample changer: Loading sample %d:%d" %(\
               int(basket_index), int(sample_index))
        log.warning(msg + " Please wait...")
        self.emit("progressInit", (msg, 100, False))

        # 2. Set diffractometer transfer phase
        logging.getLogger("HWR").debug("%s %s"%(self.diffractometer_hwobj.get_current_phase(),self.diffractometer_hwobj.PHASE_TRANSFER))
        if self.diffractometer_hwobj.get_current_phase() != \
           self.diffractometer_hwobj.PHASE_TRANSFER:
            logging.getLogger("HWR").debug("set transfer")
            self.diffractometer_hwobj.set_phase(self.diffractometer_hwobj.PHASE_TRANSFER, 60.0)
            time.sleep(2)
            if self.diffractometer_hwobj.get_current_phase() != \
               self.diffractometer_hwobj.PHASE_TRANSFER:
                log.error("Diffractometer is not in the transfer phase. " +\
                          "Sample will not be mounted")
                raise Exception("Unable to set Transfer phase")

        #logging.getLogger("HWR").debug("Sample changer: Closing guillotine...")
        #self.detector_hwobj.close_cover()
        #logging.getLogger("HWR").debug("Sample changer: Guillotine closed")
        # 3. If necessary move detector to save position
        if self._focusing_mode == "P13mode":
            if self.detector_hwobj.get_distance() < 399.0:
                log.info("Sample changer: Moving detector to save position...")
                self._veto = 1
                self.detector_hwobj.set_distance(400, timeout=45)
                time.sleep(1)
                self.waitVeto(20.0)
                log.info("Sample changer: Detector moved to save position")
        else:
            logging.getLogger("HWR").debug("Sample changer: Closing guillotine...")
            self.detector_hwobj.close_cover()
            logging.getLogger("HWR").debug("Sample changer: Guillotine closed")

        # 4. Executed command and wait till device is ready 
        if self._focusing_mode == "P13mode":
            self._executeServerTask(self.cmd_mount_sample,
                                    int(sample_index),
                                    int(basket_index))
        else:
            if self._focusing_mode == "Collimated":
                self._executeServerTask(self.cmd_mount_sample,
                                        int(sample_index),
                                        int(basket_index),
                                        1)
            elif self._focusing_mode == "Double":
                self._executeServerTask(self.cmd_mount_sample,
                                        int(sample_index),
                                        int(basket_index),
                                        3)
 
        # 5. Finish by adding a log line
        self.emit("progressStop", ())
        end_time = datetime.now()
        time_delta = "%d" % (end_time - start_time).total_seconds()
        try:
           if os.getenv("SUDO_USER"):
               user_name = os.getenv("SUDO_USER")
           else:
               user_name = os.getenv("USER")

           log_file = open(self.log_filename, "a")
           log_msg = "%s,%s,%s,%s,%s,%d,%d" % (
                     start_time.strftime("%Y-%m-%d %H:%M:%S"),
                     end_time.strftime("%Y-%m-%d %H:%M:%S"),
                     time_delta,
                     user_name,
                     "load",
                     self._mounted_puck,
                     self._mounted_sample)
           if not self.is_sample_on_gonio():
               log_msg += ",Error\n"
           else:
               log_msg += ",Success\n"
           log_file.write(log_msg)
           log_file.close()
        except:
           pass

        if self.is_sample_on_gonio():
            log.info("Sample changer: Sample %d:%d loaded" % \
                     (int(basket_index), int(sample_index)))
            if self._focusing_mode == "P13mode":
                self.diffractometer_hwobj.set_phase(\
                    self.diffractometer_hwobj.PHASE_CENTRING, 60.0)
                #self.diffractometer_hwobj.close_kappa()
        else:
            log.error("Sample changer: Failed to load sample %d:%d" % \
                      (int(basket_index), int(sample_index)))
            raise Exception ("Sample not loaded!")

    def load(self, sample=None, wait=True):
        """ Load a sample"""
        #self._setState(SampleChangerState.Ready)
        if self._focusing_mode == "P13mode":
            SampleChanger.load(self, sample, wait)
        else:
            sample = self._resolveComponent(sample)
            self.assertNotCharging()
            return self._executeTask(SampleChangerState.Loading, wait, self._doLoad, sample)

    def _doUnload(self, sample_slot=None):
        """Unloads a sample from the diffractometer"""
        log = logging.getLogger("GUI")
 
        self._setState(SampleChangerState.Ready)
        if self._focusing_mode not in ("Collimated", "Double", "P13mode"):
            error_msg = "Focusing mode is undefined. Sample loading is disabled"
            log.error(error_msg)
            return

        if self._in_error_state:
            log.error("Sample changer is in error state. " + \
                      "All commands are disabled." + \
                      "Fix the issue and reset sample changer in MXCuBE")
            return


        if self._focusing_mode == "P13mode": 
            sample_index = self._mounted_sample
            basket_index = self._mounted_puck
        else:
            sample_index = self._mounted_sample + 1
            basket_index = self._mounted_puck + 1

        msg = "Sample changer: Unloading sample %d:%d" %(\
               basket_index, sample_index)
        log.warning(msg + ". Please wait...")
        self.emit("progressInit", (msg, 100, False))

        if self.diffractometer_hwobj.get_current_phase() != \
           self.diffractometer_hwobj.PHASE_TRANSFER:
            self.diffractometer_hwobj.set_phase(self.diffractometer_hwobj.PHASE_TRANSFER, 60)
            if self.diffractometer_hwobj.get_current_phase() != \
               self.diffractometer_hwobj.PHASE_TRANSFER:
                log.error("Diffractometer is not in the transfer phase. " +\
                          "Sample will not be mounted")
                raise Exception("Unable to set Transfer phase")

        #self.detector_hwobj.close_cover()
        if self._focusing_mode == "P13mode":  
            if self.detector_hwobj.get_distance() < 399.0:
                log.info("Sample changer: Moving detector to save position ...")
                self._veto = 1
                self.detector_hwobj.set_distance(400, timeout=45)
                time.sleep(1)
                self.waitVeto(20.0)
                log.info("Sample changer: Detector moved to save position")
        else:
            self.detector_hwobj.close_cover()

        start_time = datetime.now()

        if self._focusing_mode == "P13mode":
            self._executeServerTask(self.cmd_unmount_sample,
                                    sample_index,
                                    basket_index)
        else:
            if self._focusing_mode == "Collimated":
                self._executeServerTask(self.cmd_unmount_sample,
                                        sample_index,
                                        basket_index,
                                        1)
            elif self._focusing_mode == "Double":
                self._executeServerTask(self.cmd_unmount_sample,
                                        sample_index,
                                        basket_index,
                                        3)

        self.emit("progressStop", ())
        end_time = datetime.now()
        time_delta = "%d" % (end_time - start_time).total_seconds()

        try:
           if os.getenv("SUDO_USER"):
               user_name = os.getenv("SUDO_USER")
           else:
               user_name = os.getenv("USER")
           log_file = open(self.log_filename, "a")
           log_msg = "%s,%s,%s,%s,%s,%d,%d" % (
                      start_time.strftime("%Y-%m-%d %H:%M:%S"),
                      end_time.strftime("%Y-%m-%d %H:%M:%S"),
                      time_delta,
                      user_name,
                      "unload",
                      self._mounted_puck,
                      self._mounted_sample)
           if self.is_sample_on_gonio():
               log_msg += ",Error\n"
           else:
               log_msg += ",Success\n"
           log_file.write(log_msg)
           log_file.close()
        except:
           pass

        if self.is_sample_on_gonio():
            log.error("Sample changer: Failed to unload sample %d:%d" % \
                     (basket_index, sample_index))
            raise Exception ("Sample not unloaded!")
        else:
            log.info("Sample changer: Sample %d:%d unloaded" % \
                      (basket_index, sample_index))

    def clearBasketInfo(self, basket):
        """Clears information about basket"""
        #TODO
        return

    def _doChangeMode(self, mode):
        """Changes the mode of sample changer"""
        return

    def _doAbort(self):
        """Aborts the sample changer"""
        return

    def _doReset(self):
        """Clean all sample info, move sample to his position and move puck 
           from center to base"""
        self._setState(SampleChangerState.Ready)
        self._initSCContents()
        self._in_error_state = False

    def _executeServerTask(self, method, *args):
        """Executes called cmd, waits until sample changer is ready and
           updates loaded sample info
        """
        #self.waitReady(60.0)
        self._state_string = "Bsy"
        self._progress = 5

        arg_arr = []
        for arg in args:
            arg_arr.append(arg)

        logging.getLogger("HWR").debug("Sample changer: Sending cmd with arguments: %s..." %  str(arg_arr))
        
        method(arg_arr)
        logging.getLogger("HWR").debug("Sample changer: Waiting ready...")
        self._action_started = True
        gevent.sleep(30)
        if method == self.cmd_mount_sample:
            self.wait_sample_on_gonio(120.0)
        else:
            self.waitReady(120.0)
        logging.getLogger("HWR").debug("Sample changer: Ready")
        logging.getLogger("HWR").debug("Sample changer: Waiting veto...")
        self.waitVeto(20.0)
        logging.getLogger("HWR").debug("Sample changer: Veto ready")
        #if self._isDeviceBusy():
        #    raise Exception("Action finished to early. Sample changer is not ready!!!")
        self.sample_is_loaded_changed(self.chan_sample_is_loaded.getValue())
        self._updateState()
        self._updateLoadedSample()
        self._setState(SampleChangerState.Ready)
        self._action_started = False

    def _updateState(self):
        state = self._readState()
        if (state == SampleChangerState.Moving and 
            self._isDeviceBusy(self.getState())):
            return
        self._setState(state)
       
    def _readState(self):
        """Converts state string to defined state"""
        state_converter = {"ALARM": SampleChangerState.Alarm,
                           "Err": SampleChangerState.Fault,
                           "Idl": SampleChangerState.Ready,
                           "Bsy": SampleChangerState.Moving }
        return state_converter.get(self._state_string, SampleChangerState.Unknown)
                        
    def _isDeviceBusy(self, state=None):
        """Checks whether Sample changer is busy"""
        if state is None:
            state = self._readState()
        if self._progress >= 100 and state in (SampleChangerState.Ready, 
                                               SampleChangerState.Loaded,
                                               SampleChangerState.Alarm, 
                                               SampleChangerState.Disabled, 
                                               SampleChangerState.Fault, 
                                               SampleChangerState.StandBy):
            return False
        else:
            return True

    def _isDeviceReady(self):
        """Checks whether Sample changer is ready"""
        state = self._readState()
        return state in (SampleChangerState.Ready, SampleChangerState.Charging)              

    def waitReady(self, timeout=None):
        """Waits until the samle changer is ready"""
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while self._isDeviceBusy():
                gevent.sleep(0.05)

    def waitVeto(self, timeout=20):
        with gevent.Timeout(timeout, Exception("Timeout waiting for veto")):
            while self._veto == 1:
                self.veto_changed(self.chan_veto.getValue)
                gevent.sleep(0.1)
            
    def _updateSelection(self):    
        """Updates selected basked and sample"""

        basket = None
        sample = None
        try:
          basket_no = self._selected_basket
          if basket_no is not None and basket_no>0 and \
             basket_no <= self._num_basket:
              basket = self.getComponentByAddress(\
                 Basket.getBasketAddress(basket_no))
              sample_no = self._selected_sample
              if sample_no is not None and sample_no>0 and \
                 sample_no <= Basket.NO_OF_SAMPLES_PER_PUCK:
                  sample = self.getComponentByAddress(\
                      Pin.getSampleAddress(basket_no, sample_no))            
        except:
          pass
        self._setSelectedComponent(basket)
        self._setSelectedSample(sample)

    def _updateLoadedSample(self):
        """
        Updates loaded sample
        """

        if self._sample_detected and \
           self._mounted_sample > -1 and \
           self._mounted_puck > -1 and \
           self._centre_puck:
            if self._focusing_mode == "P13mode":
                new_sample = self.getComponentByAddress(\
                         Pin.getSampleAddress(self._mounted_puck, 
                                              self._mounted_sample))
            else:
                new_sample = self.getComponentByAddress(\
                         Pin.getSampleAddress(self._mounted_puck + 1,
                                              self._mounted_sample + 1))   
        else:
            new_sample = None

        if self.getLoadedSample() != new_sample:
            old_sample = self.getLoadedSample()
            if old_sample is not None:
                # there was a sample on the gonio
                loaded = False
                has_been_loaded = True
                old_sample._setLoaded(loaded, has_been_loaded)
            if new_sample is not None:
                self._updateSampleBarcode(new_sample)
                loaded = True
                has_been_loaded = True
                new_sample._setLoaded(loaded, has_been_loaded)


    def _updateSampleBarcode(self, sample):
        """
        Updates the barcode of >sample< in the local database 
        after scanning with the barcode reader.
        """
        datamatrix = "NotAvailable"
        scanned = (len(datamatrix) != 0)
        if not scanned:    
            datamatrix = '----------'   
        sample._setInfo(sample.isPresent(), datamatrix, scanned)

    def _initSCContents(self):
        """
        Initializes the sample changer content with default values.
        """
        basket_list= [('', 4)] * self._num_basket
        for basket_index in range(self._num_basket):            
            basket=self.getComponents()[basket_index]
            datamatrix = None
            present = scanned = True
            basket._setInfo(present, datamatrix, scanned)

        # create temporary list with default sample information and indices
        sample_list=[]
        for basket_index in range(self._num_basket):            
            for sample_index in range(10):
                sample_list.append(("", basket_index + 1, sample_index + 1,
                                    1, Pin.STD_HOLDERLENGTH)) 
        # write the default sample information into permanent Pin objects 
        for spl in sample_list:
            sample = self.getComponentByAddress(\
                Pin.getSampleAddress(spl[1], spl[2]))
            datamatrix = None
            present = scanned = loaded = has_been_loaded = False
            sample._setInfo(present, datamatrix, scanned)
            sample._setLoaded(loaded, has_been_loaded)
            sample._setHolderLength(spl[4])    

    def _updateSCContents(self):
        """
        Updates sample changer content
        """
        for basket_index in range(self._num_basket):            
            basket=self.getComponents()[basket_index]
 
            if self._focusing_mode == "P13mode":
                bsk_index = basket_index + 1
            else:
                bsk_index = basket_index

            if (int(self._puck_switches) & pow(2, basket_index) > 0) or \
               (self._mounted_puck == bsk_index) and self._centre_puck:
            #f puck_switches & (1 << basket_index):
                # basket was mounted
                present = True
                scanned = False
                datamatrix = None
            else:
                # basket was removed
                present = False
                scanned = False
                datamatrix = None

            basket._setInfo(present, datamatrix, scanned)
            # set the information for all dependent samples
            """
            for sample_index in range(10):
                sample = self.getComponentByAddress(Pin.getSampleAddress(\
                    (basket_index + 1), (sample_index + 1)))
                present = sample.getContainer().isPresent()
                if present:
                    datamatrix = '%d:%d - Not defined' % \
                       (bsk_index, sample_index)
                else:
                    datamatrix = None
                datamatrix = None
                scanned = False
                sample._setInfo(present, datamatrix, scanned)
                # forget about any loaded state in newly mounted or removed basket)
                loaded = has_been_loaded = False
                sample._setLoaded(loaded, has_been_loaded)
            """

        self._triggerSelectionChangedEvent()

    def status_list_changed(self, status_string):
        tmp_string = status_string.replace(" ", "")
        tmp_string1 = tmp_string.replace("On\r", "On")
        status_string = tmp_string1.replace("\rSys", ";Sys")
        self._status_list = status_string.split(';')

        for status in self._status_list:
            property_status_list = status.split(':')
            if len(property_status_list) < 2:
                continue
         
            prop_name = property_status_list[0]
            prop_value = property_status_list[1]

            if prop_name == "Rob":
                if self._state_string != prop_value and \
                   prop_value in ("Idl", "Bsy", "Err") and self._action_started:
                    self._state_string = prop_value
                    logging.getLogger("HWR").debug("Sample changer: status changed: %s" % \
                                                   self._state_string)
                    self._updateState()
            elif prop_name == "Prgs":
                try:
                   if int(prop_value) != self._progress and self._action_started:
                       self._progress = int(prop_value)
                       self.emit("progressStep", self._progress)
                       self._info_dict["progress"] = self._progress
                except:
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
                    self._updateLoadedSample()
            elif prop_name == "Lid":
                self._info_dict["lid_opened"] = prop_value == "Opn"
            elif prop_name == "Err":
                logging.getLogger("GUI").error("Sample changer: Error (%s)" % \
                                               prop_value)
                logging.getLogger("GUI").error("Details: ")
               
                for status in self._status_list:
                    property_status_list = status.split(':')
                    if len(property_status_list) < 2:
                        continue

                    prop_name = property_status_list[0]
                    prop_value = property_status_list[1]
                    
                    if prop_name in STATUS_STR_DESC:  
                        logging.getLogger("GUI").error(\
                            " - %s: %s " % \
                            (STATUS_STR_DESC[prop_name], prop_value))

        self.emit("statusListChanged", self._status_list)
        self.emit("infoDictChanged", self._info_dict) 

    
    def update_values(self):
        self.emit("statusListChanged", self._status_list)
        self.emit("infoDictChanged", self._info_dict)
        self._triggerInfoChangedEvent()
        self._triggerSelectionChangedEvent()
