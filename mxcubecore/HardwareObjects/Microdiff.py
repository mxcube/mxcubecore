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
import sample_centring

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
        self.head_type = self.addChannel({ "type":"exporter", "exporter_address": self.exporter_addr, "name":"head_type" }, "HeadType")
        self.phases = {"Centring":1, "BeamLocation":2, "DataCollection":3, "Transfer":4}
        self.movePhase = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"move_to_phase" }, "startSetPhase")
        self.readPhase =  self.addChannel({ "type":"exporter", "exporter_address": self.exporter_addr, "name":"read_phase" }, "CurrentPhase")
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
        #check first if all the motors have stopped
        self._wait_ready(10)

        # save position in MD2 software
        self.getCommandObject("save_centring_positions")()
 
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
                    if not timeout:
                        timeout = 40
                    self._wait_ready(timeout)
        else:
            print "moveToPhase - Ready is: ", self._ready()
    
    def getPhase(self):
        return self.readPhase.getValue()

    def moveSyncMotors(self, motors_dict, wait=False, timeout=None):
        argin = ""
        #print "start moving motors =============", time.time()
        for motor in motors_dict.keys():
            position = motors_dict[motor]
            name=self.MOTOR_TO_EXPORTER_NAME[motor]
            argin += "%s=%0.3f;" % (name, position)
        move_sync_motors = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"move_sync_motors" }, "startSimultaneousMoveMotors")
        move_sync_motors(argin)

        if wait:
            while not self._ready():
                time.sleep(0.5)
        #print "end moving motors =============", time.time()
            
    def oscilScan(self, start, end, exptime, wait=False):
        scan_params = "1\t%0.3f\t%0.3f\t%0.4f\t1"% (start, (end-start), exptime)
        scan = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"start_scan" }, "startScanEx")
        scan(scan_params)
        print "scan started at ----------->", time.time()
        if wait:
            self._wait_ready(300) #timeout of 5 min
            print "finished at ---------->", time.time()

    def oscilScan4d(self, start, end, exptime,  motors_pos, wait=False):
        scan_params = "%0.3f\t%0.3f\t%f\t"% (start, (end-start), exptime)
        scan_params += "%0.3f\t" % motors_pos['1']['phiy']
        scan_params += "%0.3f\t" % motors_pos['1']['phiz']
        scan_params += "%0.3f\t" % motors_pos['1']['sampx']
        scan_params += "%0.3f\t" % motors_pos['1']['sampy']
        scan_params += "%0.3f\t" % motors_pos['2']['phiy']
        scan_params += "%0.3f\t" % motors_pos['2']['phiz']
        scan_params += "%0.3f\t" % motors_pos['2']['sampx']
        scan_params += "%0.3f" % motors_pos['2']['sampy']

        scan = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"start_scan4d" }, "startScan4DEx")
        scan(scan_params)
        print "scan started at ----------->", time.time()
        if wait:
            self._wait_ready(900) #timeout of 15 min
            print "finished at ---------->", time.time()

    def in_plate_mode(self):
        return self.head_type.getValue() == "Plate"

    def start3ClickCentring(self, sample_info=None):
        if self.in_plate_mode():
            phi_range = 10
            self.currentCentringProcedure = sample_centring.start_plate({"phi":self.centringPhi,
                                                                         "phiy":self.centringPhiy,
                                                                         "sampx": self.centringSamplex,
                                                                         "sampy": self.centringSampley,
                                                                         "phiz": self.centringPhiz }, 
                                                                        self.pixelsPerMmY, self.pixelsPerMmZ, 
                                                                        self.getBeamPosX(), self.getBeamPosY(), phi_range = phi_range)
        else:
            self.currentCentringProcedure = sample_centring.start({"phi":self.centringPhi,
                                                                   "phiy":self.centringPhiy,
                                                                   "sampx": self.centringSamplex,
                                                                   "sampy": self.centringSampley,
                                                                   "phiz": self.centringPhiz }, 
                                                                  self.pixelsPerMmY, self.pixelsPerMmZ, 
                                                                  self.getBeamPosX(), self.getBeamPosY())
                                                                         
        self.currentCentringProcedure.link(self.manualCentringDone)

def set_light_in(light, light_motor, zoom):
    """
    The move to centring phase can be quite slow, so we use the front
    light instead.
    """
    #MICRODIFF.moveToPhase(phase="Centring",  wait=True, timeout=40)
    """
    diffr = MICRODIFF.getDeviceByRole("beamstop")
    pos = diffr.getActuatorState()
    if pos == 'in':
        try:
            diffr.actuatorOut(wait=True)
            print "Now put the %s in"% light.username
            print diffr.getActuatorState()
            print MICRODIFF._ready()
            light.actuatorIn(wait=True)
        except Exception, error:
            print str(error)
    
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
    """
    MICRODIFF.getDeviceByRole("flight").move(0)
    MICRODIFF.getDeviceByRole("lightInOut").actuatorIn()

MiniDiff.set_light_in = set_light_in
