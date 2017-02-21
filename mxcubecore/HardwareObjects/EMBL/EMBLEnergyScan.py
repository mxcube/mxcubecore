#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
EMBLEnergyScan
"""

import os
import time
import gevent
import logging
import PyChooch
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from AbstractEnergyScan import AbstractEnergyScan
from HardwareRepository.BaseHardwareObjects import HardwareObject


__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]
__version__ = "2.3."


class EMBLEnergyScan(AbstractEnergyScan, HardwareObject):

    def __init__(self, name):
        """
        Descript. :
        """

        AbstractEnergyScan.__init__(self)
        HardwareObject.__init__(self, name)
        self._tunable_bl = True

        self.ready_event = None
        self.scanning = False
        self.energy_motor = None
        self.archive_prefix = None
        self.th_edge = None
        self.scan_data = None
        self.num_points = None
        self.scan_info = None

        self.energy_hwobj = None
        self.db_connection_hwobj = None
        self.transmission_hwobj = None
        self.beam_info_hwobj = None

        self.chan_scan_start = None
        self.chan_scan_status = None
        self.cmd_scan_abort = None

    def init(self):
        self.ready_event = gevent.event.Event()
        self.scan_info = {}

        self.energy_hwobj = self.getObjectByRole("energy")

        self.db_connection_hwobj = self.getObjectByRole("dbserver")
        if self.db_connection_hwobj is None:
            logging.getLogger("HWR").warning(\
                'EMBLEnergyScan: Database hwobj not defined')

        self.transmission_hwobj = self.getObjectByRole("transmission")
        if self.transmission_hwobj is None:
            logging.getLogger("HWR").warning(\
                'EMBLEnergyScan: Transmission hwobj not defined')

        self.beam_info_hwobj = self.getObjectByRole("beam_info")
        if self.beam_info_hwobj is None:
            logging.getLogger("HWR").warning(\
                'EMBLEnergyScan: Beam info hwobj not defined')

        self.chan_scan_start = self.getChannelObject('energyScanStart')
        self.chan_scan_start.connectSignal('update', self.scan_start_update)
        self.chan_scan_status = self.getChannelObject('energyScanStatus')
        self.chan_scan_status.connectSignal('update', self.scan_status_update)
        self.cmd_scan_abort = self.getCommandObject('energyScanAbort')

        self.num_points = self.getProperty("numPoints")

    def scan_start_update(self, values):
        if self.scanning:
            self.emit_new_data_point(values)

    def scan_status_update(self, status):
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

    def emit_new_data_point(self, values):
        if len(values) > 0:
            try:
                x = values[-1][0]
                y = values[-1][1]
                if not (x == 0 and y == 0):
                    # if x is in keV, transform into eV otherwise let it like it is
	            # if point larger than previous point (for chooch)
                    if len(self.scan_data) > 0:
                        if x > self.scan_data[-1][0]:
                            self.scan_data.append([(x < 1000 and x*1000.0 or x), y])
                    else:
                        self.scan_data.append([(x < 1000 and x*1000.0 or x), y])
                    self.emit('scanNewPoint', ((x < 1000 and x*1000.0 or x), y, ))
                    self.emit("progressStep", (len(self.scan_data)))
            except:
                pass

    def isConnected(self):
        return True

    def canScanEnergy(self):
        return self.isConnected()

    def startEnergyScan(self, element, edge, directory, prefix, \
                 session_id=None, blsample_id=None, exptime=3):
        log = logging.getLogger("HWR")

        self.scan_info = {"sessionId": session_id, "blSampleId": blsample_id,
                         "element": element, "edgeEnergy" : edge}
        self.scan_data = []
        if not os.path.isdir(directory):
            log.debug("EnergyScan: creating directory %s" % directory)
            try:
                os.makedirs(directory)
            except OSError, diag:
                log.error("EnergyScan: error creating directory %s (%s)" % \
                          (directory, str(diag)))
                self.emit('energyScanStatusChanged', ("Error creating directory",))
                return False

        if self.chan_scan_status.getValue() in ['ready', 'unknown', 'error']:
            self.energy_hwobj.release_break_bragg()

            if self.transmission_hwobj is not None:
                self.scan_info['transmissionFactor'] = self.transmission_hwobj.get_value()
            else:
                self.scan_info['transmissionFactor'] = None
            self.scan_info['exposureTime'] = exptime
            self.scan_info['startEnergy'] = 0
            self.scan_info['endEnergy'] = 0
            self.scan_info['startTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
            size_hor = None
            size_ver = None
            if self.beam_info_hwobj is not None:
                size_hor, size_ver = self.beam_info_hwobj.get_beam_size()
                size_hor = size_hor * 1000
                size_ver = size_ver * 1000
            self.scan_info['beamSizeHorizontal'] = size_hor
            self.scan_info['beamSizeVertical'] = size_ver
            self.chan_scan_start.setValue("%s;%s" % (element, edge))
            self.scanCommandStarted()
        else:
            log.error("Another energy scan in progress. " + \
                      "Please wait when the scan is finished")
            self.emit('energyScanStatusChanged', ("Another energy " + \
                  "scan in progress. Please wait when the scan is finished"))
            self.scanCommandFailed()

            return False

        return True

    def cancelEnergyScan(self, *args):
        if self.scanning:
            self.cmd_scan_abort()
            self.scanCommandAborted()

    def scanCommandStarted(self, *args):
        if self.scan_info["blSampleId"]:
            title = "Sample: %s Element: %s Edge: %s" % \
             (self.scan_info["blSampleId"],
              self.scan_info["element"],
              self.scan_info["edgeEnergy"])
        else:
            title = "Element: %s Edge: %s" % (self.scan_info["element"],
                                              self.scan_info["edgeEnergy"])

        graph_info = {'xlabel' : 'energy',
                      'ylabel' :  'counts',
                      'scaletype' : 'normal',
                      'title' : title}
        self.scanning = True
        self.emit('energyScanStarted', graph_info)
        self.emit("progressInit", ("Energy scan", self.num_points))

    def scanCommandFailed(self, *args):
        self.scan_info['endTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = False
        self.store_energy_scan()
        self.emit('energyScanFailed', ())
        self.emit("progressStop", ())
        self.energy_hwobj.set_break_bragg()
        self.ready_event.set()

    def scanCommandAborted(self, *args):
        self.scanning = False
        self.emit('energyScanFailed', ())
        self.emit("progressStop", ())
        self.energy_hwobj.set_break_bragg()
        self.ready_event.set()

    def scanCommandFinished(self, *args):
        with cleanup(self.ready_event.set):
            self.scan_info['endTime'] = time.strftime("%Y-%m-%d %H:%M:%S")
            logging.getLogger("HWR").debug("EMBLEnergyScan: energy scan finished")
            self.scanning = False
            self.scan_info["startEnergy"] = self.scan_data[-1][0]
            self.scan_info["endEnergy"] = self.scan_data[-1][1]
            self.emit('energyScanFinished', (self.scan_info,))
            self.emit("progressStop", ())
            self.energy_hwobj.set_break_bragg()

    def doChooch(self, elt, edge, scan_directory, archive_directory, prefix):
        symbol = "_".join((elt, edge))
        scan_file_prefix = os.path.join(scan_directory, prefix)
        archive_file_prefix = os.path.join(archive_directory, prefix)

        if os.path.exists(scan_file_prefix + ".raw"):
            i = 1
            while os.path.exists(scan_file_prefix + "%d.raw" %i):
                i = i + 1
            scan_file_prefix += "_%d" % i
            archive_file_prefix += "_%d" % i

        scan_file_raw_filename = \
            os.path.extsep.join((scan_file_prefix, "raw"))
        archive_file_raw_filename = \
            os.path.extsep.join((archive_file_prefix, "raw"))
        scan_file_efs_filename = \
            os.path.extsep.join((scan_file_prefix, "efs"))
        archive_file_efs_filename = \
            os.path.extsep.join((archive_file_prefix, "efs"))
        scan_file_png_filename = \
            os.path.extsep.join((scan_file_prefix, "png"))
        archive_file_png_filename = \
            os.path.extsep.join((archive_file_prefix, "png"))

        try:
            if not os.path.exists(scan_directory):
                os.makedirs(scan_directory)
            if not os.path.exists(archive_directory):
                os.makedirs(archive_directory)
        except:
            logging.getLogger("HWR").exception(\
                 "EMBLEnergyScan: could not create results directory.")
            self.store_energy_scan()
            self.emit("energyScanFailed", ())
            return

        try:
            scan_file_raw = open(scan_file_raw_filename, "w")
            archive_file_raw = open(archive_file_raw_filename, "w")
        except:
            logging.getLogger("HWR").exception(\
                 "EMBLEnergyScan: could not create results raw file")
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
                scan_file_raw.write("%f,%f\r\n" % (x, y))
                archive_file_raw.write("%f,%f\r\n" % (x, y))
            scan_file_raw.close()
            archive_file_raw.close()
            self.scan_info["scanFileFullPath"] = str(scan_file_raw_filename)

        pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, chooch_graph_data = \
             PyChooch.calc(scanData, elt, edge, scan_file_efs_filename)

        rm = (pk + 30) / 1000.0
        pk = pk / 1000.0
        savpk = pk
        ip = ip / 1000.0
        comm = ""
        #IK TODO clear this
        self.scan_info['edgeEnergy'] = 0.1
        self.th_edge = self.scan_info['edgeEnergy']
        logging.getLogger("HWR").info(\
              "th. Edge %s ; chooch results are pk=%f, ip=%f, rm=%f" % \
              (self.th_edge, pk, ip, rm))

        #should be better, but OK for time being
        """
        self.th_edgeThreshold = 0.01
        if math.fabs(self.th_edge - ip) > self.thEdgeThreshold:
          pk = 0
          ip = 0
          rm = self.th_edge + 0.03
          comm = "Calculated peak (%f) is more that 10eV away from the " + \
                 "theoretical value (%f). Please check your scan" % \
                 (savpk, self.th_edge)

          logging.getLogger("HWR").warning("EnergyScan: calculated peak " + \
                  "(%f) is more that 20eV %s the theoretical value (%f). " + \
                  "Please check your scan and choose the energies manually" % \
                   (savpk, (self.th_edge - ip) > 0.02 and "below" or "above", self.thEdge))
        """

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

        #logging.getLogger("HWR").info("EMBLEnergyScan: Saving png" )
        # prepare to save png files
        title = "%s  %s  %s\n%.4f  %.2f  %.2f\n%.4f  %.2f  %.2f" % \
              ("energy", "f'", "f''", pk, fpPeak, fppPeak, ip, fpInfl, fppInfl)
        fig = Figure(figsize=(15, 11))
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
        handles.append(ax2.plot(chooch_graph_x, chooch_graph_y1, color='blue'))
        handles.append(ax2.plot(chooch_graph_x, chooch_graph_y2, color='red'))
        canvas = FigureCanvasAgg(fig)

        self.scan_info["jpegChoochFileFullPath"] = str(archive_file_png_filename)
        try:
            logging.getLogger("HWR").info("Rendering energy scan and Chooch " + \
                 "graphs to PNG file : %s", scan_file_png_filename)
            canvas.print_figure(scan_file_png_filename, dpi=80)
        except:
            logging.getLogger("HWR").exception("could not print figure")
        try:
            logging.getLogger("HWR").info("Saving energy scan to archive " +\
                 "directory for ISPyB : %s", archive_file_png_filename)
            canvas.print_figure(archive_file_png_filename, dpi=80)
        except:
            logging.getLogger("HWR").exception("could not save figure")

        self.store_energy_scan()

        logging.getLogger("HWR").info("<chooch> returning")
        self.emit('choochFinished', (pk, fppPeak, fpPeak, ip, fppInfl, fpInfl,
                 rm, chooch_graph_x, chooch_graph_y1, chooch_graph_y2, title))
        return pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, rm, chooch_graph_x, \
                 chooch_graph_y1, chooch_graph_y2, title

    def scan_status_changed(self, status):
        self.emit('energyScanStatusChanged', (status,))

    def updateEnergyScan(self, scan_id, jpeg_scan_filename):
        pass

    def getElements(self):
        elements = []
        try:
            for el in self["elements"]:
                elements.append({"symbol" : el.symbol,
                                 "energy" : el.energy})
        except IndexError:
            pass
        return elements

    def getDefaultMadEnergies(self):
        energies = []
        try:
            for el in self["mad"]:
                energies.append([float(el.energy), el.directory])
        except IndexError:
            pass
        return energies

    def get_scan_data(self):
        """Returns energy scan data.
           List contains tuples of (energy, counts)
        """
        return self.scan_data

    def store_energy_scan(self):
        if self.db_connection_hwobj:
            db_status = self.db_connection_hwobj.storeEnergyScan(self.scan_info)
