import gevent
from gevent.event import AsyncResult
from Qub.Tools import QubImageSave
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository.TaskUtils import *
import Image
import tempfile
import logging
import numpy
import math
import os
import time
from HardwareRepository import HardwareRepository
import copy
try:
  import lucid
except ImportError:
  logging.warning("lucid cannot load: automatic centring is disabled")


USER_CLICKED_EVENT = AsyncResult()


def manual_centring(phi, phiy, phiz, sampx, sampy, pixelsPerMmY, pixelsPerMmZ, imgWidth, imgHeight, phiy_direction=1):
  global USER_CLICKED_EVENT
  X, Y = [], []
  centredPosRel = {}

  if all([x.isReady() for x in (phi, phiy, phiz, sampx, sampy)]):
    phiSavedPosition = phi.getPosition()
    phiSavedDialPosition = phi.getDialPosition()
  else:
    raise RuntimeError, "motors not ready"

  try:  
    while True:
      USER_CLICKED_EVENT = AsyncResult()
      x, y = USER_CLICKED_EVENT.get()
      X.append(x)
      Y.append(y)
      if len(X) == 3:
        break
      phi.moveRelative(90)

    beam_xc = imgWidth / 2
    beam_yc = imgHeight / 2
    yc = (Y[0]+Y[2]) / 2
    y =  Y[0] - yc
    x =  yc - Y[1]
    b1 = -math.radians(phiSavedDialPosition)
    rotMatrix = numpy.matrix([math.cos(b1), -math.sin(b1), math.sin(b1), math.cos(b1)])
    rotMatrix.shape = (2,2)
    dx, dy = numpy.dot(numpy.array([x,y]), numpy.array(rotMatrix))/pixelsPerMmY 

    beam_xc_real = beam_xc / float(pixelsPerMmY)
    beam_yc_real = beam_yc / float(pixelsPerMmZ)
    y = yc / float(pixelsPerMmZ)
    x = sum(X) / 3.0 / float(pixelsPerMmY)
    centredPos = { sampx: sampx.getPosition() + float(dx),
                   sampy: sampy.getPosition() + float(dy),
                   phiy: phiy.getPosition() + phiy_direction * (x - beam_xc_real),
                   phiz: phiz.getPosition() + (y - beam_yc_real) }
    return centredPos
  except:
    phi.move(phiSavedPosition)    
    raise


@task
def move_to_centred_position(centred_pos):  
  for motor, pos in centred_pos.iteritems():
    motor.move(pos)

  with gevent.Timeout(15):
    while not all([m.getState() == m.READY for m in centred_pos.iterkeys()]):
      time.sleep(0.1)


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

      if light_level:
        light_motor.move(light_level)

    while light.getWagoState()!="in":
      time.sleep(0.5)
  for i in range(4):
     logging.getLogger("HWR").info("MiniDiff: taking snapshot #%d", i+1)
     centredImages.append((phi.getPosition(),str(myimage(drawing))))
     phi.syncMoveRelative(-90)

  centredImages.reverse() # snapshot order must be according to positive rotation direction

  return centredImages


class MiniDiff(Equipment):
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

        self.connect(self, 'equipmentReady', self.equipmentReady)
        self.connect(self, 'equipmentNotReady', self.equipmentNotReady)     


    def init(self):
        self.phiy_direction = 1
        
        self.centringMethods={MiniDiff.MANUAL3CLICK_MODE: self.start3ClickCentring,\
            MiniDiff.C3D_MODE: self.startAutoCentring }
        self.cancelCentringMethods={}

        self.currentCentringProcedure = None
        self.currentCentringMethod = None

        self.centringStatus={"valid":False}

        self.phiMotor = self.getDeviceByRole('phi')
        self.phizMotor = self.getDeviceByRole('phiz')
        self.phiyMotor = self.getDeviceByRole('phiy')
        self.zoomMotor = self.getDeviceByRole('zoom')
        self.lightMotor = self.getDeviceByRole('light')
        self.focusMotor = self.getDeviceByRole('focus')
        self.sampleXMotor = self.getDeviceByRole('sampx')
        self.sampleYMotor = self.getDeviceByRole('sampy')
        self.camera = self.getDeviceByRole('camera')
        self.kappaMotor = self.getDeviceByRole('kappa')
        self.kappaPhiMotor = self.getDeviceByRole('kappa_phi')

        # mh 2013-11-05:why is the channel read directly? disabled for the moment
        # self.camera.addChannel({ 'type': 'tango', 'name': 'jpegImage' }, "JpegImage")

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
            logging.getLogger("HWR").error('MiniDiff: sampx motor is not defined in minidiff equipment %s', str(self.name()))
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
 
