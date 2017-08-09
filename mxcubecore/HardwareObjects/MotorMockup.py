from HardwareRepository.BaseHardwareObjects import Device
import math
import logging
import time
import gevent
import types
import time

class MotorMockup(Device):      
    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0,1,2,3,4,5)

    def __init__(self, name):
        Device.__init__(self, name)

    def init(self): 
        self.motorState = MotorMockup.READY
        self.username = self.name()
        # this is ugly : I added it to make the centring procedure happy
        self.specName = self.name()
        self.motorPosition = 0
        self._move_task = None
        self.velocity = 100

        if self.getProperty("start_position") is not None:
            self.motorPosition = int(self.getProperty("start_position"))
 
    def isReady(self):
        return True

    def getState(self):
        return self.motorState
    
    def motorLimitsChanged(self):
        self.emit('limitsChanged', (self.getLimits(), ))
                     
    def getLimits(self):
        return (-1E3, 1E3)

    def getPosition(self):
        return self.motorPosition

    def getDialPosition(self):
        return self.getPosition()

    def _move(self, target_pos):
        start_pos = self.motorPosition
        delta = abs(target_pos - start_pos)
        if target_pos > self.motorPosition:
          d = 1
        else:
          d = -1
        t0 = time.time()
        self.emit('stateChanged', (self.motorState, ))           
        while (time.time() - t0) < (delta / float(self.velocity)):
          self.motorPosition = start_pos + d*self.velocity*(time.time() - t0)
          self.emit('positionChanged', (self.motorPosition, ))
          time.sleep(0.02)
        self.motorPosition = target_pos
        self.emit('positionChanged', (target_pos, ))

    def _set_ready(self, task):
        self.motorState = MotorMockup.READY
        self.emit('stateChanged', (self.motorState, ))           

    def move(self, position, wait=False):
        self.motorState = MotorMockup.MOVING
        self._move_task = gevent.spawn(self._move, position)
        self._move_task.link(self._set_ready) 

    def moveRelative(self, relativePosition):
        self.move(self.getPosition() + relativePosition)

    def syncMoveRelative(self, relative_position, timeout=None):
        return self.syncMove(self.getPosition() + relative_position)

    def waitEndOfMove(self, timeout=None):
        if self._move_task is not None:
          with gevent.Timeout(timeout):
            self._move_task.join()

    def syncMove(self, position, timeout=None):
        self.move(position)
        self.waitEndOfMove(timeout)

    def motorIsMoving(self):
        return self.motorState == 'MOVING'
 
    def getMotorMnemonic(self):
        return self.name()

    def stop(self):
        if self._move_task is not None:
            self._move_task.kill()

    def update_values(self):
        self.emit('stateChanged', (self.motorState, ))
        self.emit('positionChanged', (self.motorPosition, ))

