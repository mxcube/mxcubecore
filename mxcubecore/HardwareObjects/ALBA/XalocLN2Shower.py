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
[Name]
Liquid nitrogen shower hardware object

[Description]
Specific HwObj for the liquid nitrogen pump installed at XALOC to wash the crystal

[Emitted signals]
- ln2showerIsPumpingChanged
- ln2showerFault

TODO: when the dewar is empty, the operation is INVALID and the State is FAULT
"""

import logging
import PyTango
import time

from taurus.core.tango.enums import DevState

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject

__credits__ = ["ALBA Synchrotron"]
__version__ = "3"
__category__ = "General"
__author__ = "Roeland Boer"

class XalocLN2Shower(HardwareObject):
    """
    Specific liquid nitrogen shower HwObj for XALOC beamline.
    """

    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.logger = logging.getLogger("HWR.XalocLN2Shower")
        self.userlogger = logging.getLogger("user_level_log")

        self.username = None
        self.chn_operation_mode = None
        self.chn_state = None
        self.operation_mode = None
        self.state = None
        self.is_pumping_attr = None
        self.cmd_ln2shower_wash = None
        self.cmd_ln2shower_cold = None
        self.cmd_ln2shower_setflow = None
        self.cmd_ln2shower_on = None
        self.cmd_ln2shower_off = None
        self.cmd_ln2shower_sleep = None
        
        self.wash_mounted_crystals = None # wash every crystal mounted by robot
        self.robot_path_is_safe = None
        self.sample_changer_loading = None
        
        self.collecting = None
        self.super_hwobj = None
        
 
    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        self.username = self.get_property("username")
        self.wash_mounted_crystals = self.get_property("wash_mounted_crystals")
        
        self.chn_operation_mode = self.get_channel_object("operation_mode")
        self.chn_state = self.get_channel_object("State")
        
        self.cmd_ln2shower_wash = self.get_command_object("ln2shower_wash")
        self.cmd_ln2shower_cold = self.get_command_object("ln2shower_cold")
        self.cmd_ln2shower_setflow = self.get_command_object("ln2shower_setflow")
        self.cmd_ln2shower_on = self.get_command_object("ln2shower_on")
        self.cmd_ln2shower_off = self.get_command_object("ln2shower_off")
        self.cmd_ln2shower_sleep = self.get_command_object("ln2shower_sleep")

        if HWR.beamline.sample_changer is not None:
            self.robot_path_is_safe = HWR.beamline.sample_changer.path_safe()
            self.sample_changer_loading = HWR.beamline.sample_changer.cats_running

        if HWR.beamline.detector is not None:
            if HWR.beamline.detector.get_cam_state() == "RUNNING":
                self.collecting = True
            elif HWR.beamline.detector.get_cam_state() == "STANDBY":
                self.collecting = False
            else: 
                raise Exception("The detector seems to be in a funny state")
        
        self.super_hwobj = self.get_object_by_role('beamline-supervisor')

        self.connect(self.chn_operation_mode, "update", self.operation_mode_changed)
        self.connect(self.chn_state, "update", self.state_changed)
        
        if HWR.beamline.collect is not None:
            self.connect(
                HWR.beamline.collect, "collectStarted", self.collect_started
            )
            self.connect(
                HWR.beamline.collect, "collectOscillationFinished", self.collect_finished
            )
            self.connect(
                HWR.beamline.collect, "collectOscillationFailed", self.collect_finished
            )
            
        if HWR.beamline.sample_changer is not None:
            HWR.beamline.sample_changer.connect("path_safeChanged", self.path_safe_changed)
            HWR.beamline.sample_changer.connect("loadedSampleChanged", self.loaded_sample_changed)

    def collect_started(self, owner, num_oscillations):
        #logging.getLogger("user_level_log").info("Collection started in sample_control_brick")
        self.collecting = True

    def collect_finished(self, owner, state, message, *args):
        #logging.getLogger("user_level_log").info("Collection finished in sample_control_brick")
        self.collecting = False

    def path_safe_changed(self, value):
        self.robot_path_is_safe = value
        HWR.beamline.diffractometer.wait_device_ready()
        if value == False:
            self.sample_changer_loading = True
            if self.wash_mounted_crystals and HWR.beamline.diffractometer.get_diff_phase() == 'Transfer':
                self.run_ln2shower_wash()
        else: self.sample_changer_loading = False

    def run_ln2shower_wash(self, washflow = 120):
        #TODO: move diff to transfer phase first, use XalocMiniDiff set_phase method
        
        self.logger.debug( "get_current_phase %s" % HWR.beamline.diffractometer.get_current_phase() ) 
        self.super_hwobj.wait_ready(timeout = 30)
        if not self.collecting:
            if HWR.beamline.diffractometer.get_current_phase() != HWR.beamline.diffractometer.PHASE_TRANSFER:
                HWR.beamline.diffractometer.set_diff_phase( HWR.beamline.diffractometer.PHASE_TRANSFER, timeout = 20 )
            if HWR.beamline.diffractometer.get_diff_phase() == HWR.beamline.diffractometer.PHASE_TRANSFER:
                self.cmd_ln2shower_wash(washflow, wait = False)
                return True
            else:
                return False
        else:
            self.logger.debug( "Cannot use the shower while collecting!! Wait till the collection is finished" ) 
            return False
            
        return True
            
    def run_ln2shower_off(self):
        self.cmd_ln2shower_off(wait = False)

    def operation_mode_changed(self, value):
        """
          value can be None!
        """
        if value is not None: value = int(value)
        if self.operation_mode != value:
            self.operation_mode = value
            if self.operation_mode in [3]:
                self.is_pumping_attr = True
            else:
                self.is_pumping_attr = False
            self.emit("ln2showerIsPumpingChanged", self.is_pumping_attr)
 
    def state_changed(self, value):
        """
          value can be DevState.FAULT, DevState.ON
        """
        if value is not None: 
	    if self.state != value:
		self.state = value
		self.emit("stateChanged", self.state)
		if value in [DevState.FAULT]:
		    self.emit("ln2showerFault", True)
		else:
		    self.emit("ln2showerFault", False)
    
    def is_pumping(self):
        return self.is_pumping_attr

    def loaded_sample_changed(self, sample):
        """
          For each getput, the signal is emitted twice: once when the crystal is removed, 
              once when the new crystal is mounted. 
          For a get or a put, only one signal is sent
          Want only the first signal and turn off the shower.
          
          TODO: when a put is done, the waiting time should be reduced, because the robot is in and out much faster
        """
        time_margin = 2 # waiting time between detecting change of sample and turning off the shower
        if self.sample_changer_loading:
            if self.wash_mounted_crystals:
                time.sleep( time_margin ) # give the CATS time to load the next (in case of getput)
                self.run_ln2shower_off()
            self.sample_changer_loading = False
            
