# -*- coding: utf-8 -*-
from qt import *
from Qub.Tools import QubImageSave
from HardwareRepository.BaseHardwareObjects import Equipment
import tempfile
import logging
import math
import os
import time
from HardwareRepository import HardwareRepository
from HardwareRepository import EnhancedPopen
import copy
import PyTango


### End of update of calibration data
bp = PyTango.DeviceProxy('i11-ma-cx1/ex/md2-beamposition')

cData = {
         '1':{'username': '1', 'offset': 1, 'focus_offset': -0.0819, 'lightLevel': 20, 'calibrationData': {'pixelsPerMmY': 293, 'pixelsPerMmZ': 292, 'beamPositionX': 329, 'beamPositionY': 238} },
         '2':{'username': '2', 'offset': 2, 'focus_offset': -0.0903, 'lightLevel': 20, 'calibrationData': {'pixelsPerMmY': 345, 'pixelsPerMmZ': 345, 'beamPositionX': 328, 'beamPositionY': 236} },
         '3':{'username': '3', 'offset': 3, 'focus_offset': -0.1020, 'lightLevel': 20, 'calibrationData': {'pixelsPerMmY': 453, 'pixelsPerMmZ': 454, 'beamPositionX': 326, 'beamPositionY': 233} },
         '4':{'username': '4', 'offset': 4, 'focus_offset': -0.1092, 'lightLevel': 20, 'calibrationData': {'pixelsPerMmY': 606, 'pixelsPerMmZ': 600, 'beamPositionX': 323, 'beamPositionY': 232} },
         '5':{'username': '5', 'offset': 5, 'focus_offset': -0.1098, 'lightLevel': 40, 'calibrationData': {'pixelsPerMmY': 787, 'pixelsPerMmZ': 788, 'beamPositionX': 319, 'beamPositionY': 228} },
         '6':{'username': '6', 'offset': 6, 'focus_offset': -0.1165, 'lightLevel': 40, 'calibrationData': {'pixelsPerMmY': 1033, 'pixelsPerMmZ': 1031, 'beamPositionX': 314, 'beamPositionY': 224} },
         '7':{'username': '7', 'offset': 7, 'focus_offset': -0.1185, 'lightLevel': 40, 'calibrationData': {'pixelsPerMmY': 1349, 'pixelsPerMmZ': 1351, 'beamPositionX': 306, 'beamPositionY': 217} },
         '8':{'username': '8', 'offset': 8, 'focus_offset': -0.1230, 'lightLevel': 50, 'calibrationData': {'pixelsPerMmY': 1776, 'pixelsPerMmZ': 1776, 'beamPositionX': 289, 'beamPositionY': 209} },
         '9':{'username': '9', 'offset': 9, 'focus_offset': -0.1213, 'lightLevel': 50, 'calibrationData': {'pixelsPerMmY': 2309, 'pixelsPerMmZ': 2315, 'beamPositionX': 289, 'beamPositionY': 197} },
         '10':{'username': '10', 'offset': 10, 'focus_offset':-0.1230, 'lightLevel': 50, 'calibrationData': {'pixelsPerMmY': 2890, 'pixelsPerMmZ': 2899, 'beamPositionX': 278, 'beamPositionY': 185} }
         }

def getNewCalibration():
    print 'Reading beam position calibration data'
    for zoom in cData:
        cData[zoom]['calibrationData']['beamPositionX'] = bp.read_attribute('Zoom' + zoom + '_X').value
        cData[zoom]['calibrationData']['beamPositionY'] = bp.read_attribute('Zoom' + zoom + '_Z').value

getNewCalibration()


class ProcedureIterator:
    def __init__(self, *args, **kw):
        self.procedureIterator = None
        if self.__initProcedure__(*args, **kw):
            self.__abortFlag = False
        else:
            self.__abortFlag = True
            
    def __initProcedure__(self, *args, **kw):
        """Init should return True or False depending if the initializationgetCalibrationData
        is ok or not ; if it is not ok, calling 'next()' will raise a StopIteration exception.
        __abortProcedure__ will *not* be called.
        """             
        return True
        
    def __procedure__(self):
        "Trivial generator, to be overridden in subclasses"
        yield None
        
    def __abortProcedure__(self):
        pass
    
    def next(self):
        if self.__abortFlag:
            raise StopIteration
        else:
            if self.procedureIterator is None:
               self.procedureIterator = self.__procedure__()
            return self.procedureIterator.next()
            
    def abort(self):
        self.__abortProcedure__()
        self.__abortFlag = True
        
    def stop(self):
        self.__stopProcedure__()
        
    def __stopProcedure__(self):
        pass


