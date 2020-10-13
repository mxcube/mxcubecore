#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

import os
import time
import logging
import subprocess

import gevent
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from HardwareRepository import TaskUtils
from HardwareRepository.HardwareObjects.abstract.AbstractEnergyScan import (
    AbstractEnergyScan,
)
from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository import HardwareRepository as HWR


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "General"


class EMBLEnergyScan(AbstractEnergyScan, HardwareObject):
    def __init__(self, name):

        AbstractEnergyScan.__init__(self)
        HardwareObject.__init__(self, name)
        self._tunable_bl = True

        self.status = None
        self.startup_done = False
        self.ready_event = None
        self.scanning = False
        self.th_edge = None
        self.scan_directory = None
        self.scan_data = None
        self.scan_prefix = None
        self.num_points = None
        self.scan_info = None
        self.chooch_cmd = None

        self.chan_scan_start = None
        self.chan_scan_status = None
        self.chan_scan_error = None

        self.cmd_scan_abort = None
        self.cmd_adjust_transmission = False
        self.cmd_set_max_transmission = False

    def init(self):
        self.ready_event = gevent.event.Event()
        self.scan_info = {}

        self.chan_scan_start = self.get_channel_object("energyScanStart")
        self.chan_scan_start.connect_signal("update", self.scan_start_update)
        self.chan_scan_status = self.get_channel_object("energyScanStatus")
        self.chan_scan_status.connect_signal("update", self.scan_status_update)
        self.chan_scan_error = self.get_channel_object("energyScanError")
        self.chan_scan_error.connect_signal("update", self.scan_error_update)

        self.cmd_scan_abort = self.get_command_object("energyScanAbort")
        self.cmd_adjust_transmission = self.get_command_object("cmdAdjustTransmission")
        self.cmd_set_max_transmission = self.get_command_object("cmdSetMaxTransmission")

        self.num_points = self.get_property("numPoints", 60)
        self.chooch_cmd = self.get_property("chooch_command")

    def scan_start_update(self, values):
        """Emits new scan point

        :param values: list of values
        :type values: list of two floats
        :return:
        """
        if self.scanning:
            self.emit_new_data_point(values)

    def scan_status_update(self, status):
        if self.scanning and status != self.status:
            if status == "scanning":
                logging.getLogger("GUI").info("Energy scan: Executing...")

                if HWR.beamline.transmission is not None:
                    self.scan_info[
                        "transmissionFactor"
                    ] = HWR.beamline.transmission.get_value()
                else:
                    self.scan_info["transmissionFactor"] = None
            elif status == "ready":
                if self.scanning is True:
                    logging.getLogger("GUI").info("Energy scan: Finished")
                    self.scanCommandFinished()
            elif status == "aborting":
                if self.scanning is True:
                    self.scanCommandAborted()
                    logging.getLogger("GUI").info("Energy scan: Aborted")
            elif status == "error":
                self.scanCommandFailed()
            self.status = status

    def scan_error_update(self, error_msg):
        """Prints error message

        :param error_msg: error message
        :type error_msg: str
        :return: None
        """
        if len(error_msg) > 0 and self.startup_done:
            logging.getLogger("GUI").error("Energy scan: %s" % error_msg)

    def emit_new_data_point(self, values):
        """Adds new point to the energy scan curve

        :param values: values
        :type values: list of two floats
        :return: None
        """
        if len(values) > 0:
            if type(values) in (tuple, list):
                if type(values[-1]) not in (tuple, list):
                    values = [values]
                x = values[-1][0]
                y = values[-1][1]
                # if x is in keV, transform into eV otherwise let it like it is
                # if point larger than previous point (for chooch)
                if x > 0 and y > 0:
                    if len(self.scan_data) > 0:
                        if x > self.scan_data[-1][0]:
                            self.scan_data.append([(x < 1000 and x * 1000.0 or x), y])
                    else:
                        self.scan_data.append([(x < 1000 and x * 1000.0 or x), y])
                    # a = str(x < 1000 and x*1000.0 or x) + " -- " + str(y)
                    # logging.getLogger("GUI").info(a)
                    self.emit("scanNewPoint", ((x < 1000 and x * 1000.0 or x), y))
                    self.emit("progressStep", (len(self.scan_data)))

    def isConnected(self):
        return True

    def startEnergyScan(
        self,
        element,
        edge,
        directory,
        prefix,
        session_id=None,
        blsample_id=None,
        exptime=3,
    ):
        """Starts energy scan

        :param element: scan element
        :type element: str
        :param edge: edge
        :type edge: str
        :param directory: scan directory
        :type directory: str
        :param prefix: scan prefix
        :type prefix: str
        :param session_id: session id
        :type session_id: int
        :param blsample_id: sample id
        :type blsample_id: int
        :param exptime: exposure time in seconds
        :type exptime: float
        :return: True if success, otherwise returns Fals
        """
        log = logging.getLogger("HWR")

        self.scan_info = {
            "sessionId": session_id,
            "blSampleId": blsample_id,
            "element": element,
            "edgeEnergy": edge,
        }
        self.scan_data = []
        self.scan_directory = directory
        self.scan_prefix = prefix
        self.startup_done = True

        """
        if not os.path.isdir(directory):
            log.debug("EnergyScan: creating directory %s" % directory)
            try:
                os.makedirs(directory)
            except OSError as diag:
                log.error(
                    "EnergyScan: error creating directory %s (%s)"
                    % (directory, str(diag))
                )
                self.emit("energyScanStatusChanged", ("Error creating directory",))
                return False
        """

        if self.chan_scan_status.get_value() in ["ready", "unknown", "error"]:
            if hasattr(HWR.beamline.energy, "release_break_bragg"):
                HWR.beamline.energy.release_break_bragg()

            # if self.transmission_hwobj is not None:
            #    self.scan_info['transmissionFactor'] = self.transmission_hwobj.get_value()
            # else:
            #    self.scan_info['transmissionFactor'] = None
            self.scan_info["exposureTime"] = exptime
            self.scan_info["startEnergy"] = 0
            self.scan_info["endEnergy"] = 0
            self.scan_info["startTime"] = str(time.strftime("%Y-%m-%d %H:%M:%S"))
            size_hor = None
            size_ver = None
            if HWR.beamline.beam is not None:
                size_hor, size_ver = HWR.beamline.beam.get_beam_size()
                size_hor = size_hor * 1000
                size_ver = size_ver * 1000
            self.scan_info["beamSizeHorizontal"] = size_hor
            self.scan_info["beamSizeVertical"] = size_ver
            self.chan_scan_start.set_value("%s;%s" % (element, edge))
            self.scanCommandStarted()
        else:
            log.error(
                "Another energy scan in progress. "
                + "Please wait when the scan is finished"
            )
            self.emit(
                "energyScanStatusChanged",
                (
                    "Another energy scan in progress. "
                    + "Please wait when the scan is finished"
                ),
            )
            self.scanCommandFailed()

            return False

        return True

    def cancelEnergyScan(self, *args):
        if self.scanning:
            self.cmd_scan_abort()
            self.scanCommandAborted()

    def scanCommandStarted(self, *args):
        if self.scan_info["blSampleId"]:
            title = "Sample: %s Element: %s Edge: %s" % (
                self.scan_info["blSampleId"],
                self.scan_info["element"],
                self.scan_info["edgeEnergy"],
            )
        else:
            title = "Element: %s Edge: %s" % (
                self.scan_info["element"],
                self.scan_info["edgeEnergy"],
            )

        graph_info = {
            "xlabel": "energy",
            "ylabel": "counts",
            "scaletype": "normal",
            "title": title,
        }
        self.scanning = True
        self.emit("energyScanStarted", graph_info)
        self.emit("progressInit", "Energy scan", self.num_points, False)

    def scanCommandFailed(self, *args):
        with TaskUtils.cleanup(self.ready_event.set):
            # error_msg = self.chan_scan_error.get_value()
            # print error_msg
            # logging.getLogger("GUI").error("Energy scan: %s" % error_msg)
            self.scan_info["endTime"] = str(time.strftime("%Y-%m-%d %H:%M:%S"))
            if self.scan_data:
                self.scan_info["startEnergy"] = self.scan_data[-1][0] / 1000.0
                self.scan_info["endEnergy"] = self.scan_data[-1][1] / 1000.0
            self.emit("energyScanFailed", ())
            self.emit("progressStop", ())

            if hasattr(HWR.beamline.energy, "set_break_bragg"):
                HWR.beamline.energy.set_break_bragg()
            self.scanning = False
            self.ready_event.set()

    def scanCommandAborted(self, *args):
        self.emit("energyScanFailed", ())
        self.emit("progressStop", ())
        if hasattr(HWR.beamline.energy, "set_break_bragg"):
            HWR.beamline.energy.set_break_bragg()
        self.scanning = False
        self.ready_event.set()

    def scanCommandFinished(self, *args):
        with TaskUtils.cleanup(self.ready_event.set):
            self.scan_info["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
            logging.getLogger("HWR").debug("Energy scan: finished")
            self.scanning = False
            self.scan_info["startEnergy"] = self.scan_data[-1][0]
            self.scan_info["endEnergy"] = self.scan_data[-1][1]
            self.emit("energyScanFinished", (self.scan_info,))
            self.emit("progressStop", ())
            if hasattr(HWR.beamline.energy, "set_break_bragg"):
                HWR.beamline.energy.set_break_bragg()

    def doChooch(self, elt, edge, scan_directory, archive_directory, prefix):
        archive_file_prefix = str(os.path.join(archive_directory, prefix))

        if os.path.exists(archive_file_prefix + ".raw"):
            i = 1
            while os.path.exists(archive_file_prefix + "%d.raw" % i):
                i = i + 1
            archive_file_prefix += "_%d" % i

        archive_file_raw_filename = os.path.extsep.join((archive_file_prefix, "raw"))
        archive_file_efs_filename = os.path.extsep.join((archive_file_prefix, "efs"))
        archive_file_png_filename = os.path.extsep.join((archive_file_prefix, "png"))

        try:
            if not os.path.exists(archive_directory):
                os.makedirs(archive_directory)
        except Exception:
            logging.getLogger("HWR").exception(
                "EMBLEnergyScan: could not create results directory."
            )
            self.store_energy_scan()
            self.emit("energyScanFailed", ())
            return

        try:
            archive_file_raw = open(archive_file_raw_filename, "w")
        except Exception:
            logging.getLogger("HWR").exception(
                "EMBLEnergyScan: could not create results raw file"
            )
            self.store_energy_scan()
            self.emit("energyScanFailed", ())
            return
        else:
            scanData = []
            x_array = []
            y_array = []
            for i in range(len(self.scan_data)):
                x = float(self.scan_data[i][0])
                x = x < 1000 and x * 1000.0 or x
                y = float(self.scan_data[i][1])
                scanData.append((x, y))
                x_array.append(x / 1000.0)
                y_array.append(y)
                archive_file_raw.write("%f,%f\r\n" % (x, y))
            archive_file_raw.close()
            self.scan_info["scanFileFullPath"] = str(archive_file_raw_filename)

        try:
            p = subprocess.Popen(
                [self.chooch_cmd, archive_file_raw_filename, elt, edge],
                stdout=subprocess.PIPE,
            )

            chooch_results_list = p.communicate()[0].split("\n")
            chooch_results_list.remove("")
            pk, fppPeak, fpPeak, ip, fppInfl, fpInfl = map(
                float, chooch_results_list[-2].split(" ")
            )
            chooch_graph_data = eval(chooch_results_list[-1])
        except Exception:
            self.store_energy_scan()

            logging.getLogger("GUI").error("Energy scan: Chooch failed")
            return None, None, None, None, None, None, None, [], [], [], None

        rm = (pk + 30) / 1000.0
        pk = pk / 1000.0
        savpk = pk
        ip = ip / 1000.0
        comm = ""
        self.scan_info["edgeEnergy"] = 0.1
        self.th_edge = self.scan_info["edgeEnergy"]
        logging.getLogger("GUI").info(
            "Energy Scan: Chooch results are pk=%.2f, ip=%.2f, rm=%.2f" % (pk, ip, rm)
        )

        self.scan_info["peakEnergy"] = pk
        self.scan_info["inflectionEnergy"] = ip
        self.scan_info["remoteEnergy"] = rm
        self.scan_info["peakFPrime"] = fpPeak
        self.scan_info["peakFDoublePrime"] = fppPeak
        self.scan_info["inflectionFPrime"] = fpInfl
        self.scan_info["inflectionFDoublePrime"] = fppInfl
        self.scan_info["comments"] = comm
        self.scan_info["choochFileFullPath"] = archive_file_efs_filename
        self.scan_info["filename"] = archive_file_raw_filename
        self.scan_info["workingDirectory"] = archive_directory

        chooch_graph_x, chooch_graph_y1, chooch_graph_y2 = zip(*chooch_graph_data)
        chooch_graph_x = list(chooch_graph_x)
        for i in range(len(chooch_graph_x)):
            chooch_graph_x[i] = chooch_graph_x[i] / 1000.0

        # logging.getLogger("HWR").info("EMBLEnergyScan: Saving png" )
        # prepare to save png files
        title = "%s  %s  %s\n%.4f  %.2f  %.2f\n%.4f  %.2f  %.2f" % (
            "energy",
            "f'",
            "f''",
            pk,
            fpPeak,
            fppPeak,
            ip,
            fpInfl,
            fppInfl,
        )
        fig = Figure(figsize=(15, 11))
        ax = fig.add_subplot(211)
        ax.set_title("%s\n%s" % (archive_file_efs_filename, title))
        ax.grid(True)
        ax.plot(x_array, y_array, **{"color": "black"})
        ax.set_xlabel("Energy (keV)")
        ax.set_ylabel("MCA counts")
        ax.set_xticklabels(
            np.round(
                np.linspace(
                    min(x_array), max(x_array), len(ax.get_xticklabels()), endpoint=True
                ),
                3,
            )
        )
        ax2 = fig.add_subplot(212)
        ax2.grid(True)
        ax2.set_xlabel("Energy (keV)")
        ax2.set_ylabel("")
        handles = []
        handles.append(ax2.plot(chooch_graph_x, chooch_graph_y1, color="blue"))
        handles.append(ax2.plot(chooch_graph_x, chooch_graph_y2, color="red"))
        ax2.set_xticklabels(
            np.round(
                np.linspace(
                    min(x_array), max(x_array), len(ax.get_xticklabels()), endpoint=True
                ),
                3,
            )
        )
        ax2.axvline(pk, linestyle="--", color="blue")
        ax2.axvline(ip, linestyle="--", color="red")

        canvas = FigureCanvasAgg(fig)

        self.scan_info["jpegChoochFileFullPath"] = str(archive_file_png_filename)
        try:
            logging.getLogger("HWR").info(
                "Saving energy scan to archive directory for ISPyB : %s",
                archive_file_png_filename,
            )
            canvas.print_figure(archive_file_png_filename, dpi=80)
        except Exception:
            logging.getLogger("HWR").exception("could not save figure")

        self.store_energy_scan()

        self.emit(
            "choochFinished",
            (
                pk,
                fppPeak,
                fpPeak,
                ip,
                fppInfl,
                fpInfl,
                rm,
                chooch_graph_x,
                chooch_graph_y1,
                chooch_graph_y2,
                title,
            ),
        )
        return (
            pk,
            fppPeak,
            fpPeak,
            ip,
            fppInfl,
            fpInfl,
            rm,
            chooch_graph_x,
            chooch_graph_y1,
            chooch_graph_y2,
            title,
        )

    def scan_status_changed(self, status):
        self.emit("energyScanStatusChanged", (status,))

    def updateEnergyScan(self, scan_id, jpeg_scan_filename):
        pass

    def getElements(self):
        elements = []
        try:
            for el in self["elements"]:
                elements.append(
                    {
                        "symbol": el.get_property("symbol"),
                        "energy": el.get_property("energy"),
                    }
                )
        except IndexError:
            pass
        return elements

    def get_scan_data(self):
        """Returns energy scan data.
           List contains tuples of (energy, counts)
        """
        return self.scan_data

    def store_energy_scan(self):
        if HWR.beamline.lims:
            db_status = HWR.beamline.lims.storeEnergyScan(self.scan_info)

    def adjust_transmission(self, state):
        """
        Enables/disables usage of maximal transmission set
        during the energy scan
        """
        self.cmd_adjust_transmission(state)

    def set_max_transmission(self, value):
        """
        Sets maximal transmission used during the energy scan
        """
        self.cmd_set_max_transmission(value)

    def get_adjust_transmission_state(self):
        return self.cmd_adjust_transmission.get()

    def get_max_transmission_value(self):
        return self.cmd_set_max_transmission.get()
