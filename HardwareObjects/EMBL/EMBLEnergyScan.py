"""
Descript. :
"""

import os
import math
import time
import gevent
import logging
import PyChooch
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from AbstractEnergyScan import AbstractEnergyScan
from HardwareRepository.TaskUtils import *
from HardwareRepository.BaseHardwareObjects import HardwareObject

class EMBLEnergyScan(AbstractEnergyScan, HardwareObject):

    def __init__(self, name):
        AbstractEnergyScan.__init__(self)
        HardwareObject.__init__(self, name)
        self._tunable_bl = True

        self.can_scan = None
        self.ready_event = None
        self.scanning = False
        self.energy_motor = None
        self.archive_prefix = None
        self.thEdge = None
        self.scanData = None
        
        self.db_connection_hwobj = None
        self.transmission_hwob = None
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

        self.db_connection_hwobj = self.getObjectByRole("dbserver")
        if self.db_connection_hwobj is None:
            logging.getLogger("HWR").warning('EMBLEnergyScan: Database hwobj not defined')

        self.transmission_hwobj = self.getObjectByRole("transmission")
        if self.transmission_hwobj is None:
            logging.getLogger("HWR").warning('EMBLEnergyScan: Transmission hwobj not defined')

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

    """def sConnected(self):
        self.emit('connected', ())

    def sDisconnected(self):
        self.emit('disconnected', ())"""

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
            if self.chan_scan_status.getValue() in ['ready', 'unknown', 'error']:	
                if self.transmission_hwobj is not None:
                    self.scanInfo['transmissionFactor'] = self.transmission_hwobj.get_value()
                else:
                    self.scanInfo['transmissionFactor'] = None
                self.scanInfo['exposureTime'] = exptime
                self.scanInfo['startEnergy'] = 0
                self.scanInfo['endEnergy'] = 0
                size_hor = None
                size_ver = None
                if self.beam_info_hwobj is not None:
                    size_hor, size_ver = self.beam_info_hwobj.get_beam_size()
                    size_hor = size_hor * 1000
                    size_ver = size_ver * 1000
                self.scanInfo['beamSizeHorizontal'] = size_hor
                self.scanInfo['beamSizeVertical'] = size_ver
                self.chan_scan_start.setValue("%s;%s" % (element, edge))
                self.scanCommandStarted()
            else:
                logging.getLogger("HWR").error('Another energy scan in progress. Please wait when the scan is finished')
                self.emit('energyScanStatusChanged', ("Another energy scan in progress. Please wait when the scan is finished"))
                self.scanCommandFailed()
                return False
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

    def doChooch(self, elt, edge, scan_directory, archive_directory, prefix):
        """
        Descript. :
        """
        symbol = "_".join((elt, edge))
        scan_file_prefix = os.path.join(scan_directory, prefix) 
        archive_file_prefix = os.path.join(archive_directory, prefix)

        if os.path.exists(scan_file_prefix + ".raw"):
            i = 1
            while os.path.exists(scan_file_prefix + "%d.raw" %i):
                  i = i + 1
            scan_file_prefix += "_%d" % i
            archive_file_prefix += "_%d" % i
       
        scan_file_raw_filename = os.path.extsep.join((scan_file_prefix, "raw"))
        archive_file_raw_filename = os.path.extsep.join((archive_file_prefix, "raw"))
        scan_file_efs_filename = os.path.extsep.join((scan_file_prefix, "efs"))
        archive_file_efs_filename = os.path.extsep.join((archive_file_prefix, "efs"))
        scan_file_png_filename = os.path.extsep.join((scan_file_prefix, "png"))
        archive_file_png_filename = os.path.extsep.join((archive_file_prefix, "png"))

        try:
            if not os.path.exists(scan_directory):
                os.makedirs(scan_directory)
            if not os.path.exists(archive_directory):
                os.makedirs(archive_directory)
        except:
            logging.getLogger("HWR").exception("EMBLEnergyScan: could not create energy scan result directory.")
            self.store_energy_scan()
            self.emit("energyScanFailed", ())
            return

        try:
            scan_file_raw = open(scan_file_raw_filename, "w")
            archive_file_raw = open(archive_file_raw_filename, "w")
        except:
            logging.getLogger("HWR").exception("EMBLEnergyScan: could not create energy scan result raw file")
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
                scan_file_raw.write("%f,%f\r\n" % (x, y))
                archive_file_raw.write("%f,%f\r\n" % (x, y)) 
            scan_file_raw.close()
            archive_file_raw.close()
            self.scanInfo["scanFileFullPath"] = str(scan_file_raw_filename)

        pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, chooch_graph_data = \
             PyChooch.calc(scanData, elt, edge, scan_file_efs_filename)

        rm = (pk + 30) / 1000.0
        pk = pk / 1000.0
        savpk = pk
        ip = ip / 1000.0
        comm = ""
        #IK TODO clear this
        self.scanInfo['edgeEnergy'] = 0.1
        self.thEdge = self.scanInfo['edgeEnergy']
        logging.getLogger("HWR").info("th. Edge %s ; chooch results are pk=%f, ip=%f, rm=%f" % (self.thEdge, pk,ip,rm))

        #should be better, but OK for time being
        self.thEdgeThreshold = 0.01
        if math.fabs(self.thEdge - ip) > self.thEdgeThreshold:
          pk = 0
          ip = 0
          rm = self.thEdge + 0.03
          comm = 'Calculated peak (%f) is more that 10eV away from the theoretical value (%f). Please check your scan' % \
                 (savpk, self.thEdge)

          logging.getLogger("HWR").warning('EnergyScan: calculated peak (%f) is more that 20eV %s the theoretical value (%f). Please check your scan and choose the energies manually' % \
                   (savpk, (self.thEdge - ip) > 0.02 and "below" or "above", self.thEdge))

        try:
            fi = open(scan_file_efs_filename)
            fo = open(archive_file_efs_filename, "w")
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

        #logging.getLogger("HWR").info("EMBLEnergyScan: Saving png" )
        # prepare to save png files
        title = "%s  %s  %s\n%.4f  %.2f  %.2f\n%.4f  %.2f  %.2f" % \
              ("energy", "f'", "f''", pk, fpPeak, fppPeak, ip, fpInfl, fppInfl) 
        fig = Figure(figsize = (15, 11))
        ax = fig.add_subplot(211)
        ax.set_title("%s\n%s" % (scan_file_efs_filename, title))
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

        self.scanInfo["jpegChoochFileFullPath"] = str(archive_file_png_filename)
        try:
            logging.getLogger("HWR").info("Rendering energy scan and Chooch graphs to PNG file : %s", scan_file_png_filename)
            canvas.print_figure(scan_file_png_filename, dpi = 80)
        except:
            logging.getLogger("HWR").exception("could not print figure")
        try:
            logging.getLogger("HWR").info("Saving energy scan to archive directory for ISPyB : %s", archive_file_png_filename)
            canvas.print_figure(archive_file_png_filename, dpi = 80)
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