class ManualCentringProcedure(ProcedureIterator):
    def __initProcedure__(self, phi, phiy, phiz, sampx, sampy, pixelsPerMmY, pixelsPerMmZ, imgWidth, imgHeight, minidiff): #adding minidiff to the parameter list
        self.phi = phi
        self.phiy = phiy #phiy
        self.phiz = phiz #phiz
        self.sampx = sampx #sampx
        self.sampy = sampy #sampy
        #self.pixelsPerMmY = pixelsPerMmY
        #self.pixelsPerMmZ = pixelsPerMmZ
        #self.minidiff = minidiff
        #beam_xc = beamPositionX
        #beam_yc = beamPositionY
        #MS 14.02.2013 changing read of calibration data
        #(self.pixelsPerMmY, self.pixelsPerMmZ, self.beamPositionX, self.beamPositionY)
        self.pixelsPerMmY, self.pixelsPerMmZ, self.beam_xc, self.beam_yc = minidiff.getCalibrationData3(minidiff.md2.ZoomLevel)
        self.PhiReference = 327.3
        print 
        print 'MS debug 13.11.2011 pixelsPerMmY', self.pixelsPerMmY
        print 'MS debug 13.11.2011 pixelsPerMmZ', self.pixelsPerMmZ
        print 'MS debug 13.11.2011 beamCenterX', self.beam_xc
        print 'MS debug 13.11.2011 beamCenterY', self.beam_yc
        #self.imgWidth = imgWidth
        #self.imgHeight = imgHeight
        #print 'MS debug 13.11.2011 self.imgWidth', self.imgWidth
        #print 'MS debug 13.11.2011 self.imgHeight', self.imgHeight
        print
        
        self.X = []
        self.Y = []
        self.centredPosRel = {}
        print
        print 'M.S. 23.10.2012, ManualCentringProcedure __initProcedure__'
        if phi.isReady() and phiy.isReady() and phiz.isReady() and sampx.isReady() and sampy.isReady():
            self.phiSavedPosition = self.phi.getPosition()
            return True
        else:
            return False
        
        
    def __procedure__(self):
        while len(self.X) < 3:
            self.phi.moveRelative(90) #MS 2013-07-06: 90 -> 1. for chip centering
            yield None
        print 'Debug 15.11.2012  ManualCentringProcedure(ProcedureIterator)'
        print self.X
        print self.Y
        print self.phiSavedPosition, type(self.phiSavedPosition)
        print 'self.pixelsPerMmY', self.pixelsPerMmY, 1000./self.pixelsPerMmY
        print 'self.pixelsPerMmZ', self.pixelsPerMmZ, 1000./self.pixelsPerMmZ
        print
        
        yc = (self.Y[0]+self.Y[2]) /2
        y =  self.Y[0] - yc
        x =  yc  - self.Y[1]
        
        b1   = math.radians(self.phiSavedPosition - self.PhiReference)
        #b1   = math.radians(self.phiSavedPosition)
        
        dx = (x*math.cos(b1) - y*math.sin(b1)) / self.pixelsPerMmY
        dy = (x*math.sin(b1) + y*math.cos(b1)) / self.pixelsPerMmY
        #Testing adding calibrated values for zoom 5
        #beam_xc = 308 #314. #self.imgWidth / 2
        #beam_yc = 173 #243. #self.imgHeight / 2
        beam_xc_real = self.beam_xc / float(self.pixelsPerMmY)
        beam_yc_real = self.beam_yc / float(self.pixelsPerMmZ)
        y = yc / float(self.pixelsPerMmZ)
        x = sum(self.X) / 3.0 / float(self.pixelsPerMmY)
        logging.getLogger().info("scale %f %f", float(self.pixelsPerMmY), float(self.pixelsPerMmZ))
        logging.getLogger().info("dx dy %f %f %f", dx, dy, (x-beam_xc_real))
        
        self.centredPosRel={self.sampx: self.sampx.getPosition()+dx,\
                            self.sampy: self.sampy.getPosition()+dy,\
                            self.phiy: self.phiy.getPosition()-(x-beam_xc_real),\
                            self.phiz: self.phiz.getPosition()+y-beam_yc_real}


    def __abortProcedure__(self):
        self.centredPosRel = {}
        try:
            self.phi.move(self.phiSavedPosition)
        except:
            pass
        
    def addPoint(self, x, y):
        self.X.append(x)
        self.Y.append(y)
        return len(self.X)
        
    def getCentredPosition(self):
        return self.centredPosRel


class MoveToBeamCentringProcedure(ProcedureIterator):
    def __initProcedure__(self, phi, phiy, phiz, sampx, sampy):
        self.phi = phi
        self.phiy = phiy
        self.phiz = phiz
        self.sampx = sampx
        self.sampy = sampy
        self.shouldStop = False

        if phiy.isReady() and phiz.isReady() and sampx.isReady() and sampy.isReady():
            self.phiySavedPosition = self.phiy.getPosition()
            self.phizSavedPosition = self.phiz.getPosition()
            self.sampxSavedPosition = self.sampx.getPosition()
            self.sampySavedPosition = self.sampy.getPosition()

    def __procedure__(self):
        while not self.shouldStop:
            yield None

    def __abortProcedure__(self):
        try:
            self.phiy.move(self.phiySavedPosition)
            self.phiz.move(self.phizSavedPosition)
            self.sampx.move(self.sampxSavedPosition)
            self.sampy.move(self.sampySavedPosition)
        except:
            pass

    def __stopProcedure__(self):
        self.shouldStop=True
        return self.next()

    def getCentredPosition(self):
        return { self.sampx: self.sampx.getPosition(),
                 self.sampy: self.sampy.getPosition(),
                 self.phiy: self.phiy.getPosition(),
                 self.phiz: self.phiz.getPosition() }


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
    """
    def save(self, filename, imgtype):
        logging.getLogger("HWR").info("Microdiff: saving snapshot %s" % filename)
        f = open(filename, "w")
        f.write(self.imgcopy)
        f.close()
    """
    
    def __str__(self):
        return self.imgcopy


