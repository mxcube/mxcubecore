import gevent
from gevent.event import AsyncResult

import numpy
import math
import logging, time
from MiniDiff import MiniDiff, myimage
from HardwareRepository import HardwareRepository


#from MiniDiff import MiniDiff, manual_centring
import PyTango
from HardwareRepository.TaskUtils import *
USER_CLICKED_EVENT = AsyncResult()


def manual_centring(phi, phiy, phiz, sampx, sampy, pixelsPerMmY, pixelsPerMmZ,
                    beam_xc, beam_yc, kappa, omega, phiy_direction=1):
  logging.info("MiniDiffPX1: Starting manual_centring now")
  global USER_CLICKED_EVENT
  X, Y, PHI = [], [], []
  centredPosRel = {}

  if all([x.isReady() for x in (phi, phiy, phiz, sampx, sampy)]):
    phiSavedPosition = phi.getPosition()
    #phiSavedDialPosition = phi.getDialPosition()
    phiSavedDialPosition = 327.3
    logging.info("MiniDiff phi saved dial = %f " % phiSavedDialPosition)
  else:
    logging.info("phi is ready = %s " % str(phi.isReady()))
    logging.info("phiy is ready = %s " % str(phiy.isReady()))
    logging.info("phiz is ready = %s " % str(phiz.isReady()))
    logging.info("sampx is ready = %s " % str(sampx.isReady()))
    logging.info("sampy is ready = %s " % str(sampy.isReady()))
    raise RuntimeError, "motors not ready"
  
  kappa.move(0)
  omega.move(0)
  try:  
    while True:
      USER_CLICKED_EVENT = AsyncResult()
      x, y = USER_CLICKED_EVENT.get()
      X.append(x)
      Y.append(y)
      PHI.append(phi.getPosition())
      if len(X) == 3:
        break
      phi.moveRelative(60)

    # 2014-01-19-bessy-mh: variable beam position coordinates are passed as parameters
    #beam_xc = imgWidth / 2
    #beam_yc = imgHeight / 2

    (dx1,dy1,dx2,dy2,dx3,dy3)=(X[0] - beam_xc, Y[0] - beam_yc,
                               X[1] - beam_xc, Y[1] - beam_yc,
                               X[2] - beam_xc, Y[2] - beam_yc)
    #resolution d equation
    #print "angle1 = %4.1f  angle2 = %4.1f   angle3 = %4.1f " % \
    #                  (self.anglePhi[0], self.anglePhi[1], self.anglePhi[2])
    PhiCamera=90

    #yc = (Y[0]+Y[2]) / 2.
    #y =  Y[0] - yc
    #x =  yc - Y[1]
    print "MANUAL_CENTRING:", X, Y, pixelsPerMmY, pixelsPerMmZ, beam_xc, beam_yc
    #b1 = -math.radians(phiSavedDialPosition)
    #b1 = -math.radians(phiSavedPosition - phiSavedDialPosition)
    #rotMatrix = numpy.matrix([math.cos(b1), -math.sin(b1), math.sin(b1), math.cos(b1)])
    #rotMatrix.shape = (2,2)
    #dx, dy = numpy.dot(numpy.array([x,y]), numpy.array(rotMatrix))/pixelsPerMmY 

    a1=math.radians(PHI[0]+PhiCamera)
    a2=math.radians(PHI[1]+PhiCamera)
    a3=math.radians(PHI[2]+PhiCamera)
    p01=(dy1*math.sin(a2)-dy2*math.sin(a1))/math.sin(a2-a1)        
    q01=(dy1*math.cos(a2)-dy2*math.cos(a1))/math.sin(a1-a2)
    p02=(dy1*math.sin(a3)-dy3*math.sin(a1))/math.sin(a3-a1)        
    q02=(dy1*math.cos(a3)-dy3*math.cos(a1))/math.sin(a1-a3)
    p03=(dy3*math.sin(a2)-dy2*math.sin(a3))/math.sin(a2-a3)        
    q03=(dy3*math.cos(a2)-dy2*math.cos(a3))/math.sin(a3-a2)
    #print "p01 = %6.3f  q01 = %6.3f  p02 = %6.3f  q02 = %6.3f  p03 = %6.3f  q03 = %6.3f  " %(p01,q01,p02,q02,p03,q03)

    x_echantillon=(p01+p02+p03)/3.0
    y_echantillon=(q01+q02+q03)/3.0
    z_echantillon=(-dx1-dx2-dx3)/3.0
    print "Microglide X = %d :    Y = %d :    Z = %d : " %(x_echantillon,y_echantillon,z_echantillon)
        
    x_echantillon_real=1000.*x_echantillon/pixelsPerMmY
    y_echantillon_real=1000.*y_echantillon/pixelsPerMmY
    z_echantillon_real=1000.*z_echantillon/pixelsPerMmY

    #beam_xc_real = beam_xc / float(pixelsPerMmY)
    #beam_yc_real = beam_yc / float(pixelsPerMmZ)
    #y = yc / float(pixelsPerMmZ)
    #x = sum(X) / 3.0 / float(pixelsPerMmY)
    #centredPos = { sampx: sampx.getPosition() + float(dx),
    #               sampy: sampy.getPosition() + float(dy),
    #               phiy: phiy.getPosition() + phiy_direction * (x - beam_xc_real),
    #               phiz: phiz.getPosition() + (y - beam_yc_real) }
    if (z_echantillon_real + phiy.getPosition() < phiy.getLimits()[0]) :
        logging.getLogger("HWR").error("loop too long")
        print 'loop too long '
        centredPos = {}
        phi.move(phiSavedPosition)            
    else :    
        print 'loop Ok '
        centredPos= { sampx: x_echantillon_real,
                      sampy: y_echantillon_real,
                      phiy: z_echantillon_real}
    print 'Fin procedure de centrage'
    print "   sampx: %.1f" % x_echantillon_real
    print "   sampy: %.1f" % y_echantillon_real
    print "   phiy:  %.1f" % z_echantillon_real
    #try:
    #    sampx.move(x_echantillon_real)
    #    sampy.move(y_echantillon_real)
    #    phiy.move(z_echantillon_real)
    #except:
    #    raise
    return centredPos
  except:
    phi.move(phiSavedPosition)    
    raise

