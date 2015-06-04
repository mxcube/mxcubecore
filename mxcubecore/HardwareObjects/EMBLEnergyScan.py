"""
Descript. :
"""

import os
import time
import gevent
import logging
import PyChooch
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from HardwareRepository.TaskUtils import *
from HardwareRepository.BaseHardwareObjects import Equipment

class EMBLEnergyScan(Equipment):
    """
    Descript. :
    """
    def __init__(self, name):
        """
        Descript. :
        """
        Equipment.__init__(self, name)
        self.can_scan = None
        self.ready_event = None
        self.scanning = False
        self.energy_motor = None
        self.archive_prefix = None
        self._element = None
        self._edge = None
        self.thEdge = None
        self.previousResolution = None
        self.lastResolution = None
        self.scanData = None
        
        self.energy2WavelengthConstant = None
        self.defaultWavelength = None
        self.thEdgeThreshold = None     

        self.energy_motor_hwobj = None
        self.db_connection_hwobj = None
        self.mach_current_hwobj = None
        self.beam_info_hwobj = None

        self.chan_scan_start = None
        self.chan_scan_status = None
        self.cmd_scan_abort = None

    def init(self):
        """
        Descript. :
        """
        self.ready_event = gevent.event.Event()
        self.scanInfo = {}

        self.energy2WavelengthConstant = self.getProperty("energy2WavelengthConstant")
        self.defaultWavelength = self.getProperty("defaultWavelength")
        self.thEdgeThreshold = self.getProperty("theoritical_edge_threshold")

        if self.thEdgeThreshold:
            self.thEdgeThreshold = 0.01
	
        self.energy_motor_hwobj = self.getObjectByRole("energy")
        if self.energy_motor_hwobj:
            self.energy_motor_hwobj.connect('positionChanged', 
                                         self.energyPositionChanged)
            self.energy_motor_hwobj.connect('limitsChanged', 
                                         self.energyLimitsChanged)

        self.db_connection_hwobj = self.getObjectByRole("dbserver")
        if self.db_connection_hwobj is None:
            logging.getLogger("HWR").warning('EMBLEnergyScan: Database hwobj not defined')

        self.mach_current_hwobj = self.getObjectByRole("machcurrent")
        if self.mach_current_hwobj is None:
            logging.getLogger("HWR").warning('EMBLEnergyScan: Machine current hwobj not defined')

        self.beam_info_hwobj = self.getObjectByRole("beam_info")
        if self.beam_info_hwobj is None:
            logging.getLogger("HWR").warning('EMBLEnergyScan: Beam info hwobj not defined')

        try:  
            self.chan_scan_start = self.getChannelObject('energyScanStart')
            self.chan_scan_start.connectSignal('update', self.scan_start_update)
            self.chan_scan_status = self.getChannelObject('energyScanStatus')
            self.chan_scan_status.connectSignal('update', self.scan_status_update)
            self.cmd_scan_abort = self.getCommandObject('energyScanAbort')

            self.can_scan = True
        except:
            logging.getLogger("HWR").warning('EMBLEnergyScan: unable to connect to scan channel(s)')
         
        if self.isConnected():
            self.sConnected()

    def scan_start_update(self, values):
        """
        Descript. :
        """
        if self.scanning:
            self.emitNewDataPoint(values)

    def scan_status_update(self, status):
        """
        Descript. :
        """
        if self.scanning:	
            if status == 'scanning':
                logging.getLogger("HWR").info('Executing energy scan...')
            elif status == 'ready':
                if self.scanning is True:
                    self.scanCommandFinished()
                    logging.getLogger("HWR").info('Energy scan finished')
            elif status == 'aborting':
                if self.scanning is True:
                    self.scanCommandAborted()
                    logging.getLogger("HWR").info('Energy scan aborted')	
            elif status == 'error':
                self.scanCommandFailed()  	
                logging.getLogger("HWR").error('Energy scan failed')
	    	
    def scanTransmissionUpdate(self, value):
        """
        Descript. :
        """
        if self.scanning:
            self.scanInfo['transmissionFactor'] = float(value) 

    def emitNewDataPoint(self, values):
        """
        Descript. :
        """ 
        if len(values) > 0:
            try:
                x = values[-1][0]
                y = values[-1][1]
                if not (x == 0 and y == 0):	
                    # if x is in keV, transform into eV otherwise let it like it is
	            # if point larger than previous point (for chooch)
                    if len(self.scanData) > 0: 
                        if x > self.scanData[-1][0]:
                            self.scanData.append([(x < 1000 and x*1000.0 or x), y])
                    else:
                        self.scanData.append([(x < 1000 and x*1000.0 or x), y])
                    self.emit('scanNewPoint', ((x < 1000 and x*1000.0 or x), y, ))	
            except:
                pass

    def isConnected(self):
        """
        Descript. :
        """
        return True

    def sConnected(self):
        """
        Descript. :
        """
        self.emit('connected', ())

    def sDisconnected(self):
        """
        Descript. :
        """
        self.emit('disconnected', ())

    def canScanEnergy(self):
        """
        Descript. :
        """
        return self.isConnected()

    def startEnergyScan(self, element, edge, directory, prefix, \
                 session_id= None, blsample_id= None, exptime= 3):
        """
        Descript. :
        """
        if not self.can_scan:
            logging.getLogger("HWR").error("EnergyScan: unable to start energy scan")
            self.scanCommandAborted() 
            return
 
        self._element = element
        self._edge = edge
        self.scanInfo = {"sessionId": session_id, "blSampleId": blsample_id,
                       "element": element,"edgeEnergy": edge}
        self.scanData = []
        if not os.path.isdir(directory):
            logging.getLogger("HWR").debug("EnergyScan: creating directory %s" % directory)
            try:
                os.makedirs(directory)
            except OSError, diag:
                logging.getLogger("HWR").error("EnergyScan: error creating directory %s (%s)" % (directory, str(diag)))
                self.emit('energyScanStatusChanged', ("Error creating directory",))
                return False
        try:
            if self.chan_scan_status.getValue() == 'ready':	
                self.scanInfo['transmissionFactor'] = 0
                self.scanInfo['exposureTime'] = exptime
                self.scanInfo['startEnergy'] = 0
                self.scanInfo['endEnergy'] = 0
                self.scanInfo['beamSizeHorizontal'], self.scanInfo['beamSizeVertical'] = self.beam_info_hwobj.get_beam_size()
                self.chan_scan_start.setValue("%s;%s" % (element, edge))
                self.scanCommandStarted()
            else:
                logging.getLogger("HWR").error('Another energy scan in progress. Please wait when the scan is finished')
        except:
            logging.getLogger("HWR").error('EnergyScan: error in executing energy scan command')
            self.emit('energyScanStatusChanged', ("Error in executing energy scan command",))
            self.scanCommandFailed()
            return False
        return True

    def cancelEnergyScan(self, *args):
        """
        Descript. :
        """
        if self.scanning:
            self.cmd_scan_abort()
            self.scanCommandAborted()

    def scanCommandReady(self):
        """
        Descript. :
        """ 
        if not self.scanning:
            self.emit('energyScanReady', (True,))

    def scanCommandNotReady(self):
        """
        Descript. :
        """
        if not self.scanning:
            self.emit('energyScanReady', (False,))

    def scanCommandStarted(self, *args):
        """
        Descript. :
        """
        title = "%s %s: %s %s" % (self.scanInfo["sessionId"], 
            self.scanInfo["blSampleId"], self.scanInfo["element"], self.scanInfo["edgeEnergy"])
        dic = {'xlabel': 'energy', 'ylabel': 'counts', 'scaletype': 'normal', 'title': title}
        self.emit('scanStart', (dic, ))
        self.scanInfo['startTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = True
        self.emit('energyScanStarted', ())

    def scanCommandFailed(self, *args):
        """
        Descript. :
        """
        self.scanInfo['endTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = False
        self.store_energy_scan()
        self.emit('energyScanFailed', ())
        self.ready_event.set()

    def scanCommandAborted(self, *args):
        """
        Descript. :
        """
        self.scanning = False
        self.emit('energyScanFailed', ())
        self.ready_event.set()

    def scanCommandFinished(self, *args):
        """
        Descript. :
        """
        with cleanup(self.ready_event.set):
            self.scanInfo['endTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
            logging.getLogger("HWR").debug("EMBLEnergyScan: energy scan finished")
            self.scanning = False
            self.scanInfo["startEnergy"] = self.scanData[-1][0]
            self.scanInfo["endEnergy"] = self.scanData[-1][1]
            self.emit('energyScanFinished', (self.scanInfo,))

    def doChooch(self, elt, edge, scanArchiveFilePrefix, scanFilePrefix):
        """
        Descript. :
        """
        symbol = "_".join((elt, edge))
        scanArchiveFilePrefix = "_".join((scanArchiveFilePrefix, symbol))
        i = 1
        while os.path.isfile(os.path.extsep.join((scanArchiveFilePrefix + str(i), "raw"))):
            i = i + 1
        scanArchiveFilePrefix = scanArchiveFilePrefix + str(i) 
        archiveRawScanFile = os.path.extsep.join((scanArchiveFilePrefix, "raw"))
        rawScanFile = os.path.extsep.join((scanFilePrefix, "raw"))
        scanFile = os.path.extsep.join((scanFilePrefix, "efs"))
        if not os.path.exists(os.path.dirname(scanArchiveFilePrefix)):
            os.makedirs(os.path.dirname(scanArchiveFilePrefix))
        try:
            f = open(rawScanFile, "w")
            pyarch_f = open(archiveRawScanFile, "w")
        except:
            logging.getLogger("HWR").exception("could not create raw scan files")
            self.store_energy_scan()
            self.emit("energyScanFailed", ())
            return
        else:
            scanData = []
            for i in range(len(self.scanData)):
                x = float(self.scanData[i][0])
                x = x < 1000 and x * 1000.0 or x 
                y = float(self.scanData[i][1])
                scanData.append((x, y))
                f.write("%f,%f\r\n" % (x, y))
                pyarch_f.write("%f,%f\r\n" % (x, y)) 
            f.close()
            pyarch_f.close()
            self.scanInfo["scanFileFullPath"] = str(archiveRawScanFile)

        pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, chooch_graph_data = PyChooch.calc(scanData, elt, edge, scanFile)
        rm = (pk + 30) / 1000.0
        pk = pk / 1000.0
        savpk = pk
        ip = ip / 1000.0
        comm = ""
        logging.getLogger("HWR").info("th. Edge %s ; chooch results are pk=%f, ip=%f, rm=%f" %\
               (self.thEdgeThreshold, pk, ip, rm))

        """if math.fabs(self.thEdge - ip) > self.thEdgeThreshold:
          pk = 0
          ip = 0
          rm = self.thEdge + 0.03
          comm = 'Calculated peak (%f) is more that 10eV away from the theoretical value (%f). Please check your scan' % (savpk, self.thEdge)
   
          logging.getLogger("HWR").warning('EMBLEnergyScan: calculated peak (%f) is more that 20eV %s the theoretical value (%f). Please check your scan and choose the energies manually' % (savpk, (self.thEdge - ip) > 0.02 and "below" or "above", self.thEdge))"""

        archiveEfsFile = os.path.extsep.join((scanArchiveFilePrefix, "efs"))
        try:
            fi = open(scanFile)
            fo = open(archiveEfsFile, "w")
        except:
            self.store_energy_scan()
            self.emit("energyScanFailed", ())
            return
        else:
            fo.write(fi.read())
            fi.close()
            fo.close()

        self.scanInfo["peakEnergy"] = pk
        self.scanInfo["inflectionEnergy"] = ip
        self.scanInfo["remoteEnergy"] = rm
        self.scanInfo["peakFPrime"] = fpPeak
        self.scanInfo["peakFDoublePrime"] = fppPeak
        self.scanInfo["inflectionFPrime"] = fpInfl
        self.scanInfo["inflectionFDoublePrime"] = fppInfl
        self.scanInfo["comments"] = comm

        chooch_graph_x, chooch_graph_y1, chooch_graph_y2 = zip(*chooch_graph_data)
        chooch_graph_x = list(chooch_graph_x)
        for i in range(len(chooch_graph_x)):
            chooch_graph_x[i] = chooch_graph_x[i] / 1000.0

        logging.getLogger("HWR").info("<chooch> Saving png" )
        # prepare to save png files
        title = "%10s  %6s  %6s\n%6.2f  %6.2f  %6.2f\n%6.2f  %6.2f  %6.2f" % \
              ("energy", "f'", "f''", pk, fpPeak, fppPeak, ip, fpInfl, fppInfl) 
        fig = Figure(figsize = (15, 11))
        ax = fig.add_subplot(211)
        ax.set_title("%s\n%s" % (scanFile, title))
        ax.grid(True)
        ax.plot(*(zip(*scanData)), **{"color": 'black'})
        ax.set_xlabel("Energy")
        ax.set_ylabel("MCA counts")
        ax2 = fig.add_subplot(212)
        ax2.grid(True)
        ax2.set_xlabel("Energy")
        ax2.set_ylabel("")
        handles = []
        handles.append(ax2.plot(chooch_graph_x, chooch_graph_y1, color = 'blue'))
        handles.append(ax2.plot(chooch_graph_x, chooch_graph_y2, color = 'red'))
        canvas = FigureCanvasAgg(fig)

        escan_png = os.path.extsep.join((scanFilePrefix, "png"))
        escan_archivepng = os.path.extsep.join((scanArchiveFilePrefix, "png")) 
        self.scanInfo["jpegChoochFileFullPath"] = str(escan_archivepng)
        try:
            logging.getLogger("HWR").info("Rendering energy scan and Chooch graphs to PNG file : %s", escan_png)
            canvas.print_figure(escan_png, dpi = 80)
        except:
            logging.getLogger("HWR").exception("could not print figure")
        try:
            logging.getLogger("HWR").info("Saving energy scan to archive directory for ISPyB : %s", escan_archivepng)
            canvas.print_figure(escan_archivepng, dpi = 80)
        except:
            logging.getLogger("HWR").exception("could not save figure")

        self.store_energy_scan()

        logging.getLogger("HWR").info("<chooch> returning" )
        self.emit('choochFinished', (pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, 
                 rm, chooch_graph_x, chooch_graph_y1, chooch_graph_y2, title))
        return pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, rm, chooch_graph_x, \
                 chooch_graph_y1, chooch_graph_y2, title

    def scanStatusChanged(self, status):
        """
        Descript. :
        """
        self.emit('energyScanStatusChanged', (status,))

    def updateEnergyScan(self, scan_id, jpeg_scan_filename):
        """
        Descript. :
        """
        pass

    def canMoveEnergy(self):
        """
        Descript. :
        """
        return self.canScanEnergy()
    
    def getCurrentEnergy(self):
        """
        Descript. :
        """
        if self.energy_motor_hwobj is not None:
            try:
                return self.energy_motor_hwobj.getPosition()
            except: 
                logging.getLogger("HWR").exception("EnergyScan: couldn't read energy")
                return None
        elif self.energy2WavelengthConstant is not None and self.defaultWavelength is not None:
            return self.energy2wavelength(self.defaultWavelength)
        return None

    def get_value(self):
        """
        Descript. :
        """
        return self.getCurrentEnergy()
   
    def getEnergyLimits(self):
        """
        Descript. :
        """
        lims = None
        if self.energy_motor_hwobj is not None:
            if self.energy_motor_hwobj.isReady():
                lims = self.energy_motor_hwobj.getLimits()
        return lims

    def getCurrentWavelength(self):
        """
        Descript. :
        """
        if self.energy_motor_hwobj is not None:
            try:
                return self.energy2wavelength(self.energy_motor_hwobj.getPosition())
            except:
                logging.getLogger("HWR").exception("EnergyScan: couldn't read energy")
                return None
        else:
            return self.defaultWavelength

    def getWavelengthLimits(self):
        """
        Descript. :
        """
        lims = None
        try:
            if self.energy_motor_hwobj is not None:
                if self.energy_motor_hwobj.isReady():
                    energy_lims = self.energy_motor_hwobj.getLimits()
                    lims = (self.energy2wavelength(energy_lims[1]), self.energy2wavelength(energy_lims[0]))
                    if lims[0] is None or lims[1] is None:
                        lims = None
        except:
            logging.getLogger("HWR").exception("EnergyScan: couldn't read energy limits")
        return lims
    
    def energy2wavelength(self, value):
        """
        Descript. :
        """
        if self.energy2WavelengthConstant is None:
            return None
        try:
            other_val = self.energy2WavelengthConstant / value
        except ZeroDivisionError:
            other_val = None
        return other_val

    def energyPositionChanged(self, pos):
        """
        Descript. :
        """
        wav = self.energy2wavelength(pos)
        if wav is not None:
            self.emit('energyChanged', (pos, wav))
            self.emit('valueChanged', (pos, ))

    def energyLimitsChanged(self, limits):
        """
        Descript. :
        """
        self.emit('energyLimitsChanged', (limits, ))
        try:
            wav_limits = (self.energy2wavelength(limits[1]), self.energy2wavelength(limits[0]))
            if wav_limits[0] != None and wav_limits[1] != None:
                self.emit('wavelengthLimitsChanged', (wav_limits, ))
            else:
                self.emit('wavelengthLimitsChanged', (None, ))
        except:
            logging.getLogger("HWR").exception("EnergyScan: couldn't read energy limits") 	
            self.emit('wavelengthLimitsChanged', (None, ))	

    def getElements(self):
        """
        Descript. :
        """
        elements = []
        try:
            for el in self["elements"]:
                elements.append({"symbol":el.symbol, "energy":el.energy})
        except IndexError:
            pass
        return elements

    # Mad energies commands
    def getDefaultMadEnergies(self):
        """
        Descript. :
        """
        energies = []
        try:
            for el in self["mad"]:
                energies.append([float(el.energy), el.directory])
        except IndexError:
            pass
        return energies

    def get_scan_data(self):
        """
        Descript. :
        """
        return self.scanData 

    def store_energy_scan(self):
        """
        Descript. :
        """
        blsampleid = self.scanInfo['blSampleId']
        self.scanInfo.pop('blSampleId')
        if self.db_connection_hwobj:
            db_status = self.db_connection_hwobj.storeEnergyScan(self.scanInfo)
            if blsampleid is not None:
                try:
                    energyscanid = int(db_status['energyScanId'])
                except:
                    pass
                else:
                    asoc = {'blSampleId':blsampleid, 'energyScanId': energyscanid}
                    self.db_connection_hwobj.associateBLSampleAndEnergyScan(asoc)
