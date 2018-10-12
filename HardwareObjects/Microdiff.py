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
        self.moveMultipleMotors = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"move_multiple_motors" }, "SyncMoveMotors")
        self.head_type = self.addChannel({ "type":"exporter", "exporter_address": self.exporter_addr, "name":"head_type" }, "HeadType")
        self.kappa = self.addChannel({ "type":"exporter", "exporter_address": self.exporter_addr, "name":"kappa_enable" }, "KappaIsEnabled") 
        self.phases = {"Centring":1, "BeamLocation":2, "DataCollection":3, "Transfer":4}
        self.movePhase = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"move_to_phase" }, "startSetPhase")
        self.readPhase =  self.addChannel({ "type":"exporter", "exporter_address": self.exporter_addr, "name":"read_phase" }, "CurrentPhase")
        self.scanLimits = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"scan_limits" }, "getOmegaMotorDynamicScanLimits")
        if self.getProperty("use_hwstate"):
            self.hwstate_attr = self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"hwstate" }, "HardwareState")
        else:
            self.hwstate_attr = None
        self.swstate_attr = self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"swstate" }, "State")
        self.nb_frames =  self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"nbframes" }, "ScanNumberOfFrames")
        
         # raster scan attributes
        self.scan_range = self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"scan_range" }, "ScanRange")
        self.scan_exposure_time = self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"exposure_time" }, "ScanExposureTime")
        self.scan_start_angle = self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"start_angle" }, "ScanStartAngle")
        self.scan_detector_gate_pulse_enabled = self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"detector_gate_pulse_enabled" }, "DetectorGatePulseEnabled")
        self.scan_detector_gate_pulse_readout_time = self.addChannel({"type":"exporter", "exporter_address": self.exporter_addr, "name":"detector_gate_pulse_readout_time" }, "DetectorGatePulseReadoutTime")

        self.abort_cmd = self.addCommand({ "type": "exporter", "exporter_address": self.exporter_addr, "name": "abort" }, "abort") 

        MiniDiff.MiniDiff.init(self)
        self.centringPhiy.direction = -1
        self.MOTOR_TO_EXPORTER_NAME = self.getMotorToExporterNames()
        self.move_to_coord = self.moveToBeam

        self.centringVertical = self.getDeviceByRole('centringVertical')
        self.centringFocus = self.getDeviceByRole('centringFocus')   
        
        self.frontLight = self.getDeviceByRole('FrontLight')
        self.backLight = self.getDeviceByRole('BackLight')  

        self.beam_info = self.getObjectByRole('beam_info')

        self.wait_ready = self._wait_ready

    def getMotorToExporterNames(self):
        MOTOR_TO_EXPORTER_NAME = {"focus":self.focusMotor.getProperty('motor_name'), "kappa":self.kappaMotor.getProperty('motor_name'),
                                  "kappa_phi":self.kappaPhiMotor.getProperty('motor_name'), "phi": self.phiMotor.getProperty('motor_name'),
                                  "phiy":self.phiyMotor.getProperty('motor_name'), "phiz":self.phizMotor.getProperty('motor_name'),
                                  "sampx":self.sampleXMotor.getProperty('motor_name'), "sampy":self.sampleYMotor.getProperty('motor_name'),
                                  "zoom":'Zoom' }
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
        if self.hwstate_attr:
            if self.hwstate_attr.getValue() == "Ready" and self.swstate_attr.getValue() == "Ready":
                return True
        else:
            if self.swstate_attr.getValue() == "Ready":
                return True
        return False

    def _wait_ready(self, timeout=None):
        # None means infinite timeout
        # <=0 means default timeout
        if timeout is not None and timeout <= 0:
            timeout = self.timeout
        with gevent.Timeout(timeout, RuntimeError("Timeout waiting for diffractometer to be ready")):
             while not self._ready():
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
        in_kappa_mode = self.in_kappa_mode()
        argin = ""
        #print "start moving motors =============", time.time()
        if wait:
            self._wait_ready()
        for motor in motors_dict.keys():
            position = motors_dict[motor]
            if position is None:
                continue
            name = self.MOTOR_TO_EXPORTER_NAME[motor]
            if not in_kappa_mode and motor in ('kappa','kappa_phi'):
                continue
            argin += "%s=%0.3f;" % (name, position)
        if not argin:
            return
        move_sync_motors = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"move_sync_motors" }, "startSimultaneousMoveMotors")
        move_sync_motors(argin)

        if wait:
            time.sleep(0.1)
            self._wait_ready()
        #print "end moving motors =============", time.time()
            
    def oscilScan(self, start, end, exptime, wait=False):
        if self.in_plate_mode():
            scan_speed = math.fabs(end-start) / exptime
            low_lim, hi_lim = map(float, self.scanLimits(scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            elif end > hi_lim:
                raise ValueError("Scan end abobe the allowed value %f" % hi_lim)
                
        self.nb_frames.setValue(1)
        scan_params = "1\t%0.3f\t%0.3f\t%0.4f\t1"% (start, (end-start), exptime)
        scan = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"start_scan" }, "startScanEx")
        scan(scan_params)
        print "oscil scan started at ----------->", time.time()
        if wait:
            self._wait_ready(600) #timeout of 10 min # Changed on 20180406 Daniele, because of long exposure time set by users
            print "finished at ---------->", time.time()

    def oscilScan4d(self, start, end, exptime,  motors_pos, wait=False):
        if self.in_plate_mode():
            scan_speed = math.fabs(end-start) / exptime
            low_lim, hi_lim = map(float, self.scanLimits(scan_speed))
            if start < low_lim:
                raise ValueError("Scan start below the allowed value %f" % low_lim)
            elif end > hi_lim:
                raise ValueError("Scan end abobe the allowed value %f" % hi_lim)
        self.nb_frames.setValue(1)        
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
        print "helical scan started at ----------->", time.time()
        if wait:
            self._wait_ready(900) #timeout of 15 min
            print "finished at ---------->", time.time()
            
    def oscilScanMesh(self,start, end, exptime, dead_time, mesh_num_lines, mesh_total_nb_frames, mesh_center, mesh_range, wait=False):
        #import pdb; pdb.set_trace()
        self.scan_range.setValue(end-start)
        self.scan_exposure_time.setValue(exptime/mesh_num_lines)
        self.scan_start_angle.setValue(start)
        self.scan_detector_gate_pulse_enabled.setValue(True)
        servo_time = 0.110 # adding the servo time to the readout time to avoid any servo cycle jitter 
        self.scan_detector_gate_pulse_readout_time.setValue(dead_time*1000 +servo_time)  # TODO

        # Prepositionning at the center of the grid      
        self.moveMotors(mesh_center.as_dict())
        self.centringVertical.syncMoveRelative((mesh_range['vertical_range'])/2)
        self.centringPhiy.syncMoveRelative(-(mesh_range['horizontal_range'])/2)

        scan_params = "%0.3f\t" % -mesh_range['horizontal_range']
        scan_params += "%0.3f\t" % mesh_range['vertical_range']
        scan_params += "%d\t" % mesh_num_lines
        scan_params += "%d\t" % (mesh_total_nb_frames/mesh_num_lines)
        #scan_params += "%d\t" % 1
        scan_params += "%r" % True   # TODO

        scan = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"start_raster_scan" }, "startRasterScan")
        scan(scan_params)
        print "mesh scan started at ----------->", time.time()
        if wait:
            self._wait_ready(1800) #timeout of 30 min
            print "finished at ---------->", time.time()

    def stillScan(self, pulse_duration, pulse_period, pulse_nb, wait=False):
        scan_params = "%0.6f\t%0.6f\t%d"% (pulse_duration, pulse_period, pulse_nb)
        scan = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"start_scan" }, "startStillScan")
        scan(scan_params)
        print "still scan started at ----------->", time.time()
        if wait:
            self._wait_ready(1800) #timeout of 30 min
            print "finished at ---------->", time.time()

    def in_plate_mode(self):
        try:
            return self.head_type.getValue() == "Plate"
        except:
            return False

    def in_kappa_mode(self):
        return self.head_type.getValue() == "MiniKappa" and self.kappa.getValue()

    def getPositions(self):
        pos = { "phi": float(self.phiMotor.getPosition()),
                "focus": float(self.focusMotor.getPosition()),
                "phiy": float(self.phiyMotor.getPosition()),
                "phiz": float(self.phizMotor.getPosition()),
                "sampx": float(self.sampleXMotor.getPosition()),
                "sampy": float(self.sampleYMotor.getPosition()),
                "zoom": float(self.zoomMotor.getPosition()),
                "kappa": float(self.kappaMotor.getPosition()) if self.in_kappa_mode() else None,
                "kappa_phi": float(self.kappaPhiMotor.getPosition()) if self.in_kappa_mode() else None}
        return pos

    def moveMotors(self, roles_positions_dict):
        self.moveSyncMotors(roles_positions_dict, wait=True)


    def moveToBeam(self, x, y):
        if not self.in_plate_mode():  
            MiniDiff.MiniDiff.moveToBeam(self, x, y)
        else:          
            try:
                beam_xc = self.getBeamPosX()
                beam_yc = self.getBeamPosY()

                self.centringVertical.moveRelative(self.centringPhiz.direction*(y-beam_yc)/float(self.pixelsPerMmZ))
                self.centringPhiy.moveRelative(self.centringPhiy.direction*(x-beam_xc)/float(self.pixelsPerMmY))

            except:
                logging.getLogger("user_level_log").exception("Microdiff: could not move to beam, aborting")
        

   

    def start3ClickCentring(self, sample_info=None):
        if self.in_plate_mode():
            plateTranslation = self.getDeviceByRole('plateTranslation')
            cmd_set_plate_vertical = self.addCommand({"type":"exporter", "exporter_address":self.exporter_addr, "name":"plate_vertical" }, "setPlateVertical")
            low_lim, high_lim = self.phiMotor.getDynamicLimits()
            phi_range = math.fabs(high_lim - low_lim -1)
            self.currentCentringProcedure = sample_centring.start_plate_1_click({"phi":self.centringPhi,
                                                                                 "phiy":self.centringPhiy,
                                                                                 "sampx": self.centringSamplex,
                                                                                 "sampy": self.centringSampley,
                                                                                 "phiz": self.centringVertical,
                                                                                 "plateTranslation": plateTranslation}, 
                                                                                self.pixelsPerMmY, self.pixelsPerMmZ, 
                                                                                self.getBeamPosX(), self.getBeamPosY(),
                                                                                cmd_set_plate_vertical,
                                                                                low_lim+0.5, high_lim-0.5)
        else:
            self.currentCentringProcedure = sample_centring.start({"phi":self.centringPhi,
                                                                   "phiy":self.centringPhiy,
                                                                   "sampx": self.centringSamplex,
                                                                   "sampy": self.centringSampley,
                                                                   "phiz": self.centringPhiz }, 
                                                                  self.pixelsPerMmY, self.pixelsPerMmZ, 
                                                                  self.getBeamPosX(), self.getBeamPosY(), chi_angle=self.chiAngle)

        self.currentCentringProcedure.link(self.manualCentringDone)

    def interruptAndAcceptCentring(self):
        """ Used when plate. Kills the current 1 click centring infinite loop
        and accepts fake centring - only save the motor positions
        """
        self.currentCentringProcedure.kill()
        self.do_centring = False
        self.startCentringMethod(self,self.MANUAL3CLICK_MODE)
        self.do_centring = True

    def getFrontLightLevel(self):
        return self.frontLight.getPosition()

    def setFrontLightLevel(self, level):
        return self.frontLight.move(level)

    def getBackLightLevel(self):
        return self.backLight.getPosition()

    def setBackLightLevel(self, level):
        return self.backLight.move(level)

def set_light_in(light, light_motor, zoom):
    self.frontlight.move(0)
    MICRODIFF.getDeviceByRole("BackLightSwitch").actuatorIn()

MiniDiff.set_light_in = set_light_in


def to_float(d):
    for k, v in d.iteritems():
        try:
            d[k] = float(v)
        except:
            pass
    