@task
def move_to_centred_position(centred_pos):
  logging.getLogger("HWR").info("move_to_centred_position")
  pos_to_go = []
  for motor, pos in centred_pos.iteritems():
    #print "AAA motor:", motor.name(), " pos:", pos #, dir(motor)
    pos_to_go.append(pos)
    if motor.name() in ["/uglidex", "/uglidey"]:
        #print "--->",  motor.name(), motor.getCommandNamesList()
        moveXYZ = motor.getCommandObject("moveRelativeXYZ")        
  print "POS_TO_GO: %8.2f %8.2f %8.2f" % tuple(pos_to_go)
  moveXYZ(pos_to_go)

  with gevent.Timeout(15):
    while not all([m.getState() == m.READY for m in centred_pos.iterkeys()]):
      time.sleep(0.1)



class MiniDiffPX1(MiniDiff):

   def __init__(self,*args):
       MiniDiff.__init__(self, *args)
   
   def _init(self,*args):
       MiniDiff._init(self, *args)

       bs_prop=self.getProperty("bstop")
       self.bstop_ho = None
       logging.getLogger().info("MiniDiffPX1.  Loading %s as beamstop " % str(bs_prop))

       if bs_prop is not None:
            try:
                self.bstop_ho=HardwareRepository.HardwareRepository().getHardwareObject(bs_prop)
            except:
                import traceback
                logging.getLogger().info("MiniDiffPX1.  Cannot load beamstop %s" % str(bs_prop))
                logging.getLogger().info("    - reason: " + traceback.format_exc())

       #la_prop=self.getProperty("lightarm")
       #self.ligharm_ho = None
       #logging.getLogger().info("MiniDiffPX1.  Loading %s as lightarm " % str(la_prop))
