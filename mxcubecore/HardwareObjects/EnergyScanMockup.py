import os
import time
import gevent
import logging

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from HardwareRepository.TaskUtils import *
from HardwareRepository.BaseHardwareObjects import Equipment

try:
   import PyChooch
except:
   print ("PyChooch not found")

scan_test_data = [(10841.0, 20.0), (10842.0, 20.0), (10843.0, 20.0), 
(10844.0, 20.0), (10845.0, 20.0), (10846.0, 20.0), (10847.0, 20.0), 
(10848.0, 20.0), (10849.0, 20.0), (10850.0, 20.0), (10851.0, 20.0), 
(10852.0, 20.0), (10853.0, 20.0), (10854.0, 20.0), (10855.0, 20.0), 
(10856.0, 20.0), (10857.0, 20.0), (10858.0, 20.00), (10859.0, 20.0),
(10860.0, 20.0), (10861.0, 20.1), (10862.0, 21.4), (10863.0, 30.4), 
(10864.9, 80.7), (10865.9, 299.0), (10866.7, 820.8), (10867.5, 2009.2), 
(10868.2, 4305.5), (10869.0, 8070.2), (10869.8, 13246.7), (10870.6, 19124.1), 
(10871.4, 24430.5), (10872.2, 27843.1), (10873.0, 28654.8), (10873.8, 27092.5), 
(10874.6, 24138.5), (10875.4, 20957.3), (10876.0, 18373.6), (10877.0, 16373.8), 
(10878.0, 15474.8), (10879.0, 15163.9), (10880.0, 15080.5), (10881.0, 15063.0), 
(10882.0, 15060.3), (10883.0, 15059.8), (10884.0, 15059.7), (10885.0, 15059.0),
(10886.0, 15059.0), (10887.0, 15059.0), (10888.0, 15059.0), (10889.0, 15059.0), 
(10890.0, 15059.0), (10891.0, 15059.0), (10892.0, 15059.0), (10893.0, 15059.0), 
(10894.0, 15059.0), (10895.0, 15059.0), (10896.0, 15059.0), (10897.0, 15059.0), 
(10898.0, 15059.0), (10899.0, 15059.0), (10900.0, 15059.0), (10901.0, 15059.0), 
(10902.0, 15059.0), (10903.0, 15059.0), (10904.0, 15059.0), (10905.0, 15059.0), 
(10906.0, 15059.0), (10907.0, 15059.0), (10908.0, 15059.0), (10909.0, 15059.0), 
(10910.0, 15059.0)]


