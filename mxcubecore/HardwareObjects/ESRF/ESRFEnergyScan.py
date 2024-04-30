import logging
import time
import os
import os.path
import shutil
import math
import gevent

# import PyChooch
# to run chooch in shell
import subprocess
import numpy

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg

from mxcubecore.TaskUtils import task
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractEnergyScan import (
    AbstractEnergyScan,
)
from mxcubecore import HardwareRepository as HWR


class FixedEnergy:
    @task
    def get_value(self):
        return self._tunable_bl.energy_obj.get_value()


class TunableEnergy:
    @task
    def get_value(self):
        return self._tunable_bl.energy_obj.get_value()

    @task
    def set_value(self, value):
        return self._tunable_bl.energy_obj.set_value(value, wait=True)


class GetStaticParameters:
    def __init__(self, config_file, element, edge):
        self.element = element
        self.edge = edge
        self.STATICPARS_DICT = {}
        self.STATICPARS_DICT = self._readParamsFromFile(config_file)

    def _readParamsFromFile(self, config_file):
        with open(config_file, "r") as f:
            array = []
            for line in f:
                if not line.startswith("#") and self.element in line:
                    array = line.split()
                    break

            try:
                static_pars = {}
                static_pars["atomic_nb"] = int(array[0])
                static_pars["eroi_min"] = float(array[11]) / 1000.0
                static_pars["eroi_max"] = float(array[12]) / 1000.0

                if "K" in self.edge:
                    th_energy = float(array[3]) / 1000.0
                else:
                    if "1" in self.edge:
                        # L1
                        th_energy = float(array[6]) / 1000.0
                    elif "2" in self.edge:
                        # L2
                        th_energy = float(array[7]) / 1000.0
                    else:
                        # L or L3
                        th_energy = float(array[8]) / 1000.0

                # all the values are in keV
                static_pars["edgeEnergy"] = th_energy
                static_pars["startEnergy"] = th_energy - 0.05
                static_pars["endEnergy"] = th_energy + 0.05
                static_pars["findattEnergy"] = th_energy + 0.03
                static_pars["remoteEnergy"] = th_energy + 1
                return static_pars
            except Exception as e:
                print(e)
                return {}