#
#       if la_prop is not None:
#            try:
#                self.lightarm_ho=HardwareRepository.HardwareRepository().getHardwareObject(la_prop)
#            except:
#                import traceback
##                logging.getLogger().info("MiniDiffPX1.  Cannot load lightarm %s" % str(la_prop))
#                logging.getLogger().info("    - reason: " + traceback.format_exc())


       # some defaults
       self.anticipation  = 1
       self.collect_phaseposition = 4
       self.beamPositionX = 0
       self.beamPositionY = 0
       self.beamSizeX = 0
       self.beamSizeY = 0
       self.beam_xc = 0
       self.beam_yc = 0
       self.beamShape = "rectangular"

       #print "phi_is_moving", self.phiMotor.motorIsMoving()
       #print "phi_position", self.phiMotor.getPosition()

   def prepareForAcquisition(self):
       if self.beamstopIn() == -1:
           raise Exception("Minidiff cannot get to acquisition mode")
       #self.guillotineOut()

   def beamstopIn(self):
       if self.bstop_ho is not None:
          self.bstop_ho.moveIn()
          return 0
       else:
          return -1

   def beamstopOut(self):
       if self.bstop_ho is not None:
          self.bstop_ho.moveOut()
          return 0
       else:
          return -1
   def guillotineIn(self):
       pass
   def guillotineOut(self):
       pass

   def getState(self):
       logging.info("XX1 getState")
       print "phi_position", self.phiMotor.getPosition()
       return "STANDBY"

   def getBeamInfo(self, callback=None, error_callback=None):
      logging.info("AA1: getBeamInfo in MiniDiffPX1.py ")
      #print "ZOOM_MOTOR2", self.zoomMotor["positions"][0].offset
      d = {}
      d["size_x"] = 0.100
      d["size_y"] = 0.100
      d["shape"] = "rectangular"
      self.beamSizeX = 0.100
      self.beamSizeY = 0.100
      self.beamShape = "rectangular"
      return d
      #callback( d )

   def getBeamPosX(self):
        return self.beam_xc

   def getBeamPosY(self):
        return self.beam_yc

   def get_pixels_per_mm(self):
       return (self.calib_x or 0, self.calib_y or 0)

   def getCalibrationData(self, offset):
       logging.info("XX1: getCalibration, OFFSET: %s", offset)

       if self.lightMotor is None or self.lightMotor.positionChan.device is None:
           logging.info("XX1: getCalibration, Not yet initialized")
           return (None,None)

       if self.zoomMotor is not None:
           if self.zoomMotor.hasObject('positions'):
               for position in self.zoomMotor['positions']:
                   if position.offset == offset:
                       calibrationData = position['calibrationData']
                       self.calib_x = float(calibrationData.pixelsPerMmY)
                       self.calib_y = float(calibrationData.pixelsPerMmZ)
                       self.beam_xc = float(calibrationData.beamPositionX)
                       self.beam_yc = float(calibrationData.beamPositionY)
                       self.light_level = float(position.lightLevel)
                       self.lightMotor.move(self.light_level)
                       print "CALIBR:", (self.calib_x, self.calib_y)
                       print "BEAMXY:", (self.beam_xc, self.beam_yc)
                       return (self.calib_x or 0, self.calib_y or 0)

       return (None, None)

   def motor_positions_to_screen(self, centred_positions_dict):

       self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(self.zoomMotor.getPosition())
       logging.info("motor pos to screen. Y=%s / Z=%s / zoom=%s" % (self.pixelsPerMmY, self.pixelsPerMmZ, self.zoomMotor.getPosition()))
       phi_angle = math.radians(-self.phiMotor.getPosition()) #centred_positions_dict["phi"])
       #logging.info("CENTRED POS DICT = %r", centred_positions_dict)
       sampx = centred_positions_dict["sampx"]-self.sampleXMotor.getPosition()
       sampy = centred_positions_dict["sampy"]-self.sampleYMotor.getPosition()
       phiy = self.phiy_direction * (centred_positions_dict["phiy"]-self.phiyMotor.getPosition())
       logging.info("phiy move = %f", centred_positions_dict["phiy"]-self.phiyMotor.getPosition())
       phiz = centred_positions_dict["phiz"]-self.phizMotor.getPosition()
       #logging.info("sampx=%f, sampy=%f, phiy=%f, phiz=%f, phi=%f", sampx, sampy, phiy, phiz, phi_angle)
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
        logging.info("manual centring DONE")
        try:
          motor_pos = manual_centring_procedure.get()
          if isinstance(motor_pos, gevent.GreenletExit):
            raise motor_pos
        except:
          logging.exception("Could not complete manual centring")
          self.emitCentringFailed()
        else:
          logging.info("Moving sample to centred position")
          self.emitProgressMessage("Moving sample to centred position...")
          self.emitCentringMoving()
          try:
            move_to_centred_position(motor_pos, wait = True)
          except:
            logging.exception("Could not move to centred position")
            self.emitCentringFailed()
          else:
            self.phiMotor.syncMoveRelative(-180)
          logging.info("EMITTING CENTRING SUCCESSFUL")
          self.centredTime = time.time()
          self.emitCentringSuccessful()
          self.emitProgressMessage("")

   def zoomMotorPredefinedPositionChanged(self, positionName, offset):
       logging.info("XX1: zoomMotorPredefinedPositionChanged, OFFSET: %s", offset)       
       self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData(offset)
       #self.beamPositionX, self.beamPositionY = self.getBeamPosition(offset)
       self.emit('zoomMotorPredefinedPositionChanged', (positionName, offset, ))

   def start3ClickCentring(self, sample_info=None):
       self.currentCentringProcedure = gevent.spawn(manual_centring, 
                                                    self.phiMotor,
                                                    self.phiyMotor,
                                                    self.phizMotor,
                                                    self.sampleXMotor,
                                                    self.sampleYMotor,
                                                    self.pixelsPerMmY,
                                                    self.pixelsPerMmZ,
                                                    self.getBeamPosX(),
                                                    self.getBeamPosY(),
                                                    self.kappaMotor,
                                                    self.kappaPhiMotor,
                                                    self.phiy_direction)     
       self.currentCentringProcedure.link(self.manualCentringDone)

   def imageClicked(self, x, y, xi, yi):
       USER_CLICKED_EVENT.set((x,y))

   def getPositions(self):
      return { "phi": self.phiMotor.getPosition(),
               "phiy": self.phiyMotor.getPosition(),
               "phiz": self.phizMotor.getPosition(),
               "sampx": self.sampleXMotor.getPosition(),
               "sampy": self.sampleYMotor.getPosition(),
               "kappa": self.kappaMotor.getPosition(),
               "zoom": self.zoomMotor.getPosition()}
               #"focus": self.focusMotor.getPosition(),         
               #"kappa_phi": self.kappaPhiMotor.getPosition(),

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

