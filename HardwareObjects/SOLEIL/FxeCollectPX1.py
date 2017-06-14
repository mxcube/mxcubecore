#!/usr/bin/env python
# -*- coding: utf-8 -*-


import optparse
import time
import PyTango
import pylab
import numpy
import os
import pickle


#sys.exit()

#md2             = PyTango.DeviceProxy('i11-ma-cx1/ex/md2')
#ketek           = PyTango.DeviceProxy('i11-ma-cx1/dt/dtc-mca_xmap.1')
#counter         = PyTango.DeviceProxy('i11-ma-c00/ca/cpt.2')


class XfeCollector(object):
    def __init__(self, integrationTime, filename):
        self.integrationTime = integrationTime
        self.filename = filename
        
        
        self.ketek_ins = PyTango.DeviceProxy('i10-c-cx1/dt/dtc_sdd.1-pos')
        self.fastshutter = PyTango.DeviceProxy('i10-c-cx1/ex/spishutter-pos')
        self.ketek = PyTango.DeviceProxy('i10-c-cx1/dt/ketek.1')
        #self.counter = PyTango.DeviceProxy('i11-ma-c00/ca/cpt.2')
        self.obx     = PyTango.DeviceProxy('i10-c-c03/ex/obx.1')

        print self.ketek.dynamicRange
        print self.ketek.channel00
        
        self.channelToeV = self.ketek.dynamicRange / len(self.ketek.channel00)
        
        try:
            os.mkdir(options.directory)
        except OSError, e:
            print e
        
    def setIntegrationTime(self, integrationTime = 1.):
        #self.counter.integrationTime = integrationTime
        self.ketek.presetvalue = integrationTime
        
    def setROI(self, roi_debut = 0., roi_fin = 100.):
        pass
        #self.ketek.SetROIs(numpy.array((roi_debut, roi_fin)))
        
    def insertDetector(self):
        self.ketek_ins.Insert()
        time.sleep(5)
    
    def extractDetector(self):
        self.ketek_ins.Extract()
        time.sleep(5)
        
    def measureSpectrum(self):
        #self.insert
        self.setIntegrationTime(self.integrationTime)
#        self.insertDetector()
#        self.obx.Open()
        self.fastshutter.Open()
        self.ketek.Start()
        #self.counter.Start()
        time.sleep(self.integrationTime)
        #while self.counter.State().name != 'STANDBY':
            #pass
        self.ketek.Abort()
        self.fastshutter.Close()
#        self.obx.Close()
#        self.extractDetector()
        
    def getSpectrum(self):
        return self.ketek.channel00
        
    def getXvals(self):
        start, end   = self.ketek.roisStartsEnds
        #energy_start = start * self.channelToeV
        #energy_end   = end   * self.channelToeV
        #step = (energy_end - energy_start) / len(ketek.channel00)
        step =(end - start) / len(self.ketek.channel00)
        return numpy.arange(start, end, step)
        
    def saveData(self, x, y):
        f = open(self.filename[:-4]  + '.pck', 'w')
        pickle.dump({'x': x, 'y': y}, f)
        f.close()
        
    def plotSpectrum(self):
        x = self.getXvals()
        y = self.getSpectrum()
        self.saveData(x, y)
        
        pylab.figure()
        pylab.plot(x, y)
        pylab.xlim(x[0], x[-1])
        pylab.title('X-ray fluorescence emission spectrum')
        pylab.xlabel('Channels')
        pylab.ylabel('Intensity [Counts]')
        pylab.savefig(self.filename)
        
        pylab.show()
        
if __name__ == '__main__':
    usage = 'Program will measure X-ray fluorescence spectrum\n'
    parser = optparse.OptionParser(usage = usage)

    parser.add_option('-e', '--exposure', default = 2.0, type = float, help = 'integration time (default: %default)')
    parser.add_option('-x', '--prefix', default = 'test', type = str, help = 'prefix (default = %default)')
    parser.add_option('-d', '--directory', default = '.', type = str, help = 'where to store spectrum collected (default: %default)')

    (options, args) = parser.parse_args()
    print options
    print args
    
    doCollect = XfeCollector(options.exposure, options.directory + '/' + options.prefix + '_fxe.png')
    doCollect.setROI(1, 2048)
    time.sleep(0.5)
    #doCollect.setIntegrationTime()
    doCollect.measureSpectrum()
    doCollect.plotSpectrum()
    
