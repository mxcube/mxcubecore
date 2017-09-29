# -*- coding: utf-8 -*-
from qt import *
from HardwareRepository.BaseHardwareObjects import Equipment
import logging
import PyChooch
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
#from SpecClient import SpecClientError
#from SpecClient import SpecVariable
#from SpecClient import SpecConnectionsManager
#from SpecClient import SpecEventsDispatcher
#from SimpleDevice2c import SimpleDevice #MS 05.03.2013
import os
import time
import types
import math
from xabs_lib import *
#from simple_scan_class import *
import string
#MS 05.03.2013
from PyTango import DeviceProxy
import numpy
import pickle

class EnergyScanPX1(Equipment):
    
    MANDATORY_HO={"BLEnergy":"BLEnergy"}
    
    
    def init(self):
        self.scanning = None
#        self.moving = None
        self.scanThread = None
        self.pk = None
        self.ip = None
        self.roiwidth = 0.35 # en keV largeur de la roi 
        self.before = 0.10  #  en keV Ecart par rapport au seuil pour le point de depart du scan
        self.after = 0.20   # en keV Ecart par rapport au seuil pour le dernier point du scan
        self.canScan = True
        self.nbsteps = 100 #
        self.integrationtime = 5.0
        self.directoryPrefix = None

        self.directoryPrefix=self.getProperty("directoryprefix")
        if self.directoryPrefix is None:
            logging.getLogger("HWR").error("EnergyScan: you must specify the directory prefix property")
        else :
            logging.getLogger("HWR").info("EnergyScan: directoryPrefix : %s" %(self.directoryPrefix))
            
                    # Load mandatory hardware objects
#         for ho in EnergyScan.MANDATORY_HO:
#             desc=EnergyScan.MANDATORY_HO[ho]
#             name=self.getProperty(ho)
#             if name is None:
#                  logging.getLogger("HWR").error('EnergyScan: you must specify the %s hardware object' % desc)
#                  hobj=None
#                  self.configOk=False
#             else:
#                  hobj=HardwareRepository.HardwareRepository().getHardwareObject(name)
#                  if hobj is None:
#                      logging.getLogger("HWR").error('EnergyScan: invalid %s hardware object' % desc)
#                      self.configOk=False
#             exec("self.%sHO=hobj" % ho)
# 
#         print "BLEnergyHO : ", self.BLEnergyHO
        
        paramscan = self["scan"]   
        self.roiwidth = paramscan.roiwidth
        self.before = paramscan.before
        self.after = paramscan.after
        self.nbsteps = paramscan.nbsteps
        self.integrationTime = paramscan.integrationtime
      
      
        print "self.roiwidth :", self.roiwidth
        print "self.before :", self.before
        print "self.after :", self.after
        print "self.nbsteps :", self.nbsteps
        print "self.integrationtime :", self.integrationtime
        

        self.dbConnection=self.getObjectByRole("dbserver")
        if self.dbConnection is None:
            logging.getLogger("HWR").warning('EnergyScan: you should specify the database hardware object')
        self.scanInfo=None

        if self.isSpecConnected():
            self.sConnected()
            
    def connectTangoDevices(self):
        try :
            self.BLEnergydevice = DeviceProxy(self.getProperty("blenergy")) #, verbose=False)
            self.BLEnergydevice.waitMoves = True
            self.BLEnergydevice.timeout = 30000
        except :
            logging.getLogger("HWR").error("%s not found" %(self.getProperty("blenergy")))
            self.canScan = False
            
        # Connect to device mono defined "tangoname2" in the xml file 
        # used for conversion in wavelength
        try :    
            self.monodevice = DeviceProxy(self.getProperty("mono")) #, verbose=False)
            self.monodevice.waitMoves = True
            self.monodevice.timeout = 6000
        except :    
            logging.getLogger("HWR").error("%s not found" %(self.getProperty("mono")))
            self.canScan = False
        #mono_mt_rx
        try :    
            self.mono_mt_rx_device = DeviceProxy(self.getProperty("mono_mt_rx")) #, verbose=False)
            #self.monodevice.waitMoves = True
            self.mono_mt_rx_device.timeout = 6000
        except :    
            logging.getLogger("HWR").error("%s not found" %(self.getProperty("mono_mt_rx")))
            self.canScan = False
        # Nom du device bivu (Energy to gap) : necessaire pour amelioration du positionnement de l'onduleur (Backlash)
        try :    
            self.U20Energydevice = DeviceProxy(self.getProperty("U24Energy")) #, movingState="MOVING")
            self.U20Energydevice.timeout = 30000
        except :    
            logging.getLogger("HWR").error("%s not found" %(self.getProperty("U24Energy")))
            self.canScan = False
            
        try :
            self.fluodetdevice = DeviceProxy(self.getProperty("ketek")) #, verbose=False)
            self.fluodetdevice.timeout = 1000
        except :
            logging.getLogger("HWR").error("%s not found" %(self.getProperty("ketek")))
            self.canScan = False
            
        try :    
            self.counterdevice = DeviceProxy(self.getProperty("counter")) #, verbose=False)
            self.counterdevice.timeout = 1000
        except :    
            logging.getLogger("HWR").error("%s not found" %(self.getProperty("counter")))
            self.canScan = False

        try :    
            self.xbpmdevice = DeviceProxy(self.getProperty("xbpm")) #, verbose=False)
            self.xbpmdevice.timeout = 30000
        except :    
            logging.getLogger("HWR").error("%s not found" %(self.getProperty("xbpm")))
            self.canScan = False
       
        try :    
            self.attdevice = DeviceProxy(self.getProperty("attenuator")) #, verbose=False)
            self.attdevice.timeout = 6000
        except :    
            logging.getLogger("HWR").error("%s not found" %(self.getProperty("attenuator")))
            self.canScan = False
        
