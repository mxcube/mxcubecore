# -*- coding: utf-8 -*-
import gevent
from gevent.event import AsyncResult
from Qub.Tools import QubImageSave
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository.TaskUtils import *
import Image
import tempfile
import logging
import math
import os
import time
from HardwareRepository import HardwareRepository
import copy
import sample_centring
import numpy
import PyTango
import calibrator
import scan_and_align

class myimage:
    def __init__(self, drawing):
        self.drawing = drawing
        matrix = self.drawing.matrix()
        self.zoom = 1
        if matrix is not None:
            self.zoom = matrix.m11()
        self.img = self.drawing.getPPP()
        fd, name = tempfile.mkstemp()
        os.close(fd)
        QubImageSave.save(name, self.img, self.drawing.canvas(), self.zoom, "JPEG")
        f = open(name, "r")
        self.imgcopy = f.read()
        f.close()
        os.unlink(name)
    def __str__(self):
        return self.imgcopy


def take_snapshots(light, light_motor, phi, zoom, drawing):
  logging.getLogger("HWR").info("MiniDiffPX2: take_snapshots")
  centredImages = []

  if light is not None:
    light.wagoIn()

    # No light level, choose default
    if light_motor.getPosition() == 0:
      zoom_level = zoom.getPosition()
      light_level = None

      try:
        light_level = zoom['positions'][0][zoom_level].getProperty('lightLevel')
      except IndexError:
        logging.getLogger("HWR").info("Could not get default light level")
        light_level = 1

      if light_level:
        light_motor.move(light_level)

    while light.getWagoState()!="in":
      time.sleep(0.5)

  for i in range(4):
     logging.getLogger("HWR").info("MiniDiff: taking snapshot #%d", i+1)
     centredImages.append((phi.getPosition(),str(myimage(drawing))))
     phi.syncMoveRelative(-90)
     time.sleep(2)

  centredImages.reverse() # snapshot order must be according to positive rotation direction

  return centredImages


