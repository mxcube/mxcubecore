import logging
import os
import time

import gevent
import gevent.event
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractEnergyScan import AbstractEnergyScan
from mxcubecore.TaskUtils import cleanup

scan_test_data = [
    (10841.0, 20.0),
    (10842.0, 20.0),
    (10843.0, 20.0),
    (10844.0, 20.0),
    (10845.0, 20.0),
    (10846.0, 20.0),
    (10847.0, 20.0),
    (10848.0, 20.0),
    (10849.0, 20.0),
    (10850.0, 20.0),
    (10851.0, 20.0),
    (10852.0, 20.0),
    (10853.0, 20.0),
    (10854.0, 20.0),
    (10855.0, 20.0),
    (10856.0, 20.0),
    (10857.0, 20.0),
    (10858.0, 20.00),
    (10859.0, 20.0),
    (10860.0, 20.0),
    (10861.0, 20.1),
    (10862.0, 21.4),
    (10863.0, 30.4),
    (10864.9, 80.7),
    (10865.9, 299.0),
    (10866.7, 820.8),
    (10867.5, 2009.2),
    (10868.2, 4305.5),
    (10869.0, 8070.2),
    (10869.8, 13246.7),
    (10870.6, 19124.1),
    (10871.4, 24430.5),
    (10872.2, 27843.1),
    (10873.0, 28654.8),
    (10873.8, 27092.5),
    (10874.6, 24138.5),
    (10875.4, 20957.3),
    (10876.0, 18373.6),
    (10877.0, 16373.8),
    (10878.0, 15474.8),
    (10879.0, 15163.9),
    (10880.0, 15080.5),
    (10881.0, 15063.0),
    (10882.0, 15060.3),
    (10883.0, 15059.8),
    (10884.0, 15059.7),
    (10885.0, 15059.0),
    (10886.0, 15059.0),
    (10887.0, 15059.0),
    (10888.0, 15059.0),
    (10889.0, 15059.0),
    (10890.0, 15059.0),
    (10891.0, 15059.0),
    (10892.0, 15059.0),
    (10893.0, 15059.0),
    (10894.0, 15059.0),
    (10895.0, 15059.0),
    (10896.0, 15059.0),
    (10897.0, 15059.0),
    (10898.0, 15059.0),
    (10899.0, 15059.0),
    (10900.0, 15059.0),
    (10901.0, 15059.0),
    (10902.0, 15059.0),
    (10903.0, 15059.0),
    (10904.0, 15059.0),
    (10905.0, 15059.0),
    (10906.0, 15059.0),
    (10907.0, 15059.0),
    (10908.0, 15059.0),
    (10909.0, 15059.0),
    (10910.0, 15059.0),
]

chooch_graph_data = (
    (12628, 0, -5),
    (12629, 0, -5),
    (12630, 0, -5),
    (12631, 0, -5),
    (12632, 0, -5),
    (12633, 0, -5),
    (12634, 0, -5),
    (12635, 0, -5),
    (12636, 0, -5),
    (12637, 0, -5),
    (12638, 0, -5),
    (12639, 0, -5),
    (12640, 0, -5),
    (12641, 0, -6),
    (12642, 0, -6),
    (12643, 0, -6),
    (12644, 0, -6),
    (12645, 0, -6),
    (12646, 0, -6),
    (12647, 0, -6),
    (12648, 0, -6),
    (12649, 0, -7),
    (12650, 0, -7),
    (12651, 0, -7),
    (12652, 0, -8),
    (12653, 0, -8),
    (12654, 0, -8),
    (12655, 1, -9),
    (12655, 2, -9),
    (12656, 3, -10),
    (12657, 4, -9),
    (12658, 5, -9),
    (12659, 6, -8),
    (12659, 6, -7),
    (12660, 6, -6),
    (12661, 5, -5),
    (12662, 4, -5),
    (12663, 4, -5),
    (12664, 3, -5),
    (12665, 3, -5),
    (12666, 3, -5),
    (12667, 3, -5),
    (12668, 3, -5),
    (12669, 3, -5),
    (12670, 3, -5),
    (12671, 3, -5),
    (12672, 3, -5),
    (12673, 3, -5),
    (12674, 3, -5),
    (12675, 3, -5),
    (12676, 3, -5),
    (12677, 3, -5),
    (12678, 3, -5),
    (12679, 3, -5),
    (12680, 3, -5),
    (12681, 3, -5),
    (12682, 3, -5),
    (12683, 3, -5),
    (12684, 3, -4),
    (12685, 3, -4),
    (12686, 3, -4),
    (12687, 3, -4),
    (12688, 3, -4),
    (12689, 3, -4),
    (12690, 3, -4),
    (12691, 3, -4),
    (12692, 3, -4),
    (12693, 3, -4),
    (12694, 3, -4),
    (12695, 3, -4),
    (12696, 3, -4),
)


