from qt import *
from Qub.Tools import QubImageSave
from HardwareRepository.BaseHardwareObjects import Equipment
import tempfile
import logging
import math
import os
import time
from HardwareRepository import HardwareRepository
import MiniDiff
from HardwareRepository import EnhancedPopen
import copy
import gevent

class Microdiff(MiniDiff.MiniDiff):
    def init(self):
        self.phiMotor = self.getDeviceByRole('phi')
        self.x_calib = self.addChannel({ "type":"exporter", "exporter_address": self.phiMotor.exporter_address, "name":"x_calib" }, "CoaxCamScaleX")
        self.y_calib = self.addChannel({ "type":"exporter", "exporter_address": self.phiMotor.exporter_address, "name":"y_calib" }, "CoaxCamScaleY")       
        self.moveMultipleMotors = self.addCommand({"type":"exporter", "exporter_address":self.phiMotor.exporter_address, "name":"move_multiple_motors" }, "SyncMoveMotors")

        MiniDiff.MiniDiff.init(self)

        self.phiy_direction = -1

 
    def getCalibrationData(self, offset):
        return (1.0/self.x_calib.getValue(), 1.0/self.y_calib.getValue())


    def emitCentringSuccessful(self):
        # save position in MD2 software
        self.getCommandObject("save_centring_position")()
 
        # do normal stuff
        return MiniDiff.MiniDiff.emitCentringSuccessful(self)