class TakeSnapshotsProcedure(ProcedureIterator):
    def __initProcedure__(self,light,phi,zoom,drawing):
        self.light = light
        self.phi = phi
        self.zoom = zoom
        self.drawing = drawing
        self.centredImages = []
        return True
        
    def __procedure__(self):
        if self.light is not None:
            if self.light.getWagoState()!="in":
                self.light.wagoIn()
                while self.light.getWagoState()!="in":
                    qApp.processEvents()
                curr_zoom=self.zoom.getPosition()
                if curr_zoom>1.0:
                    self.zoom.syncMoveRelative(-1.0)
                else:
                    self.zoom.syncMoveRelative(+1.0)
                self.zoom.syncMove(curr_zoom)
        for i in range(4):
            logging.getLogger("HWR").info("Microdiff: taking snapshot #%d", i+1)
            self.centredImages.append((self.phi.getPosition(),self.getSnapshot()))
            self.phi.syncMoveRelative(-90) #MS 2013-07-06: 90 -> 5 for chip centering
            yield None
        self.centredImages.reverse() # snapshot order must be according to positive rotation direction
        
    def getSnapshot(self):
        return str(myimage(self.drawing))
        
    def __abortProcedure__(self):
        self.centredImages = []
        
    def getCentredImages(self):
        return self.centredImages


class AutoCentringProcedure:
    def __init__(self, search_cmd, abort_cmd, message_chan, error_chan, minidiff_ho, sample_info, centringSuccessful=None, progressMessage=None, centringFailed=None, loopCentringOnly=False):
        #logging.getLogger("HWR").debug(" %s %s" % (hwr_address, minidiff_ho))
        self.__centringSuccessful = centringSuccessful
        self.__progressMessage = progressMessage
        self.__centringFailed = centringFailed
        self.minidiff_ho = minidiff_ho
        self.success = False
        self.search_cmd=search_cmd
        self.abort_cmd=abort_cmd
        self.loop_centring_only = loopCentringOnly
        self.minidiff_ho.KappaIsEnabled = False
        message_chan.connectSignal("update", self.__messageReceived)

        try:
            blsampleid=int(sample_info["blsampleid"])
        except:
            blsampleid=None
        search_cmd(repr({ "blsampleid": blsampleid, "loopcentringonly": loopCentringOnly}))

    def abort(self):
        try:
            self.abort_cmd()
            logging.getLogger("HWR").info("Closing automatic centring script (PID: %d)", self.script.pid)
            #os.kill(self.script.pid, 9)
        except:
            pass 

    def __messageReceived(self, msg):
        if msg=="Tango message":
          return

        if len(msg)>10:
            sub=msg[:10]
            kind=sub.strip()
            msg=msg[10:]
            
            if kind=="ERROR":
                logging.getLogger("HWR").error(msg)
                self.__progressMessage(msg)
                if callable(self.__centringFailed):
                    self.__centringFailed()
                return
            elif kind=="DEBUG":
                logging.getLogger("HWR").debug(msg)
                return
            elif kind=="WARNING":
                logging.getLogger("HWR").warning(msg)
                return
            elif kind=="SUCCESS":
                self.success = True
                if callable(self.__centringSuccessful):
                    self.__centringSuccessful()
                return

        if callable(self.__progressMessage):
           logging.getLogger("HWR").info(msg)
           self.__progressMessage(msg)

    def getCentredPosition(self):
        minidiff = self.minidiff_ho
        return { minidiff.sampleXMotor: minidiff.sampleXMotor.getPosition(),
                 minidiff.sampleYMotor: minidiff.sampleYMotor.getPosition(),
                 minidiff.phizMotor: minidiff.phizMotor.getPosition(),
                 minidiff.phiyMotor: minidiff.phiyMotor.getPosition() }


