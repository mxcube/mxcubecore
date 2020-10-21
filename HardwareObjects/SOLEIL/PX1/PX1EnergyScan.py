"""

Notes:

   EnergyScan and Energy are now separate hardware objects.

   Methods for Managing Energy and Wavelength are now removed from
   this hardware object (V.Rey - Jan 2018)

   This has been modified to follow the AbstractEnergyScan method

"""
import logging
import os
import time
import math
import numpy
import gevent
import subprocess

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from AbstractEnergyScan import AbstractEnergyScan
from HardwareRepository.TaskUtils import task, cleanup

from xabs_lib import McMaster
from HardwareRepository.Command.Tango import DeviceProxy

from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository import HardwareRepository as HWR


class PX1EnergyScan(AbstractEnergyScan, Equipment):

    round_cutoff = 4
    roi_width = 0.30

    default_steps = 80
    before_edge = 0.035
    after_edge = 0.045
    scan_range = after_edge + before_edge

    integration_time = 1
    thEdgeThreshold = 0.01

    def __init__(self, name):
        AbstractEnergyScan.__init__(self)
        Equipment.__init__(self, name)

        self.scanning = False
        self.stopping = False

        self.ready_event = None

        self.e_edge = ""

        self.scan_info = {}
        self.scan_data = []

        self.log = logging.getLogger("HWR")

    def init(self):
        self.ready_event = gevent.event.Event()

        self.ruche_hwo = self.getObjectByRole("ruche")

        self.fluodet_hwo = self.getObjectByRole("fluodet")
        self.px1env_hwo = self.getObjectByRole("px1environment")

        self.mono_dp = DeviceProxy(self.getProperty("mono_dev"))
        self.ble_dp = DeviceProxy(self.getProperty("ble_dev"))
        self.fp_dp = DeviceProxy(self.getProperty("fp_dev"))

        test_data_file = self.getProperty("test_data")

        self.log.debug(" using test data %s" % test_data_file)

        self.test_data_mode = False

        if test_data_file:
            self.simul_data = self.load_data_file(test_data_file)
            if len(self.simul_data):
                self.test_data_mode = True

        # USING TEST. UNCOMMENT NEXT LINE TO USE REAL DATA IN ALL CASES
        # self.test_data_mode = False

        normdiode = self.getProperty("normalization_diode")
        self.norm_diode_dev = DeviceProxy(normdiode)

        self.number_of_steps = self.getProperty("number_of_steps")
        if self.number_of_steps is None:
            self.number_of_steps = self.default_steps

    def isConnected(self):
        return True

    # SCAN info (for graph)
    def new_data_point(self, x, y):
        logging.info("EnergyScan newPoint %s, %s" % (x, y))
        x = (x < 1000) and x * 1000 or x

        self.emit("scanNewPoint", (x, y))
        self.emit("progressStep", (len(self.scan_data)))

        self.scan_data.append((x, y))

    # SCAN info end (for graph)

    # Calculate scan values
    def get_edge_from_xabs(self, element, edge):
        edge = edge.upper()
        if edge[0] == "K":
            roi_center = McMaster[element]["edgeEnergies"]["K-alpha"]
        elif edge[0] == "L":
            roi_center = McMaster[element]["edgeEnergies"]["L-alpha"]
        if edge[0] == "L":
            edge = "L3"
        e_edge = McMaster[element]["edgeEnergies"][edge]

        return e_edge, roi_center

    def get_egy_values_to_scan(self):
        nb_steps = self.number_of_steps
        points = numpy.arange(0.0, 1.0 + 1.0 / (nb_steps), 1.0 / (nb_steps))

        points *= self.scan_range
        points -= self.before_edge
        points += self.e_edge
        points = numpy.array(map(self.round_egy, points))

        return points

    def round_egy(self, en):
        return round(en, self.round_cutoff)

    # Calculate scan values end

    # HARDWARE ACCESS
    def move_mono(self, energy):
        self.mono_dp.energy = float(energy)
        self.wait_device(self.mono_dp)

    def wait_device(self, device):
        while device.state().name in ["MOVING", "RUNNING"]:
            time.sleep(0.1)

    def go_to_collect(self, timeout=30):
        if self.px1env_hwo.isPhaseFluoScan():
            return

        self.px1env_hwo.gotoFluoScanPhase()

        t0 = time.time()
        while not self.px1env_hwo.isPhaseFluoScan():
            if (time.time() - t0) > timeout:
                logging.debug("PX1EnergyScan - Timed out while going to FluoXPhase")
                break
            time.sleep(0.1)

    def get_transmission(self):
        """Get or set the transmission"""
        return self.fp_dp.TrueTrans_FP

    def move_beamline_energy(self, energy):
        current_energy = self.ble_dp.energy
        if abs(current_energy - energy) > 0.001:
            self.ble_dp.energy = energy
            self.wait_device(self.ble_dp)

    def move_egy_to_peak(self, pk):
        self.move_beamline_energy(pk)

    def open_fast_shutter(self):
        HWR.beamline.fast_shutter.openShutter()

    def close_fast_shutter(self):
        HWR.beamline.fast_shutter.closeShutter()

    def close_safety_shutter(self):
        HWR.beamline.safety_shutter.closeShutter()

    def fluodet_prepare(self):
        self.fluodet_hwo.set_preset(float(self.integration_time))

    def set_mca_roi(self):
        # calibration
        A = -0.0161723871876
        B = 0.00993475667754
        C = 0.0

        # roi_center = A + B*self.roi_center + C*self.roi_center**2
        self.roi_center += A

        egy_start = 1000.0 * (self.roi_center - self.roi_width / 2.0)
        egy_end = 1000.0 * (self.roi_center + self.roi_width / 2.0)

        self.roi_start_chan = int(egy_start / (B * 1.0e3))
        self.roi_end_chan = int(egy_end / (B * 1e3))

        self.fluodet_hwo.set_roi(self.roi_start_chan, self.roi_end_chan)

    def acquire_point(self, en):

        self.open_fast_shutter()
        self.fluodet_hwo.start()
        self.fluodet_hwo.wait()
        self.close_fast_shutter()

        roi_counts = self.fluodet_hwo.get_roi_counts()
        intensity = self.norm_diode_dev.intensity

        point = float(roi_counts / intensity)

        return point

    def stop(self):
        self.stopping = True

    def abort(self):
        self.stop()
        self.close_fast_shutter()

    # HARDWARE ACCESS END

    # GENERAL SCAN PROGRAMMING
    def escan_prepare(self):
        self.stopping = False

        self.scan_data = []

        self.go_to_collect()

        self.e_edge, self.roi_center = self.get_edge_from_xabs(
            self.scan_info["element"], self.scan_info["edgeEnergy"]
        )

        self.set_mca_roi()
        self.fluodet_prepare()

        self.points = self.get_egy_values_to_scan()
        self.log.info(
            "   edge for %s/%s is %s"
            % (self.scan_info["element"], self.scan_info["edgeEnergy"], self.e_edge)
        )
        self.log.info("   points : %s" % str(self.points))

        self.num_points = len(self.points)
        self.ble_value = self.e_edge + 0.01

        self.scan_info["fluorescenceDetector"] = "Ketek detector"
        self.scan_info["transmissionFactor"] = self.get_transmission()
        self.scan_info["exposureTime"] = self.integration_time
        self.scan_info["startEnergy"] = 0.0  # updated at the end of the scan
        self.scan_info["endEnergy"] = 0.0  # updated at the end of the scan

        try:
            size_hor, size_ver = HWR.beamline.beam.get_beam_size()
            size_hor *= 1000
            size_ver *= 1000
        except Exception:
            size_hor = None
            size_ver = None

        self.scan_info["beamSizeHorizontal"] = size_hor
        self.scan_info["beamSizeVertical"] = size_ver

    def startEnergyScan(
        self, element, edge, directory, prefix, session_id=None, blsample_id=None
    ):

        log = logging.getLogger("HWR")

        self.scan_info = {
            "sessionId": session_id,
            "blSampleId": blsample_id,
            "element": element,
            "edgeEnergy": edge,
        }

        self.scan_data = []

        self.scan_prefix = prefix
        self.scan_directory = directory

        if not os.path.isdir(directory):
            log.debug("EnergyScan: creating directory %s" % directory)
            try:
                os.makedirs(directory)
            except OSError as diag:
                log.error(
                    "EnergyScan: error creating directory %s (%s)"
                    % (directory, str(diag))
                )
                self.emit("scanStatusChanged", ("Error creating directory",))
                return False

        try:
            self.escan_prepare()

            self.scanCommandStarted()

            self.move_beamline_energy(self.ble_value)

            for en in self.points:
                if self.stopping:
                    break

                self.move_mono(en)
                point_value = self.acquire_point(en)
                self.new_data_point(en, point_value)

            self.ready_event.set()

            self.scanCommandFinished()
        except Exception:
            import traceback

            logging.getLogger("HWR").error(
                "EnergyScan: problem starting energy scan. %s" % traceback.format_exc()
            )
            self.scanCommandFailed()
            self.scanStatusChanged("error starting energy scan")
            return False

        return True

    def cancelEnergyScan(self, *args):
        if self.scanning:
            self.abort()
            self.scanCommandAborted()

    def scanStatusChanged(self, status):
        self.emit("scanStatusChanged", (status,))

    def scanCommandStarted(self, *args):
        self.scan_info["startTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.scanning = True

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

        self.emit("energyScanStarted", graph_info)
        self.emit("progressInit", "Energy scan", self.num_points)

    def scanCommandFailed(self, *args):
        with cleanup(self.ready_event.set):
            self.scan_info["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")

            if self.scan_data:
                self.scan_info["startEnergy"] = self.scan_data[-1][0]
                self.scan_info["endEnergy"] = self.scan_data[-1][1]

            self.emit("energyScanFailed", ())
            self.emit("progressStop", ())

            self.scanning = False
            self.ready_event.set()

    def scanCommandAborted(self, *args):
        self.emit("energyScanFailed", ())
        self.emit("progressStop", ())
        self.scanning = False
        self.ready_event.set()

    def scanCommandFinished(self, *args):
        logging.getLogger("HWR").debug("EnergyScan: finished")

        with cleanup(self.ready_event.set):
            self.scan_info["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")

            self.scanning = False

            self.scan_info["startEnergy"] = self.scan_data[-1][0]
            self.scan_info["endEnergy"] = self.scan_data[-1][1]

            self.log.debug("Scan finished. data is: %s " % str(self.scan_data))
            self.emit("energyScanFinished", (self.scan_info,))
            self.emit("progressStop", ())

    def doChooch(
        self, elt, edge, scan_directory, archive_directory, prefix, run_number=None
    ):

        symbol = "_".join((elt, edge))

        self.log.info("EnergyScan. executing doChooch")

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
                "PX1EnergyScan: could not create results directory."
            )
            self.store_energy_scan()
            self.scanCommandFailed()
            return

        if not self.save_raw(scan_file_raw_filename, archive_file_raw_filename):
            logging.getLogger("HWR").exception(
                "PX1EnergyScan: could not save data raw file"
            )
            self.store_energy_scan()
            self.scanCommandFailed()
            return

        self.scan_info["scanFileFullPath"] = str(scan_file_raw_filename)

        # run chooch command
        self.log.info(
            "EnergyScan. running chooch %s %s %s %s"
            % (self.chooch_cmd, scan_file_efs_filename, elt, edge)
        )
        self.log.info(
            "   on success efs file should be saved : %s" % scan_file_efs_filename
        )
        try:
            p = subprocess.Popen(
                [
                    self.chooch_cmd,
                    scan_file_raw_filename,
                    elt,
                    edge,
                    scan_file_efs_filename,
                ],
                stdout=subprocess.PIPE,
            )
            #
            chooch_result_lines = p.communicate()[0].split("\n")

            # there could messages in stdout. results are identified with -chooch_results- header line
            # produced by command (look for run_chooch in [..]/MXCuBE/tools
            next_lineno = 0
            found = 0
            for line in chooch_result_lines:
                next_lineno += 1
                if line == "chooch_results":
                    result_line = self.clean_chooch_line(
                        chooch_result_lines[next_lineno]
                    )
                    found = 1
                    break

            if found:
                self.log.debug("chooch got data back. %s" % result_line)
                result_data = eval(result_line)
                (
                    pk,
                    fppPeak,
                    fpPeak,
                    ip,
                    fppInfl,
                    fpInfl,
                    chooch_graph_data,
                ) = result_data
            else:
                self.store_energy_scan()
                logging.getLogger("HWR").error(
                    "Energy scan: Chooch cannot parse results"
                )
                return
            # scan_data = self.get_scan_data()
            # self.log.debug("running chooch with values: element=%s, element=%s" % (elt,edge))
            # self.log.debug("                   data is: %s" % str(scan_data))

            # result = PyChooch.calc(scan_data, elt, edge)
            # self.log.debug("          chooch returns : %s" % str(result))
            # pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, chooch_graph_data = \
            #       result
        except Exception:
            import traceback

            self.log.debug(traceback.format_exc())
            self.store_energy_scan()
            logging.getLogger("HWR").error("Energy scan: Chooch failed")
            return

        self.log.info("EnergyScan. running chooch done")

        # scanData = self.get_scan_data()
        # logging.info('scanData %s' % scanData)
        # logging.info('PyChooch file %s' % PyChooch.__file__)
        # pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, chooch_graph_data = PyChooch.calc(scanData, elt, edge, scanFile)

        rm = (pk + 30) / 1000.0
        pk = pk / 1000.0
        savpk = pk
        ip = ip / 1000.0

        self.thEdge = self.e_edge

        logging.getLogger("HWR").info(
            "th. Edge %s ; chooch results are pk=%f, ip=%f, rm=%f"
            % (self.thEdge, pk, ip, rm)
        )
        if math.fabs(self.thEdge - ip) > self.thEdgeThreshold:
            if (self.thEdge - ip) > 0.02:
                side = "below"
            else:
                side = "above"
            logging.info(
                "PX1EnergyScan. Theoretical edge too different from the one just determined. thEdgeThreshold = %.2f"
                % self.thEdgeThreshold
            )
            pk = 0
            ip = 0
            rm = self.thEdge + 0.03

            logging.getLogger("HWR").warning(
                "EnergyScan: calculated peak is %s theoretical value more than 20eV"
                % side
            )
            logging.getLogger("HWR").warning("   calculated = %s" % savpk)
            logging.getLogger("HWR").warning("  theoretical = %s" % self.thEdge)

        if not self.copy_efs(scan_file_efs_filename, archive_file_efs_filename):
            logging.getLogger("HWR").warning("  copy efs failed ")
            self.store_energy_scan()
            self.scanCommandFailed()
            return

        logging.getLogger("HWR").warning(
            "  efs file has been archived at %s" % archive_file_efs_filename
        )

        if pk > 0 and (not self.test_data_mode):
            self.move_egy_to_peak(pk)

        self.scan_info["peakEnergy"] = pk
        self.scan_info["inflectionEnergy"] = ip
        self.scan_info["remoteEnergy"] = rm
        self.scan_info["peakFPrime"] = fpPeak
        self.scan_info["peakFDoublePrime"] = fppPeak
        self.scan_info["inflectionFPrime"] = fpInfl
        self.scan_info["inflectionFDoublePrime"] = fppInfl
        self.scan_info["comments"] = ""

        self.scan_info["choochFileFullPath"] = scan_file_efs_filename
        self.scan_info["filename"] = archive_file_raw_filename
        # self.scan_info["workingDirectory"] = archive_directory

        logging.getLogger("HWR").warning(
            "  generating graph data from %s" % str(chooch_graph_data)
        )

        chooch_graph_x, chooch_graph_y1, chooch_graph_y2 = zip(*chooch_graph_data)
        chooch_graph_x = list(chooch_graph_x)
        for i in range(len(chooch_graph_x)):
            chooch_graph_x[i] = chooch_graph_x[i] / 1000.0

        logging.getLogger("HWR").info("PX1EnergScan. Saving png")

        # prepare to save png files
        title = "%10s  %6s  %6s\n%10s  %6.2f  %6.2f\n%10s  %6.2f  %6.2f" % (
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

        scan_data = self.get_scan_data()

        fig = Figure(figsize=(15, 11))
        ax = fig.add_subplot(211)
        ax.set_title("%s\n%s" % (scan_file_efs_filename, title))
        ax.grid(True)
        ax.plot(*(zip(*scan_data)), **{"color": "black"})
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

        escan_ispyb_path = HWR.beamline.session.path_to_ispyb(archive_file_png_filename)
        self.scan_info["jpegChoochFileFullPath"] = str(escan_ispyb_path)

        try:
            logging.getLogger("HWR").info(
                "Rendering energy scan and Chooch graphs to PNG file : %s",
                scan_file_png_filename,
            )
            canvas.print_figure(scan_file_png_filename, dpi=80)
        except Exception:
            logging.getLogger("HWR").exception("could not print figure")
        try:
            logging.getLogger("HWR").info(
                "Rendering energy scan and Chooch graphs to PNG file : %s",
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

    def clean_chooch_line(self, result_line):
        line = result_line.replace("nan", "0")
        return line

    def save_raw(self, scan_filename, archive_filename):
        try:
            scan_file_raw = open(scan_filename, "w")
            archive_file_raw = open(archive_filename, "w")
            self.log.info("EnergyScan. saving data in %s" % scan_filename)
            self.log.info("EnergyScan. archiving data in %s" % archive_filename)
        except Exception:
            logging.getLogger("HWR").exception(
                "EMBLEnergyScan: could not create results raw file"
            )
            return False

        scan_data = self.get_scan_data()
        for i in range(len(scan_data)):
            x = float(scan_data[i][0])
            y = float(scan_data[i][1])
            x = x < 1000 and x * 1000.0 or x  # convert to kEv if not done yet
            scan_file_raw.write("%f %f\r\n" % (x, y))
            archive_file_raw.write("%f %f\r\n" % (x, y))

        scan_file_raw.close()
        archive_file_raw.close()
        return True

    def copy_efs(self, from_file, to_file):
        try:
            with open(from_file) as ifd, open(to_file, "w") as ofd:
                ofd.write(ifd.read())
            return True
        except Exception:
            return False

    @task
    def store_energy_scan(self):
        if HWR.beamline.lims:
            scan_info = dict(self.scan_info)
            sample_id = scan_info["blSampleId"]
            scan_info.pop("blSampleId")

            self.log.debug("storing energy scan info in ISPyB")
            db_ret = HWR.beamline.lims.storeEnergyScan(scan_info)
            self.log.debug("stored %s" % str(db_ret))

            if sample_id is not None and db_ret is not None:
                scan_id = db_ret["energyScanId"]

                asoc = {"blSampleId": sample_id, "energyScanId": scan_id}
                HWR.beamline.lims.associate_bl_sample_and_energy_scan(asoc)

        if self.ruche_hwo:
            self.ruche_hwo.trigger_sync(self.escan_archivepng)

    # Elements commands
    def getElements(self):
        elements = []
        try:
            for el in self["elements"]:
                elements.append({"symbol": el.symbol, "energy": el.energy})
        except IndexError:
            pass
        return elements

    def getDefaultMadEnergies(self):
        # this does not seem to be used anywhere
        energies = []
        try:
            for el in self["mad"]:
                energies.append([float(el.energy), el.directory])
        except IndexError:
            pass
        return energies

    def get_scan_data(self):
        if self.test_data_mode:
            return self.simul_data
        return self.scan_data

    def load_data_file(self, filename):
        lines = open(filename).readlines()

        data = []
        in_header = True

        for line in lines:
            line = line.strip()
            try:
                x, y = map(float, line.split())
                # got good data... i
                in_header = False
            except Exception:
                if in_header:
                    continue
                else:
                    print("Wrong line in data file")

            data.append((x, y))

        self.log.debug(" loaded simulated data is \n%s" % str(data))
        return data


def test_hwo(scan):
    print("ELEMENTS:")
    print("---------")
    print(scan.getElements())
    print(scan.get_scan_data())
