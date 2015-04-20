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

MICRODIFF = None

class Microdiff(MiniDiff.MiniDiff):
    def init(self):
        global MICRODIFF
        MICRODIFF = self
        self.timeout = 3
        self.phiMotor = self.getDeviceByRole('phi')
        self.exporter_addr = self.phiMotor.exporter_address
        self.x_calib = self.addChannel({ "type":"exporter", "exporter_address": self.exporter_addr, "name":"x_calib" }, "CoaxCamScaleX")
        self.y_calib = self.addChannel({ "type":"exporter", "exporter_address": self.exporter_addr, "name":"y_calib" }, "CoaxCamScaleY")       
        self.moveMultipleMotors = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"move_multiple_motors" }, "SyncMoveMotors")

        self.phases = {"Centring":1, "BeamLocation":2, "DataCollection":3, "Transfer":4}
        self.movePhase = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"move_to_phase" }, "startSetPhase")
        self.readPhase =  self.addChannel({ "type":"exporter", "exporter_address": self.exporter_addr, "name":"read_phase" }, "CurrentPhaseIndex")
        self.hwstate_attr = self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"hwstate" }, "HardwareState")
        self.swstate_attr = self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"swstate" }, "State")

        MiniDiff.MiniDiff.init(self)
        #self.hwstate_attr.connectSignal("update", self.valueChanged)
        self.centringPhiy.direction = -1
        self.MOTOR_TO_EXPORTER_NAME = self.getMotorToExporterNames()

    def getMotorToExporterNames(self):
        #only temporary. Get the names from the xml files
        MOTOR_TO_EXPORTER_NAME = {"focus":"AlignmentX", "kappa":"Kappa",
                                  "kappa_phi":"Phi", "phi": "Omega",
                                  "phiy":"AlignmentY", "phiz":"AlignmentZ",
                                  "sampx":"CentringX", "sampy":"CentringY",
                                  "zoom":"Zoom"}
        return MOTOR_TO_EXPORTER_NAME
        
    def getCalibrationData(self, offset):
        return (1.0/self.x_calib.getValue(), 1.0/self.y_calib.getValue())

    def emitCentringSuccessful(self):
        # save position in MD2 software
        self.getCommandObject("save_centring_position")()
 
        # do normal stuff
        return MiniDiff.MiniDiff.emitCentringSuccessful(self)

    def _ready(self):
        if self.hwstate_attr.getValue() == "Ready" and self.swstate_attr.getValue() == "Ready":
            return True
        return False

    def _wait_ready(self, timeout=None):
        if timeout <= 0:
            timeout = self.timeout
        tt1 = time.time()
        while time.time() - tt1 < timeout:
             if self._ready():
                 break
             else:
                 time.sleep(0.5)

    def moveToPhase(self, phase, wait=False, timeout=None):
        if self._ready():
            if self.phases.has_key(phase):
                self.movePhase(phase)
                if wait:
                    self._wait_ready(40)
    
    def getPhase(self):
        return self.readPhase.getValue()

    def moveSyncMotors(self, motors_dict, wait=False, timeout=None):
        argin = ""
        for motor in motors_dict.keys():
            position = motors_dict[motor]
            name=self.MOTOR_TO_EXPORTER_NAME[motor]
            argin += "%s=%0.3f;" % (name, position)
        move_sync_motors = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"move_sync_motors" }, "startSimultaneousMoveMotors")
        move_sync_motors(argin)

        if wait:
            while not self._ready():
                time.sleep(0.5)
        #self._wait_ready(timeout)
            
    def oscilScan(self, start, end, exptime, wait=False):
        scan_params = "1\t%0.3f\t%0.3f\t%0.4f\t1"% (start, (end-start), exptime)
        """
        scan_params = []
        scan_params.append(int(1))
        scan_params.append(float(start))
        scan_params.append(float(end-start))
        scan_params.append(float(exptime))
        scan_params.append(int(1)) # only one oscillation)
        """
        scan = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"start_scan" }, "startScanEx")
        scan(scan_params)
        print "started at ----------->", time.time()
        if wait:
            self._wait_ready(1000)
            print "finished at ---------->", time.time()

    def oscilScan4d(self, start, end, exptime,  motors_pos, wait=False):
        """
        scan_params = []
        scan_params.append(start)                 
        scan_params.append(end - start)
        scan_params.append(exptime)
        """
        scan_params = "%0.3f\t%0.3f\t%0.4f\t"% (start, (end-start), exptime)
        for i in motors_pos.values():
            #scan_params.append(i)
            scan_params += "%0.3f\t", i
        scan = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"start_scan" }, "startScan4dEx")
        scan(scan_params)
        if wait:
            self._wait_ready(10000)

def set_light_in(light, light_motor, zoom):
    MICRODIFF.moveToPhase(phase="Centring",  wait=True, timeout=40)
    
    # No light level, choose default
    if light_motor.getPosition() == 0:
        zoom_level = int(zoom.getPosition())
        light_level = None

        try:
            light_level = zoom['positions'][0][zoom_level].getProperty('lightLevel')
        except IndexError:
            logging.getLogger("HWR").info("Could not get default light level")
            light_level = 1

        if light_level:
            light_motor.move(light_level)

MiniDiff.set_light_in = set_light_in