#        try :    
#            self.md2device = DeviceProxy(self.getProperty("md2")) #, verbose=False)
#            self.md2device.timeout = 2000
#        except :    
#            logging.getLogger("HWR").error("%s not found" %(self.getProperty("md2")))
#            self.canScan = False
        
        try:
            self.lightdevice = DeviceProxy(self.getProperty("lightextract")) #, verbose=False)
            self.lightdevice.timeout = 2000
        except :    
            logging.getLogger("HWR").error("%s not found" %(self.getProperty("lightextract")))
            self.canScan = False

        try:
            self.bstdevice = DeviceProxy(self.getProperty("bst")) #, verbose=False)
            self.bstdevice.timeout = 2000
        except :    
            logging.getLogger("HWR").error("%s not found" %(self.getProperty("bst")))
            self.canScan = False

        try:
            self.ketekinsertdevice = DeviceProxy(self.getProperty("ketekinsert")) #, verbose=False)
            self.ketekinsertdevice.timeout = 2000
        except :    
            logging.getLogger("HWR").error("%s not found" %(self.getProperty("ketekinsert")))
            self.canScan = False

        try:
            self.fastshutterdevice = DeviceProxy(self.getProperty("fastshutter")) #, verbose=False)
            self.fastshutterdevice.timeout = 2000
        except :    
            logging.getLogger("HWR").error("%s not found" %(self.getProperty("fastshutter")))
            self.canScan = False
        
                            
    def isConnected(self):
        return self.isSpecConnected()
        
    def isSpecConnected(self):
        logging.getLogger("HWR").debug('EnergyScan:isSpecConnected')
        return True

    # Handler for spec connection
    def sConnected(self):
        logging.getLogger("HWR").debug('EnergyScan:sConnected')
        self.emit('connected', ())
        self.emit('setDirectory', (self.directoryPrefix,))


    # Handler for spec disconnection
    def sDisconnected(self):
        logging.getLogger("HWR").debug('EnergyScan:sDisconnected')
        self.emit('disconnected', ())

    # Energy scan commands
    def canScanEnergy(self):
        logging.getLogger("HWR").debug('EnergyScan:canScanEnergy : %s' %(str(self.canScan)))
        return self.canScan

 
#        return self.doEnergyScan is not None

    def startEnergyScan(self, 
                        element, 
                        edge, 
                        directory, 
                        prefix, 
                        session_id = None, 
                        blsample_id = None):
        
        logging.getLogger("HWR").debug('EnergyScan:startEnergyScan')
        print 'edge', edge
        print 'element', element
        print 'directory', directory
        print 'prefix', prefix
        #logging.getLogger("HWR").debug('EnergyScan:edge', edge)
        #logging.getLogger("HWR").debug('EnergyScan:element', element)
        #logging.getLogger("HWR").debug('EnergyScan:directory', directory)
        #logging.getLogger("HWR").debug('EnergyScan:prefix', prefix)
        #logging.getLogger("HWR").debug('EnergyScan:edge', edge)
        self.scanInfo={"sessionId":session_id,
                       "blSampleId":blsample_id,
                       "element":element,
                       "edgeEnergy":edge}
