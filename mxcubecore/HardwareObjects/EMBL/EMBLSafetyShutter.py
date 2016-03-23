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
EMBLSafetyShutter
"""

import logging
import gevent
from HardwareRepository.BaseHardwareObjects import Device


__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]

__version__ = "2.2."
__maintainer__ = "Ivars Karpics"
__email__ = "ivars.karpics[at]embl-hamburg.de"
__status__ = "Draft"


class EMBLSafetyShutter(Device):
    shutterState = {
        3: 'unknown',
        1: 'closed',
        0: 'opened',
        9: 'moving',
        17: 'automatic',
        23: 'fault',
        46: 'disabled',
        -1: 'error'
        }

    def __init__(self, name):
        Device.__init__(self, name)
       
        self.use_shutter = None
        self.data_collection_state = None
        self.shutter_open_perm_abs_cond = None
        self.shutter_open_perm_bp_cond = None
        self.shutter_open_perm_abs_value = None
        self.shutter_open_perm_bp_value = None
        self.shutter_is_open_condition = None
        self.shutter_is_open_value = None
        self.shutter_state_value = None
        
        self.cmd_open_shutter = None
        self.cmd_close_shutter = None 

        self.chan_collection_state = None
        self.chan_shutter_open_perm_abs_value = None
        self.chan_shutter_open_perm_bp_value = None  
        self.chan_shutter_is_open = None

    def init(self):
        self.chan_collection_state = self.getChannelObject('chanCollectStatus')
        if self.chan_collection_state is not None:
            self.chan_collection_state.connectSignal('update', 
                self.data_collection_state_changed)

        self.cmd_open_shutter = self.getCommandObject('cmdOpenShutter')
        self.cmd_close_shutter = self.getCommandObject('cmdCloseShutter')

        self.shutter_open_perm_abs_cond = \
             int(self.getProperty('shutterOpenPermissionCondAbs'))
        self.shutter_open_perm_bp_cond = \
             int(self.getProperty('shutterOpenPermissionCondBp')) 
      
        self.chan_shutter_open_perm_abs_value = \
             self.getChannelObject('chanShutterPermCondAbs')
        if self.chan_shutter_open_perm_abs_value is not None:
            self.chan_shutter_open_perm_abs_value.connectSignal('update', \
                 self.shutter_perm_abs_value_changed)

        self.chan_shutter_open_perm_bp_value = \
             self.getChannelObject('chanShutterPermCondBp')
        if self.chan_shutter_open_perm_bp_value is not None:
            self.chan_shutter_open_perm_bp_value.connectSignal('update', \
                 self.shuuter_perm_bp_value_changed)
        
        self.chan_shutter_is_open = self.getChannelObject('chanShutterIsOpen')
        if self.chan_shutter_is_open is not None:
            self.chan_shutter_is_open.connectSignal('update', 
                 self.shutter_is_open_changed)

        self.shutter_is_open_condition = \
             int(self.getProperty("shutterIsOpenCondition"))

        self.use_shutter = self.getProperty('useShutter')
        if self.use_shutter is None:
            self.use_shutter = True 

        self.getWagoState = self.getShutterState

    def connected(self):
        self.setIsReady(True)

    def disconnected(self):
        self.setIsReady(False)

    def check_conditions(self):
        if (self.shutter_open_perm_abs_value != \
            self.shutter_open_perm_abs_cond or 
            self.shutter_open_perm_bp_value != \
            self.shutter_open_perm_bp_cond):
            return False
        else:
            return True

    def shutter_perm_abs_value_changed(self, state):
        self.shutter_open_perm_abs_value = int(state)
        self.getShutterState()

    def shuuter_perm_bp_value_changed(self, state):
        self.shutter_open_perm_bp_value = int(state)
        self.getShutterState()

    def data_collection_state_changed(self, state):
        self.data_collection_state = state
        self.getShutterState()

    def shutter_can_open(self):
        return self.check_conditions()

    def shutter_is_open_changed(self, state):
        value = self.shutter_is_open_value
        self.shutter_is_open_value = int(state)
        self.getShutterState()

    def is_shuter_open(self):
        return self.shutter_is_open_value == self.shutter_is_open_condition

    def getShutterState(self):
        if (not self.shutter_can_open()  or 
	    self.data_collection_state == "collecting"):
            self.shutter_state_value = self.shutterState[46] #disabled
        elif self.is_shuter_open():
            self.shutter_state_value = self.shutterState[0] #opened
        else:
            self.shutter_state_value = self.shutterState[1] #closed

        if not self.use_shutter:
            self.shutter_state_value = self.shutterState[0]
         
        self.emit('shutterStateChanged', (self.shutter_state_value,))
        return self.shutter_state_value

    # set the shutter open command to any TEXT value of size 1 to open it
    def openShutter(self):
        if not self.use_shutter:
            logging.getLogger().info('Safety shutter is disabled')
            return
        self.control_shutter(True)

    # set the shutter close command to any TEXT value of size 1 to open it
    def closeShutter(self):
        self.control_shutter(False) 

    def control_shutter(self, open_state):
        if open_state:
            gevent.spawn(self.open_shutter_thread)
        else:
            gevent.spawn(self.close_shutter_thread)

    def close_shutter_thread(self):
        logging.getLogger().info('Safety shutter: Closing beam shutter...')
        self.emit('shutterStateChanged', (self.shutterState[0])) #closed
        gevent.sleep(2)
        try:
            self.cmd_close_shutter("c")
        except:
            logging.getLogger().error('Safety shutter: unable to close shutter')

    def open_shutter_thread(self):
        logging.getLogger().info('Safety shutter: Openning beam shutter...')
        self.emit('shutterStateChanged', (self.shutterState[1])) #opened
        gevent.sleep(2) 
        try:
            self.cmd_open_shutter("o")
            gevent.sleep(4)
            if (not self.is_shuter_open()):
                logging.getLogger().info("Safety shutter: Opening beam " + \
                    "shutter a second time is taking some more time....")
                self.cmd_open_shutter("o") 
        except:
            logging.getLogger().error('Safety shutter: unable to open shutter')


