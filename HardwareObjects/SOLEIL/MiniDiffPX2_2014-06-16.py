# -*- coding: utf-8 -*-

import logging, time, math, numpy
from MiniDiff import MiniDiff
from gevent.event import AsyncResult
import gevent
import PyTango
import os

USER_CLICKED_EVENT = AsyncResult()

def manual_centring(phi, phiy, phiz, sampx, sampy, pixelsPerMmY, pixelsPerMmZ, beam_xc, beam_yc, phiy_direction=1):
  global USER_CLICKED_EVENT
  X, Y = [], []
  centredPosRel = {}

  logging.info("=== MANUAL CENTRING STARTED")
  if all([x.isReady() for x in (phi, phiy, phiz, sampx, sampy)]):
    phiSavedPosition = phi.getPosition()
    phiSavedDialPosition = 0. #327.3 
    #phiSavedDialPosition = phi.getDialPosition()
    #logging.info("MiniDiff phi saved dial = %f " % phiSavedDialPosition)
  else:
    raise RuntimeError, "motors not ready"

  try:  
    while True:
      USER_CLICKED_EVENT = AsyncResult()
      logging.info("=== WAITING FOR USER INPUT")
      x, y = USER_CLICKED_EVENT.get()
      X.append(x)
      Y.append(y)
      if len(X) == 3:
        break
      logging.info("=== CLICKED")
      phi.moveRelative(90)

    yc = (Y[0]+Y[2]) / 2
    y =  Y[0] - yc
    x =  yc - Y[1]
    #b1 = -math.radians(phiSavedDialPosition)
    b1 = -math.radians(phiSavedPosition - phiSavedDialPosition)
    rotMatrix = numpy.matrix([math.cos(b1), -math.sin(b1), math.sin(b1), math.cos(b1)])
    rotMatrix.shape = (2,2)
    dx, dy = numpy.dot(numpy.array([x,y]), numpy.array(rotMatrix))/pixelsPerMmZ

    beam_xc_real = beam_xc / float(pixelsPerMmY)
    beam_yc_real = beam_yc / float(pixelsPerMmZ)
    y = yc / float(pixelsPerMmZ)
    x = sum(X) / 3.0 / float(pixelsPerMmY)
    centredPos = { sampx: sampx.getPosition() + float(dx),
                   sampy: sampy.getPosition() + float(dy),
                   phiy: phiy.getPosition() + phiy_direction * (x - beam_xc_real),
                   phiz: phiz.getPosition() + (y - beam_yc_real) }
    logging.info("=== centredPos %s" % str(centredPos))
    return centredPos
  except:
    phi.move(phiSavedPosition)    
    raise

class MiniDiffPX2(MiniDiff):

    def _init(self,*args):
        MiniDiff._init(self, *args)

        self.md2_ready = False

        try:
            self.md2 = PyTango.DeviceProxy( self.tangoname )
        except:
            logging.error("MiniDiffPX2 / Cannot connect to tango device: %s ", self.tangoname )
        else:
            self.md2_ready = True

        # some defaults
        self.anticipation  = 1
        self.collect_phaseposition = 4

    def init(self):
        #self.md2          = PyTango.DeviceProxy('i11-ma-cx1/ex/md2')
        self.beamPosition = PyTango.DeviceProxy('i11-ma-cx1/ex/md2-beamposition')
        MiniDiff.init(self)
        
    def getCalibrationData(self, offset=None):
        return 1000./self.md2.CoaxCamScaleX, 1000./self.md2.CoaxCamScaleY

    def getBeamPosX(self):
        zoom = str(self.zoomMotor.getPosition())
        return self.beamPosition.read_attribute('Zoom' + zoom + '_X').value
 
    def getBeamPosY(self):
        zoom = str(self.zoomMotor.getPosition())
        return self.beamPosition.read_attribute('Zoom' + zoom + '_Z').value

    def getState(self):
        return str( self.md2.state() )

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
                                                     self.phiy_direction)

        self.currentCentringProcedure.link(self.manualCentringDone)

    def imageClicked(self, x, y, xi, yi):
        USER_CLICKED_EVENT.set((x,y))


    def wait(self, device):
        while device.state().name in ['MOVING', 'RUNNING']:
            time.sleep(.1)
    
    def setScanStartAngle(self, sangle):
        logging.info("MiniDiffPX2 / setting start angle to %s ", sangle )
        #if self.md2_ready:

        executed = False
        while executed is False:
            try:
                self.wait(self.md2)
                self.md2.write_attribute("ScanStartAngle", sangle )
                executed = True
            except Exception, e:
                print e
                logging.info('Problem writing ScanStartAngle command')
                logging.info('Exception ' + str(e))

    def startScan(self, wait=True):
        logging.info("MiniDiffPX2 / starting scan " )
        if self.md2_ready:
            diffstate = self.getState()
            logging.info("SOLEILCollect - diffractometer scan started  (state: %s)" % diffstate)
            
        executed = False
        while executed is False:
            try:
                self.wait(self.md2)
                self.md2.command_inout('StartScan')
                self.wait(self.md2)
                executed = True
                logging.info('Successfully executing StartScan command')
            except Exception, e:
                print e
                os.system('echo $(date) error executing StartScan command >> /927bis/ccd/collectErrors.log')
                logging.info('Problem executing StartScan command')
                logging.info('Exception ' + str(e))
        return
        # self.getCommandObject("start_scan")() - if we define start_scan command in *xml

    def goniometerReady(self, oscrange, npass, exptime):
       logging.info("MiniDiffPX2 / programming gonio oscrange=%s npass=%s exptime=%s" % (oscrange,npass, exptime) )

       if self.md2_ready:

          diffstate = self.getState()
          logging.info("SOLEILCollect - setting gonio ready (state: %s)" % diffstate)

          self.md2.write_attribute('ScanAnticipation', self.anticipation)
          self.md2.write_attribute('ScanNumberOfPasses', npass)
          self.md2.write_attribute('ScanRange', oscrange)
          self.md2.write_attribute('ScanExposureTime', exptime)
          self.md2.write_attribute('PhasePosition', self.collect_phaseposition)
    
    def getBeamSize(self):
        return (10, 5)

    def getBeamInfo(self, callback=None, error_callback=None):
        logging.info(" I am getBeamInfo in MiniDiffPX2.py ")
        d = {}
        d["size_x"], d["size_y"] = self.getBeamSize()
        d["shape"] = "rectangular"
        return d
    
    def beamPositionCheck(self):
        import calibrator
        calib = calibrator.calibrator(fresh=True, save=True)
        calib.prepare()
        for zoom in calib.zooms:
            calibrator.main(calib, zoom)
        calib.tidy()
        calib.updateMD2BeamPositions()
        calib.updateDatabase()
        calib.writeTxt()
        