#        if self.fluodetectorHO is not None:
#            self.scanInfo['fluorescenceDetector']=self.fluodetectorHO.userName()
        if not os.path.isdir(directory):
            logging.getLogger("HWR").debug("EnergyScan: creating directory %s" % directory)
            try:
                os.makedirs(directory)
            except OSError,diag:
                logging.getLogger("HWR").error("EnergyScan: error creating directory %s (%s)" % (directory,str(diag)))
                self.emit('scanStatusChanged', ("Error creating directory",))
                return False
        self.doEnergyScan(element, edge, directory, prefix)
        return True
        
    def cancelEnergyScan(self):
        logging.getLogger("HWR").debug('EnergyScan:cancelEnergyScan')
        if self.scanning:
            self.scanning = False
            
    def scanCommandReady(self):
        logging.getLogger("HWR").debug('EnergyScan:scanCommandReady')
        if not self.scanning:
            self.emit('energyScanReady', (True,))
            
    def scanCommandNotReady(self):
        logging.getLogger("HWR").debug('EnergyScan:scanCommandNotReady')
        if not self.scanning:
            self.emit('energyScanReady', (False,))
            
    def scanCommandStarted(self):
        logging.getLogger("HWR").debug('EnergyScan:scanCommandStarted')

        self.scanInfo['startTime']=time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = True
        self.emit('energyScanStarted', ())
    
    def scanCommandFailed(self):
        logging.getLogger("HWR").debug('EnergyScan:scanCommandFailed')
        self.scanInfo['endTime']=time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = False
        self.storeEnergyScan()
        self.emit('energyScanFailed', ())
        
    def scanCommandAborted(self):
        logging.getLogger("HWR").debug('EnergyScan:scanCommandAborted')
    
    def scanCommandFinished(self,result):
        logging.getLogger("HWR").debug("EnergyScan: energy scan result is %s" % result)
        self.scanInfo['endTime']=time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = False
        if result==-1:
            self.storeEnergyScan()
            self.emit('scanStatusChanged', ("Scan aborted",))
            self.emit('energyScanFailed', ())
            return

        self.storeEnergyScan()
        self.emit('energyScanFinished', (self.scanInfo,))
        self.scanInfo=None
        
    def doChooch(self, scanObject, scanDesc):
                 #elt, 
                 #edge):
                 #scanArchiveFilePrefix = 'scanArchiveFilePrefix', 
                 #scanFilePrefix = 'scanFilePrefix'):
                     
        logging.getLogger().info("EnergyScan: doChooch")
        print 'scanObject', scanObject
        print 'scanDesc', scanDesc
        #archiveRawScanFile=os.path.extsep.join((scanArchiveFilePrefix, "raw"))
        #rawScanFile=os.path.extsep.join((scanFilePrefix, "raw"))
        #scanFile=os.path.extsep.join((scanFilePrefix, "efs"))
      
        #if not os.path.exists(os.path.dirname(scanArchiveFilePrefix)):
            #os.mkdir(os.path.dirname(scanArchiveFilePrefix))
        
        #try:
            #f=open(rawScanFile, "w")
            #pyarch_f=open(archiveRawScanFile, "w")
        #except:
            #logging.getLogger("HWR").exception("could not create raw scan files")
            #self.storeEnergyScan()
            #self.emit("energyScanFailed", ())
            #return
        #else:
            #scanData = []
            #for i in range(len(scanObject.x)):
                    #x = float(scanObject.x[i])
                    #x = x < 1000 and x*1000.0 or x 
                    #y = float(scanObject.y[i])
                    #scanData.append((x, y))
                    #f.write("%f,%f\r\n" % (x, y))
                    #pyarch_f.write("%f,%f\r\n"% (x, y)) 
            #f.close()
            #pyarch_f.close()
            #self.scanInfo["scanFileFullPath"]=str(archiveRawScanFile)
        
        filenameIn = self.filenameIn
        filenameOut = filenameIn[:-3] + 'efs'
        scanData = []
        
        contents = file(filenameIn).readlines()
        file(filenameIn).close()
        
        for value in contents:
          if value[0] != '#' :
              vals = value.split()
              x = float(vals[0])
              x = x < 1000 and x*1000.0 or x #This is rather cryptic but seems to work (MS 11.03.13)
              y = float(vals[1])
              #if y == 0.0:
                  #self.scanCommandFailed()
                  #self.scanStatus.setText("data not valid for chooch")
                  #print "data not valid for chooch"
                  #return
              scanData.append((x, y))
              
        elt = scanDesc['element']
        edge = scanDesc['edgeEnergy']
        
        try:
            pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, chooch_graph_data = PyChooch.calc(scanData,
                                                                                    elt, 
                                                                                    edge, 
                                                                                    filenameOut)
        except:
            pk = self.thEdge
            rm = (pk + 50.) / 1000.0
            savpk = pk
            ip = pk - 5. / 1000.0
            logging.getLogger("HWR").info("Chooch failed badly")
            #, fppPeak, fpPeak, ip, fppInfl, fpInfl, chooch_graph_data = self.thEdge, 
            
        rm = (pk + 50.) / 1000.0
        pk = pk / 1000.0
        savpk = pk
        ip = ip / 1000.0
        comm = ""
        logging.getLogger("HWR").info("th. Edge %s ; chooch results are pk=%f, ip=%f, rm=%f" % (self.thEdge,  pk, ip, rm))

        if math.fabs(self.thEdge - ip) > 0.01:
            pk = 0
            ip = 0
            rm = self.thEdge + 0.05
            comm = 'Calculated peak (%f) is more that 10eV away from the theoretical value (%f). Please check your scan' % (savpk, self.thEdge)
    
            logging.getLogger("HWR").warning('EnergyScan: calculated peak (%f) is more that 10eV %s the theoretical value (%f). Please check your scan and choose the energies manually' % (savpk, (self.thEdge - ip) > 0.01 and "below" or "above", self.thEdge))
        
        scanFile = filenameIn
        archiveEfsFile = filenameOut #os.path.extsep.join((scanArchiveFilePrefix, "efs"))
        try:
            fi = open(scanFile)
            fo = open(archiveEfsFile, "w")
        except:
            self.storeEnergyScan()
            self.emit("energyScanFailed", ())
            return
        else:
            fo.write(fi.read())
            fi.close()
            fo.close()

        self.scanInfo["peakEnergy"]=pk
        self.scanInfo["inflectionEnergy"]=ip
        self.scanInfo["remoteEnergy"]=rm
        self.scanInfo["peakFPrime"]=fpPeak
        self.scanInfo["peakFDoublePrime"]=fppPeak
        self.scanInfo["inflectionFPrime"]=fpInfl
        self.scanInfo["inflectionFDoublePrime"]=fppInfl
        self.scanInfo["comments"] = comm

        chooch_graph_x, chooch_graph_y1, chooch_graph_y2 = zip(*chooch_graph_data)
        chooch_graph_x = list(chooch_graph_x)
        for i in range(len(chooch_graph_x)):
          chooch_graph_x[i]=chooch_graph_x[i]/1000.0

        logging.getLogger("HWR").info("<chooch> Saving png" )
        # prepare to save png files
        title="%10s  %6s  %6s\n%10s  %6.2f  %6.2f\n%10s  %6.2f  %6.2f" % ("energy", "f'", "f''", pk, fpPeak, fppPeak, ip, fpInfl, fppInfl) 
        fig=Figure(figsize=(15, 11))
        ax=fig.add_subplot(211)
        ax.set_title("%s\n%s" % (scanFile, title))
        ax.grid(True)
        ax.plot(*(zip(*scanData)), **{"color":'black'})
        ax.set_xlabel("Energy")
        ax.set_ylabel("MCA counts")
        ax2=fig.add_subplot(212)
        ax2.grid(True)
        ax2.set_xlabel("Energy")
        ax2.set_ylabel("")
        handles = []
        handles.append(ax2.plot(chooch_graph_x, chooch_graph_y1, color='blue'))
        handles.append(ax2.plot(chooch_graph_x, chooch_graph_y2, color='red'))
        canvas=FigureCanvasAgg(fig)

        escan_png = filenameOut[:-3] + 'png' #.replace('.esf', '.png') #os.path.extsep.join((scanFilePrefix, "png"))
        escan_archivepng = filenameOut[:-4] + '_archive.png'  #os.path.extsep.join((scanArchiveFilePrefix, "png")) 
        self.scanInfo["jpegChoochFileFullPath"]=str(escan_archivepng)
        try:
            logging.getLogger("HWR").info("Rendering energy scan and Chooch graphs to PNG file : %s", escan_png)
            canvas.print_figure(escan_png, dpi=80)
        except:
            logging.getLogger("HWR").exception("could not print figure")
        try:
            logging.getLogger("HWR").info("Saving energy scan to archive directory for ISPyB : %s", escan_archivepng)
            canvas.print_figure(escan_archivepng, dpi=80)
        except:
            logging.getLogger("HWR").exception("could not save figure")

        self.storeEnergyScan()
        self.scanInfo=None

        logging.getLogger("HWR").info("<chooch> returning" )
        return pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, rm, chooch_graph_x, chooch_graph_y1, chooch_graph_y2, title
    
    def scanStatusChanged(self,status):
        logging.getLogger("HWR").debug('EnergyScan:scanStatusChanged')
        self.emit('scanStatusChanged', (status,))
        
    def storeEnergyScan(self):
        logging.getLogger("HWR").debug('EnergyScan:storeEnergyScan')
        #if self.dbConnection is None:
            #return
        #try:
            #session_id=int(self.scanInfo['sessionId'])
        #except:
            #return
        return
        
    def updateEnergyScan(self, scan_id, jpeg_scan_filename):
        logging.getLogger("HWR").debug('EnergyScan:updateEnergyScan')

    # Elements commands
    def getElements(self):
        logging.getLogger("HWR").debug('EnergyScan:getElements')
        elements=[]
        try:
            for el in self["elements"]:
                elements.append({"symbol":el.symbol, "energy":el.energy})
        except IndexError:
            pass
        return elements

    # Mad energies commands
    def getDefaultMadEnergies(self):
        logging.getLogger("HWR").debug('EnergyScan:getDefaultMadEnergies')
        energies=[]
        try:
            for el in self["mad"]:
                energies.append([float(el.energy), el.directory])
        except IndexError:
            pass
        return energies
        
    def getFilename(self, directory, filename, element, edge):
        filenameIn = os.path.join(directory, filename)
        filenameIn += "_" + element + "_" + "_".join(edge) + ".dat"
        return filenameIn
    
    def doEnergyScan(self, element, edge, directory, filename):
        logging.getLogger("HWR").info('EnergyScan: Element:%s Edge:%s' %(element,edge))

        e_edge, roi_center = self.getEdgefromXabs(element, edge)
        self.thEdge = e_edge
        self.element = element
        self.edge = edge
        
        print 'e_edge = %5.4f , roi_center = %5.4f' %(e_edge, roi_center) 
        
        filenameIn = self.getFilename(directory, filename, element, edge) # filenameIn
        self.filenameIn = filenameIn
        
        # Demarrage du thread de scan
        self.scanCommandStarted()
        self.pk = None
        self.ip = None
        self.scanThread = EnergyScanThread(self,
                                           e_edge,
                                           roi_center,
                                           filenameIn)
        self.scanThread.start()

    def getEdgefromXabs(self, el, edge):
        edge = string.upper(edge)
        roi_center = McMaster[el]['edgeEnergies'][edge + '-alpha']
        if edge == 'L':
            edge = 'L3'
        e_edge = McMaster[el]['edgeEnergies'][edge]
        return (e_edge, roi_center)    
        
    def newPoint(self, x, y):
        logging.getLogger("HWR").debug('EnergyScan:newPoint')
        print 'newPoint', x, y
        self.emit('addNewPoint', (x, y))
    
    def newScan(self,scanParameters):
        logging.getLogger("HWR").debug('EnergyScan:newScan')
        self.emit('newScan', (scanParameters,))
        
    def startMoveEnergy(self, value):   # Copie du code ecrit dans BLEnergy.py pour gestion du backlash onduleur.
   
        # MODIFICATION DE CETTE FONCTION POUR COMPENSER LE PROBLEME D'HYSTERESIS DE L"ONDULEUR
        # PAR CETTE METHODE ON APPLIQUE TOUJOURS UN GAP CROISSANT
        backlash = 0.1 # en mmte
        gaplimite = 5.5  # en mm
        self.doBacklashCompensation = False # True #MS 2013-05-21