#         try:
#           self.auto_loop_centring = self.getChannelObject("auto_centring_flag")
#         except KeyError:
#           logging.getLogger("HWR").warning("MiniDiff: automatic loop centring will not auto start after SC loading")
#         else:
#           self.auto_loop_centring.connectSignal("update", self.do_auto_loop_centring)

    def setSampleInfo(self, sample_info):
        self.currentSampleInfo = sample_info

    def emitDiffractometerMoved(self, *args):
      self.emit("diffractometerMoved", ())
        
#     def do_auto_loop_centring(self, n, old={"n":None}):
#         if n == old["n"]: 
#           return
#         old["n"]=n
#         if n < 0:
#           return

#         # this is a terrible hack... we have to know if we are running within mxCuBE
#         # with automatic centring brick, otherwise we should not start auto loop centring
#         # (for example: if we have been imported in Automatic Centring server, or in
#         # mxCuBE hutch version with no automatic centring brick...) 
#         from qt import QApplication
#         continue_auto_centring = False
#         for w in QApplication.allWidgets():
#           if callable(w.name) and str(w.name()) == 'autocentring':
#             continue_auto_centring = w.isInstanceModeMaster()
#             break
#         if not continue_auto_centring:
#           return

#         try:
#               if self.currentCentringProcedure is not None:
#                 return

#               if str(self.getChannelObject("auto_crystal_centring_enabled").getValue())=='1':
#                 loop_only=False
#               else:
#                 loop_only=True
#               if loop_only and str(self.getChannelObject("auto_loop_centring_enabled").getValue())=='0':
#                 return
#               if str(self.getChannelObject("playback_centring_enabled").getValue())=='1':
#                 sample_info=self.currentSampleInfo
#               else:
#                 sample_info=None

