#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Object that integrates everything needed to perform collects on Proxima2A'''

import PyTango
import os
import sys
import re
import math
import numpy
import time
import itertools

# We badly need threading
import threading

# and logging
import logging, logging.handlers

class collect(object):
    motorsNames = ['PhiTableXAxisPosition', 
                   'PhiTableYAxisPosition', 
                   'PhiTableZAxisPosition',
                   'CentringTableXAxisPosition', 
                   'CentringTableYAxisPosition']
                   
    motorShortNames = ['PhiX', 'PhiY', 'PhiZ', 'SamX', 'SamY']
    
    shortFull = dict(zip(motorShortNames, motorsNames))
    
    def __init__(self,
                exposure = 0.5,
                oscillation = 0.5,
                passes = 1,
                start = 0.0,
                firstImage = 1,
                nImages = 1,
                Range = None,
                anticipation = 1,
                overlap = 0.0,
                directory = '/tmp/test-data',
                run = 1,
                prefix = 'F6',
                suffix = 'img',
                template = 'prefix_1_###.img',
                comment = '',
                resolution = None,
                energy = None,
                transmission = None,
                attenuation = None,
                inverse = None,
                test = True,
                grid = False,
                helical = False,
                linear = False):
        
        # Initialize all the devices that are going to be used during the collect            
        self.md2             = PyTango.DeviceProxy('i11-ma-cx1/ex/md2')
        self.publisher       = PyTango.DeviceProxy('i11-ma-cx1/ex/md2-publisher')
        self.phase           = PyTango.DeviceProxy('i11-ma-cx1/ex/md2-phase')
        self.adsc            = PyTango.DeviceProxy('i11-ma-cx1/dt/adsc')
        self.limaadsc        = PyTango.DeviceProxy('i11-ma-cx1/dt/limaadsc')
        self.header          = PyTango.DeviceProxy('i11-ma-cx1/ex/header')
        self.mono1           = PyTango.DeviceProxy('i11-ma-c03/op/mono1')
        self.detector_mt_ts  = PyTango.DeviceProxy('i11-ma-cx1/dt/dtc_ccd.1-mt_ts')
        self.detector_mt_tx  = PyTango.DeviceProxy('i11-ma-cx1/dt/dtc_ccd.1-mt_tx')
        self.detector_mt_tz  = PyTango.DeviceProxy('i11-ma-cx1/dt/dtc_ccd.1-mt_tz')
        self.obx             = PyTango.DeviceProxy('i11-ma-c04/ex/obx.1')
        self.mono_mt_rx      = PyTango.DeviceProxy('i11-ma-c03/op/mono1-mt_rx')
        self.ble             = PyTango.DeviceProxy('i11-ma-c00/ex/beamlineenergy')
        self.xbpm            = PyTango.DeviceProxy('i11-ma-c04/dt/xbpm_diode.1')
        self.pss             = PyTango.DeviceProxy('i11-ma-ce/pss/db_data-parser')
        
        # MD2 related options
        self.ScanAnticipation   = anticipation # 1
        self.ScanNumberOfPasses = passes # 1
        self.ScanRange          = oscillation # 10
        self.ScanExposureTime   = exposure # 1.0
        self.ScanStartAngle     = start #0.0
        self.ScanOverlap        = overlap
        # General collect options
        self.imagePath          = directory
        self.nImages            = nImages
        self.Range              = Range
        self.oscillation        = oscillation
        self.overlap            = overlap
        self.startAngle         = start
        self.firstImage         = firstImage
        self.suffix             = suffix
        self.prefix             = prefix
        self.inverse            = inverse
        self.template           = template
        self.energy             = energy
        self.resolution         = resolution
        self.run                = run
        
        # state variables
        self.imageNum           = None
        self.collectDone        = None
        self.stt                = None
        self.currentImageName   = None
        self.test               = test
        self.grid               = grid
        self.helical            = helical
        self.linear             = linear
        self.Stop               = False
        self.Abort              = False
        
        if self.Range != None:
            self.nbFrames = int( math.ceil( (self.Range - self.startAngle) / self.oscillation ) )
        else:
            self.nbFrames = int(self.nImages)
        
        self.totalImages = self.nbFrames   
        
        if self.inverse is not None:
            self.template_inv = template.replace('_' + str(self.run) + '_',  '_' + str(int(run) + 1) + '_')
            self.totalImages = self.nbFrames * 2
    
        self.Positions = []
        
        self.logger = logging.getLogger("collect_log")
        #self.logger.setLevel(logging.INFO)
        #ch = logging.StreamHandler() #handlers.StreamHandler()
        #ch.setLevel(logging.INFO)
        
        #formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        #ch.setFormatter(formatter)
        
        #self.logger.addHandler(ch)
        

    def state(self, stt = None):
        if stt == None:
            return self.stt
        self.stt = stt

    
    def wait(self, device):
        #self.logger.info('Waiting for ' + str(device))
        #self.logger.info(time.asctime(), str(__name__), 'INFO', 'waiting for device' + str(device))
        #print time.asctime(), str(__name__), 'INFO', 'waiting for device' + str(device)
        while device.state().name == 'MOVING':
            time.sleep(.1)
        
        while device.state().name == 'RUNNING':
            time.sleep(.1)
         
         
    def moveToPosition(self, position={}, epsilon = 0.0002):
        if position != {}:
            for motor in position:
                while abs(self.md2.read_attribute(self.shortFull[motor]).value - position[motor]) > epsilon:
                    self.wait(self.md2)
                    self.md2.write_attribute(self.shortFull[motor], position[motor])
            self.wait(self.md2)
        return
            

    def getMotorValues(self):
        position = {}
        for motor in self.motorShortNames:
            position[motor] = self.md2.read_attribute(self.shortFull[motor]).value
            
        return position
    
    def getPhiValue(self):
        return self.md2.read_attribute('PhiPosition').value
        

    def saveCurrentPosition(self):
        self.Positions.append(self.getMotorValues())

    
    def saveHelicalStart(self):
        self.helicalStart = self.getMotorValues()
    

    def saveHelicalFinal(self):
        self.helicalFinal = self.getMotorValues()


    def saveLinarStart(self):
        self.linearStart = self.getMotorValues()
        
        
    def saveLinearFinal(self):
        self.linearFinal = self.getMotorValues()
        

    def calculateHelicalOffset(self):
        start = self.helicalStart
        final = self.helicalFinal
        Phi_start = self.ScanStartAngle
        
        PhiY_range = start['PhiY'] - final['PhiY']
        helical_start = {}
        helical_final = {}
        
        helical_start['SamX'] = (start['SamX'] - final['SamX']) / PhiY_range
        helical_start['SamY'] = (start['SamY'] - final['SamY']) / PhiY_range
        helical_start['PhiZ'] = (start['PhiZ'] - final['PhiZ']) / PhiY_range
        
        helical_final['SamX'] = (start['PhiY'] * final['SamX'] - final['PhiY'] * start['SamX']) / PhiY_range
        helical_final['SamY'] = (start['PhiY'] * final['SamY'] - final['PhiY'] * start['SamY']) / PhiY_range
        helical_final['PhiZ'] = (start['PhiY'] * final['PhiZ'] - final['PhiY'] * start['PhiZ']) / PhiY_range
        
        Phi_range = self.nImages * (self.oscillation - self.overlap)
        Phi_final = Phi_start + Phi_range
        
        helical_start['PhiY'] = PhiY_range / Phi_range
        helical_final['PhiY'] = ((Phi_start * final['PhiY']) - (Phi_final * start['PhiY'])) / Phi_range
        
        return helical_start, helical_final


    def calculateHelicalCollectPosition(self, n, offset_start, offset_final):
        Phi_start = self.ScanStartAngle
        
        position = {}
        
        Phi = Phi_start + n * (self.oscillation - self.overlap)

        position['PhiY'] = offset_start['PhiY'] * Phi + offset_final['PhiY']
        position['PhiZ'] = offset_start['PhiZ'] * position['PhiY'] + offset_final['PhiZ']
        position['SamX'] = offset_start['SamX'] * position['PhiY'] + offset_final['SamX']
        position['SamY'] = offset_start['SamY'] * position['PhiY'] + offset_final['SamY']
        
        return position


    def calculateLinearCollectPosition(self, n):
        start = self.helicalStart #linearStart
        final = self.helicalFinal #linearFinal
        displacements = {}
        for motor in start:
            displacements[motor] = final[motor] - start[motor]
        
        position = {}
        for motor in start:
            position[motor] = start[motor] + displacements[motor] * float(n)/self.nImages
            
        return position
    
    
    def rotate3D(self, angle, unit='radians'):
        if unit != 'radians':
            angle = math.radians(angle)
            
        r = numpy.array([[ math.cos(angle),  math.sin(angle), 0.], 
                         [-math.sin(angle),  math.cos(angle), 0.], 
                         [              0.,               0., 1.]])
        return r
        

    def shift3D(self, displacement):
        s = numpy.array([[1., 0., 0., displacement[0]], 
                         [0., 1., 0., displacement[1]], 
                         [0., 0., 1., displacement[2]],
                         [0., 0., 0.,              1.]])
        return s
        
    def scale3D(self, factor):
        s = numpy.diag(factor + [1.])
        return s
      

    def rotate(self, angle, unit='radians'):
        if unit != 'radians':
            angle = math.radians(angle)
            
        r = numpy.array([[ math.cos(angle),  math.sin(angle), 0.], 
                         [-math.sin(angle),  math.cos(angle), 0.], 
                         [              0.,               0., 1.]])
        return r
        

    def shift(self, displacement):
        s = numpy.array([[1., 0., displacement[0]], 
                         [0., 1., displacement[1]], 
                         [0., 0.,              1.]])
        return s


    def scale(self, factor):
        s = numpy.diag([factor[0], factor[1], 1.])
        return s
        

    def scan(self, center, nbsteps, lengths, attributes):
        '''2D scan on an md2 attribute'''
        
        center = numpy.array(center)
        nbsteps = numpy.array(nbsteps)
        lengths = numpy.array(lengths)
        
        stepsizes = lengths / nbsteps
        
        print 'center', center
        print 'nbsteps', nbsteps
        print 'lengths', lengths
        print 'stepsizes', stepsizes
        
        # adding [1] so that we can use homogeneous coordinates
        positions = list(itertools.product(range(nbsteps[0]), range(nbsteps[1]), [1])) 
        
        points = [numpy.array(position) for position in positions]
        points = numpy.array(points)
        points = numpy.dot(self.shift(- nbsteps / 2.), points.T).T
        points = numpy.dot(self.scale(stepsizes), points.T).T
        points = numpy.dot(self.shift(center), points.T).T
        
        grid = numpy.reshape(points, numpy.hstack((nbsteps, 3)))
        
        gs = grid.shape
        for i in range(gs[0]):
            line = grid[i, :]
            if (i + 1) % 2 == 0:
                line = line[: : -1]
            for point in line:
                self.moveMotors()
                self.measure()
    

    def raster(self, grid):
        gs = grid.shape
        orderedGrid = []
        for i in range(gs[0]):
            line = grid[i, :]
            if (i + 1) % 2 == 0:
                line = line[: : -1]
            orderedGrid.append(line)
        return numpy.array(orderedGrid)
        

    def calculateGridPositions(self, start=[0., 0.], nbsteps=[15, 10], lengths=[1.5, 1.], angle=0., motors=['PhiY', 'PhiZ']):
        #import scipy.ndimage #rotate, shift
        center = numpy.array(start)
        nbsteps = numpy.array(nbsteps)
        lengths = numpy.array(lengths)
        
        stepsizes = lengths / nbsteps
        
        print 'center', center
        print 'nbsteps', nbsteps
        print 'lengths', lengths
        print 'stepsizes', stepsizes
        
        # adding [1] so that we can use homogeneous coordinates
        positions = list(itertools.product(range(nbsteps[0]), range(nbsteps[1]), [1])) 
        
        points = [numpy.array(position) for position in positions]
        points = numpy.array(points)
        points = numpy.dot(self.shift(- nbsteps / 2.), points.T).T
        points = numpy.dot(self.rotate(angle), points.T).T
        points = numpy.dot(self.scale(stepsizes), points.T).T
        points = numpy.dot(self.shift(center), points.T).T
        
        grid = numpy.reshape(points, numpy.hstack((nbsteps, 3)))
        
        rastered = self.raster(grid)
        
        orderedPositions = rastered.reshape((grid.size/3, 3))
        
        dictionariesOfOrderedPositions = [{motors[0]: position[0], motors[1]: position[1]} for position in orderedPositions]
        
        return dictionariesOfOrderedPositions


    def setGridParameters(self, start, nbsteps, lengths):
        self.grid_start = start
        self.grid_nbsteps = nbsteps
        self.grid_lengths = lengths
        self.grid_angle = self.getPhiValue()

    def getCollectPositions(self, imageNums):
        positions = []
        if self.helical:
            positions = [self.calculateLinearCollectPosition(n) for n in range(self.nImages)]
            #offset_start, offset_final = self.calculateHelicalOffset()
            #for n in imageNums:
                #position = self.calculateHelicalCollectPosition(n, offset_start, offset_final)
                #positions.append(position)
        elif self.linear:
            positions = [self.calculateLinearCollectPosition(n) for n in range(self.nImages)]
        elif self.grid:
            positions = self.calculateGridPositions(self.grid_start, self.grid_nbsteps, self.grid_lengths)
        else:
            positions = [{} for k in range(len(imageNums))]
        return positions


    def goniometerReady(self):
        self.logger.info('Preparing MD2')
        self.md2.write_attribute('ScanAnticipation', self.ScanAnticipation)
        self.md2.write_attribute('ScanNumberOfPasses', self.ScanNumberOfPasses)
        self.md2.write_attribute('ScanRange', self.ScanRange)
        self.md2.write_attribute('ScanExposureTime', self.ScanExposureTime)
        #self.md2.write_attribute('ScanStartAngle', self.ScanStartAngle)
        self.md2.write_attribute('PhasePosition', 4)
      

    def initializeDetectorAttributes(self):
        self.logger.info('Reading all the attributes of limaadsc and adsc device servers')
        pass
        #for att in self.limaadsc.get_attribute_list():
            #self.limaadsc.read_attribute(att)
            #time.sleep(0.01)
        #for att in self.adsc.get_attribute_list():
            #self.adsc.read_attribute(att)
            #time.sleep(0.01)

    def detectorReady(self):
        self.logger.info('Preparing Detector')
        if self.limaadsc.state().name != 'STANDBY':
            self.limaadsc.Stop()
            time.sleep(0.5)
            
        if self.adsc.state().name != 'STANDBY':
            #self.adsc.Stop()
            time.sleep(0.5)
        
        if not self.imagePath.endswith('/'):
            self.imagePath += '/'
        self.wait(self.adsc)
        self.adsc.write_attribute('imagePath', self.imagePath)
        self.limaadsc.write_attribute('nbFrames', self.nbFrames)
        
        
    
    def safeOpenSafetyShutter(self):
        self.logger.info('Opening the safety shutter -- checking the hutch PSS state')
        if int(self.pss.prmObt) == 1:
            self.obx.Open()
            while self.obx.State().name != 'OPEN' and self.stt not in ['STOP', 'ABORT']:
                time.sleep(0.1)
        self.logger.info(self.obx.State().name)


    def openSafetyShutter(self):
        self.logger.info('Opening the safety shutter')
        if self.test:
            return
        while self.obx.State().name != 'OPEN' and self.stt not in ['STOP', 'ABORT']:
            self.logger.info(self.obx.State().name)
            self.safeOpenSafetyShutter()
            time.sleep(0.1)
    
    
    def closeSafetyShutter(self):
        self.logger.info('Closing the safety shutter')
        if self.test:
            return
        self.obx.Close()
        

    def lastImage(self, 
                  xformstatusfile = '/927bis/ccd/.lastImage', 
                  integer = 1, 
                  imagePath = '/927bis/ccd/test/', 
                  fileName = 'test.img'):
        #os.system('echo "' + str(integer) + ' ' + imagePath + fileName + '" > ' + xformstatusfile)
        line = str(integer) + ' ' + os.path.join(imagePath, fileName)
        f = open(xformstatusfile, 'w')
        f.write(line)
        f.close()
        
    
    def beamCenter(self):
        '''Will calculate beam center coordinates'''

        # Useful values 
        tz_ref = -6.5     # reference tz position for linear regression
        tx_ref = -17.0    # reference tx position for linear regression
        q = 0.102592 #pixel size in milimeters
        
        wavelength  = self.mono1.read_attribute('lambda').value
        distance    = self.detector_mt_ts.read_attribute('position').value
        tx          = self.detector_mt_tx.position
        tz          = self.detector_mt_tz.position
        
        zcor = tz - tz_ref
        xcor = tx - tx_ref
        
        Theta = numpy.matrix([[  1.55557116e+03,  1.43720063e+03], 
                              [ -8.51067454e-02, -1.84118001e-03], 
                              [ -1.99919592e-01,  3.57937064e+00]]) #values from 16.05.2013
        
        X = numpy.matrix ([1., distance, wavelength])
        
        Origin = Theta.T * X.T
        Origin = Origin * q
        
        return Origin[1] + zcor, Origin[0] + xcor   
        
        
    def setupHeader(self):
        '''Will set up header given the actual values of beamline energy, mono and detector distance'''        
        X, Y = self.beamCenter()
        BeamCenterX = str( round(X, 3) )
        BeamCenterY = str( round(Y, 3) )
        head = self.header.header
        head = re.sub('BEAM_CENTER_X=\d\d\d\.\d', 'BEAM_CENTER_X=' + BeamCenterX, head)
        head = re.sub('BEAM_CENTER_Y=\d\d\d\.\d', 'BEAM_CENTER_Y=' + BeamCenterY, head)
        return head


    def createFileName(self, imageNum, template = 'prefix_1_####.img'):
        '''Will create a filename combining a template and image number.'''
        filename = template.replace('####', str(imageNum).zfill(4))
        return filename


    def setEnergy(self, energy = None):
        self.logger.info('Setting energy')
        '''set energy for the collect'''
        self.energy = energy
        if self.energy is not None:
            ble.energy = self.energy


    def setResolution(self, resolution = None):
        '''set the resolution for the collect'''
        self.logger.info('Setting resolution')
        self.resolution = resolution
        if self.resolution is not None:
            diameter = 315. # detector diameter in mm
            radius = diameter / 2.
            wavelength = self.mono1.Lambda
            theta = math.asin(wavelength / 2. / self.resolution)
            distance = radius / math.tan(2. * theta)
            self.detector_mt_ts.position = distance


    def setTransmission(self, transmission = None):
        Fp   = PyTango.DeviceProxy('i11-ma-c00/ex/fp_parser')
        if transmission is None:
            return 
            
        Ps_h         = PyTango.DeviceProxy('i11-ma-c02/ex/fent_h.1')
        Ps_v         = PyTango.DeviceProxy('i11-ma-c02/ex/fent_v.1')
        Const        = PyTango.DeviceProxy('i11-ma-c00/ex/fpconstparser')
        
        truevalue = (2.0 - math.sqrt(4 - 0.04 * x)) / 0.02

        newGapFP_H = math.sqrt( (truevalue / 100.0) * Const.FP_Area_FWHM / Const.Ratio_FP_Gap )
        newGapFP_V = newGapFP_H * Const.Ratio_FP_Gap
        
        Ps_h.gap = newGapFP_H
        Ps_v.gap = newGapFP_V


    def setAttenuation(self, attenuation = None):
        Attenuator = DeviceProxy('i11-ma-c05/ex/att.1')
        labels = [  
                    '00 Extract', 
                    '01 Carbon 200um', 
                    '02 Carbon 250um', 
                    '03 Carbon 300um', 
                    '04 Carbon 500um', 
                    '05 Carbon 1mm', 
                    '06 Carbon 2mm', 
                    '07 Carbon 3mm', 
                    '10 Ref Fe 5um', 
                    '11 Ref Pt 5um'
                ]

        if attenuation is None:
            return
            
        NumToLabel = dict([(int(l.split()[0]), l) for l in labels])
        Attenuator.write_attribute(NumToLabel[x], True)


    def safeTurnOff(self, device):
        if device.state().name == 'STANDBY':
            device.Off()
            

    def prepareWedges(self, firstImage, nbFrames, ScanStartAngle):
        '''Based on collect parameters will prepare all the wedges to be collected.'''
        self.logger.info('Preparing wedges')
        wedges = []
        
        if self.inverse is None:
            imageNums = range(firstImage, nbFrames + firstImage)
            positions = self.getCollectPositions(imageNums)
            wedges.append({'imageNumbers': imageNums, 
                           'startAtAngle': ScanStartAngle, 
                           'template': self.template, 
                           'positions': positions})
        else:
            wedgeSize = int(self.inverse)
            numberOfFullWedges, lastWedgeSize = divmod(nbFrames, wedgeSize)
            for k in range(0, numberOfFullWedges):
                _ScanStartAngle = ScanStartAngle + k * wedgeSize * (self.ScanRange - self.ScanOverlap)
                _firstImage = firstImage + k * wedgeSize
                imageNums = range(_firstImage, _firstImage + wedgeSize)
                positions = self.getCollectPositions(imageNums)
                
                wedges.append({'imageNumbers': imageNums, 
                               'startAtAngle': _ScanStartAngle, 
                               'template': self.template, 
                               'positions': positions})
                wedges.append({'imageNumbers': imageNums, 
                               'startAtAngle': _ScanStartAngle + 180, 
                               'template': self.template_inv, 
                               'positions': positions})
            
            _ScanStartAngle = ScanStartAngle + numberOfFullWedges * wedgeSize * (self.ScanRange - self.ScanOverlap)
            _firstImage = firstImage + numberOfFullWedges * wedgeSize
            imageNums = range(_firstImage, _firstImage + lastWedgeSize)
            positions = self.getCollectPositions(imageNums)
            
            wedges.append({'imageNumbers': imageNums, 
                           'startAtAngle': _ScanStartAngle, 
                           'template': self.template, 
                           'positions': positions})
            wedges.append({'imageNumbers': imageNums, 
                           'startAtAngle': _ScanStartAngle + 180, 
                           'template': self.template_inv, 
                           'positions': positions})
        
        #self.logger.info('Wedges to collect: ')
        print 'Wedges to collect:'
        print wedges
        return wedges


    def start(self):
        '''Start the collect as a thread'''
        self.logger.info('Starting Collect Thread')
        self.collectThread = threading.Thread(target = self.collect)
        self.collectThread.daemon = True
        self.collectThread.start()


    def stop(self):
        self.logger.info('Stopping the collect')
        self.Stop = True
        self.stt = 'STOP'
    

    def abort(self):
        self.logger.info('Aborting the collect')
        self.md2.CloseFastShutter()
        self.limaadscStop()
        self.stop()
        self.Abort = True
        self.stt = 'ABORT'


    def collect(self):
        self.logger.info('Starting the collect')
        self.state('RUNNING')
        self.collectDone = False
        self.imageNum = 0
        self.setEnergy()
        self.setResolution()
        self.openSafetyShutter()
        self.goniometerReady()
        self.detectorReady()
        self.initializeDetectorAttributes()
        
        wedges = self.prepareWedges(self.firstImage, self.nbFrames, self.ScanStartAngle)

        while self.mono_mt_rx.state().name != 'OFF':
            self.safeTurnOff(self.mono_mt_rx)
            time.sleep(0.1)
        
        for wedge in wedges:
            self.collectWedge(wedge)

        self.mono_mt_rx.On()
        self.closeSafetyShutter()
        self.collectDone = True
        self.state('STANDBY')


    def collectWedge(self, wedge):
        '''Will collect a single wedge of diffraction images'''
        self.logger.info('Collecting Wedge')
        startOscillationAngle = wedge['startAtAngle']
        template = wedge['template']
        
        for imageNum, position in zip(wedge['imageNumbers'], wedge['positions']):
            if self.Stop:
                return
                
            self.imageNum += 1
            fileName = self.createFileName(imageNum, template=template)
            self.currentImageName = fileName
            
            self.moveToPosition(position)
            self.wait(self.md2)
            self.collectImage(fileName, startOscillationAngle)
            
            if self.grid:
                startOscillationAngle = self.grid_angle
            else:
                startOscillationAngle += (self.ScanRange - self.ScanOverlap)
            self.lastImage(integer=self.imageNum, imagePath=self.imagePath, fileName=fileName)


    def collectImage(self, fileName, ScanStartAngle):
        '''Will collect a single diffraction image'''
        imageTaken = False
        while imageTaken is False and self.stt not in ['STOP', 'ABORT']:
            try:
                self.logger.info('Collecting image ' + fileName + ' at angle ' + str(ScanStartAngle))
                self.wait(self.adsc)
                self.adsc.write_attribute('fileName', fileName)
                self.wait(self.adsc)

                self.wait(self.md2)
                self.md2.write_attribute('ScanStartAngle', ScanStartAngle)
                
                self.wait(self.adsc)
                head = self.setupHeader()
                self.adsc.command_inout('SetHeaderParameters', head) 
                self.wait(self.adsc)
                # the following three lines are the core of the collect 
                # taking one diffraction image via oscillation method
            
                self.limaadscSnap()
                self.StartScan()
                self.limaadscStop()
                imageTaken = True
            except Exception, e:
                print e
                import traceback
                traceback.print_exc()
                self.logger.info('Problem occured during collection of image ' + fileName)
                self.logger.info(traceback.print_exc())
                
        
    def StartScan(self):
        self.wait(self.md2)
        try:
            self.md2.command_inout('StartScan')
            self.wait(self.md2)
        except Exception, e:
            print e
            self.logger.info('Problem executing StartScan command')
            self.logger.info('Exception ' + str(e))
        return


    def limaadscSnap(self):
        while self.limaadsc.log[-1].find('yat::DEVICE_SNAP_MSG') == -1:
            self.limaadsc.command_inout('Snap')
            time.sleep(0.001)
        return


    def limaadscStop(self, timeout=0.1):
        k = 0
        while self.limaadsc.log[-1].find('Acquisition is Stopped.') == -1:
            k += 1
            self.limaadsc.command_inout('Stop')
            if k > 1:
                self.logger.info('Problem executing Stop command on limaadsc. Attempt %d to stop it.' % k)
            time.sleep(0.05)
        return
            