class MiniDiffPX2(Equipment):
    MANUAL3CLICK_MODE = "Manual 3-click"
    C3D_MODE = "Computer automatic"
    #MOVE_TO_BEAM_MODE = "Move to Beam"

    def __init__(self, *args):
        Equipment.__init__(self, *args)

        self.phiMotor = None
        self.phizMotor = None
        self.phiyMotor = None
        self.lightMotor = None
        self.zoomMotor = None
        self.sampleXMotor = None
        self.sampleYMotor = None
        self.camera = None
        self.sampleChanger = None
        self.lightWago = None
        self.currentSampleInfo = None
        self.aperture = None
      
        self.pixelsPerMmY=None
        self.pixelsPerMmZ=None
        self.imgWidth = None
        self.imgHeight = None
        self.centredTime = 0
        self.user_confirms_centring = True

        self.connect(self, 'equipmentReady', self.equipmentReady)
        self.connect(self, 'equipmentNotReady', self.equipmentNotReady)     


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
        try:
            phiDirection = self.phiMotor.getProperty("direction")
            if phiDirection == None:
                 phiDirection = 1
        except:
            phiDirection=1

        self.centringPhi=sample_centring.CentringMotor(self.phiMotor, direction=phiDirection)
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
        
        # some defaults
        self.anticipation  = 1
        self.collect_phaseposition = 'DataCollection'
        
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


    def setSampleInfo(self, sample_info):
        self.currentSampleInfo = sample_info

    def emitDiffractometerMoved(self, *args):
      self.emit("diffractometerMoved", ())
        
    def isReady(self):
        return self.isValid() and not any([m.motorIsMoving() for m in (self.sampleXMotor, self.sampleYMotor, self.zoomMotor, self.phiMotor, self.phizMotor, self.phiyMotor)])
    

    def isValid(self):
        return self.sampleXMotor is not None and \
            self.sampleYMotor is not None and \
            self.zoomMotor is not None and \
            self.phiMotor is not None and \
            self.phizMotor is not None and \
            self.phiyMotor is not None and \
            self.camera is not None


    def apertureChanged(self, *args):
        # will trigger minidiffReady signal for update of beam size in video
        self.equipmentReady()
         

    def equipmentReady(self):
        self.emit('minidiffReady', ())


    def equipmentNotReady(self):
        self.emit('minidiffNotReady', ())


    def wagoLightStateChanged(self,state):
        pass


    def phiMotorStateChanged(self,state):
        self.emit('phiMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))


    def phizMotorStateChanged(self, state):
        self.emit('phizMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))


    def phiyMotorStateChanged(self, state):
        self.emit('phiyMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))


    def getCalibrationData(self, offset):
        return self.get_pixels_per_mm()
        if self.zoomMotor is not None:
            if self.zoomMotor.hasObject('positions'):
                for position in self.zoomMotor['positions']:
                    if position.offset == offset:
                        calibrationData = position['calibrationData']
                        return (float(calibrationData.pixelsPerMmY) or 0, float(calibrationData.pixelsPerMmZ) or 0)
        return (None, None)


    def zoomMotorPredefinedPositionChanged(self, positionName, offset):
        self.pixelsPerMmY, self.pixelsPerMmZ = self.get_pixels_per_mm() # self.getCalibrationData(offset)
        self.emit('zoomMotorPredefinedPositionChanged', (positionName, offset, ))


    def zoomMotorStateChanged(self, state):
        self.emit('zoomMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))


    def sampleXMotorStateChanged(self, state):
        self.emit('sampxMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))


    def sampleYMotorStateChanged(self, state):
        self.emit('sampyMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))


    def invalidateCentring(self):
        logging.info("Invalidating centring manualCentringProcedure is %s", str(self.currentCentringProcedure) )
        if self.currentCentringProcedure is None and self.centringStatus["valid"]:
            self.centringStatus={"valid":False}
            self.emitProgressMessage("")
            self.emit('centringInvalid', ())


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

    def getBeamPosX(self):
        return self.md2.BeamPositionHorizontal

    def getBeamPosY(self):
        return self.md2.BeamPositionVertical
    
    def getState(self):
        motors = ['Omega', 'AlignmentX', 'AlignmentY', 'AlignmentZ', 'CentringX', 'CentringY', 'ApertureHorizontal', 'ApertureVertical', 'CapillaryHorizontal', 'CapillaryVertical', 'ScintillatorHorizontal', 'ScintillatorVertical']
        state = set([self.getMotorState(m) for m in motors])
        if len(state) == 1 and 'STANDBY' in state:
            return 'STANDBY'
        else:
            return 'MOVING'
        
    def getOmegaState(self):
        return self.md2.getMotorState('Omega').name
        
    def getMotorState(self, motor_name):
        return self.md2.getMotorState(motor_name).name
        
    def get_pixels_per_mm(self):
        return 1.0/self.md2.CoaxCamScaleX, 1.0/self.md2.CoaxCamScaleY
        
    def getBeamInfo(self, update_beam_callback):
        #get_beam_info = self.getCommandObject("getBeamInfo")
        #get_beam_info(callback=update_beam_callback, error_callback=None, wait=True)
        d = {}
        d["size_x"] = 0.010
        d["size_y"] = 0.005
        d["shape"] = "rectangular"
        self.beamSizeX = 0.010
        self.beamSizeY = 0.005
        self.beamShape = "rectangular"
        return d
       
    def sendGonioToCollect(self, oscrange, npass, exptime):
        logging.info("MiniDiffPX2 / send gonio to collect oscrange=%s npass=%s exptime=%s" % (oscrange,npass, exptime) )
        if self.md2_ready:

            diffstate = self.getState()
            logging.info("SOLEILCollect - setting gonio ready (state: %s)" % diffstate)

            #self.md2.write_attribute('ScanAnticipation', self.anticipation)
            self.md2.write_attribute('ScanNumberOfPasses', npass)
            self.md2.write_attribute('ScanRange', oscrange)
            self.md2.write_attribute('ScanExposureTime', exptime)
            logging.info("SOLEILCollect - setting the collect phase position %s" % self.collect_phaseposition)
            logging.info("SOLEILCollect - current phase %s" % self.md2.currentphase)
            logging.info("SOLEILCollect - current phase index %s" % self.md2.currentphaseindex)
            if self.md2.currentphase != self.collect_phaseposition:
                logging.getLogger("user_level_log").info("Setting gonio to data collection phase.")
                self.md2.startsetphase(self.collect_phaseposition)
            else:
                self.md2.backlightison=False
              
    def verifyGonioInCollect(self):
        while self.md2.currentphase != self.collect_phaseposition:
            time.sleep(0.1)
        logging.getLogger("user_level_log").info("Capillary beamstop in the beam path, starting to collect.")
              
    def goniometerReady(self, oscrange, npass, exptime):
       logging.info("MiniDiffPX2 / programming gonio oscrange=%s npass=%s exptime=%s" % (oscrange,npass, exptime) )

       if self.md2_ready:

          diffstate = self.getState()
          logging.info("SOLEILCollect - setting gonio ready (state: %s)" % diffstate)

          #self.md2.write_attribute('ScanAnticipation', self.anticipation)
          self.md2.write_attribute('ScanNumberOfPasses', npass)
          self.md2.write_attribute('ScanRange', oscrange)
          self.md2.write_attribute('ScanExposureTime', exptime)
          logging.info("SOLEILCollect - setting the collect phase position %s" % self.collect_phaseposition)
          logging.info("SOLEILCollect - current phase %s" % self.md2.currentphase)
          logging.info("SOLEILCollect - current phase index %s" % self.md2.currentphaseindex)
          if self.md2.currentphase != self.collect_phaseposition:
              logging.getLogger("user_level_log").info("Setting gonio to data collection phase.")
              logging.getLogger("user_level_log").info("Moving capillary beamstop to the beam path, collect will start in 25 seconds.")
              self.md2.startsetphase(self.collect_phaseposition)
              while self.md2.currentphase != self.collect_phaseposition:
                time.sleep(0.1)
              logging.getLogger("user_level_log").info("Capillary beamstop in the beam path, starting to collect.")
          else:
              self.md2.backlightison=False
          
    def wait(self):
        logging.info("MiniDiffPX2 wait" )
        #while device.state().name in ['MOVING', 'RUNNING']:
        while self.getState() in ['MOVING', 'RUNNING'] or self.getOmegaState() in ['MOVING']:
            logging.info("MiniDiffPX2 wait" )
            time.sleep(.1)
            
    def setScanStartAngle(self, sangle):
        logging.info("MiniDiffPX2 / setting start angle to %s ", sangle )
        #if self.md2_ready:

        executed = False
        while executed is False:
            try:
                self.wait()
                logging.info("MiniDiffPX2 state %s " % self.md2.State() )
                self.md2.write_attribute("ScanStartAngle", sangle )
                executed = True
            except Exception, e:
                print e
                logging.info('Problem writing ScanStartAngle command')
                logging.info('Exception ' + str(e))
    
    def startScan(self, wait=True):
        logging.info("MiniDiffPX2 / starting scan " )
        start = time.time()
        if self.md2_ready:
            diffstate = self.getState()
            logging.info("SOLEILCollect - diffractometer scan started  (state: %s)" % diffstate)
            
        executed = False
        while executed is False:
            try:
                self.wait()
                self.md2.command_inout('startScan')
                #self.wait()
                executed = True
                logging.info('Successfully executing StartScan command')
            except Exception, e:
                executed = False
                print e
                os.system('echo $(date) error executing StartScan command >> /927bis/ccd/collectErrors.log')
                logging.info('Problem executing StartScan command')
                logging.info('Exception ' + str(e))
                
        
        while self.md2.fastshutterisopen is False and self.md2.lasttaskinfo[3] == 'null':
            logging.info('Successfully executing StartScan command, waiting for fast shutter to open or scan to finish')
            time.sleep(0.05)
        
        while self.md2.fastshutterisopen is True and self.md2.lasttaskinfo[3] == 'null':
            logging.info('Successfully executing StartScan command, waiting for fast shutter to close or scan to finish')
            time.sleep(0.05)
            
        #while self.md2.lasttaskinfo[3] is 'null':
            #logging.info('Successfully executing StartScan command, waiting for scan to finish')
            #time.sleep(0.05)
        #while self.md2.fastshutterisopen is False and time.time() - start < self.md2.scanexposuretime:
            #time.sleep(0.02)
        ##time.sleep(self.md2.scanexposuretime)
        #while self.md2.fastshutterisopen is True:
            #logging.info('Successfully executing StartScan command, waiting for fast shutter to close')
            #time.sleep(0.02)
        logging.info("MiniDiffPX2 Scan took %s seconds "  % str(time.time() - start))
        return
    
    def moveToBeam(self, x, y):
        try:
            beam_xc = self.getBeamPosX()
            beam_yc = self.getBeamPosY()
            self.phizMotor.moveRelative((y-beam_yc)/float(self.pixelsPerMmZ))
            self.phiyMotor.moveRelative((x-beam_xc)/float(self.pixelsPerMmY))
        except:
            logging.getLogger("HWR").exception("MiniDiff: could not center to beam, aborting")


    def getAvailableCentringMethods(self):
        return self.centringMethods.keys()


    def startCentringMethod(self,method,sample_info=None):
        logging.getLogger("HWR").exception("MiniDiffPX2: starting the centring method")
        if self.currentCentringMethod is not None:
            logging.getLogger("HWR").error("MiniDiff: already in centring method %s" % self.currentCentringMethod)
            return
        
        curr_time=time.strftime("%Y-%m-%d %H:%M:%S")
        self.centringStatus={"valid":False, "startTime":curr_time}

        self.emitCentringStarted(method)

        try:
            fun=self.centringMethods[method]
        except KeyError,diag:
            logging.getLogger("HWR").error("MiniDiff: unknown centring method (%s)" % str(diag))
            self.emitCentringFailed()
        else:
            try:
                fun(sample_info)
            except:
                logging.getLogger("HWR").exception("MiniDiff: problem while centring")
                self.emitCentringFailed()


    def cancelCentringMethod(self,reject=False):
        if self.currentCentringProcedure is not None:
            try:
                self.currentCentringProcedure.kill()
            except:
                logging.getLogger("HWR").exception("MiniDiff: problem aborting the centring method")
            try:
                fun=self.cancelCentringMethods[self.currentCentringMethod]
            except KeyError,diag:
                self.emitCentringFailed()
            else:
                try:
                    fun()
                except:
                    self.emitCentringFailed()
        else:
            self.emitCentringFailed()

        self.emitProgressMessage("")

        if reject:
            self.rejectCentring()


    def currentCentringMethod(self):
        return self.currentCentringMethod


    def start3ClickCentring(self, sample_info=None):
        logging.getLogger("HWR").exception("MiniDiffPX2: starting the 3 click centring")
        self.currentCentringProcedure = sample_centring.start({"phi":self.centringPhi,
                                                               "phiy":self.centringPhiy,
                                                               "sampx": self.centringSamplex,
                                                               "sampy": self.centringSampley,
                                                               "phiz": self.centringPhiz }, 
                                                              self.pixelsPerMmY, self.pixelsPerMmZ, 
                                                              self.getBeamPosX(), self.getBeamPosY(), chi_angle=0.0)
                                                                         
        self.currentCentringProcedure.link(self.manualCentringDone)

  
    def motor_positions_to_screen(self, centred_positions_dict):
        self.pixelsPerMmY, self.pixelsPerMmZ = self.get_pixels_per_mm() #getCalibrationData(self.zoomMotor.getPosition())
        phi_angle = math.radians(self.centringPhi.direction*self.phiMotor.getPosition()) 
        sampx = self.centringSamplex.direction * (centred_positions_dict["sampx"]-self.sampleXMotor.getPosition())
        sampy = self.centringSampley.direction * (centred_positions_dict["sampy"]-self.sampleYMotor.getPosition())
        phiy = self.centringPhiy.direction * (centred_positions_dict["phiy"]-self.phiyMotor.getPosition())
        phiz = self.centringPhiz.direction * (centred_positions_dict["phiz"]-self.phizMotor.getPosition())
        rotMatrix = numpy.matrix([math.cos(phi_angle), -math.sin(phi_angle), math.sin(phi_angle), math.cos(phi_angle)])
        rotMatrix.shape = (2, 2)
        invRotMatrix = numpy.array(rotMatrix.I)
        dx, dy = numpy.dot(numpy.array([sampx, sampy]), invRotMatrix)*self.pixelsPerMmY
        beam_pos_x = self.getBeamPosX()
        beam_pos_y = self.getBeamPosY()

        x = (phiy * self.pixelsPerMmY) + beam_pos_x
        y = dy + (phiz * self.pixelsPerMmZ) + beam_pos_y

        return x, y
 
    def manualCentringDone(self, manual_centring_procedure):
        try:
          motor_pos = manual_centring_procedure.get()
          if isinstance(motor_pos, gevent.GreenletExit):
            raise motor_pos
        except:
          logging.exception("Could not complete manual centring")
          self.emitCentringFailed()
        else:
          self.emitProgressMessage("Moving sample to centred position...")
          self.emitCentringMoving()
          try:
            sample_centring.end()
          except:
            import traceback
            logging.exception("Could not move to centred position")
            logging.debug( traceback.format_exc() )
            self.emitCentringFailed()
          self.centredTime = time.time()
          self.emitProgressMessage("    - moved to centred position finished")
          self.emitCentringSuccessful()
          self.emitProgressMessage("")

    def autoCentringDone(self, auto_centring_procedure): 
        self.emitProgressMessage("")
        self.emit("newAutomaticCentringPoint", (-1,-1))

        res = auto_centring_procedure.get()
        
        if isinstance(res, gevent.GreenletExit):
          logging.error("Could not complete automatic centring")
          self.emitCentringFailed()
        else:
          positions = self.zoomMotor.getPredefinedPositionsList()
          i = len(positions) / 2
          self.zoomMotor.moveToPosition(positions[i-1])

          #be sure zoom stop moving
          while self.zoomMotor.motorIsMoving():
              time.sleep(0.1)

          self.pixelsPerMmY, self.pixelsPerMmZ = self.get_pixels_per_mm() # .self.getCalibrationData(self.zoomMotor.getPosition())

          if self.user_confirms_centring:
            self.emitCentringSuccessful()
          else:
            self.emitCentringSuccessful()
            self.acceptCentring()
              
    def startAutoCentring(self, sample_info=None, loop_only=False):
        self.currentCentringProcedure = sample_centring.start_auto(self.camera, 
                                                                   {"phi":self.centringPhi,
                                                                    "phiy":self.centringPhiy,
                                                                    "sampx": self.centringSamplex,
                                                                    "sampy": self.centringSampley,
                                                                    "phiz": self.centringPhiz },
                                                                   self.pixelsPerMmY, self.pixelsPerMmZ, 
                                                                   self.getBeamPosX(), self.getBeamPosY(), 
                                                                   msg_cb=self.emitProgressMessage,
                                                                   new_point_cb=lambda point: self.emit("newAutomaticCentringPoint", point))
       
        self.currentCentringProcedure.link(self.autoCentringDone)

	self.emitProgressMessage("Starting automatic centring procedure...")
       
    @task 
    def moveToCentredPosition(self, centred_position):
      motor_position_dict = { self.sampleXMotor: centred_position.sampx,
                              self.sampleYMotor: centred_position.sampy,
                              self.phiMotor: centred_position.phi,
                              self.phiyMotor: centred_position.phiy,
                              self.phizMotor: centred_position.phiz }
      return sample_centring.move_motors(motor_position_dict)

    def imageClicked(self, x, y, xi, yi):
        sample_centring.user_click(x,y)

    def emitCentringStarted(self,method):
        self.currentCentringMethod=method
        self.emit('centringStarted', (method,False))

    def acceptCentring(self):
        self.centringStatus["valid"]=True
        self.centringStatus["accepted"]=True
        self.emit('centringAccepted', (True,self.getCentringStatus()))

    def rejectCentring(self):
        if self.currentCentringProcedure:
          self.currentCentringProcedure.kill()
        self.centringStatus={"valid":False}
        self.emitProgressMessage("")
        self.emit('centringAccepted', (False,self.getCentringStatus()))

    def emitCentringMoving(self):
        self.emit('centringMoving', ())

    def emitCentringFailed(self):
        self.centringStatus={"valid":False}
        method=self.currentCentringMethod
        self.currentCentringMethod = None
        self.currentCentringProcedure=None
        self.emit('centringFailed', (method,self.getCentringStatus()))

    def emitCentringSuccessful(self):
        if self.currentCentringProcedure is not None:
            curr_time=time.strftime("%Y-%m-%d %H:%M:%S")
            self.centringStatus["endTime"]=curr_time
            self.centringStatus["motors"]=self.getPositions()
            centred_pos = self.currentCentringProcedure.get()
            for role in self.centringStatus["motors"].iterkeys():
              motor = self.getDeviceByRole(role)
              try:
                self.centringStatus["motors"][role] = centred_pos[motor]
              except KeyError:
		continue
            self.centringStatus["method"]=self.currentCentringMethod
            self.centringStatus["valid"]=True
            
            method=self.currentCentringMethod
            self.emit('centringSuccessful', (method,self.getCentringStatus()))
            self.currentCentringMethod = None
            self.currentCentringProcedure = None
        else:
            logging.getLogger("HWR").debug("MiniDiff: trying to emit centringSuccessful outside of a centring")


    def emitProgressMessage(self,msg=None):
        #logging.getLogger("HWR").debug("%s: %s", self.name(), msg)
        self.emit('progressMessage', (msg,))


    def getCentringStatus(self):
        return copy.deepcopy(self.centringStatus)


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


    def takeSnapshots(self, wait=False):
        self.camera.forceUpdate = True
        
        # try:
        #     centring_valid=self.centringStatus["valid"]
        # except:
        #     centring_valid=False
        # if not centring_valid:
        #     logging.getLogger("HWR").error("MiniDiff: you must centre the crystal before taking the snapshots")
        # else:
        snapshotsProcedure = gevent.spawn(take_snapshots, 
                                          self.lightWago, 
                                          self.lightMotor,
                                          self.phiMotor, 
                                          self.zoomMotor, 
                                          self._drawing)
        self.emit('centringSnapshots', (None,))
        self.emitProgressMessage("Taking snapshots")
        self.centringStatus["images"]=[]
        snapshotsProcedure.link(self.snapshotsDone)

        if wait:
          self.centringStatus["images"] = snapshotsProcedure.get()

 
    def snapshotsDone(self, snapshotsProcedure):
        self.camera.forceUpdate = False
        
        try:
           self.centringStatus["images"] = snapshotsProcedure.get()
        except:
           logging.getLogger("HWR").exception("MiniDiff: could not take crystal snapshots")
           self.emit('centringSnapshots', (False,))
           self.emitProgressMessage("")
        else:
           self.emit('centringSnapshots', (True,))
           self.emitProgressMessage("")
        self.emitProgressMessage("Sample is centred!")
        #self.emit('centringAccepted', (True,self.getCentringStatus()))

    def simulateAutoCentring(self,sample_info=None):
        pass
    
    def beamPositionCheck(self):
        logging.getLogger("HWR").info("Going to check the beam position at all zooms")
        logging.getLogger("user_level_log").info("Starting beam position check for all zooms")
        gevent.spawn(self.bpc)
    
    def bpc(self):
        calib = calibrator.calibrator(fresh=True, save=True)
        logging.getLogger("user_level_log").info("Adjusting camera exposure time for visualisation on the scintillator")
        calib.prepare()
        logging.getLogger("user_level_log").info("Calculating beam position for individual zooms")
        for zoom in calib.zooms:
            logging.getLogger("user_level_log").info("Zoom %s" % zoom)
            calibrator.main(calib, zoom)
            
        logging.getLogger("user_level_log").info("Saving results into database")
        calib.updateMD2BeamPositions()
        logging.getLogger("user_level_log").info("Setting camera exposure time back to 0.050 seconds")
        calib.tidy()
        diff = calib.get_difference_zoom_10()
        logging.getLogger("user_level_log").info("The beam moved %s um horizontally and %s um vertically since the last calibration" % (str(round(diff[0],1)), str(round(diff[1],1))) )
        
        calib.saveSnap()
        
        logging.getLogger("user_level_log").info("Beam position check finished")
        
    def apertureAlign(self):
        logging.getLogger("HWR").info("Going to realign the current aperture")
        logging.getLogger("user_level_log").info("Aligning the current aperture")
        gevent.spawn(self.aa)
        
    def aa(self):
        logging.getLogger("user_level_log").info("Adjusting camera exposure time for visualisation on the scintillator")
        a = scan_and_align.scan_and_align('aperture', display=False)
        logging.getLogger("user_level_log").info("Scanning the aperture")
        a.scan()
        a.align(optimum='com')
        a.save_scan()
        logging.getLogger("user_level_log").info("Setting camera exposure time back to 0.050 seconds")
        logging.getLogger("user_level_log").info("Aligning aperture finished")
        a.predict()