#               self.emitCentringStarted(MiniDiff.C3D_MODE)
#               self.startAutoCentring(sample_info=sample_info, loop_only=loop_only)
#         except:  
#            logging.getLogger("HWR").warning("MiniDiff: automatic centring fails to start (hint: is the centring server running?)")


    def isReady(self):
      if self.isValid():
         motorsQuiet = True 
   
         for m in (self.sampleXMotor, self.sampleYMotor, self.zoomMotor, self.phiMotor, self.phizMotor, self.phiyMotor):
            if m.motorIsMoving():
                 motorsQuiet = False
   
         return motorsQuiet
      else:
         return False

      #return self.isValid() and all([not m.motorIsMoving() for m in (self.sampleXMotor, self.sampleYMotor, self.zoomMotor, self.phiMotor, self.phizMotor, self.phiyMotor)])
    

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
        if self.zoomMotor is not None:
            if self.zoomMotor.hasObject('positions'):
                for position in self.zoomMotor['positions']:
                    if position.offset == offset:
                        calibrationData = position['calibrationData']
                        return (float(calibrationData.pixelsPerMmY) or 0, float(calibrationData.pixelsPerMmZ) or 0)
        return (None, None)


    def zoomMotorPredefinedPositionChanged(self, positionName, offset):
        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(offset)
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
        if self.currentCentringProcedure is None and self.centringStatus["valid"]:
            self.centringStatus={"valid":False}
            self.emitProgressMessage("")
            self.emit('centringInvalid', ())


    def phizMotorMoved(self, pos):
        if time.time() - self.centredTime > 1.0:
          self.invalidateCentring()

    def phiyMotorMoved(self, pos):
        if time.time() - self.centredTime > 1.0:
           self.invalidateCentring()


    def sampleXMotorMoved(self, pos):
        if time.time() - self.centredTime > 1.0:
           self.invalidateCentring()


    def sampleYMotorMoved(self, pos):
        if time.time() - self.centredTime > 1.0:
           self.invalidateCentring()


    def sampleChangerSampleIsLoaded(self, state):
        if time.time() - self.centredTime > 1.0:
           self.invalidateCentring()


    def moveToBeam(self, x, y):
        try:
            self.phizMotor.moveRelative((y-(self.imgHeight/2))/float(self.pixelsPerMmZ))
            self.phiyMotor.moveRelative((x-(self.imgWidth/2))/float(self.pixelsPerMmY))
        except:
            logging.getLogger("HWR").exception("MiniDiff: could not center to beam, aborting")


    def getAvailableCentringMethods(self):
        return self.centringMethods.keys()


    def startCentringMethod(self,method,sample_info=None):
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
        self.currentCentringProcedure = gevent.spawn(manual_centring, 
                                                     self.phiMotor,
                                                     self.phiyMotor,
                                                     self.phizMotor,
                                                     self.sampleXMotor,
                                                     self.sampleYMotor,
                                                     self.pixelsPerMmY,
                                                     self.pixelsPerMmZ,
                                                     self.imgWidth,
                                                     self.imgHeight,
                                                     self.phiy_direction)
         
        self.currentCentringProcedure.link(self.manualCentringDone)

  
    def motor_positions_to_screen(self, centred_positions_dict):
        self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(self.zoomMotor.getPosition())
        phi_angle = math.radians(-self.phiMotor.getPosition()) #centred_positions_dict["phi"])
        #logging.info("CENTRED POS DICT = %r", centred_positions_dict)
        sampx = centred_positions_dict["sampx"]-self.sampleXMotor.getPosition()
        sampy = centred_positions_dict["sampy"]-self.sampleYMotor.getPosition()
        phiy = self.phiy_direction * (centred_positions_dict["phiy"]-self.phiyMotor.getPosition())
        #logging.info("phiy move = %f", centred_positions_dict["phiy"]-self.phiyMotor.getPosition())
        phiz = centred_positions_dict["phiz"]-self.phizMotor.getPosition()
        #logging.info("sampx=%f, sampy=%f, phiy=%f, phiz=%f, phi=%f", sampx, sampy, phiy, phiz, phi_angle)
        rotMatrix = numpy.matrix([math.cos(phi_angle), -math.sin(phi_angle), math.sin(phi_angle), math.cos(phi_angle)])
        rotMatrix.shape = (2, 2)
        invRotMatrix = numpy.array(rotMatrix.I)
        dx, dy = numpy.dot(numpy.array([sampx, sampy]), invRotMatrix)*self.pixelsPerMmY
        beam_pos_x = self.imgWidth / 2
        beam_pos_y = self.imgHeight / 2

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
            move_to_centred_position(motor_pos, wait = True)
          except:
            logging.exception("Could not move to centred position")
            self.emitCentringFailed()
          else:
            self.phiMotor.syncMoveRelative(-180)
          #logging.info("EMITTING CENTRING SUCCESSFUL")
          self.centredTime = time.time()
          self.emitCentringSuccessful()
          self.emitProgressMessage("")


    def moveToCentredPosition(self, centred_position, wait = False):
      try:
        motor_pos = {self.sampleXMotor: centred_position.sampx,
                     self.sampleYMotor: centred_position.sampy,
                     self.phiMotor: centred_position.phi,
                     self.phiyMotor: centred_position.phiy,
                     self.phizMotor: centred_position.phiz}

        return move_to_centred_position(motor_pos, wait=wait)
      except:
        logging.exception("Could not move to centred position")


    def autoCentringDone(self, auto_centring_procedure):
        self.emitProgressMessage("")
        self.emit("newAutomaticCentringPoint", (-1,-1))
        
        res = auto_centring_procedure.get()

        if isinstance(res, gevent.GreenletExit):
          logging.error("Could not complete automatic centring")
          self.emitCentringFailed()
        else:
          self.emitCentringSuccessful()
              

    def do_auto_centring(self, phi, phiy, phiz, sampx, sampy, zoom, camera, phiy_direction):
        if not lucid:
          return

        imgWidth = camera.getWidth()
        imgHeight = camera.getHeight()

        def find_loop(pixels_per_mm_horizontal, show_point=True):
          #img_array = numpy.fromstring(camera.getChannelObject("image").getValue(), numpy.uint8)
          rgbImgChan    = camera.addChannel({ 'type': 'tango', 'name': 'rgbimage', "read_as_str": 1 }, "RgbImage")
          raw_data = rgbImgChan.getValue()
          snapshot_filename = os.path.join(tempfile.gettempdir(), "mxcube_sample_snapshot.png")
          Image.fromstring("RGB", (imgWidth, imgHeight), raw_data).save(snapshot_filename)

          info, x, y = lucid.find_loop(snapshot_filename, pixels_per_mm_horizontal=pixels_per_mm_horizontal)
          
          self.emitProgressMessage("Loop found: %s (%d, %d)" % (info, x, y))
          logging.debug("Loop found: %s (%d, %d)" % (info, x, y))
          if show_point:
              self.emit("newAutomaticCentringPoint", (x,y))
          return x,y
        
        def centre_loop(pixelsPerMmY, pixelsPerMmZ): #, lastCoord=(-1, -1)):
          X = []
          Y = []
          phiSavedDialPosition = phi.getDialPosition()
         
          self.emitProgressMessage("Doing automatic centring")
          a = 0
          for angle in (0, 90, 90):
            a+=1
            self.emitProgressMessage("%d: moving at angle %f" % (a, phi.getPosition()+angle))
            phi.syncMoveRelative(angle)
            x, y = find_loop(pixelsPerMmY) 
            if x < 0 or y < 0:
              for i in range(1,5):
                logging.debug("loop not found - moving back") 
                phi.syncMoveRelative(-20)
                x, y = find_loop(pixelsPerMmY)
                if x >=0:
                  if y < imgHeight/2:
                    y = 0
                    self.emit("newAutomaticCentringPoint", (x,y))
                    X.append(x); Y.append(y)
                    break
                  else:
                    y = imgHeight
                    self.emit("newAutomaticCentringPoint", (x,y))
                    X.append(x); Y.append(y)
                    break
                if i == 4:
                  if X and Y:
                    logging.debug("loop not found - trying with last coordinates")
                    self.emit("newAutomaticCentringPoint", (X[-1],Y[-1]))
                    X.append(X[-1]); Y.append(Y[-1])
                  else:
                    # should never happen in normal conditions!
                    return
              phi.syncMoveRelative(i*20)
            else:
              X.append(x); Y.append(y)
              
          beam_xc = imgWidth / 2
          beam_yc = imgHeight / 2
          yc = (Y[0]+Y[2]) / 2
          y =  Y[0] - yc
          x =  yc - Y[1]
          b1 = -math.radians(phiSavedDialPosition)
          rotMatrix = numpy.matrix([math.cos(b1), -math.sin(b1), math.sin(b1), math.cos(b1)])
          rotMatrix.shape = (2,2)
          dx, dy = numpy.dot(numpy.array([x,y]), numpy.array(rotMatrix))/pixelsPerMmY

          beam_xc_real = beam_xc / float(pixelsPerMmY)
          beam_yc_real = beam_yc / float(pixelsPerMmZ)
          y = yc / float(pixelsPerMmZ)
          x = sum(X) / 3.0 / float(pixelsPerMmY)
          centredPos = { sampx: sampx.getPosition() + float(dx),
                         sampy: sampy.getPosition() + float(dy),
                         phiy: phiy.getPosition() + phiy_direction * (x - beam_xc_real),
                         phiz: phiz.getPosition() + (y - beam_yc_real) }
          return centredPos

        def check_centring(pixels_per_mm_horizontal):
          centring_results = []
          lastCoord = [] 
          for angle in (0,-90,-90):
            phi.syncMoveRelative(angle)
            self.emit("newAutomaticCentringPoint", (-1,-1))
            logging.debug("checking centring at angle %d", phi.getPosition())
            x, y = find_loop(pixels_per_mm_horizontal)
            lastCoord.append((x,y))
            centring_results.append(x > imgWidth*0.35 and x < imgWidth*0.65 and y > imgHeight*0.35 and y < imgHeight*0.65)
            logging.debug("  centring is %s", "ok" if centring_results[-1] else "bad")
          
          return all(centring_results),lastCoord
         
 
        #check if loop is there at the beginning
        i = 0
        while -1 in find_loop(self.pixelsPerMmY):
          phi.syncMoveRelative(90)
          i+=1
          if i>4:
            return
        lastCoord = []
        centred = True #False
        for i in range(2): #was 4
          motor_pos = centre_loop(self.pixelsPerMmY, self.pixelsPerMmZ)
          move_to_centred_position(motor_pos)
          #checked,lastCoord = check_centring()
          #if not checked:
          #  continue
          #else:
          #  centred = True
          #  break

        if centred:
          # move zoom
          self.emit("newAutomaticCentringPoint", (-1,-1))
          positions = zoom.getPredefinedPositionsList()
          i = len(positions) / 2
          zoom.moveToPosition(positions[i-1])

          #be sure zoom stop moving
          while zoom.motorIsMoving():
              time.sleep(0.1)

          self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(zoom.getPosition())

          # last centring
          #motor_pos = centre_loop(self.pixelsPerMmY, self.pixelsPerMmZ) 
          #move_to_centred_position(motor_pos)         
 
          return motor_pos

    def startAutoCentring(self,sample_info=None, loop_only=False):
        self.currentCentringProcedure = gevent.spawn(self.do_auto_centring, self.phiMotor,
                                                     self.phiyMotor,
                                                     self.phizMotor,
                                                     self.sampleXMotor,
                                                     self.sampleYMotor,
                                                     self.zoomMotor,
                                                     self.camera,
                                                     self.phiy_direction)
        self.currentCentringProcedure.link(self.autoCentringDone)
	self.emitProgressMessage("Starting automatic centring procedure...")
        

    def imageClicked(self, x, y, xi, yi):
        USER_CLICKED_EVENT.set((x,y))


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

            motors = {}
            motor_pos = self.currentCentringProcedure.get()
            for motor_role in ('phiy', 'phiz', 'sampx', 'sampy', 'zoom', 'phi', 'focus', 'kappa', 'kappa_phi'):
                mot_obj = self.getDeviceByRole(motor_role)

                try:
                    motors[motor_role] = motor_pos[mot_obj] 
                except KeyError:
                    motors[motor_role] = mot_obj.getPosition()
            self.centringStatus["motors"]=motors
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
               "kappa": self.kappaMotor.getPosition(),
               "kappa_phi": self.kappaPhiMotor.getPosition(),
               "zoom": self.zoomMotor.getPosition()}
    

    def takeSnapshots(self, wait=False):
        self.camera.forceUpdate = True
        
        # try:
        #     centring_valid=self.centringStatus["valid"]
        # except:
        #     centring_valid=False
        # if not centring_valid:
        #     logging.getLogger("HWR").error("MiniDiff: you must centre the crystal before taking the snapshots")
        # else:
        snapshotsProcedure = gevent.spawn(take_snapshots, self.lightWago, self.lightMotor ,self.phiMotor,self.zoomMotor,self._drawing)
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