#        self.mono_mt_rx_device.On()
        #time.sleep(5)
        
        if (str(self.BLEnergydevice.State()) != "MOVING") :# MS .State -> .State() 06.03.2013
            if self.doBacklashCompensation :
                try : 
                    # Recuperation de la valeur de gap correspondant a l'energie souhaitee
                    self.U20Energydevice.autoApplyComputedParameters = False
                    self.U20Energydevice.energy = value
                    newgap = self.U20Energydevice.computedGap
                    actualgap = self.U20Energydevice.gap

                    self.U20Energydevice.autoApplyComputedParameters = True
                
                    # On applique le backlash que si on doit descendre en gap	    
                    if newgap < actualgap + backlash:
                        # Envoi a un gap juste en dessous (backlash)    
                        if newgap-backlash > gaplimite :
                            self.U20Energydevice.gap = newgap - backlash
                        else :
                            self.U20Energydevice.gap = gaplimite
                            self.U20Energydevice.gap = newgap + backlash
                        time.sleep(1)
                except :           
                    logging.getLogger("HWR").error("%s: Cannot move undulator U20 : State device = %s", self.name(), self.U20Energydevice.State())

            try :
                # Envoi a l'energie desiree    
                self.BLEnergydevice.energy = value
            except :           
                logging.getLogger("HWR").error("%s: Cannot move BLEnergy : State device = %s", self.name(), self.BLEnergydevice.State())
        
        else : 
            statusBLEnergydevice = self.BLEnergydevice.Status()
            logging.getLogger("HWR").error("%s: Cannot move : State device = %s", self.name(), self.BLEnergydevice.State())

            for i in statusBLEnergydevice.split("\n") :
                logging.getLogger().error("\t%s\n" % i)
            logging.getLogger().error("\tCheck devices")
                # Envoi a l'energie desiree    