class MicrodiffPX2(Equipment):
    MANUAL3CLICK_MODE = "Manual 3-click"
    C3D_MODE = "Computer automatic"
    MOVE_TO_BEAM_MODE = "Move to Beam"

    def __init__(self, *args):
        Equipment.__init__(self, *args)
        self.NO_AUTO_LOOP_CENTRING = True
        self.phiMotor = None
        self.phizMotor = None
        self.phiyMotor = None
        self.zoomMotor = None
        self.sampleXMotor = None
        self.sampleYMotor = None
        self.camera = None
        self.sampleChanger = None
        self.lightWago = None

        self.pixelsPerMmY=1
        self.pixelsPerMmZ=1
        self.imgWidth = None
        self.imgHeight = None
        self.currentSampleInfo = None

        self.currentCentringProcedure = None
        self.currentCentringMethod = None
        self.connect(self, 'equipmentReady', self.equipmentReady)
        self.connect(self, 'equipmentNotReady', self.equipmentNotReady)     

    def init(self):
        self.centringMethods={MicrodiffPX2.MANUAL3CLICK_MODE: self.start3ClickCentring,\
            MicrodiffPX2.C3D_MODE: self.startAutoCentring, 
            MicrodiffPX2.MOVE_TO_BEAM_MODE: self.startMoveToBeamCentring }
        self.cancelCentringMethods={}
        self.flexibleMethods={MicrodiffPX2.MANUAL3CLICK_MODE:False,\
            MicrodiffPX2.C3D_MODE: False, 
            MicrodiffPX2.MOVE_TO_BEAM_MODE: True }

        #self.moveToCentredProcedure = None
        #self.snapshotsProcedure = None

        self.centringStatus={"valid":False}

        self.phiMotor = self.getDeviceByRole('phi')
        self.phizMotor = self.getDeviceByRole('phiz')
        self.phiyMotor = self.getDeviceByRole('phiy')
        self.zoomMotor = self.getDeviceByRole('zoom')
        self.lightMotor = self.getDeviceByRole('lightLevel')
        self.lightWago = self.getDeviceByRole('lightInOut')
        self.focusMotor = self.getDeviceByRole('focus')
        self.sampleXMotor = self.getDeviceByRole('sampx')
        self.sampleYMotor = self.getDeviceByRole('sampy')
        self.camera = self.getDeviceByRole('camera')
        self.md2 = PyTango.DeviceProxy('i11-ma-cx1/ex/md2') #MS 6.4.2012
        print 'MS debug 15.11.2012 MicrodiffPX2(Equipment) self.phiMotor.tangoname'
        print self.phiMotor.tangoname
        
        self.x_calib = self.addChannel({ "type":"tango", "tangoname": self.phiMotor.tangoname, "name":"x_calib", "polling": 1000 }, "CoaxCamScaleX") #, "polling":"events" }, "CoaxCamScaleX")
        #self.x_calib = self.addChannel({ "type":"tango", "tangoname": 'i11-ma-cx1/ex/md2', "name":"x_calib" }, "CoaxCamScaleX")
        self.y_calib = self.addChannel({ "type":"tango", "tangoname": self.phiMotor.tangoname, "name":"y_calib", "polling": 1000 }, "CoaxCamScaleY") #, "polling":"events" }, "CoaxCamScaleY")       
        #self.y_calib = self.addChannel({ "type":"tango", "tangoname": 'i11-ma-cx1/ex/md2', "name":"y_calib" }, "CoaxCamScaleY")
        self.x_calib.connectSignal("update", self._update_x_calib)
        self.y_calib.connectSignal("update", self._update_y_calib)
        #self.connect(self.pixelsPerMmY, "update", self._update_y_calib)
        #self.connect(self.pixelsPerMmZ, "update", self._update_x_calib)
        self.moveMultipleMotors = self.addCommand({"type":"tango", "tangoname":self.phiMotor.tangoname, "name":"move_multiple_motors" }, "SyncMoveMotors")
        sc_prop=self.getProperty("samplechanger")
        if sc_prop is not None:
            try:
                self.sampleChanger=HardwareRepository.HardwareRepository().getHardwareObject(sc_prop)
            except:
                pass

        if self.phiMotor is not None:
            self.connect(self.phiMotor, 'stateChanged', self.phiMotorStateChanged)
            self.phiMotor.motorState = 2
        else:
            logging.getLogger("HWR").error('Microdiff: phi motor is not defined in minidiff equipment %s', str(self.name()))
        if self.phizMotor is not None:
            self.connect(self.phizMotor, 'stateChanged', self.phizMotorStateChanged)
            self.connect(self.phizMotor, 'positionChanged', self.phizMotorMoved)
            self.phizMotor.motorState = 2
        else:
            logging.getLogger("HWR").error('Microdiff: phiz motor is not defined in minidiff equipment %s', str(self.name()))
        if self.phiyMotor is not None:
            self.connect(self.phiyMotor, 'stateChanged', self.phiyMotorStateChanged)
            self.connect(self.phiyMotor, 'positionChanged', self.phiyMotorMoved)
            self.phiyMotor.motorState = 2
        else:
            logging.getLogger("HWR").error('Microdiff: phiy motor is not defined in minidiff equipment %s', str(self.name()))
        if self.zoomMotor is not None:
            self.connect(self.zoomMotor, 'predefinedPositionChanged', self.zoomMotorPredefinedPositionChanged)
            self.connect(self.zoomMotor, 'stateChanged', self.zoomMotorStateChanged)
        else:
            logging.getLogger("HWR").error('Microdiff: zoom motor is not defined in minidiff equipment %s', str(self.name()))
        if self.sampleXMotor is not None:
            self.connect(self.sampleXMotor, 'stateChanged', self.sampleXMotorStateChanged)
            self.connect(self.sampleXMotor, 'positionChanged', self.sampleXMotorMoved)
            self.sampleXMotor.motorState = 2
        else:
            logging.getLogger("HWR").error('Microdiff: sampx motor is not defined in minidiff equipment %s', str(self.name()))
        if self.sampleYMotor is not None:
            self.connect(self.sampleYMotor, 'stateChanged', self.sampleYMotorStateChanged)
            self.connect(self.sampleYMotor, 'positionChanged', self.sampleYMotorMoved)
            self.sampleYMotor.motorState = 2
        else:
            logging.getLogger("HWR").error('Microdiff: sampy motor is not defined in minidiff equipment %s', str(self.name()))
        if self.camera is None:
            logging.getLogger("HWR").error('Microdiff: camera is not defined in minidiff equipment %s', str(self.name()))
        else:
            self.imgWidth, self.imgHeight = self.camera.getWidth(), self.camera.getHeight()
        if self.sampleChanger is None:
            logging.getLogger("HWR").warning('Microdiff: sample changer is not defined in minidiff equipment %s', str(self.name()))
        else:
            try:
                self.connect(self.sampleChanger, 'sampleIsLoaded', self.sampleChangerSampleIsLoaded)
            except:
                logging.getLogger("HWR").exception('Microdiff: could not connect to sample changer smart magnet')
        try:
            self.auto_loop_centring = self.getChannelObject("auto_centring_flag")
        except KeyError:
            logging.getLogger("HWR").warning("MiniDiff: automatic loop centring will not auto start after SC loading")
        else:
            self.auto_loop_centring.connectSignal("update", self.do_auto_loop_centring)

    def setSampleInfo(self, sample_info):
        self.currentSampleInfo = sample_info

    def do_auto_loop_centring(self, n):
        if n <= 0:
          return

        # this is a terrible hack... we have to know if we are running within mxCuBE
        # with automatic centring brick, otherwise we should not start auto loop centring
        # (for example: if we have been imported in Automatic Centring server, or in
        # mxCuBE hutch version with no automatic centring brick...)
        continue_auto_centring = False
        for w in QApplication.allWidgets():
          if callable(w.name) and str(w.name()) == 'autocentring':
            continue_auto_centring = w.isInstanceModeMaster()
            break
        if not continue_auto_centring:
          return

        try:
              if self.currentCentringProcedure is not None:
                return

              self.emitCentringStarted(MicrodiffPX2.C3D_MODE, False)
              if str(self.getChannelObject("auto_crystal_centring_enabled").getValue())=='1':
                loop_only=False
              else:
                loop_only=True
              if loop_only and str(self.getChannelObject("auto_loop_centring_enabled").getValue())=='0':
                return
              if str(self.getChannelObject("playback_centring_enabled").getValue())=='1':
                sample_info=self.currentSampleInfo
              else:
                sample_info=None

              self.startAutoCentring(sample_info=sample_info, loop_only=loop_only)
        except:
           logging.getLogger("HWR").warning("Microdiff: automatic centring fails to start (hint: is the centring server running?)")


    def motorsReady(self):
        print
        print 'M.S. motorsReady()',
        print 'self.sampleXMotor.getState(), self.sampleYMotor.getState(), self.zoomMotor.getState(), self.phiMotor.getState(), self.phizMotor.getState(), self.phiyMotor.getState()'
        print self.sampleXMotor.getState(), self.sampleYMotor.getState(), self.zoomMotor.getState(), self.phiMotor.getState(), self.phizMotor.getState(), self.phiyMotor.getState()
        print
        return self.sampleXMotor.getState() == self.sampleXMotor.READY and \
               self.sampleYMotor.getState() == self.sampleYMotor.READY and \
               self.zoomMotor.getState() == self.zoomMotor.READY and \
               self.phiMotor.getState() == self.phiMotor.READY and \
               self.phizMotor.getState() == self.phizMotor.READY and \
               self.phiyMotor.getState() == self.phiyMotor.READY

    def isReady(self):
        try:
          #logging.getLogger().info("sampleX: %s, sampleY: %s, zoomMotor: %s, phiMotor: %s, phizMotor: %s, phiyMotor: %s", self.sampleXMotor.getState(), self.sampleYMotor.getState(), self.zoomMotor.getState(), self.phiMotor.getState(), self.phizMotor.getState(), self.phiyMotor.getState())
          #print
          #print 'M.S. 23.10.2012, Equipment.isReady(self)', Equipment.isReady(self)
          #print 'self.motorsReady()', self.motorsReady()
          #print
          return True #Equipment.isReady(self) and self.motorsReady()
        except:
          return True

    def isValid(self):
        return self.sampleXMotor is not None and \
            self.sampleYMotor is not None and \
            self.zoomMotor is not None and \
            self.phiMotor is not None and \
            self.phizMotor is not None and \
            self.phiyMotor is not None and \
            self.camera is not None


    def equipmentReady(self):
        self.emit('minidiffReady', ())

    def equipmentNotReady(self):
        self.emit('minidiffNotReady', ())


    def phiMotorStateChanged(self,state):
        self.emit('phiMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))
        if state==self.phiMotor.READY and hasattr(self.currentCentringProcedure, "finished"):
          logging.getLogger().info("centring successful")
          self.emitCentringSuccessful()


    def phizMotorStateChanged(self, state):
        self.emit('phizMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))


    def phiyMotorStateChanged(self, state):
        self.emit('phiyMotorStateChanged', (state, ))
        self.emit('minidiffStateChanged', (state,))


    #def getCalibrationData(self, offset):
        #print
        #print '\n'*25
        #print 'MS Debug 15.11.2012 getCalibrationData'
        #print 'self.x_calib.getValue()', self.x_calib.getValue()
        #print 'self.y_calib.getValue()', self.y_calib.getValue()
        #print 'offset', offset
        #print '\n'*25
        #return (1000.0/self.x_calib.getValue(), 1000.0/self.y_calib.getValue())
    
    def getCalibrationData(self, offset):
        print
        print "MS debug 6.2.2013 getCalibrationData(), offset, type(offset)", offset, type(offset)
        if self.zoomMotor is not None:
            print "self.zoomMotor is not None"
            if self.zoomMotor.hasObject('positions'):
                print "self.zoomMotor.hasObject('positions')"
                print "self.zoomMotor['positions']", self.zoomMotor['positions']
                for position in self.zoomMotor['positions']: #['positions']:
                    print "position, type(position), position.offset: ", position, type(position)
                    print "position.getObjectByRole('offset') ", position.getObjectByRole('offset') 
                    if position.getObjectByRole('offset') == offset:
                        print "position.getObjectByRole('offset') == offset" 
                        print "I am in!"
                        calibrationData = position.getObjectByRole('calibrationData')
                        print "MS debug 1.2.13 getCalibrationData()"
                        print '(float(calibrationData.pixelsPerMmY) or 0, float(calibrationData.pixelsPerMmZ) or 0, float(calibrationData.beamPositionX) or 0, float(calibrationData.beamPositionY) or 0)'
                        print (float(calibrationData.pixelsPerMmY) or 0, float(calibrationData.pixelsPerMmZ) or 0, float(calibrationData.beamPositionX) or 0, float(calibrationData.beamPositionY) or 0)
                        self.pixelsPerMmY = float(calibrationData.pixelsPerMmY)
                        self.pixelsPerMmZ = float(calibrationData.pixelsPerMmZ)
                        self.beamPositionX = float(calibrationData.beamPositionX)
                        self.beamPositionY = float(calibrationData.beamPositionY)
                        print self.pixelsPerMmY, self.pixelsPerMmZ, self.beamPositionX, self.beamPositionY
                        print
                        return (float(calibrationData.pixelsPerMmY) or 0, float(calibrationData.pixelsPerMmZ) or 0, float(calibrationData.beamPositionX) or 0, float(calibrationData.beamPositionY) or 0)
        print "I am not in "
        print
        return (None, None, None, None)
        
    def _update_x_calib(self, value):
        #logging.getLogger().debug("new pixels per mm horizontal value=%f", 1000.0/value)
        self.pixelsPerMmY = 1000.0/self.md2.CoaxCamScaleX #value
        pass

    def _update_y_calib(self, value):
        #logging.getLogger().debug("new pixels per mm vertical value=%f", 1000.0/value)
        self.pixelsPerMmZ = 1000.0/self.md2.CoaxCamScaleY #value
        pass
    
    #def getCalibrationData2(self,position):
        #print
        #print 'MS debug 13.11.2012 getCalibrationData2()'
        #print 'position', position
        #print 'self.zoomMotor', self.zoomMotor
        #print 'self.zoomMotor.hasObject(\'positions\')', self.zoomMotor.hasObject('positions')
        #print 'self.zoomMotor[\'positions\']', self.zoomMotor['positions']
        #if self.zoomMotor is not None:
            #if self.zoomMotor.hasObject('positions'):
                #for position2 in self.zoomMotor['positions']:
                    #print 'position2.username', position2.username
                    #if position2.username == position:
                        #print 'position2[\'calibrationData\']', position2['calibrationData']  #.calibrationData     
                        #calibrationData = position2['calibrationData'] #.calibrationData #position2['calibrationData']
                        #print 'calibrationData', calibrationData
                        #print "MiniDiff calibrationData2",calibrationDa   self.pixelsPerMmZ=calibrationData.pixelsPerMmZ
                        #self.beamPositionX=calibrationData.beamPositionX
                        #self.beamPositionY=calibrationData.beamPositionY ta.pixelsPerMmY, calibrationData.pixelsPerMmZ
                        #print "MiniDiff beamPosition2",calibrationData.beamPositionX, calibrationData.beamPositionY
                        #self.pixelsPerMmY=calibrationData.pixelsPerMmY
                        #self.pixelsPerMmZ=calibrationData.pixelsPerMmZ
                        #self.beamPositionX=calibrationData.beamPositionX
                        #self.beamPositionY=calibrationData.beamPositionY
                        #print 'self.pixelsPerMmZ', self.pixelsPerMmZ
                        #print 'self.pixelsPerMmY', self.pixelsPerMmY
                        #print 
                        #return (float(self.pixelsPerMmY), float(self.pixelsPerMmZ))
        #return (None, None)
     
    def getCalibrationData3(self, position):
        position = str(position)
        #position = str(self.md2.ZoomLevel) #MS testing 
        self.pixelsPerMmY = cData[position]['calibrationData']['pixelsPerMmY']
        self.pixelsPerMmZ = cData[position]['calibrationData']['pixelsPerMmZ']
        self.beamPositionX = cData[position]['calibrationData']['beamPositionX']
        self.beamPositionY = cData[position]['calibrationData']['beamPositionY']
        return (self.pixelsPerMmY, self.pixelsPerMmZ, self.beamPositionX, self.beamPositionY)
        
    def zoomMotorPredefinedPositionChanged(self, positionName, offset):
        print 'self.md2.ZoomLevel', self.md2.ZoomLevel
        self.pixelsPerMmY, self.pixelsPerMmZ, self.beamPositionX, self.beamPositionY = self.getCalibrationData3(str(self.md2.ZoomLevel))
        #self.pixelsPerMmY, self.pixelsPerMmZ = self.getCalibrationData2(offset) #MS 13.11.2012
        positionName = str(self.md2.ZoomLevel)
        offset = cData[positionName]['offset']
        print
        print 'MS debug 13.11.2012 zoomMotorPredefinedPositionChanged(self, positionName, offset):'
        print 'positionName', positionName
        print 'offset', offset
        print 'pixelsPerMmZ', self.pixelsPerMmY
        print 'pixelsPerMmY', self.pixelsPerMmZ
        print 
        
        logging.getLogger().info("zoom motor pos. changed to %s, pixels by mm X=%f, Y=%f", positionName, self.pixelsPerMmY, self.pixelsPerMmZ)
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
        self.invalidateCentring()


    def phiyMotorMoved(self, pos):
        self.invalidateCentring()


    def sampleXMotorMoved(self, pos):
        self.invalidateCentring()


    def sampleYMotorMoved(self, pos):
        self.invalidateCentring()


    def sampleChangerSampleIsLoaded(self, state):
        self.invalidateCentring()


    def moveToBeam(self, x, y):
        try:
            self.phizMotor.moveRelative((y-(self.imgHeight/2))/float(self.pixelsPerMmZ))
            self.phiyMotor.moveRelative((x-(self.imgWidth/2))/float(self.pixelsPerMmY))
            logging.getLogger().info("move scale %f %f", float(self.pixelsPerMmZ), float(self.pixelsPerMmY))

        except:
            logging.getLogger("HWR").exception("Microdiff: could not center to beam, aborting")


    def getAvailableCentringMethods(self):
        return self.centringMethods.keys()


    def startCentringMethod(self,method,sample_info=None):
        if self.currentCentringMethod is not None:
            logging.getLogger("HWR").error("Microdiff: already in centring method %s" % self.currentCentringMethod)
            return
        #self.snapshotsProcedure = None
        
        curr_time=time.strftime("%Y-%m-%d %H:%M:%S")
        print
        print 'M.S. 23.10.2012, startCenteringMethod, curr_time', curr_time
        self.centringStatus={"valid":False, "startTime":curr_time}

        try:
            flexible=self.flexibleMethods[method]
        except KeyError:
            flexible=False
            
        
        print
        print 'M.S. 23.10.2012, startCenteringMethod, method', method
        self.emitCentringStarted(method,flexible)

        try:
            fun=self.centringMethods[method]
            print
            print 'M.S. 23.10.2012, startCenteringMethod, fun', fun
        except KeyError,diag:
            logging.getLogger("HWR").error("Microdiff: unknown centring method (%s)" % str(diag))
            self.emitCentringFailed()
        else:
            try:
                fun(sample_info)
                print
                print 'M.S. 23.10.2012, startCenteringMethod, fun(sample_info)', fun(sample_info)
                print
            except:
                logging.getLogger("HWR").exception("Microdiff: problem while centring")
                self.emitCentringFailed()


    def cancelCentringMethod(self,reject=False):
        if self.currentCentringProcedure is not None:
            try:
                self.currentCentringProcedure.abort()
            except:
                logging.getLogger("HWR").exception("Microdiff: problem aborting the centring method")
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
        self.currentCentringProcedure = ManualCentringProcedure(self.phiMotor,
                                                                self.phiyMotor,
                                                                self.phizMotor,
                                                                self.sampleXMotor,
                                                                self.sampleYMotor,
                                                                self.pixelsPerMmY,
                                                                self.pixelsPerMmZ,
                                                                self.imgWidth,
                                                                self.imgHeight, self)
        print 'M.S. 23.10.2012, self.currentCentringProcedure', self.currentCentringProcedure
        print "Click on the sample..."
        self.emitProgressMessage("Click on the sample...")


    def startMoveToBeamCentring(self,sample_info=None):
        self.currentCentringProcedure = MoveToBeamCentringProcedure(self.phiMotor,
                                                                    self.phiyMotor,
                                                                    self.phizMotor,
                                                                    self.sampleXMotor,
                                                                    self.sampleYMotor)
        self.emitProgressMessage("Click on the sample...")


    def startAutoCentring(self,sample_info=None, loop_only=False):
        # sample info is the BL sample ID for the moment (None or an integer) 
        # in the future, this could be a dictionary
        #logging.getLogger("HWR").info("in startAutoCentring")
        try:
            centring_server = self["autoCentering"].centring_server
        except:
            logging.getLogger("HWR").error("%s: no automatic centring script", self.name())
            self.cancelCentringMethod()
        else:        
            if not hasattr(self, "_search_cmd"): 
                self._search_cmd=self.addCommand({"type":"tango", "tangoname":centring_server, "name":"search" }, "Search")
                self._abort_cmd=self.addCommand({"type":"tango", "tangoname":centring_server, "name":"abort" }, "Abort")
                self._message_chan=self.addChannel({"type":"tango", "tangoname":centring_server,"name":"message", "polling":"events"}, "Message")
                self._error_chan=self.addChannel({"type":"tango", "tangoname":centring_server,"name":"error", "polling":"events"}, "Error")

            self.currentCentringProcedure = AutoCentringProcedure(self._search_cmd, self._abort_cmd, self._message_chan, self._error_chan, self, sample_info,
                                                                  centringSuccessful=self.emitCentringSuccessful,
                                                                  progressMessage=self.emitProgressMessage,
                                                                  centringFailed=self.emitCentringFailed,
                                                                  loopCentringOnly=loop_only )
            self.emitProgressMessage("Starting automatic centring procedure...")


    def imageClicked(self, x, y, xi, yi):
        print
        print 'M.S. 23.10.2012 imageClicked, hello!'
        print 'self.currentCentringMethod', self.currentCentringMethod
        print
        if self.currentCentringMethod!=MicrodiffPX2.MANUAL3CLICK_MODE:
            return
        #if self.moveToCentredProcedure is not None or self.snapshotsProcedure is not None:
        #    return
        #if self.snapshotsProcedure is not None:
        #     return       
 
        added=self.currentCentringProcedure.addPoint(x, y)

        try:
            ach = self.currentCentringProcedure.next()
        except StopIteration:
            self.emitProgressMessage("Moving sample to centred position...")
            self.emitCentringMoving()
            motor_pos=self.currentCentringProcedure.getCentredPosition()
            motor_names = [x.motor_name+x.motor_pos_attr_suffix for x in motor_pos.keys()]
            motor_pos = list(motor_pos.itervalues())
            #logging.getLogger().info("moving multiple:%s", [motor_pos,motor_names])
            self.moveMultipleMotors([motor_pos,motor_names])
            self.phiMotor.move(self.phiMotor.getPosition()-180)
            self.currentCentringProcedure.finished=True
            self.emitCentringSuccessful()
        else:
            if added==2:
                print "Click on the sample one last time..."
                self.emitProgressMessage("Click on the sample one last time...")
            else:
                print "Click on the sample again..."
                self.emitProgressMessage("Click on the sample again...")


    def emitCentringStarted(self,method,flexible):
        self.currentCentringMethod=method
        self.emit('centringStarted', (method,flexible))


    def acceptCentring(self):
        logging.getLogger("HWR").debug("Microdiff:acceptCentring")
        if self.currentCentringMethod is not None:
            try:
                flexible=self.flexibleMethods[self.currentCentringMethod]
            except KeyError:
                flexible=False
            if not flexible:
                logging.getLogger("HWR").error("Microdiff: still centring (%s), cannot accept!" % self.currentCentringMethod)
                return
            try:
                self.currentCentringProcedure.stop()
            except StopIteration:
                pass
            self.emitCentringSuccessful()

        self.centringStatus["valid"]=True
        self.centringStatus["accepted"]=True
        logging.getLogger("HWR").debug("Microdiff:acceptCentring")
        print 'self.centringStatus', self.centringStatus
        self.takeSnapshots()
        self.emitProgressMessage("Sample is centered!")
        self.emit('centringAccepted', (True, self.getCentringStatus()))


    def rejectCentring(self):
        if self.currentCentringMethod is not None:
            try:
                flexible=self.flexibleMethods[self.currentCentringMethod]
            except KeyError:
                flexible=False
            if not flexible:
                logging.getLogger("HWR").error("Microdiff: still centring (%s), cannot reject!" % self.currentCentringMethod)
                return
            try:
                self.currentCentringProcedure.abort()
            except:
                pass
            self.emitCentringFailed()

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

            motor_pos=self.currentCentringProcedure.getCentredPosition()
            #self.snapshotsProcedure=None
            motors={}
            for motor in motor_pos:
                #motor_specname=motor.specName
                motor_pos=motor.getPosition()
                #motors[motor_specname]=motor_pos
            #extra_motors={self.zoomMotor.specName:self.zoomMotor.getPosition(),\
                #self.phiMotor.specName:self.phiMotor.getPosition()}
            self.centringStatus["motors"]=motors
            #self.centringStatus["extraMotors"]=extra_motors
            self.centringStatus["method"]=self.currentCentringMethod
            self.centringStatus["valid"]=True
 
            if self.currentCentringMethod == MicrodiffPX2.C3D_MODE and self.currentCentringProcedure.loop_centring_only:
                self.emitProgressMessage("Loop pre-centring has finished. Please continue manually")
            else:
                self.emitProgressMessage("Sample centring has finished.")

            method=self.currentCentringMethod
            self.currentCentringMethod = None
            self.currentCentringProcedure = None
            logging.getLogger("HWR").info("%r", self.centringStatus)
            self.emit('centringSuccessful', (method, self.getCentringStatus()))
        else:
            logging.getLogger("HWR").debug("Microdiff: trying to emit centringSuccessful outside of a centring")


    def emitProgressMessage(self,msg=None):
        #logging.getLogger("HWR").debug("%s: %s", self.name(), msg)
        self.emit('progressMessage', (msg,))


    def getCentringStatus(self):
        #logging.getLogger().info("getcentringStatus %s", self.centringStatus)
        p = copy.deepcopy(self.centringStatus)
        return p
        

    def takeSnapshots(self):
        try:
            centring_valid=self.centringStatus["valid"]
            print 'MS 17.02.2013 takeSnapshots(), centring_valid, self.centringStatus["valid"]', self.centringStatus["valid"]
        except:
            centring_valid=False
        done=False
        if not centring_valid:
            logging.getLogger("HWR").error("Microdiff: you must center the crystal before taking the snapshots")
        else:
            #self.snapshotsProcedure = TakeSnapshotsProcedure(self.lightWago,self.phiMotor,self.zoomMotor,self._drawing)
            self.emit('centringSnapshots', (None,))
            self.emitProgressMessage("Taking snapshots")
            snapshots = []
            self.centringStatus["images"]=snapshots
            for i in range(4):
              logging.getLogger("HWR").info("Microdiff: taking snapshot #%d", i+1)
              snapshots.append((self.phiMotor.getPosition(),str(myimage(self._drawing))))
              t0=time.time()
              self.phiMotor.syncMoveRelative(-90)
              logging.getLogger().info("phi took %g ms to move", (time.time()-t0)*1000)
            snapshots.reverse() # snapshot order must be according to positive rotation direction
            print 'len(snapshots)', len(snapshots)
            done=True
            """ 
            while 1:
                try:
                    self.snapshotsProcedure.next()
                except StopIteration:
                    images=self.snapshotsProcedure.getCentredImages()
                    self.centringStatus["images"]=self.snapshotsProcedure.getCentredImages()
                    done=True
                    break
                except:
                    logging.getLogger("HWR").exception("Microdiff: could not take crystal snapshots")
                    break
             """
            if done:
                self.emit('centringSnapshots', (True,))
            else:
                self.emit('centringSnapshots', (False,))
            self.emitProgressMessage("")
        #self.snapshotsProcedure=None
        return done


    def simulateAutoCentring(self,sample_info=None):
        pass