def take_snapshots(light, light_motor, phi, zoom, drawing):

  centredImages = []

  logging.getLogger("HWR").info("PX1 take snapshots")

  if light is not None:

    logging.getLogger("HWR").info("take snapshots:  putting the light in")
    light.wagoIn()

    zoom_level  = zoom.getPosition()
    light_level = light_motor.getPosition()
    logging.getLogger("HWR").info("take snapshots:  zoom level is %s / light level is %s" % (str(zoom_level), str(light_level)))

    # No light level, choose default
    if light_motor.getPosition() == 0:

       light_level = None

       logging.getLogger().info("take snapshots: looking for default light level for this zoom ")
       for position in zoom['positions']:
          try:
              offset = position.offset
              logging.getLogger().info("take snapshots: zoom-level is: %s / comparing with table position: %s " % (str(zoom_level), str(offset)))
              if int(offset) == int(zoom_level):
                 light_level = position['ligthLevel']
                 logging.getLogger().info("take snapshots - light level for zoom position %s is %s" % (str(zoom_level),str(light_level)))
          except IndexError:
              pass

       if light_level:
          light_motor.move(light_level)

    t0 = time.time(); timeout = 5

    while light.getWagoState() != "in":
      time.sleep(0.5)
      if (time.time() - t0) > timeout:
          raise Exception("SnapshotException","Timeout while inserting light")

  for i in range(4):
     logging.getLogger("HWR").info("MiniDiff: taking snapshot #%d", i+1)
     centredImages.append((phi.getPosition(),str(myimage(drawing))))
     if i < 3:
        phi.syncMoveRelative(-90)
     time.sleep(2)
  #phi.syncMoveRelative(270)

  centredImages.reverse() # snapshot order must be according to positive rotation direction

  return centredImages