#        self.BLEnergydevice.energy = value
    def getChoochValue(self, pk, ip) :
        logging.getLogger("HWR").debug('EnergyScan:getChoochValue')
        self.pk = pk
        self.ip = ip

class EnergyScanThread(QThread):
    def __init__(self,
                 parent,
                 e_edge,
                 roi_center,
                 filenameIn):

        QThread.__init__(self)
        
        self.parent     = parent
        self.e_edge     = e_edge
        self.roi_center = roi_center
        self.filenameIn = filenameIn
#        self.mrtx = DeviceProxy('i11-ma-c03/op/mono1-mt_rx')
        self.miniSteps = 1 #30
        self.integrationTime = 1.
        
    def run(self):
        self.result = -1
        logging.getLogger("HWR").debug('EnergyScanThread:run')
#        	mono = SimpleDevice("i10-c-c02/op/mono1")
#         qbpm1 = SimpleDevice("i10-c-c02/dt/xbpm_diode.1")
#         counter = SimpleDevice("i10-c-c00/ca/bai.1144-pci.1h-cpt.1")
#        if self.parent.BLEnergyHO is not None:
#            self.parent.connect(self.parent.BLEnergyHO,qt.PYSIGNAL('setEnergy'),self.energyChanged)
#             self.parent.BLEnergyHO.setEnergy(7.0)
        self.prepare4EScan()
        self.scan (((self.parent.counterdevice, "counter1"), (self.parent.xbpmdevice, "intensity")), # sSensors
                    (self.parent.monodevice, "energy"),                                              # sMotor
                     self.e_edge - self.parent.before,                                               # sStart
                     self.e_edge + self.parent.after,                                                # sEnd
                     self.parent.nbsteps,                                                            # nbSteps
                     sFileName = self.filenameIn,                                                    # sFileName 
                     integrationTime = self.integrationTime/self.miniSteps) #integrationTime=self.parent.integrationtime
        
        
        self.parent.scanCommandFinished(self.result)
        self.afterScan()
   
    def prepare4EScan(self):
        logging.getLogger("HWR").debug('EnergyScanThread:prepare4EScan')
