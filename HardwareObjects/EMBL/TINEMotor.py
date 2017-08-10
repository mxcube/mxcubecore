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

import logging
import gevent

from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository import HardwareRepository

(NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0, 1, 2, 3, 4, 5)


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3"
__category__ = "Motor"


def energyConverter(wavelength):
    """
    Descript. :
    """
    if wavelength != 0:	
        energy = float(12.398425 / wavelength)
    else:
        energy = 0	
    return energy

class TINEMotor(Device):    
    """
    Descript. :
    """

    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0, 1, 2, 3, 4, 5) 
  
    def __init__(self, name): 
        """
        Descript. :
        """
        Device.__init__(self, name)	
        self.objName = name  
        self.motorState = READY
        self.motorState2 = 'noninit'
        self.limits = None
        self.staticLimits = None
        self.current_position = None
        self.previousPosition = None
        self.static_limits = None

        self.chan_position = None
        self.chan_state = None
        self.chan_limits = None
        self.cmd_set_position = None
        self.cmd_stop_axis = None

        self.converter = None
        self.epsilon = None
        self.verboseUpdate = None
        self.maxMotorPosition = None
        self.moveConditions = None
        #self.moveHOSignals = None
	
    def init(self):
        """
        Descript. :
        """
        self.current_position = -10.0
        self.previousPosition = -10.0

        self.chan_position = self.getChannelObject('axisPosition')
        if self.chan_position is not None:
            self.chan_position.connectSignal('update', self.motor_position_changed)
          
        self.chan_state = self.getChannelObject('axisState')
        if self.chan_state is not None:
            self.chan_state.connectSignal('update', self.motor_state_changed)
        
        self.chan_limits = self.getChannelObject('axisLimits')
        if self.chan_limits is not None:  
            self.chan_limits.connectSignal('update', self.motor_limits_changed)
        else:
            try:
                self.static_limits = self.getProperty("staticLimits")
                self.static_limits = eval(self.static_limits)
                self.motor_limits_changed(self.static_limits)
            except:
                pass

        self.cmd_set_position = self.getCommandObject('setPosition')
        if self.cmd_set_position:
            self.cmd_set_position.connectSignal('connected', self.connected)
            self.cmd_set_position.connectSignal('disconnected', self.disconnected)
    
        self.cmd_stop_axis = self.getCommandObject('stopAxis')
        if self.cmd_stop_axis:
            self.cmd_stop_axis.connectSignal('connected', self.connected)
            self.cmd_stop_axis.connectSignal('disconnected', self.disconnected)

        self.cmd_set_online = self.getCommandObject('setOnline')

        self.converter = self.getProperty("converter") 
        self.epsilon = self.getProperty("epsilon")    
        self.verboseUpdate = self.getProperty("verboseUpdate")
        self.maxMotorPosition = self.getProperty("maxMotorPosition")
        self.moveConditions = self.getProperty("moveConditions")
        #self.moveHOSignals = self.getProperty("moveHOSignals")

        self.username = self.getProperty('username')

        try:
           self.step_limits = eval(self.getProperty("stepLimits"))
        except:
           pass

    def isReady(self):
        return True
      
    def isConnected(self):
        """
        Descript. :
        """
        return True
               
    def connected(self):
        """
        Descript. :
        """
        self.setIsReady(True) 
     
    def disconnected(self):
        """
        Descript. :
        """
        self.setIsReady(True)

    def connectNotify(self, signal):
        """
        Descript. :
        """
        if self.connected():
            if signal == 'stateChanged':
                self.motor_state_changed()
            elif signal == 'limitsChanged':
                self.motor_limits_changed(self.getLimits())
            elif signal == 'positionChanged':
                self.motor_position_changed(self.getPosition())
    
    def motor_limits_changed(self, limits):
        """
        Descript. :
        """
        self.limits = limits
        self.emit('limitsChanged', (limits, ))

    def getLimits(self):
        """
        Descript. :
        """
        if self.chan_limits:
            self.limits = self.chan_limits.getValue()
        else:
            self.limits = self.static_limits
        return self.limits

    def get_step_limits(self):
        """
        Descript. :
        """
        return self.step_limits
  
    def getState(self):
        """
        Descript. :
        """
        if (self.moveConditions and not self.checkConditions(self.moveConditions)):
            self.motorState = UNUSABLE
            self.motorState2 = 'unusable'
            self.emit('stateChanged', (self.motorState, ))
            return self.motorState

        if self.chan_state is not None:
            actualState = self.chan_state.getValue()
        else:
            actualState = "ready"
 
        if type(actualState) in (list, tuple):
            actualState = actualState[0]

        if (actualState != self.motorState2):
            if actualState == 'ready':
                self.motorState = READY
            elif actualState == 0:
                self.motorState = READY
            #else actualState == 'moving':
            else:
                self.motorState = MOVING
            self.emit('stateChanged', (self.motorState, ))            
                
        if actualState == 'ready':
            self.motorState2 = actualState
            self.motorState = READY
        elif actualState == 'moving':
            self.motorState2 = actualState
            self.motorState = MOVING
        return self.motorState 
        
    def getPosition(self):
        """
        Descript. :
        """
        if self.chan_position:
            value = self.chan_position.getValue()
            if type(value) in (list, tuple):
                value = value[0]
            if self.converter is not None:
                value = eval(self.converter)(value)
            return value

    def stop(self):
        """
        Descript. :
        """
        self.cmd_stop_axis()
    
    def move(self, target, wait=False):
        """
        Descript. :
        """
        self.__changeMotorState(MOVING)
        if self.chan_state is not None:
            self.chan_state.setOldValue('moving')
        if target == float('nan'):
            logging.getLogger().debug('Refusing to move %s to target nan'%(self.objNamem))
        else:
            self.cmd_set_position(target)

        if wait:
            self._waitDeviceReady(30)
        if self.chan_state is None:
            self.motor_state_changed("not used state")
            

    def __changeMotorState(self, state):
        """
        Descript. :
        """
        self.motorState = state
        self.emit('stateChanged', (state, ))
        
    def motor_state_changed(self, dummy_state):
        """
        Descript. :
        """
        self.motorState = self.getState()
        self.emit('stateChanged', (self.motorState, ))
        
    def motor_position_changed(self, dummy_argument):
        """
        Descript. :
        """
        position = self.getPosition()   
        if type(position) in (list, tuple):
            position = position[0] 
        if (self.epsilon is None) or (abs(float(position) - float(self.previousPosition)) > float(self.epsilon)) : 
            self.emit('positionChanged', (position, ))
            self.current_position = position
            if (self.verboseUpdate == True):
                logging.getLogger().debug('Updating motor postion %s to %s from %s ' \
                  %(self.objName, position, self.previousPosition))
            self.previousPosition = position

    def getMotorMnemonic(self):
        """
        Descript. :
        """
        return "TINEMotor"

    def getMotorStatus(self, motor_name):
        """
        Descript. :
        """
        state_message = ""
        state_OK = True

        if self.maxMotorPosition:
            if self.getPosition() > self.maxMotorPosition:
                state_OK = None
                state_message = "%s is possibly out of range.\nDo not recommend to proceed!" % motorName

        return state_OK, state_message
            
    def checkConditions(self, cond_dict):
        """
        Descript. :
        """
        conditions = eval(cond_dict)
        for cond in conditions:
            if (conditions[cond] != eval("self.%s" % cond)):
                return False
        return True

    def update_values(self):    
        self.emit('limitsChanged', self.limits)
        self.emit('positionChanged', (self.current_position, ))
        self.emit('stateChanged', (self.motorState, ))

    def _isDeviceReady(self):
        return self.motorState == self.getState()
        #return self.motorState == READY

    def _waitDeviceReady(self,timeout=None):
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self._isDeviceReady():
                gevent.sleep(0.05)

    def enable_motor(self):
        if self.cmd_set_online:
            self.cmd_set_online(1)
            gevent.sleep(2)

    def disable_motor(self):
        if self.cmd_set_online:
            self.cmd_set_online(0)
            gevent.sleep(2)

    def moveRelative(self, relativePosition, wait=False, enable=False):
        self.move(self.getPosition() + relativePosition, wait=wait)