def main():
    import optparse
    
    usage = 'Program to perform collect on PX2 beamline.\n\n%prog -n <number_of_images>\n\nNumber of images to be collected has to be specified, others are optional.'
    parser = optparse.OptionParser(usage = usage)

    parser.add_option('-e', '--exposure', default = 0.5, type = float, help = 'exposure time (default: %default)')
    parser.add_option('-o', '--oscillation', default = 0.5, type = float, help = 'oscillation range (default: %default)')
    parser.add_option('-p', '--passes', default = 1, type = int, help = 'number of passes (default: %default)')
    parser.add_option('-s', '--start', default = 0.0, type = float, help = 'collect start angle (default: %default)')
    parser.add_option('-n', '--nImages', default = 1, type = int, help = 'Number of images to collect (default = %default')
    parser.add_option('-r', '--range', default = None, type = float, help = 'collect range. This is alternative way to specify how much we want to explore (alternative to --nImages)')
    parser.add_option('-a', '--anticipation', default = 1, type = int, help = 'scan anticipation (default: %default)')
    parser.add_option('-l', '--overlap', default = 0.0, type = float, help = 'scanning overlap (default: %default)')
    parser.add_option('-d', '--directory', default = '/tmp/test-data', type = str, help = 'where to store collected images (default: %default)')
    parser.add_option('-u', '--run', default = 1, type = int, help = 'run number')
    parser.add_option('-f', '--firstImage', default = 1, type = int, help = 'Image number to start with. Useful if some images were collected already and we do not want to overwrite them (default: %default)')
    parser.add_option('-x', '--prefix', default = 'F6', type = str, help = 'prefix (default = %default)')
    parser.add_option('-i', '--suffix', default = 'img', type = str, help = 'suffix (default = %default)')
    parser.add_option('-t', '--template', default = 'prefix_1_####.img', type = str, help = 'teplate (default = %default)')
    parser.add_option('-c', '--comment', default = '', type = str, help = 'Add your comment here ...')
    parser.add_option('-I', '--inverse', default = None, help = 'Inverse collects, parameter is integer specifying reference interval i.e. number of images in the wedge (default = %default)')
    parser.add_option('-E', '--energy', default = None, help = 'Energy at which to perform the collect')
    parser.add_option('-R', '--resolution', default = None, help = 'Resolution at which to perform the collect')
    parser.add_option('-D', '--distance', default = None, help = 'Detector distance at which to perfom the collect')
    parser.add_option('-T', '--transmission', default = None, help = 'Set transmission for the collect')
    parser.add_option('-A', '--attenuation', default = None, help = 'Set the attenuation for the collect')
    parser.add_option('-N', '--test', default = False, help = 'Collect without beam (do not attempt to open the safety shutter')
    
    (options, args) = parser.parse_args()
    print options
    print args
    
    ScanAnticipation = options.anticipation # 1
    ScanNumberOfPasses = options.passes # 1
    ScanRange = options.oscillation # 10
    ScanExposureTime = options.exposure # 1.0
    ScanStartAngle = options.start #0.0
    ScanOverlap = options.overlap
    
    if options.nImages == None and options.range == None :
        print parser.usage
        sys.exit("Option nImages or option range have to be specified.")

    if options.range != None:
        nbFrames = int( math.ceil( (options.range - options.start) / options.oscillation ) )
    else:
        nbFrames = int(options.nImages)

    print 'nbFrames', nbFrames

    collectObject = Collect.collect(    
                                        exposure = options.exposure,
                                        oscillation = options.oscillation,
                                        passes = options.passes,
                                        start = options.start,
                                        firstImage = options.firstImage,
                                        nImages = options.nImages,
                                        overlap = options.overlap,
                                        directory = options.directory,
                                        run = options.run,
                                        prefix = options.prefix,
                                        suffix = options.suffix,
                                        template = options.template,
                                        resolution = float(options.resolution),
                                        energy = float(options.energy),
                                        transmission = float(options.transmission),
                                        attenuation = int(options.attenuation)
                                    )
    collectObject.start()
    
if __name__ == '__main__':
    main()
    
