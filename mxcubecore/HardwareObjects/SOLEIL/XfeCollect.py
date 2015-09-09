#!/usr/bin/env python
# -*- coding: utf-8 -*-


import optparse
import time
import PyTango
import pylab
import numpy
import os
import pickle
import math
from xabs_lib import *

class XfeCollect(object):
    def __init__(self, integrationTime = .64, directory = '/tmp', prefix = 'test', sessionId = None, sampleId = None, test=False, optimize=False):
        self.integrationTime = integrationTime
        self.directory = directory
        self.prefix = prefix
        self.sessionId = sessionId
        self.sampleId = sampleId
        self.filename = os.path.join(self.directory, self.prefix + '_fxe.png') #filename
        
        self.md2     = PyTango.DeviceProxy('i11-ma-cx1/ex/md2')
        self.fluodet   = PyTango.DeviceProxy('i11-ma-cx1/dt/dtc-mca_xmap.1')
        #self.counter = PyTango.DeviceProxy('i11-ma-c00/ca/cpt.2')
        self.obx     = PyTango.DeviceProxy('i11-ma-c04/ex/obx.1')
        self.ble     = PyTango.DeviceProxy('i11-ma-c00/ex/beamlineenergy')
        self.monodevice = PyTango.DeviceProxy('i11-ma-c03/op/mono1')
        self.optimize = optimize
        self.test = test
        self.fluodet.presettype = 1
        self.fluodet.peakingtime = 2.5
        self.channelToeV = 10. #self.fluodet.dynamicRange / len(self.fluodet.channel00)
        try:
            os.mkdir(directory)
        except OSError, e:
            print e
    
    def wait(self, device):
        while device.state().name == 'MOVING':
            time.sleep(.1)
        
        while device.state().name == 'RUNNING':
            time.sleep(.1)
            
    def transmission(self, x=None):
        '''Get or set the transmission'''
        if self.test == True: return 0
        Fp = PyTango.DeviceProxy('i11-ma-c00/ex/fp_parser')
        if x == None:
            return Fp.TrueTrans_FP

        Ps_h = PyTango.DeviceProxy('i11-ma-c02/ex/fent_h.1')
        Ps_v = PyTango.DeviceProxy('i11-ma-c02/ex/fent_v.1')
        Const = PyTango.DeviceProxy('i11-ma-c00/ex/fpconstparser')

        truevalue = (2.0 - math.sqrt(4 - 0.04 * x)) / 0.02

        newGapFP_H = math.sqrt(
            (truevalue / 100.0) * Const.FP_Area_FWHM / Const.Ratio_FP_Gap)
        newGapFP_V = newGapFP_H * Const.Ratio_FP_Gap

        Ps_h.gap = newGapFP_H
        Ps_v.gap = newGapFP_V
        
    def secondaryTransmission(self, x=None):
        '''Get or set the transmission by secondary slits'''
        if self.test == True: return 0
        Fp = PyTango.DeviceProxy('i11-ma-c00/ex/fp_parser')
        if x == None:
            return Fp.TrueTrans_FP

        Ss_h = PyTango.DeviceProxy('i11-ma-c04/ex/fent_h.2')
        Ps_v = PyTango.DeviceProxy('i11-ma-c04/ex/fent_v.2')
        Const = PyTango.DeviceProxy('i11-ma-c00/ex/fpconstparser')

        truevalue = (2.0 - math.sqrt(4 - 0.04 * x)) / 0.02

        newGapFP_H = math.sqrt(
            (truevalue / 100.0) * Const.FP_Area_FWHM / Const.Ratio_FP_Gap)
        newGapFP_V = newGapFP_H * Const.Ratio_FP_Gap

        Ps_h.gap = newGapFP_H
        Ps_v.gap = newGapFP_V
        
    def go10eVabovetheEdge(self):
        if self.test == True: return 0
        self.ble.write_attribute('energy', self.thEdge + 0.01)
        self.wait(self.ble)
            
    def getEdgefromXabs(self, el, edge):
        edge = edge.upper()
        roi_center = McMaster[el]['edgeEnergies'][edge + '-alpha']
        if edge == 'L':
            edge = 'L3'
        e_edge = McMaster[el]['edgeEnergies'][edge]
        return (e_edge, roi_center)    
        
    def optimizeTransmission(self, element, edge):
        if self.test == True: return 0
        print 'Going to optimize transmission'
        self.optimize = True
        e_edge, roi_center = self.getEdgefromXabs(element, edge)
        self.thEdge = e_edge
        self.element = element
        self.edge = edge
        
        self.go10eVabovetheEdge()
        self.setTransmission = 0.5
        self.transmission(self.setTransmission)
        self.inverseDeadTime = 0.
        self.tentativeDeadTime = 1.
        self.lowBoundary = 0
        self.highBoundary = None
        k = 0
        self.obx.Open()
        self.insertDetector()
        while not .7 < self.tentativeDeadTime < .8:
            if self.transmission() > 50:
                break
            
            self.measureSpectrum()
            ICR = self.fluodet.inputCountRate00
            OCR = self.fluodet.outputCountRate00
            eventTime = self.fluodet.realTime00
            self.inverseDeadTime = 1. - (OCR / ICR) # * eventTime
            self.tentativeDeadTime = (OCR / ICR)
            k += 1
            print 'Cycle %d, deadtime is %f' % (k, self.inverseDeadTime)
            self.adjustTransmission()
        print 'Transmission optimized at %s, the deadtime is %s' % (self.currentTransmission, self.inverseDeadTime)
        print 'Tentative real deadtime is %f' % self.tentativeDeadTime
        self.obx.Open()
        self.extractDetector()
        
    def adjustTransmission(self):
        if self.test == True: return 0
        self.currentTransmission = self.transmission()
        print 'current transmission is %f' % self.currentTransmission
        print 'the deadtime is %f' % self.inverseDeadTime
        if self.tentativeDeadTime < 0.7: #too much flux
            self.highBoundary = self.setTransmission
            self.setTransmission -= (self.highBoundary - self.lowBoundary)/2.
        else: #too little flux
            self.lowBoundary = self.setTransmission
            if self.highBoundary is None:
                self.setTransmission *= 2
            else:
                self.setTransmission += (self.highBoundary - self.lowBoundary)/2.
        self.transmission(self.setTransmission)
        
    def canSpectrum(self):
        return True
        
    def setIntegrationTime(self, integrationTime = 0.64):
        if self.test == True: return 0
        #self.counter.integrationTime = integrationTime
        self.fluodet.presetvalue = float(integrationTime)
        
    def setROI(self, roi_debut = 0., roi_fin = 2048.):
        if self.test == True: return 0
        self.fluodet.SetROIs(numpy.array((roi_debut, roi_fin)))
        #pass
    
    def insertDetector(self):
        if self.test == True: return 0
        self.md2.FluoDetectorIsBack = False
        time.sleep(5)
    
    def extractDetector(self):
        if self.test == True: return 0
        self.md2.FluoDetectorIsBack = True
    
    def startXfeSpectrum(self):
        self.transmission(0.5)
        self.measureSpectrum()
        return 
        
    def cancelXfeSpectrum(self):
        if self.test == True: return 0
        self.close_fast_shutter()
        self.fluodet.Abort()
        self.obx.Close()
        self.extractDetector()
        
    def isConnected(self):
        return True
        
    def open_fast_shutter(self):
        while self.md2.FastShutterIsOpen is False:
            print 'Fast shutter is open ?', self.md2.FastShutterIsOpen
            while self.get_state() != 'Ready':
                time.sleep(0.1)
            print 'opening the fast shutter'
            try:
                self.md2.FastShutterIsOpen = True
            except:
                import traceback
                traceback.print_exc()
        
    def close_fast_shutter(self):
        self.md2.FastShutterIsOpen = False

    def get_state(self):
        for state in self.md2.motorstates:
            if 'Moving' in state:
                return 'Moving'
        return 'Ready'
        
    def set_collect_phase(self):
        phase_name = 'DataCollection'
        self.md2.startSetPhase(phase_name)
        while self.md2.currentPhase != phase_name or self.get_state() != 'Ready':
            time.sleep(0.1)
        
    def get_calibration(self):
        A = -0.0161723871876
        B = 0.00993475667754
        C = 0.0
        return A, B, C
        
    def measureSpectrum(self):
        if self.test == True: return 0
        self.setIntegrationTime(self.integrationTime)
        if self.optimize != True:
            self.insertDetector()
            self.obx.Open()
        #self.transmission(1)
        time.sleep(1)
        self.set_collect_phase()
        self.open_fast_shutter()
        self.fluodet.Start()
        #self.counter.Start()
        while self.fluodet.state().name != 'STANDBY':
            time.sleep(0.1)
            #time.sleep(int(self.integrationTime))
        self.close_fast_shutter()
        if self.optimize != True:
            self.extractDetector()
        
    def get_calibrated_energies(self):
        energies = self.getXvals()
        A, B, C = self.get_calibration()
        energies += A + B*energies + C*energies**2
        return energies
        
    def getSpectrum(self):
        return self.fluodet.channel00
        
    def getMcaConfig(self):
        return {'att': '7', 'energy': 12.65, 'bsX': 1, 'bsY': 2 }
    
    def getXvals(self):
        start, end   = 0, 2048
        step = 1
        return numpy.arange(start, end, step)

    def getValue(self):
        return self.getXvals(), self.getSpectrum()

    def saveData(self):
        f = open(self.filename[:-4]  + '.pck', 'w')
        x = self.getXvals()
        y = self.getSpectrum()
        energies = self.get_calibrated_energies()
        cal = self.get_calibration()
        pickle.dump({'x': x, 'energies': energies, 'calibration': cal, 'y': y}, f)
        f.close()
        #self.plotSpectrum()
        
    def plotSpectrum(self):
        x = self.get_calibrated_energies() #getXvals()
        y = self.getSpectrum()
        self.saveData()
        
        pylab.figure()
        pylab.plot(x, y)
        pylab.xlim(x[0], x[-1])
        pylab.title('X-ray fluorescence emission spectrum')
        pylab.xlabel('Energy [keV]')
        pylab.ylabel('Intensity [Counts]')
        pylab.savefig(self.filename)
        
        ##pylab.show()
        
if __name__ == '__main__':
    usage = 'Program to perform collect on PX2 beamline.\n\n%prog -n <number_of_images>\n\nNumber of images to be collected has to be specified, others are optional.'
    parser = optparse.OptionParser(usage = usage)

    parser.add_option('-e', '--exposure', default = 2.0, type = float, help = 'integration time (default: %default)')
    parser.add_option('-x', '--prefix', default = 'test', type = str, help = 'prefix (default = %default)')
    parser.add_option('-d', '--directory', default = '/tmp/fxetests2', type = str, help = 'where to store spectrum collected (default: %default)')

    (options, args) = parser.parse_args()
    print options
    print args
    
    doCollect = XfeCollect(options.exposure, options.directory, options.prefix)
    doCollect.setROI(1, 2048)
    time.sleep(0.5)
    doCollect.measureSpectrum()
    doCollect.plotSpectrum()
    pylab.show()