#        self.mrtx.On()
        
        self.parent.connectTangoDevices()
        if not self.parent.canScan :     
            return
        # Rontec configuration
        if self.parent.fluodetdevice.State().name == "RUNNING" :
            self.parent.fluodetdevice.Abort()
            while self.parent.fluodetdevice.State().name != 'STANDBY':
                pass
        #self.parent.fluodetdevice.energyMode = 1
        #time.sleep(0.5)
        #self.parent.fluodetdevice.readDataSpectrum = 0
        #time.sleep(0.5)
        #self.parent.fluodetdevice.SetSpeedAndResolutionConfiguration(0)
        #time.sleep(0.5)
        self.parent.fluodetdevice.presettype = 1
        self.parent.fluodetdevice.peakingtime = 2.5 #2.1
        self.parent.fluodetdevice.presetvalue = 0.64 #1.
        
        #conversion factor: 2048 channels correspond to 20,000 eV hence we have approx 10eV per channel
        #channelToeV = self.parent.fluodetdevice.dynamicRange / len(self.parent.fluodetdevice.channel00)
        channelToeV = 10. #MS 2013-05-23
        roi_debut = 1000.0*(self.roi_center - self.parent.roiwidth / 2.0) #values set in eV
        roi_fin   = 1000.0*(self.roi_center + self.parent.roiwidth / 2.0) #values set in eV
        print 'roi_debut', roi_debut
        print 'roi_fin', roi_fin
        
        
        channel_debut = int(roi_debut / channelToeV) 
        channel_fin   = int(roi_fin / channelToeV)
        print 'channel_debut', channel_debut
        print 'channel_fin', channel_fin
        
        # just for testing MS 07.03.2013, has to be removed for production
        ##### remove for production ####
        #roi_debut = 1120.
        #roi_fin = 1124.
        ##### remove for production ####
       
        self.parent.fluodetdevice.SetROIs(numpy.array((channel_debut, channel_fin)))
        time.sleep(0.1)
        #self.parent.fluodetdevice.integrationTime = 0
        
        # Beamline Energy Positioning and Attenuation setting
        #self.parent.startMoveEnergy(self.e_edge - (self.parent.before - self.parent.after)/2.0)
        self.parent.startMoveEnergy(self.e_edge + (self.parent.after - self.parent.before)/2.0)
        
        #self.parent.attdevice.computedAttenuation = currentAtt
        
        # Positioning Light, BST, Rontec
        self.parent.lightdevice.Extract()
#        self.parent.md2device.write_attribute('BackLightIsOn', False)
        time.sleep(1)
#        self.parent.bstdevice.Insert()
        self.parent.ketekinsertdevice.Insert()
#        self.parent.md2device.write_attribute('FluoDetectorBack', 0)
        time.sleep(4)
