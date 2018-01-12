import sys
import gevent
import time
import logging
import math
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository.TaskUtils import *


class BIOMAXTransmission(Equipment):

    def init(self):
        self.ready_event = gevent.event.Event()
        self.transmission_motor = None
        self.moving = None
        self.limits = [0, 100]
	self.threhold = 5

        try:
            self.transmission_motor =  self.getObjectByRole("transmission_motor")
        except KeyError:
            logging.getLogger("HWR").warning('Error initializing transmission motor')
        if self.transmission_motor is not None:
            self.transmission_motor.connect('positionChanged', self.transmissionPositionChanged)

   
    def isReady(self):
        return True

    def get_value(self):
	return "%.3f" % self.transmission_motor.getPosition()

    def getAttFactor(self):
	return "%.3f" % self.transmission_motor.getPosition()

    def getAttState(self):
	return 1

    def getLimits(self):
	return (0, 100)

    def setpoint_reached(self, setpoint):
	curr_pos = float(self.get_value())
	return abs(curr_pos - setpoint) < 5

    def set_value(self, value, wait=False):
	if value < self.limits[0] or value > self.limits[1]:
	    raise Exception('Transmssion out of limits.')
	self.transmission_motor.move(value)
	if wait:
	    with gevent.Timeout(30, Exception("Timeout waiting for device ready")):
	        while not self.setpoint_reached(value):
	            gevent.sleep(0.1)

    	self._update()

    def _update(self):
        self.emit("attStateChanged", self.getAttState())

    def transmissionPositionChanged(self, *args):
	pos = self.get_value()
        self.emit('valueChanged', (pos, ))
   
    def stop(self):
	self.transmission_motor.stop()