class EnergyScanMockup(AbstractEnergyScan):
    def __init__(self, name):
        AbstractEnergyScan.__init__(self, name)

    def init(self):

        self.ready_event = gevent.event.Event()
        self.energy_scan_parameters = {}
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
                        self.scan_data.append([(x < 1000 and x * 1000.0 or x), y])
                else:
                    self.scan_data.append([(x < 1000 and x * 1000.0 or x), y])
                self.emit("scanNewPoint", (x < 1000 and x * 1000.0 or x), y)
            time.sleep(0.05)
        self.scanCommandFinished()

    def execute_energy_scan(self, energy_scan_parameters):
        self.energy_scan_parameters["exposureTime"] = 0.01
        print(self.cpos)
        if HWR.beamline.transmission is not None:
            self.energy_scan_parameters["transmissionFactor"] = (
                HWR.beamline.transmission.get_value()
            )
        else:
            self.energy_scan_parameters["transmissionFactor"] = None
        size_hor = None
        size_ver = None
        if HWR.beamline.beam is not None:
            size_hor, size_ver = HWR.beamline.beam.get_beam_size()
            size_hor = size_hor * 1000
            size_ver = size_ver * 1000
        self.energy_scan_parameters["beamSizeHorizontal"] = size_hor
        self.energy_scan_parameters["beamSizeVertical"] = size_ver
        self.energy_scan_parameters["startEnergy"] = 0
        self.energy_scan_parameters["endEnergy"] = 0
        self.energy_scan_parameters["fluorescenceDetector"] = "Mockup detector"
        self.scan_data = []
        self.result_value_emitter = gevent.spawn(self.emit_result_values)

    def do_chooch(self, elt, edge, scan_directory, archive_directory, prefix):
        """
        Descript. :
        """
        symbol = "_".join((elt, edge))
        scan_file_prefix = os.path.join(scan_directory, prefix)
        archive_file_prefix = os.path.join(archive_directory, prefix)

        if os.path.exists(scan_file_prefix + ".raw"):
            i = 1
            while os.path.exists(scan_file_prefix + "%d.raw" % i):
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
        except Exception:
            logging.getLogger("HWR").exception(
                "EnergyScan: could not create energy scan result directory."
            )
            self.store_energy_scan()
            self.emit("energyScanFailed", ())
            return

        try:
            scan_file_raw = open(scan_file_raw_filename, "w")
            archive_file_raw = open(archive_file_raw_filename, "w")
        except Exception:
            logging.getLogger("HWR").exception(
                "EnergyScan: could not create energy scan result raw file"
            )
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
            self.energy_scan_parameters["scanFileFullPath"] = str(
                scan_file_raw_filename
            )

        pk = 7.519
        ip = 7.516
        rm = 7.54
        fpPeak = -12.6
        fppPeak = 20.7
        fpInfl = -21.1
        fppInfl = 11.9
        comm = "Mockup results"
        self.energy_scan_parameters["edgeEnergy"] = 0.1
        self.thEdge = self.energy_scan_parameters["edgeEnergy"]
        logging.getLogger("HWR").info(
            "th. Edge %s ; chooch results are pk=%f, ip=%f, rm=%f"
            % (self.thEdge, pk, ip, rm)
        )

        self.energy_scan_parameters["peakEnergy"] = pk
        self.energy_scan_parameters["inflectionEnergy"] = ip
        self.energy_scan_parameters["remoteEnergy"] = rm
        self.energy_scan_parameters["peakFPrime"] = fpPeak
        self.energy_scan_parameters["peakFDoublePrime"] = fppPeak
        self.energy_scan_parameters["inflectionFPrime"] = fpInfl
        self.energy_scan_parameters["inflectionFDoublePrime"] = fppInfl
        self.energy_scan_parameters["comments"] = comm
        self.energy_scan_parameters["choochFileFullPath"] = scan_file_efs_filename
        self.energy_scan_parameters["filename"] = archive_file_raw_filename
        self.energy_scan_parameters["workingDirectory"] = archive_directory

        chooch_graph_x, chooch_graph_y1, chooch_graph_y2 = zip(*chooch_graph_data)
        chooch_graph_x = list(chooch_graph_x)
        for i in range(len(chooch_graph_x)):
            chooch_graph_x[i] = chooch_graph_x[i] / 1000.0

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
        ax.set_title("%s" % title)
        ax.grid(True)
        ax.plot(*(zip(*self.scan_data)), **{"color": "black"})
        ax.set_xlabel("Energy")
        ax.set_ylabel("MCA counts")
        ax2 = fig.add_subplot(212)
        ax2.grid(True)
        ax2.set_xlabel("Energy")
        ax2.set_ylabel("")
        handles = []
        handles.append(ax2.plot(chooch_graph_x, chooch_graph_y1, color="blue"))
        handles.append(ax2.plot(chooch_graph_x, chooch_graph_y2, color="red"))
        canvas = FigureCanvasAgg(fig)

        self.energy_scan_parameters["jpegChoochFileFullPath"] = str(
            archive_file_png_filename
        )
        try:
            logging.getLogger("HWR").info(
                "Rendering energy scan and Chooch " + "graphs to PNG file : %s",
                scan_file_png_filename,
            )
            canvas.print_figure(scan_file_png_filename, dpi=80)
        except Exception:
            logging.getLogger("HWR").exception("could not print figure")
        try:
            logging.getLogger("HWR").info(
                "Saving energy scan to archive " + "directory for ISPyB : %s",
                archive_file_png_filename,
            )
            canvas.print_figure(archive_file_png_filename, dpi=80)
        except Exception:
            logging.getLogger("HWR").exception("could not save figure")

        self.store_energy_scan()

        logging.getLogger("HWR").info("<chooch> returning")
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

    def get_elements(self):
        elements = []
        try:
            for el in self["elements"]:
                elements.append({"symbol": el.symbol, "energy": el.energy})
        except IndexError:
            pass
        return elements

    #
    # def getDefaultMadEnergies(self):
    #     energies = []
    #     try:
    #         for el in self["mad"]:
    #             energies.append([float(el.energy), el.directory])
    #     except IndexError:
    #         pass
    #     return energies

    def is_connected(self):
        return True

    def scanCommandStarted(self, *args):
        """
        Descript. :
        """
        print(self.energy_scan_parameters)
        title = "%s %s: %s %s" % (
            self.energy_scan_parameters["sessionId"],
            self.energy_scan_parameters["blSampleId"],
            self.energy_scan_parameters["element"],
            self.energy_scan_parameters["edgeEnergy"],
        )
        dic = {
            "xlabel": "energy",
            "ylabel": "counts",
            "scaletype": "normal",
            "title": title,
        }
        self.emit("scanStart", dic)
        self.emit("energyScanStarted", dic)
        self.energy_scan_parameters["startTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = True

    def scanCommandFinished(self, *args):
        """
        Descript. :
        """
        with cleanup(self.ready_event.set):
            self.energy_scan_parameters["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
            logging.getLogger("HWR").debug("Energy Scan: finished")
            self.scanning = False
            self.energy_scan_parameters["startEnergy"] = self.scan_data[-1][0] / 1000.0
            self.energy_scan_parameters["endEnergy"] = self.scan_data[-1][1] / 1000.0
            self.emit("energyScanFinished", self.energy_scan_parameters)

    def get_scan_data(self):
        """
        Descript. :
        """
        return self.scan_data

    def store_energy_scan(self):
        """
        Descript. :
        """
        if HWR.beamline.lims:
            db_status = HWR.beamline.lims.storeEnergyScan(self.energy_scan_parameters)