class EnergyScanMockup(Equipment):
    def init(self):
        self.ready_event = gevent.event.Event()
        self.scan_info = {}
        self.result_value_emitter = None
        self.scan_data = []
        self.thEdgeThreshold = 5
        self.energy2WavelengthConstant = 12.3980
        self.defaultWavelength = 0.976 

    def emit_result_values(self):
        for value_tuple in scan_test_data:
            x = value_tuple[0]
            y = value_tuple[1]
            if not (x == 0 and y == 0):
                # if x is in keV, transform into eV otherwise let it like it is
                # if point larger than previous point (for chooch)
                if len(self.scan_data) > 0:
                    if x > self.scan_data[-1][0]:
                        self.scan_data.append([(x < 1000 and x*1000.0 or x), y])
                else:
                    self.scan_data.append([(x < 1000 and x*1000.0 or x), y])
                self.emit('scanNewPoint', (x < 1000 and x*1000.0 or x), y)
            time.sleep(0.05)
        self.scanCommandFinished()

    def startEnergyScan(self, element, edge, directory, prefix,
                        session_id = None, blsample_id= None, exptime= 3):

        self._element = element
        self._edge = edge
        self.scan_info = {"sessionId": session_id, "blSampleId": blsample_id,
                         "element": element,"edgeEnergy": edge}
        self.scan_info['transmissionFactor'] = 0
        self.scan_info['exposureTime'] = exptime
        self.scan_info['startEnergy'] = 0
        self.scan_info['endEnergy'] = 0
        self.scan_info['beamSizeHorizontal'] = 0
        self.scan_info['beamSizeVertical'] = 0
        self.scan_data = []
        self.scanCommandStarted()
        self.result_value_emitter = gevent.spawn(self.emit_result_values)
        #self.emit('energyScanFinished', (self.scan_info,))
        #self.ready_event.set()

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
            for i in range(len(self.scan_data)):
                x = float(self.scan_data[i][0])
                x = x < 1000 and x * 1000.0 or x
                y = float(self.scan_data[i][1])
                scanData.append((x, y))
                f.write("%f,%f\r\n" % (x, y))
                pyarch_f.write("%f,%f\r\n" % (x, y))
            f.close()
            pyarch_f.close()
            self.scan_info["scanFileFullPath"] = str(archiveRawScanFile)

        
        pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, chooch_graph_data = PyChooch.calc(scanData, elt, edge, scanFile)

        rm = (pk + 30) / 1000.0
        pk = pk / 1000.0
        savpk = pk
        ip = ip / 1000.0
        comm = ""
        logging.getLogger("HWR").info("th. Edge %s ; chooch results are pk=%f, ip=%f, rm=%f" %\
               (self.thEdgeThreshold, pk, ip, rm))
        
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

        self.scan_info["peakEnergy"] = pk
        self.scan_info["inflectionEnergy"] = ip
        self.scan_info["remoteEnergy"] = rm
        self.scan_info["peakFPrime"] = fpPeak
        self.scan_info["peakFDoublePrime"] = fppPeak
        self.scan_info["inflectionFPrime"] = fpInfl
        self.scan_info["inflectionFDoublePrime"] = fppInfl
        self.scan_info["comments"] = comm

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
        self.scan_info["jpegChoochFileFullPath"] = str(escan_archivepng)
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
        self.emit('choochFinished', pk, fppPeak, fpPeak, ip, fppInfl, fpInfl,
                 rm, chooch_graph_x, chooch_graph_y1, chooch_graph_y2, title)
        return pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, rm, chooch_graph_x, \
                 chooch_graph_y1, chooch_graph_y2, title

    def getCurrentEnergy(self):
        return 12


    def getCurrentWavelength(self):
        return 12


    def getElements(self):
        elements=[]
        try:
            for el in self["elements"]:
                elements.append({"symbol":el.symbol, "energy":el.energy})
        except IndexError:
            pass
        return elements

    def getDefaultMadEnergies(self):
        energies=[]
        try:
            for el in self["mad"]:
                energies.append([float(el.energy), el.directory])
        except IndexError:
            pass
        return energies


    def canMoveEnergy(self):
        return False
    

    def isConnected(self):
        return True

    def scanCommandStarted(self, *args):
        """
        Descript. :
        """
        title = "%s %s: %s %s" % (self.scan_info["sessionId"],
            self.scan_info["blSampleId"], self.scan_info["element"], self.scan_info["edgeEnergy"])
        dic = {'xlabel': 'energy', 'ylabel': 'counts', 'scaletype': 'normal', 'title': title}
        self.emit('scanStart', dic)
        self.scan_info['startTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = True
        self.emit('energyScanStarted')

    def scanCommandFinished(self, *args):
        """
        Descript. :
        """
        with cleanup(self.ready_event.set):
            self.scan_info['endTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
            logging.getLogger("HWR").debug("EMBLEnergyScan: energy scan finished")
            self.scanning = False
            self.scan_info["startEnergy"] = self.scan_data[-1][0]
            self.scan_info["endEnergy"] = self.scan_data[-1][1]
            self.emit('energyScanFinished', self.scan_info)

    def get_scan_data(self):
        """
        Descript. :
        """
        return self.scan_data

    def store_energy_scan(self):
        """
        Descript. :
        """
        return 
