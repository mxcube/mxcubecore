import logging
from MiniDiff import *
import PyTango
import os

class MiniDiffPX3(MiniDiff):
    def __init__(self, *args):
        MiniDiff.MiniDiff.__init__(self, *args)

    def init(self):
        self.centringMethods={self.MANUAL3CLICK_MODE: self.start3ClickCentring,\
            self.C3D_MODE: self.startAutoCentring }
        self.cancelCentringMethods={}

        self.currentCentringProcedure = None
        self.currentCentringMethod = None

        self.centringStatus={"valid":False}

        try:
          phiz_ref = self["centringReferencePosition"].getProperty("phiz")
        except:
          phiz_ref = None
        
        self.phiMotor = self.getDeviceByRole('phi')
        self.phizMotor = self.getDeviceByRole('phiz')
        self.phiyMotor = self.getDeviceByRole("phiy")
        self.zoomMotor = self.getDeviceByRole('zoom')
        self.lightMotor = self.getDeviceByRole('light')
        self.focusMotor = self.getDeviceByRole('focus')
        self.sampleXMotor = self.getDeviceByRole("sampx")
        self.sampleYMotor = self.getDeviceByRole("sampy")
        self.camera = self.getDeviceByRole('camera')
        self.centringPhi=sample_centring.CentringMotor(self.phiMotor, direction=-1)
        self.centringPhiz=sample_centring.CentringMotor(self.phizMotor, reference_position=phiz_ref)
        self.centringPhiy=sample_centring.CentringMotor(self.phiyMotor, direction=-1)
        self.centringSamplex=sample_centring.CentringMotor(self.sampleXMotor)
        self.centringSampley=sample_centring.CentringMotor(self.sampleYMotor)
        
        try:
            self.md2 = PyTango.DeviceProxy(self.tangoname) #'i11-ma-cx1/ex/md2')
        except:
            logging.error("MiniDiffPX2 / Cannot connect to tango device: %s ", self.tangoname )
        else:
            self.md2_ready = True
            
        sc_prop=self.getProperty("samplechanger")
        if sc_prop is not None:
            try:
                self.sampleChanger=HardwareRepository.HardwareRepository().getHardwareObject(sc_prop)
            except:
                pass
        wl_prop=self.getProperty("wagolight")
        if wl_prop is not None:
            try:
                self.lightWago=HardwareRepository.HardwareRepository().getHardwareObject(wl_prop)
            except:
                pass
        aperture_prop = self.getProperty("aperture")
        if aperture_prop is not None:
            try:
                self.aperture = HardwareRepository.HardwareRepository().getHardwareObject(aperture_prop)
            except:
                pass
            
        if self.phiMotor is not None:
            self.connect(self.phiMotor, 'stateChanged', self.phiMotorStateChanged)
            self.connect(self.phiMotor, "positionChanged", self.emitDiffractometerMoved)
        else:
            logging.getLogger("HWR").error('MiniDiff: phi motor is not defined in minidiff equipment %s', str(self.name()))
        if self.phizMotor is not None:
            self.connect(self.phizMotor, 'stateChanged', self.phizMotorStateChanged)
            self.connect(self.phizMotor, 'positionChanged', self.phizMotorMoved)
            self.connect(self.phizMotor, "positionChanged", self.emitDiffractometerMoved)
        else:
            logging.getLogger("HWR").error('MiniDiff: phiz motor is not defined in minidiff equipment %s', str(self.name()))
        if self.phiyMotor is not None:
            self.connect(self.phiyMotor, 'stateChanged', self.phiyMotorStateChanged)
            self.connect(self.phiyMotor, 'positionChanged', self.phiyMotorMoved)
            self.connect(self.phiyMotor, "positionChanged", self.emitDiffractometerMoved)
        else:
            logging.getLogger("HWR").error('MiniDiff: phiy motor is not defined in minidiff equipment %s', str(self.name()))
        if self.zoomMotor is not None:
            self.connect(self.zoomMotor, 'predefinedPositionChanged', self.zoomMotorPredefinedPositionChanged)
            self.connect(self.zoomMotor, 'stateChanged', self.zoomMotorStateChanged)
        else:
            logging.getLogger("HWR").error('MiniDiff: zoom motor is not defined in minidiff equipment %s', str(self.name()))
        if self.sampleXMotor is not None:
            self.connect(self.sampleXMotor, 'stateChanged', self.sampleXMotorStateChanged)
            self.connect(self.sampleXMotor, 'positionChanged', self.sampleXMotorMoved)
            self.connect(self.sampleXMotor, "positionChanged", self.emitDiffractometerMoved)
        else:
            logging.getLogger("HWR").error('MiniDiff: sampx motor is not defined in minidiff equipment %s', str(self.name()))
        if self.sampleYMotor is not None:
            self.connect(self.sampleYMotor, 'stateChanged', self.sampleYMotorStateChanged)
            self.connect(self.sampleYMotor, 'positionChanged', self.sampleYMotorMoved)
            self.connect(self.sampleYMotor, "positionChanged", self.emitDiffractometerMoved)
        else:
            logging.getLogger("HWR").error('MiniDiff: sampy motor is not defined in minidiff equipment %s', str(self.name()))
        if self.camera is None:
            logging.getLogger("HWR").error('MiniDiff: camera is not defined in minidiff equipment %s', str(self.name()))
        else:
            self.imgWidth, self.imgHeight = self.camera.getWidth(), self.camera.getHeight()
        if self.sampleChanger is None:
            logging.getLogger("HWR").warning('MiniDiff: sample changer is not defined in minidiff equipment %s', str(self.name()))
        else:
            try:
                self.connect(self.sampleChanger, 'sampleIsLoaded', self.sampleChangerSampleIsLoaded)
            except:
                logging.getLogger("HWR").exception('MiniDiff: could not connect to sample changer smart magnet')
        if self.lightWago is not None:
            self.connect(self.lightWago, 'wagoStateChanged', self.wagoLightStateChanged)
        else:
            logging.getLogger("HWR").warning('MiniDiff: wago light is not defined in minidiff equipment %s', str(self.name()))
        if self.aperture is not None:
            self.connect(self.aperture, 'predefinedPositionChanged', self.apertureChanged)
            self.connect(self.aperture, 'positionReached', self.apertureChanged)
            
    
    def phizMotorMoved(self, pos):
        if time.time() - self.centredTime > 2.0:
          logging.info("phiZMotorMoved time.time() - self.centredTime %s", str(time.time() - self.centredTime) )
          self.invalidateCentring()

    def phiyMotorMoved(self, pos):
        if time.time() - self.centredTime > 2.0:
           logging.info("phiyMotorMoved time.time() - self.centredTime %s", str(time.time() - self.centredTime) )
           self.invalidateCentring()

    def sampleXMotorMoved(self, pos):
        if time.time() - self.centredTime > 2.0:
           logging.info("sampleXMotorMoved time.time() - self.centredTime %s", str(time.time() - self.centredTime) )
           self.invalidateCentring()


    def sampleYMotorMoved(self, pos):
        if time.time() - self.centredTime > 2.0:
           logging.info("sampleYMotorMoved time.time() - self.centredTime %s", str(time.time() - self.centredTime) )
           self.invalidateCentring()


    def sampleChangerSampleIsLoaded(self, state):
        if time.time() - self.centredTime > 2.0:
           self.invalidateCentring()
    
    def getCalibrationData(self, offset):
        return self.get_pixels_per_mm()
        
    def get_pixels_per_mm(self):
        return 1000./self.md2.CoaxCamScaleX, 1000./self.md2.CoaxCamScaleY
        
    def getBeamInfo(self, update_beam_callback):
        d = {}
        d["size_x"] = 0.010
        d["size_y"] = 0.005
        d["shape"] = "rectangular"
        self.beamSizeX = 0.010
        self.beamSizeY = 0.005
        self.beamShape = "rectangular"
        return d
    
    def getBeamPosX(self):
        return self.md2.BeamPositionHorizontal

    def getBeamPosY(self):
        return self.md2.BeamPositionVertical
        
    def getPositions(self):
        return { "phi": self.phiMotor.getPosition(),
               "focus": self.focusMotor.getPosition(),
               "phiy": self.phiyMotor.getPosition(),
               "phiz": self.phizMotor.getPosition(),
               "sampx": self.sampleXMotor.getPosition(),
               "sampy": self.sampleYMotor.getPosition(),
               #"kappa": self.kappaMotor.getPosition(),
               #"kappa_phi": self.kappaPhiMotor.getPosition(),
               "zoom": self.zoomMotor.getPosition()}
               
    def moveMotors(self, roles_positions_dict):
        motor = { "phi": self.phiMotor,
                  "focus": self.focusMotor,
                  "phiy": self.phiyMotor,
                  "phiz": self.phizMotor,
                  "sampx": self.sampleXMotor,
                  "sampy": self.sampleYMotor,
                  #"kappa": self.kappaMotor,
                  #"kappa_phi": self.kappaPhiMotor,     
                  "zoom": self.zoomMotor }
       
       for role, pos in roles_positions_dict.iteritems():
           motor[role].move(pos)
 
        # TODO: remove this sleep, the motors states should
        # be MOVING since the beginning (or READY if move is
        # already finished) 
        time.sleep(1)
 
        while not all([m.getState() == m.READY for m in motor.itervalues()]):
           time.sleep(0.1)          
    
    def beamPositionCheck(self):
        os.system('calibrator.py')
    
    def apertureAlign(self):
        os.system('scan_and_align.py')