#        self.parent.safetyshutterdevice.Open()
        while self.parent.ketekinsertdevice.State().name == "MOVING" or self.parent.BLEnergydevice.State().name == "MOVING":
            time.sleep(1)
    
    def scan(self,
             sSensors, 
             sMotor, 
             sStart, 
             sEnd,
             nbSteps = 100, 
             sStepSize = None,
             sFileName = None,
             stabilisationTime = 0.1,
             interactive = False,
             wait_beamline_status = True,
             integrationTime = 0.25,
             mono_mt_rx = None):
        
        logging.getLogger("HWR").debug('EnergyScanThread:scan')
        print 'sSensors', sSensors
        print 'sMotor', sMotor
        #self.mrtx.On()
        time.sleep(1)
        
        if not self.parent.canScan :   
            return
        
        # initialising
        sData = []
        sSensorDevices = []
        sMotorDevice = sMotor[0]
        print "sStepSize:", sStepSize
 
        if not sStepSize:
            sStepSize = float(sEnd - sStart) / nbSteps
            nbSteps += 1
        else:
            nbSteps = int(1 + ((sEnd - sStart)/sStepionTime)) #__setattr__("integrationTime", integrationTime)Size))
        print "nbsteps:", nbSteps
        
        print "Starting new scan using:"
        sSensorDevices = sSensors
        nbSensors = len(sSensorDevices)
        doIntegrationTime = False
        
        # Rechercher les sensors compteur car besoin d'integrer avant de lire la valeur
        sSensorCounters = []
        for sSensor in sSensorDevices:
            try:
                sSensor[0].__getattr__("integrationTime")
            except:
                pass
            else:
                doIntegrationTime = True 
                if sSensor[0].State == "RUNNING" :
                    sSennsor[0].Stop()
                sSensor[0].write_attribute("integrationTime", integrationTime) #__setattr__("integrationTime", integrationTime)
                sSensorCounters.append(sSensor[0])
        print "sSensorDevices", sSensorDevices                
        print "nbSensors = ", nbSensors
        print "Motor  = %s" % sMotorDevice.name()
        print "Scanning %s from %f to %f by steps of %f (nsteps = %d)" % \
                    (sMotorDevice.name(),sStart, sEnd, sStepSize, nbSteps)
        
        t  = time.localtime()
        sDate = "%02d/%02d/%d - %02d:%02d:%02d" %(t[2],t[1],t[0],t[3],t[4],t[5])
        sTitle = 'EScan - %s ' % (sDate)
    
        # Parametrage du SoleilPlotBrick
        scanParameter = {}
        scanParameter['title'] = sTitle        
        scanParameter['xlabel'] = "Energy in keV"
        scanParameter['ylabel'] = "Normalized counts"
        self.parent.newScan(scanParameter)    
        
        # Pre-positioning the motor     
        if  not self.parent.scanning :
            return
        try :
            while str(sMotorDevice.State()) == 'MOVING':
                time.sleep(1)            
            sMotorDevice.write_attribute(sMotor[1], sStart) 
        except :
            print "probleme sMotor"
            self.parent.scanCommandFailed()    
        # while (sMotorDevice.State == 'MOVING')
        
        # complete record of the collect MS 23.05.2013
        # How to represent a fluorescence emission spectra record
        # Element, Edge, DateTime, Total accumulation time per data point, Number of recordings per data point 
        # DataPoints: Undulator energy, Mono energy, ROI counts, InCounts, OutCounts, Transmission, XBPM1 intensity, counts for all Channels
        #collectRecord = {}
        #time_format = "%04d-%02d-%02d - %02d:%02d:%02d"
        #DateTime = time_format % (t[0], t[1], t[2], t[3], t[4], t[5])
        
        #collectRecord['DateTime'] = DateTime
        #collectRecord['Edge'] = self.parent.edge
        #collectRecord['Element'] = self.parent.element
        #collectRecord['TheoreticalEdge'] = self.parent.thEdge
        #collectRecord['ROIwidth'] = self.parent.roiwidth
        #collectRecord['ROIcenter'] = self.roi_center
        #collectRecord['ROIStartsEnds'] = self.roisStartsEnds
        #collectRecord['IntegrationTime'] = integrationTime
        #collectRecord['StabilisationTime'] = stabilisationTime
        #collectRecord['Transmission'] = ''c
        #collectRecord['Filter'] = ''
        #collectRecord['DataPoints'] = {}
        
        # Ecriture de l'entete du fichier
        try :
            f = open(sFileName, "w")
        except :
            print "probleme ouverture fichier"
            self.parent.scanCommandFailed()
            return
        
        f.write("# %s\n" % (sTitle))
        f.write("# Motor  = %s\n" % sMotorDevice.name())
        # On insere les valeurs normalisees dans le deuxieme colonne
        f.write("# Normalized value\n")
        
        for sSensor in sSensorDevices:
            print "type(sSensor) = " ,type(sSensor)
            f.write("# %s\n" % (sSensor[0].name()))
        
        f.write("# Counts on the fluorescence detector: all channels")
        f.write("# Counts on the fluorescence detector: channels up to end of ROI")
        
        tDebut = time.time()
        
        # On ajoute un sensor pour la valeur normalisee (specifique au EScan)
        nbSensors = nbSensors + 1
        fmt_f = "%12.4e" + (nbSensors + 3)*"%12.4e" + "\n"
        _ln = 0
        
        channel_debut, channel_end = self.parent.fluodetdevice.roisStartsEnds
        # Entering the Scan loop
        measurement = 0
        for sI in range(nbSteps): #range(nbSteps): MS. 11.03.2013 lower the number for quick tests
            print 'Step sI', sI, 'of', nbSteps
            # test sur l utilisateur n a pas demande un stop
            if  not self.parent.scanning :
                break
            pos_i = sStart + (sI * sStepSize)
            
            # positionnement du moteur
            while str(sMotorDevice.State()) == 'MOVING':
                time.sleep(1)
            sMotorDevice.write_attribute(sMotor[1], pos_i) #sMotorDevice.__setattr__(sMotor[1], pos_i)
            
            
            # opening the fast shutter
            self.parent.fastshutterdevice.Open()
            #self.parent.md2device.OpenFastShutter() #write_attribute('FastShutterIsOpen', 1)
            #while self.parent.md2device.read_attribute('FastShutterIsOpen') != 1:
                #time.nsleep(0.05)  
                
            # Attente de stabilisation 
            #time.sleep(stabilisationTime)
            
            # starting the measurement for the energy step
            #miniSteps = 3
            roiCounts = 0
            intensity = 0
            eventsInRun = 0
            eventsInRun_upToROI = 0
            eventsInRun_diffusion = 0
            for mS in range(self.miniSteps):
                measurement += 1
                self.parent.fluodetdevice.Start()
                time.sleep(0.1)
                #self.parent.counterdevice.Start()
                #time.sleep(integrationTime/self.miniSteps)
                #while self.parent.counterdevice.State().name != 'STANDBY':
                    #pass
                #self.parent.fluodetdevice.Abort()
                while self.parent.fluodetdevice.State().name != 'STANDBY':
                    time.sleep(0.1)
