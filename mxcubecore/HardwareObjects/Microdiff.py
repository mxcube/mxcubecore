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
        self.timeout = 3
        self.phiMotor = self.getDeviceByRole('phi')
        exporter_addr = self.phiMotor.exporter_address
        self.x_calib = self.addChannel({ "type":"exporter", "exporter_address": exporter_addr, "name":"x_calib" }, "CoaxCamScaleX")
        self.y_calib = self.addChannel({ "type":"exporter", "exporter_address": exporter_addr, "name":"y_calib" }, "CoaxCamScaleY")       
        self.moveMultipleMotors = self.addCommand({"type":"exporter", "exporter_address":exporter_addr, "name":"move_multiple_motors" }, "SyncMoveMotors")

        self.phases = {"Centring":1, "BeamLocation":2, "DataCollection":3, "Transfer":4}
        self.movePhase = self.addCommand({"type":"exporter", "exporter_address":exporter_addr, "name":"move_to_phase" }, "startSetPhase")
        self.readPhase =  self.addChannel({ "type":"exporter", "exporter_address": exporter_addr, "name":"read_phase" }, "CurrentPhaseIndex")
        self.hwstate_attr = self.addChannel({"type":"exporter", "exporter_address": exporter_addr, "name":"hwstate" }, "HardwareState")

        MiniDiff.MiniDiff.init(self)
        #self.hwstate_attr.connectSignal("update", self.valueChanged)
        self.centringPhiy.direction = -1

    def getCalibrationData(self, offset):
        return (1.0/self.x_calib.getValue(), 1.0/self.y_calib.getValue())

    def emitCentringSuccessful(self):
        # save position in MD2 software
        self.getCommandObject("save_centring_position")()
 
        # do normal stuff
        return MiniDiff.MiniDiff.emitCentringSuccessful(self)

    def moveToPhase(self, phase, wait=False):
        if self.hwstate_attr.getValue() == "Ready":
            if self.phases.has_key(phase):
                self.movePhase(phase)
                if wait:
                    tt1 = time.time()
                    while time.time() - tt1 < self.timeout:
                        if self.hwstate_attr.getValue() == "Ready":
                            break
                        else:
                            time.sleep(0.5)
    
    def getPhase(self):
        return self.readPhase.getValue()
