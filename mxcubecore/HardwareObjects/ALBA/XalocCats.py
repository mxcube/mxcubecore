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

"""
[Name] XalocCats

[Description]
HwObj used to control the CATS sample changer via Tango.

[Signals]
- powerStateChanged
- runningStateChanged

Comments:
In case of failed put push button, CatsMaint calls the reset command in the DS
In case of failed get push button, CatsMaint calls the recoverFailure command in the DS
"""

#from __future__ import print_function

import logging
import time
import PyTango
import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.Cats90 import Cats90, SampleChangerState#, TOOL_SPINE

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"

TIMEOUT = 3
DOUBLE_GRIPPER_DRY_WAIT_TIME = 80 # time the double gripper takes in going from home to midway soak during a dry

TOOL_FLANGE, TOOL_UNIPUCK, TOOL_SPINE, TOOL_PLATE, \
    TOOL_LASER, TOOL_DOUBLE_GRIPPER = (0,1,2,3,4,5)
BASKET_UNKNOWN, BASKET_SPINE, BASKET_UNIPUCK = (0, 1, 2)
#
# Number of samples per puck type
#
SAMPLES_SPINE = 10
SAMPLES_UNIPUCK = 16

class XalocCats(Cats90):
    """
    Main class used @ ALBA to integrate the CATS-IRELEC sample changer.
    """

    def __init__(self, *args):
        Cats90.__init__(self, *args)
        self.logger = logging.getLogger("HWR.XalocCats")
        self.detdist_saved = None

        self.shifts_channel = None
        self.diff_phase_channel = None
        self.diff_state_channel = None
        self.super_phase_channel = None
        self.super_state_channel = None
        self.detdist_position_channel = None
        self.omega_position_channel = None
        self.kappa_position_channel = None
        self._chnisDetDistSafe = None
        
        self._chnPathSafe = None
        self._chnCollisionSensorOK = None
        self._chnIsCatsIdle = None
        self._chnIsCatsHome = None
        self._chnIsCatsRI1 = None
        self._chnIsCatsRI2 = None
        self._chnNBSoakings = None
        self._chnLidSampleOnTool = None
        self._chnNumSampleOnTool = None
        
        self.go_transfer_cmd = None
        self.diff_go_sampleview_cmd = None
        self.super_go_sampleview_cmd = None
        self.super_abort_cmd = None

        self._cmdLoadHT = None
        self._cmdChainedLoadHT = None
        self._cmdUnloadHT = None
        self._cmdClearMemory = None
        self._cmdSetTool = None

        self.auto_prepare_diff = None
        self.mount_and_pick = None
        self.sample_can_be_centered = None
        
        self.logger.debug("unipuck_tool property = %s" % self.get_property("unipuck_tool") )

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        Cats90.init(self)
        # TODO: Migrate to taurus channels instead of tango channels
        self.shifts_channel = self.get_channel_object("shifts")
        self.diff_phase_channel = self.get_channel_object("diff_phase")
        self.diff_state_channel = self.get_channel_object("diff_state")
        self.super_phase_channel = self.get_channel_object("super_phase")
        self.super_state_channel = self.get_channel_object("super_state")
        self.detdist_position_channel = self.get_channel_object("detdist_position")
        self.omega_position_channel = self.get_channel_object("omega_position") # position of the omega axis
        self.kappa_position_channel = self.get_channel_object("kappa_position") # position of the kappa axis
        self._chnisDetDistSafe = self.get_channel_object("DetDistanceSafe")

        #self._chnPathSafe = self.get_channel_object("_chnPathSafe")
        self._chnCollisionSensorOK = self.get_channel_object("_chnCollisionSensorOK")
        self._chnIsCatsIdle = self.get_channel_object( "_chnIsCatsIdle" )
        self._chnIsCatsHome = self.get_channel_object( "_chnIsCatsHome" )
        self._chnIsCatsRI1 = self.get_channel_object( "_chnIsCatsRI1" )
        self._chnIsCatsRI2 = self.get_channel_object( "_chnIsCatsRI2" )
        self._chnNBSoakings = self.get_channel_object( "_chnNBSoakings" )
        self._chnLidSampleOnTool = self.get_channel_object( "_chnLidSampleOnTool" )
        self._chnNumSampleOnTool = self.get_channel_object( "_chnNumSampleOnTool" )
        
        self.go_transfer_cmd = self.get_command_object("go_transfer")
        self.diff_go_sampleview_cmd = self.get_command_object("diff_go_sampleview")
        self.super_go_sampleview_cmd = self.get_command_object("super_go_sampleview")
        self.super_abort_cmd = self.get_command_object("super_abort")

        self._cmdLoadHT = self.get_command_object("_cmdLoadHT")
        self._cmdChainedLoadHT = self.get_command_object("_cmdChainedLoadHT")
        self._cmdUnloadHT = self.get_command_object("_cmdUnloadHT")
        self._cmdChainedLoadPick= self.get_command_object("_cmdChainedLoadPick")

        self._cmdClearMemory = self.get_command_object("_cmdClearMemory")
        self._cmdSetTool = self.get_command_object("_cmdSetTool")
        self._cmdSetTool2 = self.get_command_object("_cmdSetTool2")

        self.auto_prepare_diff = self.get_property("auto_prepare_diff")
        self.mount_and_pick = False 
        self.sample_can_be_centered = True

        if self._chnPathRunning is not None:
            self._chnPathRunning.connect_signal("update", self._update_running_state)

        if self._chnPowered is not None:
            self._chnPowered.connect_signal("update", self._update_powered_state)

        ret,msg = self._check_coherence()
        if not ret: 
            logging.getLogger('user_level_log').warning( msg )
            
        # quick fix to get Cats to accept the unipuck_tool
        #    the property is set in Cats90, but the property unipuck_tool is somehow not read properly
        self.set_unipuck_tool(5)


    #def cats_state_changed(self, value):

        #logging.getLogger("HWR").debug("Cats90 cats_state_changed chnState value is %s, value == PyTango.DevState.ON %s, type %s" % \
                                         #(str(value) , value == PyTango.DevState.ON, type(value) )
                                      #)
        #timeout = 1
        #if self.cats_state != value:
            ## hack for transient states
    
            #t0 = time.time()
            #while value in [PyTango.DevState.ALARM, PyTango.DevState.ON]:
                #time.sleep(0.1)
                #self.logger.warning(
                        #"SAMPLE CHANGER could be in transient state (state is %s). trying again" 
                                    #% self.cats_state 
                    #)
                #value = self._chnState.get_value()
                #if (time.time() - t0) > timeout:
                    ##self.logger.warning("SAMPLE CHANGER state change timed out %s)" % self.cats_state )
                    ##logging.getLogger('user_level_log').error("SAMPLE CHANGER state is not ready")
                    #break

        #logging.getLogger("HWR").debug("Cats90. cats_state_changed, updating power state to %s " % value)

        #self.cats_state = value
        #self._update_state()

    def is_ready(self):
        """
        Returns a boolean value indicating is the sample changer is ready for operation.

        @return: boolean
        """
        return self.state == SampleChangerState.Ready or \
            self.state == SampleChangerState.Loaded or \
            self.state == SampleChangerState.Charging or \
            self.state == SampleChangerState.StandBy or \
            self.state == SampleChangerState.Disabled

    #TODO: rename this method, it is the supervisor that is sent to transfer
    def diff_send_transfer(self, timeout = 36):
        """
        Checks if beamline diff is in TRANSFER phase (i.e. sample changer in
        TRANSFER phase too). If is not the case, It sends the supervisor to TRANSFER
        phase. Then waits for the minimal conditions of the beamline to start the transfer

        @return: boolean
        """
        if self.read_super_phase().upper() == "TRANSFER":
            #self.logger.error("Supervisor is already in transfer phase")
            return True

        # First wait till the diff is ready to accept a go_transfer_cmd
        if not self._wait_diff_on(timeout): return False
        time.sleep(0.1)
 
        self.go_transfer_cmd()

        # To improve the speed of sample mounting, the wait for phase done was removed.
        # Rationale: the time it takes the diff to go to transfer phase is about 7-9 seconds. 
        # The limiting factor is actually the detector safe position (-70), which takes 19.1 seconds to reach from the minimal distance
        # The fastest mouting time with pick is in the 7-9 secs range, so mounting without pick 
        #    will take much longer before arriving at the diff
        # NOTE For pick mounting, a time sleep may be required.
        # Another potentially limiting step is omega movement. At an max omega of 2160, it takes 36 seconds to reach 0
        #  omega is somehow involved in calculating the  diff mounting position, so omega should be at zero before continuing
        #  TODO check if we can improve the involvement of omega in the calculations.
        # kappa should also be considered. Max kappa angle is 255, speed 17. Thus, at most kappa to zero takes 15 secs
        #ret = self._wait_diff_phase_done('TRANSFER')
        ret1 = self._wait_kappa_zero() 
        ret2 = self._wait_omega_zero() 
        ret3 = self._wait_det_safe()
        return ( ret1 and ret2 and ret3 )

    def _wait_diff_on(self, timeout = 36):
        t0 = time.time()
        while True:
            state = self.diff_state_channel.get_value()
            if state == PyTango.DevState.ON:
                break

            if (time.time() - t0) > timeout:
                self.logger.error("Diff timeout waiting for ON state. Returning")
                return False

        return True

    # TODO: Move to XalocSupervisor 
    def _wait_super_ready(self):
        while True:
            state = str(self.super_state_channel.get_value())
            if state == "ON":
                self.logger.debug("Supervisor is in ON state. Returning")
                break
            time.sleep(0.2)

    def _wait_cats_idle(self):
        while True:
            if self._chnIsCatsIdle.get_value():
                self.logger.debug("_chnIsCatsIdle %s, type %s" % ( str(self._chnIsCatsIdle.get_value()), type(self._chnIsCatsIdle.get_value()) ) )
                self.logger.debug("CATS is idle. Returning")
                break
            time.sleep(0.2)

    def _wait_cats_home(self, timeout):
        t0 = time.time()
        while True:
            if self._chnIsCatsHome.get_value():
                self.logger.debug("CATS is home. Returning")
                break
            time.sleep(0.2)
            if time.time() - t0 > timeout: return False
        
        return True

    def _wait_det_safe(self, timeout=30):
        t0 = time.time()
        while True:
            if self._chnisDetDistSafe.get_value():
                self.logger.debug("Detector is in a safe position. Returning")
                break
            time.sleep(0.2)
            if time.time() - t0 > timeout: return False
        
        return True
        
    def _wait_kappa_zero(self, timeout = 15.):
        #self.logger.debug("_wait_kappa_zero timeout %.2f kappa pos %.4f" % (timeout, self.kappa_position_channel.get_value() ) ) 
        t0 = time.time()
        while True:
            if abs( self.kappa_position_channel.get_value() ) < 0.1:# the error in position is very high (0.07 um) when starting from 2160
                self.logger.debug("kappa is zero. Returning")
                break
            time.sleep(0.5)
            if time.time() - t0 > timeout: return False
        
        return True

    def _wait_omega_zero(self, timeout = 37.):
        #self.logger.debug("_wait_omega_zero timeout %.2f omega pos %.4f" % (timeout, self.omega_position_channel.get_value() ) ) 
        t0 = time.time()
        while True:
            if abs( self.omega_position_channel.get_value() ) < 0.1:# the error in position is very high (0.07 um) when starting from 2160
                self.logger.debug("Omega is zero. Returning")
                break
            time.sleep(0.5)
            if time.time() - t0 > timeout: return False
        
        return True

    def _wait_super_moving(self):
        allokret = True # No problems
        while allokret:
            state = str(self.super_state_channel.get_value())
            if not self._chnCollisionSensorOK.get_value(): 
                self._update_state()
                raise Exception ("The robot had a collision, call your LC or floor coordinator")
            elif state == "MOVING":
                self.logger.debug("Supervisor is in MOVING state. Returning")
                return allokret
            time.sleep(0.1)

        return allokret

    def _wait_diff_phase_done(self, final_phase, timeout = 20 ):
        """
        Method to wait a phase change. When supervisor reaches the final phase, the
        method returns True.

        @final_phase: target phase
        @return: boolean
        """
       
        t0 = time.time()
        while self.read_diff_phase().upper() != final_phase:
            state = self.diff_state_channel.get_value()
            phase = self.read_diff_phase().upper()
            if not state in [ PyTango.DevState.ON , PyTango.DevState.MOVING ]:
                self.logger.error("Diff is in a funny state %s" % str(state))
                return False

            self.logger.debug("Diff waiting to finish phase change")
            time.sleep(0.2)
            if time.time() - t0 > timeout: break

        if self.read_diff_phase().upper() != final_phase:
            self.logger.error("Diff is not yet in %s phase. Aborting load" %
                              final_phase)
            return False
        else:
            self.logger.info(
                "Diff is in %s phase. Beamline ready for the next step..." %
                final_phase)
            return True

    def _wait_phase_done(self, final_phase, timeout = 20 ):
        """
        Method to wait a phase change. When supervisor reaches the final phase, the
        method returns True.

        @final_phase: target phase
        @return: boolean
        """
       
        t0 = time.time()
        while self.read_super_phase().upper() != final_phase:
            state = str(self.super_state_channel.get_value())
            phase = self.read_super_phase().upper()
            if not str(state) in [ "MOVING", "ON" ]:
                self.logger.error("Supervisor is in a funny state %s" % str(state))
                return False

            self.logger.debug("Supervisor waiting to finish phase change")
            time.sleep(0.2)

        t0 = time.time()
        timeout = 5
        while self.read_super_phase().upper() != final_phase or timeout > time.time() - t0:
            logging.getLogger("HWR").warning(
                "Phase changed done. Waiting phase change....")
            time.sleep(0.2)

        if self.read_super_phase().upper() != final_phase:
            self.logger.error("Supervisor is not yet in %s phase. Aborting load" %
                              final_phase)
            return False
        else:
            self.logger.info(
                "Supervisor is in %s phase. Beamline ready to start sample loading..." %
                final_phase)
            return True

    def save_detdist_position(self):
        self.detdist_saved = self.detdist_position_channel.get_value()
        self.logger.error("Saving current det.distance (%s)" % self.detdist_saved)

    def restore_detdist_position(self):
        if abs(self.detdist_saved - self.detdist_position_channel.get_value()) >= 0.1:
            self.logger.error(
                "Restoring det.distance to %s" % self.detdist_saved)
            self.detdist_position_channel.set_value(self.detdist_saved)

    def read_super_phase(self):
        """
        Returns supervisor phase (CurrentPhase attribute from Beamline Supervisor
        TangoDS)

        @return: str
        """
        return self.super_phase_channel.get_value()

    def read_diff_phase(self):
        """
        Returns supervisor phase (CurrentPhase attribute from Beamline Supervisor
        TangoDS)

        @return: str
        """
        return self.diff_phase_channel.get_value()

    def load(self, sample=None, wait=False, wash=False):
        """
        Loads a sample. Overides to include ht basket.

        @sample: sample to load.
        @wait:
        @wash: wash dring the load opearation.
        @return:
        """

        self.sample_can_be_centered = True

        self.logger.debug(
            "Loading sample %s / type(%s)" %
            (sample, type(sample)))

        ok, msg = self._check_incoherent_sample_info()
        if not ok:
            self.sample_can_be_centered = False
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
                    "The sample %s is already loaded" % sample.get_address())
            else:
                # Unload first / do a chained load
                pass

        # This runs the AbstractSampleChanger method!
        ok = self._execute_task(SampleChangerState.Loading,
                                 wait, self._do_load, sample, None, use_ht)
        #if not ok: self.sample_can_be_centered = False
        
        if ok: HWR.beamline.diffractometer.sample_has_been_centred = False
        
        return ok

    def unload(self, sample_slot=None, shifts=None, wait=False):
        """
        Unload the sample. If sample_slot=None, unloads to the same slot the sample was
        loaded from.

        @sample_slot:
        @wait:
        @return:
        """
        
        self.sample_can_be_centered = True

        sample_slot = self._resolve_component(sample_slot)

        self.assert_not_charging()

        # In case we have manually mounted we can command an unmount
        if not self.has_loaded_sample():
            self.sample_can_be_centered = False
            raise Exception("No sample is loaded")

        # This runs the AbstractSampleChanger method!
        ok = self._execute_task(SampleChangerState.Unloading,
                                 wait, self._do_unload, sample_slot)
        if not ok: self.sample_can_be_centered = False

        return ok

    def _update_running_state(self, value):
        """
        Emits signal with new Running State

        @value: New running state
        """
        self.emit('runningStateChanged', (value, ))

    def _update_powered_state(self, value):
        """
        Emits signal with new Powered State

        @value: New powered state
        """
        self.emit('powerStateChanged', (value, ))

    def _do_load(self, sample=None, shifts=None, use_ht=False, waitsafe=True):
        """
        Loads a sample on the diffractometer. Performs a simple put operation if the
        diffractometer is empty, and a sample exchange (unmount of old + mount of new
        sample) if a sample is already mounted on the diffractometer.
        Overides Cats90 method.
        
        @sample: sample to load.
        @shifts: mounting point offsets.
        @use_ht: mount a sample from hot tool.
        """
        if not self._chnPowered.get_value():
            # TODO: implement a wait with timeout method.
            self.logger.debug("CATS power is OFF. Trying to switch the power ON...")
            self._cmdPowerOn()  # try switching power on
            time.sleep(2) # gevent.sleep(2)??

        current_tool = self.get_current_tool()

        self.save_detdist_position()
        ret = self.diff_send_transfer()

        if ret is False:
            self.logger.error(
                "Supervisor cmd transfer phase returned an error.")
            self._update_state()
            raise Exception(
                "Supervisor cannot get to transfer phase. Aborting sample changer operation. Ask LC or floor coordinator to check the supervisor and diff device servers")

        if not self._chnPowered.get_value():
            raise Exception(
                "CATS power is not enabled. Please switch on arm power before "
                "transferring samples.")

        # obtain mounting offsets from diffr
        shifts = self._get_shifts()

        if shifts is None:
            xshift, yshift, zshift = ["0", "0", "0"]
        else:
            xshift, yshift, zshift = map(str, shifts)

        # get sample selection
        selected = self.get_selected_sample()

        self.logger.debug("Selected sample is %s (prev %s)" %
                          (str(selected), str(sample)))

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
        if not use_ht and self.has_loaded_sample() and selected == self.get_loaded_sample(): # sample on diff is the one loaded
            self._update_state()
            raise Exception("The sample " +
                            str(self.get_loaded_sample().get_address()) +
                            " is already loaded")

        if not self.has_loaded_sample() and self.cats_sample_on_diffr() == 1:
            self.logger.warning(
                "Sample on diffractometer, loading aborted!")
            self._update_state()
            raise Exception("The sample " +
                            str(self.get_loaded_sample().get_address()) +
                            " is already loaded")

        if self.cats_sample_on_diffr() == -1 and self.has_loaded_sample(): # no sample on diff, but cats has sample info
            self._update_state()
            raise Exception(
                "Conflicting info between diffractometer and on-magnet detection."
                "Consider 'Clear'")

        # end some cancel cases

        # if load_ht
        loaded_ht = self.is_loaded_ht()

        #
        # Loading HT sample
        #
        if use_ht:  # loading HT sample

            if loaded_ht == -1:  # has loaded but it is not HT
                # first unmount (non HT)
                self.logger.error("Mixing load/unload dewar vs HT, NOT IMPLEMENTED YET. Unload sample first")
                return

            tool = self.tool_for_basket(100)  # basketno)

            if tool != current_tool:
                self.logger.warning("Changing tool from %s to %s" %
                                    (current_tool, tool))
                changing_tool = True
            else:
                changing_tool = False

            argin = ["2", str(sample), "0", "0", xshift, yshift, zshift]
            self.logger.warning("Loading HT sample, %s" % str(argin))
            if loaded_ht == 1:  # has ht loaded
                cmd_ok = self._execute_server_task(self._cmdChainedLoadHT,
                                                 argin, waitsafe=True)
            else:
                cmd_ok = self._execute_server_task(self._cmdLoadHT, argin, waitsafe=False)

        #
        # Loading non HT sample
        #
        else:
            if loaded_ht == 1:  # has an HT sample mounted
                # first unmount HT
                self.logger.warning(
                    "Mixing load/unload dewar vs HT, NOT IMPLEMENTED YET, unload sample first")
                return

            basketno = selected.get_basket_no()
            sampleno = selected.get_vial_no()

            lid, sample = self.basketsample_to_lidsample(basketno, sampleno)
            tool = self.tool_for_basket(basketno)
            stype = self.get_cassette_type(basketno)

            if tool != current_tool:
                self.logger.warning("Changing tool from %s to %s" %
                                    (current_tool, tool))
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
                zshift]

            if tool == 2:
                read_barcode = self.read_datamatrix and \
                               self._cmdChainedLoadBarcode is not None
            else:
                if self.read_datamatrix:
                    self.logger.error("Reading barcode only possible with spine pucks, no barcode will be read")
                read_barcode = False

            if loaded_ht == -1:  # has a loaded but it is not an HT

                if changing_tool:
                    raise Exception(
                        "This operation requires a tool change. You should unload"
                        "sample first")

                chained_load_command = self._cmdChainedLoad
                if not self.mount_and_pick and not read_barcode:
                    self.logger.warning("Chained load sample, sending to cats: %s"
                            % argin)
                if read_barcode: 
                    self.logger.warning(
                        "Chained load sample (barcode), sending to cats: %s" % argin)
                    chained_load_command = self._cmdChainedLoadBarcode                    
                if self.mount_and_pick:
                    self.logger.warning("Chained load sample with pick function, sending to cats: %s"
                        % argin)
                    chained_load_command = self._cmdChainedLoadPick                    

                cmd_ok = self._execute_server_task(
                        chained_load_command, argin, waitsafe=True)
            elif loaded_ht == 0: # no loaded sample
                load_command = self._cmdLoad
                waitsafe = True
                if not self.mount_and_pick and not read_barcode:
                    self.logger.warning("Load sample, sending to cats:  %s" % argin)
                if read_barcode:
                    self.logger.warning("Load sample (barcode), sending to cats: %s"
                        % argin)
                    load_command = self._cmdLoadBarcode
                if self.mount_and_pick:
                    load_command = self._cmdLoad
                    waitsafe = False # with waitsafe false, the execute_task waits still the path_running is false
                cmd_ok = self._execute_server_task(
                    load_command, argin, waitsafe=waitsafe)
                if self.mount_and_pick:
                    self.user_level_log.warning("Load a sample first, then use Mount Pick, mount cancelled")
                    #argin = [
                        #str(tool),
                        #str(lid),
                        #str(sample),
                        #str(stype),
                        #"0",
                        #xshift,
                        #yshift,
                        #zshift]
                    #cmd_ok = self._execute_server_task(
                        #self._cmdPick, argin, waitsafe=True)

        self.mount_and_pick = False # Dont use pick for the next mounting cycle unless requested

        # At this point, due to the waitsafe, we can be sure that the robot has left RI2 and will not return
        # TODO: check if the diff should be prepared or not
        collision_occurred = False
        if not self._chnCollisionSensorOK.get_value(): 
            collision_occurred = True

        # A time sleep is needed to get updates on the sample status etc.
        time.sleep(3)

        if not cmd_ok:
            self.logger.info("Load Command failed on device server")
            return False
        elif self.auto_prepare_diff and not changing_tool and not collision_occurred:
            self.logger.info(
                "AUTO_PREPARE_DIFF (On) sample changer is in safe state... "
                "preparing diff now")
            allok, msg = self._check_coherence()
            if allok:
                logging.getLogger('user_level_log').info( 'Sample successfully loaded' )
                self.logger.info("Restoring detector distance")
                self.restore_detdist_position()
                return True
            else:
                # Now recover failed put for double gripper
                # : double should be in soak, single should be ??
                #isPathRunning amd cats_idle dont work for tool 5, becuase cats stays in running state after failed put. 
                #_wait_cats_home followed by immediate abort fails because double tool passed through home on the way to soak
                # time.sleep(5) fails because of a possible dry for double 
                # When doing a dry, CATS passes through home, so a double wait_cats_home is necessary, with a time.sleep of a couple of seconds in between so CATS starts drying
                # An alternative is to abort at arriving home, clear memeory and move to soak
                if not self._check_incoherent_sample_info()[0] : 
                    msg = "Your sample was NOT loaded! Click OK to recover, please make sure your sample is there"
                else:
                    msg = "The CATS device indicates there was a problem in unmounting the sample, click ok to recover from a Fix Fail Get"
                self.emit("taskFailed", str(msg))
                
                logging.getLogger('user_level_log').error( 'There was a problem loading your sample, please wait for the system to recover' )
                self._wait_cats_home(10) # wait for robot to return from diff
                time.sleep( 5 ) # give it time to move, if it goes for a dry, the _chnNBSoakings is set to 0
                #self.logger.info("self._chnNBSoakings  %d " % self._chnNBSoakings.get_value() )
                if self.get_current_tool() == TOOL_DOUBLE_GRIPPER: 
                    if self._chnNBSoakings.get_value() == 0: 
                        self.logger.info("A dry will now be done, waiting %d seconds" % DOUBLE_GRIPPER_DRY_WAIT_TIME)
                        time.sleep( DOUBLE_GRIPPER_DRY_WAIT_TIME ) # long timeout because of possible dry of the double gripper
                    else: 
                        #self.logger.info("no dry, waiting 3 seconds" )
                        time.sleep( 3 ) # allow the gripper time to move on
                if not self._check_incoherent_sample_info()[0] : # this could be replaced by checking return value of _check_coherence, see TODO there
                    # the behaviour of the SPINE gripper is different when failing put or when failing get. For put, it does a dry, for get, it doesnt
                    if self.get_current_tool() == TOOL_SPINE: 
                        time.sleep( 16 )
                    self.recover_cats_from_failed_put()
                else:
                    self._do_recover_failure()
                    msg = "The CATS device indicates there was a problem in unmounting the sample, click ok to recover from a Fix Fail Get"
                self._update_state()
                return False
                #raise Exception( msg )
                
        else:
            self.logger.info(
                "AUTO_PREPARE_DIFF (Off) sample loading done / or changing tool (%s)" %
                changing_tool)

        # Check again the collision sensor in case the robot collided after being in a safe position
        if not self._chnCollisionSensorOK.get_value() or collision_occurred:
            self._update_state()
            msg = "The robot had a collision, call your LC or floor coordinator"
            self.emit("taskFailed", str(msg))
            raise Exception ( msg )

    def _wait_device_safe(self,timeout=10):
        """
        Waits until the samle changer HO is safe, aka not returning to diff.

        :returns: None
        :rtype: None
        """
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self.path_safe():
                gevent.sleep(0.01)

    def _do_unload(self, sample_slot=None, shifts=None):
        """
        Unloads a sample from the diffractometer.
        Overides Cats90 method.

        @sample_slot:
        @shifts: mounting position
        """
        if not self._chnPowered.get_value():
            try: self._cmdPowerOn()  # try switching power on
            except Exception as e:
                raise Exception(e)

        #TODO: wait for cats poweron

        ret = self.diff_send_transfer()

        if ret is False:
            self.logger.error(
                "Supervisor cmd transfer phase returned an error.")
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
            self.logger.warning("Unload sample, no sample mounted detected")
            return

        loaded_basket, loaded_sample = self.lidsample_to_basketsample(
            loaded_lid, loaded_num)

        tool = self.tool_for_basket(loaded_basket)

        argin = [str(tool), "0", xshift, yshift, zshift]

        self.logger.warning("Unload sample, sending to cats:  %s" %
                            argin)
        if loaded_ht == 1:
            cmd_ret = self._execute_server_task(self._cmdUnloadHT, argin, waitsafe=True)
        else:
            cmd_ret = self._execute_server_task(self._cmdUnload, argin, waitsafe=True)

        # At this point, due to the waitsafe, we can be sure that the robot has left RI2 and will not return
        # A time sleep is needed to get updates on the sample status etc.
        time.sleep(3)


        allok = self._check_coherence()[0]
        if not allok:
                self._wait_super_ready()
                if not self.has_loaded_sample() and self.cats_sample_on_diffr():
                      msg = "The CATS device indicates there was a problem in unmounting the sample, click on Fix Fail Get"
                self._update_state()
                raise Exception( msg )

        return True

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
        
        sampinfobool, sampinfomessage = self._check_incoherent_sample_info()
        unknownsampbool, unknownsampmessage = self._check_unknown_sample_presence()
        msg = sampinfomessage + unknownsampmessage
        return ( sampinfobool and unknownsampbool ), msg

    def _check_unknown_sample_presence(self):
        
        detected = self._chnSampleIsDetected.get_value()
        loaded_lid = self._chnLidLoadedSample.get_value()
        loaded_num = self._chnNumLoadedSample.get_value()
        #self.logger.debug("detected %s, type detected %s, loaded_lid %d, loaded_num %d, loaded_num type %s" % ( str(detected), type(detected), loaded_lid, loaded_num, type(loaded_num)  ) )
        #self.logger.debug("-1 in [loaded_lid, loaded_num] %s, detected %s" % ( -1 in [loaded_lid, loaded_num], detected ) )
        #self.logger.debug("-1 in [loaded_lid, loaded_num] and detected: %s" % ( -1 in [loaded_lid, loaded_num] and detected ) )


        if -1 in [loaded_lid, loaded_num] and detected:
            return False, "Sample detected on Diffract. but there is no info about it"

        return True, ""

    def _check_incoherent_sample_info(self):
        """
          Check for sample info in CATS but no physically mounted sample
           (Fix failed PUT)
          Returns False in case of incoherence, True if all is ok
        """
        #self.logger.debug('self._chnSampleIsDetected %s' % self._chnSampleIsDetected.get_value() )
        detected = self._chnSampleIsDetected.get_value()
        loaded_lid = self._chnLidLoadedSample.get_value()
        loaded_num = self._chnNumLoadedSample.get_value()
        #self.logger.debug("detected %s, loaded_lid %d, loaded_num %d" % ( str(detected), loaded_lid, loaded_num ) )

        if not detected and not ( -1 in [loaded_lid, loaded_num] ):
            return False, "There is info about a sample but it is not detected on the diffract."

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
        self.logger.debug('Shifts of the diffractometer position: %s' % str(shifts) )
        return shifts

    # TODO: fix return type
    def is_ht_sample(self, address):
        """
        Returns is sample address belongs to hot tool basket.

        @address: sample address
        @return: int or boolean
        """
        try: basket, sample = address.split(":") # address is string (when loading from tree)
        except: basket, sample = address # address is tuple (when loading from sample changer tab)

        try:
            if int(basket) >= 100:
                return int(sample)
            else:
                return False
        except Exception as e:
            self.logger.debug("Cannot identify sample in hot tool")
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

    def _do_reset(self):
        """
          Called when user pushes "Fix fail PUT" button
          Overrides the _doReset in CatsMaint, adding checks whether calling this method is justified
        """
        self.recover_cats_from_failed_put()

    def recover_cats_from_failed_put(self):
        """
           Deletes sample info on diff, but should retain info of samples on tools, eg when doing picks
           TODO: tool2 commands are not working, eg SampleNumberInTool2
        """
        self.logger.debug("XalocCats recovering from failed put. Failed put is %s" % str( self._check_incoherent_sample_info() ) )

        if not self._check_incoherent_sample_info()[0]:
            self._cmdAbort()
            savelidsamptool = self._chnLidSampleOnTool.get_value()
            savenumsamptool = self._chnNumSampleOnTool.get_value()
            #savelidsamptool2 = self._chnLidSampleOnTool2() # Not implemented yet
            #savenumsamptool2 = self._chnNumSampleOnTool2() # Not implemented yet
            self._cmdClearMemory()
            if not -1 in [savelidsamptool, savenumsamptool ]:
                basketno, bsampno = self.lidsample_to_basketsample(
                      savelidsamptool,savenumsamptool
                    )
                argin = [ str(savelidsamptool), 
                           str(savenumsamptool), 
                           str( self.get_cassette_type( basketno ) ) 
                        ]
                self.logger.debug("XalocCats recover from failed put. Sending to robot %s" % argin )
                cmdok = self._execute_server_task( self._cmdSetTool, argin )
            #if not -1 in [savelidsamptool2, savenumsamptool2 ]:
            #   basketno, bsampno = self.lidsample_to_basketsample(savelidsamptool2,savenumsamptool2) # Not implemented yet
            #   argin = [ str(savelidsamptool2), str(savenumsamptool2), str(self.get_cassette_type(basketno)) ]
            #   self._execute_server_task( self._cmdSetTool2, argin )
        else: raise Exception("The conditions of the beamline do not fit a failed put situation, "
                                "Fixed failed PUT is not justified. Find another solution.")

    def _do_recover_failure(self):
        """
          Called when user pushes "Fix fail GET" button
          Overrides the _do_recover_failure in CatsMaint, adding checks whether calling this method is justified
        """
        self.logger.debug("XalocCats recovering from failed get")
        self.recover_cats_from_failed_get()

    def recover_cats_from_failed_get(self):
        """
           Deletes sample info on diff, but should retain info of samples on tools, eg when doing picks
           TODO: tool2 commands are not working, eg SampleNumberInTool2
        """
        if not self._check_unknown_sample_presence()[0]:
            self._cmdRecoverFailure()
        else: raise Exception("The conditions of the beamline do not fit a failed get situation, "
                                "Fixed failed GET is not justified. Find another solution.")
        

    def lidsample_to_basketsample(self, lid, num):
        if self.is_isara():
            return lid, num
        else:
            if lid == 100:
                return lid, num
            
            lid_base = (lid - 1) * self.baskets_per_lid  # nb of first basket in lid
            basket_type = self.basket_types[lid_base]

            if basket_type == BASKET_UNIPUCK:
                samples_per_basket = SAMPLES_UNIPUCK
            elif basket_type == BASKET_SPINE:
                samples_per_basket = SAMPLES_SPINE
            else:
                samples_per_basket = self.samples_per_basket

            lid_offset = ((num - 1) / samples_per_basket) + 1
            sample_pos = ((num - 1) % samples_per_basket) + 1
            basket = lid_base + lid_offset
            return basket, sample_pos

    def basketsample_to_lidsample(self, basket, num):
        if self.is_isara():
            return basket, num
        else:
            if basket == 100:
                return basket, num

            lid = ((basket - 1) / self.baskets_per_lid) + 1

            basket_type = self.basket_types[basket - 1]
            if basket_type == BASKET_UNIPUCK:
                samples_per_basket = SAMPLES_UNIPUCK
            elif basket_type == BASKET_SPINE:
                samples_per_basket = SAMPLES_SPINE
            else:
                samples_per_basket = self.samples_per_basket

            sample = (((basket - 1) % self.baskets_per_lid) * samples_per_basket) + num
            return lid, sample


        
    def _execute_server_task(self, method, *args, **kwargs):
        """
        Executes a task on the CATS Tango device server
        Xaloc: added collision detection while waiting for safe

        :returns: None
        :rtype: None
        """
        self._wait_device_ready(3.0)
        try:
            task_id = method(*args)
        except:
            import traceback
            self.logger.debug("XalocCats exception while executing server task")
            self.logger.debug(traceback.format_exc())
            task_id = None
            raise Exception("The command could not be sent to the robot, check its state.")
            #TODO: why not return with an Exception here to inform there is a problem with the CATS?

        waitsafe = kwargs.get('waitsafe',False)
        waitfinished = kwargs.get('waitfinished',False)
        logging.getLogger("HWR").debug("Cats90. executing method %s / task_id %s / waiting only for safe status is %s" % (str(method), task_id, waitsafe))
        
        # What does the first part of the if do? It's not resetting anything...
        ret=None
        if task_id is None: #Reset
            while self._is_device_busy():
                gevent.sleep(0.1)
            return False
        else:
            # introduced wait because it takes some time before the attribute PathRunning is set
            # after launching a transfer
            time.sleep(6.0)
            while True:
                if waitsafe:
                    if self.path_safe():
                        logging.getLogger("HWR").debug("Cats90. server execution polling finished as path is safe")
                        break
                elif not self.path_running():
                        logging.getLogger("HWR").debug("Cats90. server execution polling finished as path is not running")
                        break
                elif not self._chnCollisionSensorOK.get_value(): 
                    # Should the exception be raised here?? It is also done in _do_load
                    self._update_state()
                    raise Exception ("The robot had a collision, call your LC or floor coordinator")
                # in case nothing is happening. The check for RI1 is because there is a transient loss of sample info when changing samples
                if not self._check_unknown_sample_presence()[0] and not self._chnIsCatsRI1.get_value():
                    break
                gevent.sleep(0.1)            
            ret = True
        return ret


def test_hwo(hwo):
    hwo._updateCatsContents()
    print("Is path running? ", hwo.is_path_running())
    print("Loading shifts:  ", hwo._get_shifts())
    print("Sample on diffr :  ", hwo.cats_sample_on_diffr())
    print("Baskets :  ", hwo.basket_presence)
    print("Baskets :  ", hwo.get_basket_list())
    if hwo.has_loaded_sample():
        print("Loaded is: ", hwo.get_loaded_sample().getCoords())
    print("Is mounted sample: ", hwo.is_mounted_sample((1, 1)))