#                    pass
#                roiCounts += self.parent.fluodetdevice.roi00_01
                roiCounts += self.parent.fluodetdevice.roi02_01
                intensity += self.parent.xbpmdevice.intensity
                eventsInRun += self.parent.fluodetdevice.eventsInRun02
                #print 5*'\n'
                #print 'realTime00', self.parent.fluodetdevice.realTime00
                #print 5*'\n'
#                eventsInRun_upToROI += sum(self.parent.fluodetdevice.channel00[ :channel_end + 1])
                eventsInRun_upToROI += sum(self.parent.fluodetdevice.channel02[ :channel_end + 1])
                eventsInRun_diffusion += sum(self.parent.fluodetdevice.channel02[ channel_end + 50 :])
                #collectRecord['DataPoints'][measurement] = {}
                #collectRecord['DataPoints'][measurement]['MonoEnergy'] = pos_i
                #collectRecord['DataPoints'][measurement]['ROICounts']  = self.parent.fluodetdevice.roi00_01
                
            #Lecture de la position du moteur            
            pos_readed = sMotorDevice.read_attribute(sMotor[1]).value #__getattr__(sMotor[1])
            
            # On laisse une place pour mettre la valeur normalisee (specifique au EScan)
            measures = [pos_readed, -1.0]
            print "Position: %12.4e   Measures: " % pos_readed
            
            # Lecture des differents sensors           
            measures.append(roiCounts) #measures[2]#(self.parent.fluodetdevice.roi00_01) #eventsInRun00)
            measures.append(intensity) #measures[3]#(self.parent.xbpmdevice.intensity)
            measures.append(eventsInRun) #measures[4]#(self.parent.fluodetdevice.eventsInRun00)
            measures.append(eventsInRun_upToROI)#measures[5]
            measures.append(eventsInRun_diffusion)
            # closing the fastshutter
            self.parent.fastshutterdevice.Close() 
            #self.parent.md2device.CloseFastShutter() #write_attribute('FastShutterIsOpen', 0)
            #while self.parent.md2device.read_attribute('FastShutterIsOpen') != 0:
                #time.sleep(0.05)
               
            # Valeur normalisee specifique au EScan 
            #(Oblige an mettre le sensor compteur en premier et le xbpm en deuxieme dans le liste des sensors)               
            try:
                measures[1] = measures[2] / measures[6] #measures[3]  
#                measures[1] = measures[2] / measures[3]   
#                measures[1] = measures[2]   
            except ZeroDivisionError, e:
                print e
                print 'Please verify that the safety shutter is open.'
                measures[1] = 0.0
            
            # Demande de mise a jour du SoleilPlotBrick
            #if sI % 5 == 0:
            self.parent.newPoint(measures[0], measures[1])    
              
            
            #Ecriture des mesures dans le fichier
            f.write(fmt_f % tuple(measures))
            
            _ln += 1
            if not _ln % 10:
                f.flush() # flush the buffer every 10 lines
        
        # Exiting the Scan loop      
        self.parent.fastshutterdevice.Close()
#        while self.parent.fastshutterdevice.State != 'CLOSE':
#            time.sleep(0.1)
#        self.parent.md2device.CloseFastShutter() 
        #while self.parent.md2device.read_attribute('FastShutterIsOpen') != 0:
            #time.sleep(0.05)
        
        self.parent.fluodetdevice.Abort()
        
#        self.parent.md2device.write_attribute('FluoDetectorBack', 1)
#        time.sleep(2)
        #self.parent.mono_mt_rx_device.On()
        if  not self.parent.scanning :
            self.result = -1
        else :
            self.result = 1

        tScanTotal = time.time() - tDebut
        print "Time taken for the scan = %.2f sec" % (tScanTotal)
        f.write("# Duration = %.2f sec\n" % (tScanTotal))
        f.close()

    def afterScan(self) :
        logging.getLogger("HWR").debug('EnergyScanThread:afterScan')
#        self.parent.safetyshutterdevice.Close()
        if self.parent.pk :
            self.parent.startMoveEnergy(self.parent.pk)
            