class ESRFEnergyScan(AbstractEnergyScan, HardwareObject):
    def __init__(self, name, tunable_bl):
        AbstractEnergyScan.__init__(self)
        HardwareObject.__init__(self, name)
        self._tunable_bl = tunable_bl

    def execute_command(self, command_name, *args, **kwargs):
        wait = kwargs.get("wait", True)
        cmd_obj = self.get_command_object(command_name)
        return cmd_obj(*args, wait=wait)

    def init(self):
        self.energy_obj = self.get_object_by_role("energy")
        self.beamsize = self.get_object_by_role("beamsize")
        self.transmission = self.get_object_by_role("transmission")
        self.ready_event = gevent.event.Event()
        if HWR.beamline.lims is None:
            logging.getLogger("HWR").warning(
                "EnergyScan: you should specify the database hardware object"
            )
        self.scanInfo = None
        self._tunable_bl.energy_obj = self.energy_obj

    def is_connected(self):
        return True

    def get_static_parameters(self, config_file, element, edge):
        pars = GetStaticParameters(config_file, element, edge).STATICPARS_DICT

        offset_keV = self.get_property("offset_keV")
        pars["startEnergy"] += offset_keV
        pars["endEnergy"] += offset_keV
        pars["element"] = element

        return pars

    def open_safety_shutter(self, timeout=None):
        HWR.beamline.safety_shutter.openShutter()
        with gevent.Timeout(
            timeout, RuntimeError("Timeout waiting for safety shutter to open")
        ):
            while HWR.beamline.safety_shutter.getShutterState() == "closed":
                time.sleep(0.1)

    def close_safety_shutter(self, timeout=None):
        HWR.beamline.safety_shutter.closeShutter()
        while HWR.beamline.safety_shutter.getShutterState() == "opened":
            time.sleep(0.1)

    def escan_prepare(self):

        if self.beamsize:
            bsX = self.beamsize.get_size(self.beamsize.get_value().name)
            self.energy_scan_parameters["beamSizeHorizontal"] = bsX
            self.energy_scan_parameters["beamSizeVertical"] = bsX

    def escan_postscan(self):
        self.execute_command("cleanScan")

    def escan_cleanup(self):
        self.close_fast_shutter()
        self.close_safety_shutter()
        try:
            self.execute_command("cleanScan")
        except Exception:
            pass
        self.emit("energyScanFailed", ())
        self.ready_event.set()

    def close_fast_shutter(self):
        self.execute_command("close_fast_shutter")

    def open_fast_shutter(self):
        self.execute_command("open_fast_shutter")

    def move_energy(self, energy):
        try:
            HWR.beamline.energy.set_value(energy)
        except Exception:
            self.emit("energyScanFailed", ())
            raise RuntimeError("Cannot move energy")

    def cancelEnergyScan(self, *args):
        """ Called by queue_entry.py. To be removed"""
        self.escan_cleanup()

    # Elements commands
    def get_elements(self):
        elements = []
        try:
            for el in self["elements"]:
                elements.append({"symbol": el.symbol, "energy": el.energy})
        except IndexError:
            pass

        return elements

    def storeEnergyScan(self):
        if HWR.beamline.lims is None:
            return
        try:
            int(self.energy_scan_parameters["sessionId"])
        except Exception:
            return

        # remove unnecessary for ISPyB fields:
        self.energy_scan_parameters.pop("prefix")
        self.energy_scan_parameters.pop("eroi_min")
        self.energy_scan_parameters.pop("eroi_max")
        self.energy_scan_parameters.pop("findattEnergy")
        self.energy_scan_parameters.pop("edge")
        self.energy_scan_parameters.pop("directory")
        self.energy_scan_parameters.pop("atomic_nb")

        gevent.spawn(
            StoreEnergyScanThread, HWR.beamline.lims, self.energy_scan_parameters
        )

    def do_chooch(self, elt, edge, directory, archive_directory, prefix):
        self.energy_scan_parameters["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")

        raw_data_file = os.path.join(directory, "data.raw")

        symbol = "_".join((elt, edge))
        archive_prefix = "_".join((prefix, symbol))
        raw_scan_file = os.path.join(directory, (archive_prefix + ".raw"))
        efs_scan_file = raw_scan_file.replace(".raw", ".efs")
        raw_arch_file = os.path.join(archive_directory, (archive_prefix + "1" + ".raw"))

        i = 0
        while os.path.isfile(raw_arch_file):
            i += 1
            raw_arch_file = os.path.join(
                archive_directory, (archive_prefix + str(i) + ".raw")
            )

        png_scan_file = raw_scan_file.replace(".raw", ".png")
        png_arch_file = raw_arch_file.replace(".raw", ".png")

        if not os.path.exists(archive_directory):
            os.makedirs(archive_directory)
        try:
            f = open(raw_scan_file, "w")
        except IOError:
            self.storeEnergyScan()
            self.emit("energyScanFailed", ())
            return
        else:
            scan_data = []
            try:
                with open(raw_data_file, "r") as raw_file:
                    for line in raw_file.readlines()[2:]:
                        try:
                            (x, y) = line.split("\t")
                        except Exception:
                            (x, y) = line.split()
                        x = float(x.strip())
                        y = float(y.strip())
                        scan_data.append((x, y))
                        f.write("%f,%f\r\n" % (x, y))
                f.close()
            except IOError:
                self.storeEnergyScan()
                self.emit("energyScanFailed", ())
                return

        shutil.copy2(raw_scan_file, raw_arch_file)
        self.energy_scan_parameters["scanFileFullPath"] = raw_arch_file

        """
        result = PyChooch.calc(scan_data, elt, edge, efs_scan_file)
        # PyChooch occasionally returns an error and the result
        # the sleep command assures that we get the result
        time.sleep(1)
        print(result[0])
        pk = result[0] / 1000.0
        fppPeak = result[1]
        fpPeak = result[2]
        ip = result[3] / 1000.0
        fppInfl = result[4]
        fpInfl = result[5]
        chooch_graph_data = result[6]
        """
        # while waiting fro chooch to work...
        subprocess.call(
            [
                "/opt/pxsoft/bin/chooch",
                "-e",
                elt,
                "-a",
                edge,
                "-o",
                efs_scan_file,
                "-g",
                png_scan_file,
                raw_data_file,
            ]
        )
        time.sleep(5)
        with open(efs_scan_file, "r") as f:
            for _ in range(3):
                next(f)
            nparr = numpy.array([list(map(float, line.split())) for line in f])
        fppPeak = nparr[:, 1].max()
        idx = numpy.where(nparr[:, 1] == fppPeak)
        pk = nparr[:, 0][idx][0] / 1000.0
        fpPeak = nparr[:, 2][idx][0]
        fppInfl = nparr[:, 2].min()
        idx = numpy.where(nparr[:, 2] == fppInfl)
        ip = nparr[:, 0][idx][0] / 1000.0
        fpInfl = nparr[:, 1][idx][0]
        rm = pk + 0.03

        comm = ""
        th_edge = float(self.energy_scan_parameters["edgeEnergy"])

        logging.getLogger("HWR").info(
            "Chooch results: pk = %f, ip = %f, rm = %f, Theoretical edge: %f"
            % (pk, ip, rm, th_edge)
        )

        # +- shift from the theoretical edge [eV]
        edge_shift = 10
        calc_shift = (th_edge - ip) * 1000
        if math.fabs(calc_shift) > edge_shift:
            rm = th_edge + 0.03
            comm = "%s" % "below" if (calc_shift) > edge_shift else "above"
            comm = (
                "Calculated peak (%f) is more than %d eV %s the theoretical value (%f)."
                % (pk, edge_shift, comm, th_edge)
            )

            logging.getLogger("user_level_log").info(
                "EnergyScan: %s Check your scan and choose the energies manually" % comm
            )
            pk = 0
            ip = 0

        efs_arch_file = raw_arch_file.replace(".raw", ".efs")
        if os.path.isfile(efs_scan_file):
            shutil.copy2(efs_scan_file, efs_arch_file)
        else:
            self.storeEnergyScan()
            self.emit("energyScanFailed", ())
            return

        self.energy_scan_parameters["filename"] = raw_arch_file.split("/")[-1]
        self.energy_scan_parameters["peakEnergy"] = pk
        self.energy_scan_parameters["inflectionEnergy"] = ip
        self.energy_scan_parameters["remoteEnergy"] = rm
        self.energy_scan_parameters["peakFPrime"] = fpPeak
        self.energy_scan_parameters["peakFDoublePrime"] = fppPeak
        self.energy_scan_parameters["inflectionFPrime"] = fpInfl
        self.energy_scan_parameters["inflectionFDoublePrime"] = fppInfl
        self.energy_scan_parameters["comments"] = comm

        """
        chooch_graph_x, chooch_graph_y1, chooch_graph_y2 = zip(*chooch_graph_data)
        chooch_graph_x = list(chooch_graph_x)
        chooch_graph_x = [x / 1000.0 for x in chooch_graph_x]
        """
        logging.getLogger("HWR").info("Saving png")
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
        if os.path.isfile(png_scan_file):
            shutil.copy2(png_scan_file, png_arch_file)
        else:
            self.storeEnergyScan()
            self.emit("energyScanFailed", ())
            return
        """
        fig = Figure(figsize=(15, 11))
        ax = fig.add_subplot(211)
        ax.set_title("%s\n%s" % (efs_scan_file, title))
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
        """
        self.energy_scan_parameters["jpegChoochFileFullPath"] = str(png_arch_file)
        """
        try:
            logging.getLogger("HWR").info(
                "Rendering energy scan and Chooch graphs to PNG file : %s",
                png_scan_file,
            )
            canvas.print_figure(png_scan_file, dpi=80)
        except Exception:
            logging.getLogger("HWR").exception("could not print figure")
        try:
            logging.getLogger("HWR").info(
                "Saving energy scan to archive directory for ISPyB : %s", png_arch_file
            )
            canvas.print_figure(png_arch_file, dpi=80)
        except Exception:
            logging.getLogger("HWR").exception("could not save figure")
        """
        self.storeEnergyScan()

        self.emit(
            "chooch_finished",
            (
                pk,
                fppPeak,
                fpPeak,
                ip,
                fppInfl,
                fpInfl,
                rm,
                # chooch_graph_x,
                # chooch_graph_y1,
                # chooch_graph_y2,
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
            [],
            [],
            [],
            # chooch_graph_x,
            # chooch_graph_y1,
            # chooch_graph_y2,
            title,
        )


def StoreEnergyScanThread(db_conn, scan_info):
    scan_info = dict(scan_info)
    blsample_id = scan_info["blSampleId"]
    scan_info.pop("blSampleId")

    try:
        db_status = db_conn.storeEnergyScan(scan_info)
        if blsample_id is not None:
            try:
                escan_id = int(db_status["energyScanId"])
            except (NameError, KeyError):
                pass
            else:
                asso = {"blSampleId": blsample_id, "energyScanId": escan_id}
                db_conn.associateBLSampleAndEnergyScan(asso)
    except Exception as e:
        print(e)
