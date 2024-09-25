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
BIOMAXEnergyScan
"""

import tango
import os
import time
import gevent
import logging

try:
    import PyChooch
except ImportError:
    logging.getLogger("HWR").warning("EnergyScan: PyChooch not available")
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.pyplot as plt
from numpy import arange
from mxcubecore.HardwareObjects.abstract.AbstractEnergyScan import AbstractEnergyScan
from mxcubecore.TaskUtils import cleanup
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR
import numpy as np
import traceback
import h5py

SCAN_TRANSMISSION = 0.5
MIN_COUNTS = 1000
MAX_COUNTS = 5000
AVG_COUNTS = 2500

__author__ = "Abdullah Amjad, Mikel Eguiraun, Ishkan Gorgisyan"
__credits__ = ["MXCuBE colaboration"]

__version__ = "2.2."
__maintainer__ = "Mikel Eguiraun"
__email__ = "mikel.eguiraun[at]maxiv.lu.se"
__status__ = "Production"


class BIOMAXContinuousScan(AbstractEnergyScan):
    def __init__(self, name):
        """
        Descript. :
        """
        AbstractEnergyScan.__init__(self, name)
        self.ready_event = None
        self.scan_data = None
        self.initial_transmission_value = None
        self.initial_energy_value = None

        # Lis harmonic jumps. Should not scan over these.
        self.Eh = [6000, 9060.0, 12610.0, 17270.0, 20400, 25000]

    def init(self):
        """
        Descript. :
        """
        self.ready_event = gevent.event.Event()
        self.energy_scan_parameters = {}
        self.xray_table = open(
            "/mxn/groups/biomax/amptek/maxlab_macros/energy_edges.dat", "r"
        )
        self.remote_energy_table = open(
            "/mxn/groups/biomax/amptek/maxlab_macros/remote-energy.dat", "r"
        )

        try:
            self.xspress3 = tango.DeviceProxy("b311a-e/dia/xfs-01")
        except tango.DevFailed:
            logging.getLogger("HWR").error(
                "BIOMAXEnergyScan: unable to connect to Counter Device"
            )

        try:
            self.pandabox = tango.DeviceProxy("b311a/tim/panda-01")
        except tango.DevFailed:
            logging.getLogger("HWR").error("Unable to connect to pandabox")

        try:
            self.door = tango.DeviceProxy("biomax/door/01")
        except tango.DevFailed:
            logging.getLogger("HWR").error("Unable to connect to sardana door device")

        try:
            self.pidx = tango.DeviceProxy("b311a/ctl/pid-01")
            self.pidx.set_timeout_millis(7000)
            self.pidy = tango.DeviceProxy("b311a/ctl/pid-02")
            self.pidy.set_timeout_millis(7000)
        except tango.DevFailed:
            logging.getLogger("HWR").error("Unable to connect to pid controllers")

    def calculate_emission_and_edge_energy(self, element=None, edge=None):
        edge_energy = 0.0
        emission = 0.0
        next(self.xray_table)
        for line in self.xray_table:
            fields = line.split()
            if element == fields[1]:
                if edge == "K":
                    edge_energy = float(fields[3])
                    emission = float(fields[4])
                if edge == "L":
                    edge_energy = float(fields[8])
                    emission = float(fields[9])
        self.xray_table.seek(0)
        logging.getLogger("HWR").info(
            "Absorption edge for %s %s: %f eV; Emission energy: %f eV",
            element,
            edge,
            edge_energy,
            emission,
        )
        return (edge_energy, emission)

    def prepare_detector(self, emission):
        """
        Preparing Xspress3mini detector
        """
        self.xspress3.Init()
        self.xspress3.Window1_Ch0 = [int(emission / 10) - 15, int(emission / 10) + 15]
        # To be triggered by panda
        self.xspress3.TriggerMode = "EXTERNAL_MULTI_GATE"
        # prevent writing to the file
        self.xspress3.WriteHdf5 = False
        self.xspress3.nTriggers = 1
        self.xspress3.nFramesPerTrigger = 1

    def run_sardana_macro(self, start_energy, end_energy, scan_file, scan_dir):
        # sardana macro will ensure the correc meas group!
        if self.door.state() != tango.DevState.ON:
            logging.getLogger("HWR").error(
                "Unable to run scan macro, door is not ready"
            )
            raise RuntimeError("Unable to run scan macro, door is not ready")
        logging.getLogger("HWR").info(
            "Sardana macro: energyContScan_mx3 %s %s %s %s",
            str(start_energy),
            str(end_energy),
            scan_file,
            scan_dir,
        )

        self.door.runMacro(
            [
                "energyContScan_mx3",
                str(start_energy),
                str(end_energy),
                scan_file,
                scan_dir,
            ]
        )
        logging.getLogger("HWR").info("Sardana macro launched, now waiting for finish")

        time.sleep(1)  # in case the state does not change fast, maybe needed
        with gevent.Timeout(60, RuntimeError("Scan macro timeout")):
            while self.door.state() == tango.DevState.RUNNING:
                gevent.sleep(0.2)

    def stop_pid_controllers(self):
        try:
            if (self.pidx.State() == tango.DevState.MOVING) and (
                self.pidy.State() == tango.DevState.MOVING
            ):
                self.pidx.StopCtrlLoop()
                self.pidy.StopCtrlLoop()
        except tango.DevFailed:
            logging.getLogger("HWR").warning(
                "Exception while stopping PID loops, nevertheless data acquisition continues."
            )

    def start_pid_controllers(self):
        if (self.pidx.State() != tango.DevState.MOVING) or (
            self.pidy.State() != tango.DevState.MOVING
        ):
            self.pidx.StartCtrlLoop()
            self.pidy.StartCtrlLoop()

            with gevent.Timeout(
                10, Exception("Timeout waiting for PID Controllers to be ready")
            ):
                while (self.pidx.State() != tango.DevState.MOVING) or (
                    self.pidy.State() != tango.DevState.MOVING
                ):
                    gevent.sleep(0.2)

    def prepare_panda(self, trig_time):
        """
        preparing the pandabox for triggering the shutter and detector
        """
        # trigger based on bragg positions
        self.pandabox.TriggerDomain = "POSITION"
        self.pandabox.EncInUse = True
        self.pandabox.ShutterDelay = 0.07
        logging.getLogger("HWR").info("closing the colibri shutter")
        self.pandabox.CloseShutter()

    def acq_detector(self, wait=True):
        """
        Start tango  device for the acquisition.

        Here we use the trigger signal from self.panda to both trigger the detector
        and open the colibri shutter for acquisition
        """
        self.xspress3.arm()

        with gevent.Timeout(10, Exception("Timeout waiting for xspress3 to be ready")):
            while self.xspress3.State().name != "RUNNING":
                gevent.sleep(0.2)

        ## send a single trigger
        self.pandabox.Start()

        if wait:
            with gevent.Timeout(
                10, Exception("Timeout waiting for acquisition to finish")
            ):
                while self.xspress3.State().name == "RUNNING":
                    gevent.sleep(0.2)

    def choose_attenuation(self):
        element = self.energy_scan_parameters["element"]
        edge = self.energy_scan_parameters["edge"]
        edge_energy, emission = self.calculate_emission_and_edge_energy(element, edge)
        _energy = edge_energy + 30

        # preparing xspress3
        logging.getLogger("HWR").info("Preparing fluorescence detector")

        self.prepare_detector(emission)

        # preparing the pandabox
        logging.getLogger("HWR").info("Preparing PandaBOX")

        self.pandabox.TriggerDomain = "TIME"
        self.pandabox.EncInUse = False
        self.pandabox.ExposureTime = 0.01
        self.pandabox.LatencyTime = 0
        self.pandabox.nPoints = 1
        # 40ms delay to start measuring when the shutter is fully open
        self.pandabox.ShutterDelay = 0.07
        self.pandabox.Arm()
        self.pandabox.CloseShutter()

        try:
            logging.getLogger("HWR").info(
                "Setting prepare transmission energy %s" % str(_energy)
            )
            HWR.beamline.energy.start_move_energy(_energy / 1000, check_beam=True)
        except Exception as ex:
            msg = "EnergyScan: cannot set scan Energy {}".format(ex)
            logging.getLogger("HWR").error(msg)
            raise RuntimeError(msg)

        try:
            logging.getLogger("HWR").info(
                "Setting start transmission %s" % str(SCAN_TRANSMISSION)
            )
            HWR.beamline.transmission.set_value(float(SCAN_TRANSMISSION), wait=True)
        except Exception as ex:
            msg = "EnergyScan: cannot set scan transmission {}".format(ex)
            logging.getLogger("HWR").error(msg)
            raise RuntimeError(msg)

        self.acq_detector()  # only used for prepare transmission
        counts = self.xspress3.ReadDtcCounts_Window1([0, 1, 1])[0]
        raw_counts = self.xspress3.ReadRawCounts_Window1([0, 1, 1])[0]
        logging.getLogger("HWR").info(
            "Setting start transmission, counts: %s" % str(counts)
        )
        logging.getLogger("HWR").info(
            "Setting start transmission, counts: %s" % str(raw_counts)
        )
        transmission = SCAN_TRANSMISSION

        if counts <= MIN_COUNTS:
            if counts > 0:
                transmission = SCAN_TRANSMISSION * (AVG_COUNTS / counts)
                if transmission > 10:
                    transmission = 10
                    logging.getLogger("HWR").info(
                        "Optimal transmission not found, but adjusted to 10%"
                    )
                else:
                    logging.getLogger("HWR").info(
                        "Optimal transmission found %s" % str(transmission)
                    )
            else:
                logging.getLogger("HWR").info(
                    "Optimal transmission not found, counts are zero."
                )

        elif counts > MAX_COUNTS:
            transmission = SCAN_TRANSMISSION * (AVG_COUNTS / counts)
            logging.getLogger("HWR").info(
                "Optimal transmission found %s" % str(transmission)
            )

        try:
            logging.getLogger("HWR").info(
                "Setting transmission for energy scan %s" % str(transmission)
            )
            HWR.beamline.transmission.set_value(float(transmission), wait=True)
        except Exception as ex:
            msg = "EnergyScan: cannot set scan transmission {}".format(ex)
            logging.getLogger("HWR").error(msg)
            raise RuntimeError(msg)

    def prepare_directory(self, directory):
        if not os.path.isdir(directory):
            logging.getLogger("HWR").debug(
                "EnergyScan: creating directory %s" % directory
            )
            try:
                os.makedirs(directory)
            except OSError as ex:
                logging.getLogger("HWR").error(
                    "EnergyScan: error creating directory %s (%s)"
                    % (directory, str(ex))
                )
                self.emit("energyScanFailed", ("Error creating directory",))
                raise RuntimeError(
                    "EnergyScan: error creating directory %s (%s)"
                    % (directory, str(ex))
                )

        energy_scan_filename = self.energy_scan_parameters["filename"]
        logging.getLogger("HWR").debug(
            "BIOMAXEnergyScan: {}".format(energy_scan_filename)
        )
        if os.path.exists(energy_scan_filename):
            logging.getLogger("HWR").debug(
                "BIOMAXEnergyScan: Aborting execution, File already exists on disk {}".format(
                    energy_scan_filename
                )
            )
            logging.getLogger("user_level_log").error(
                "BIOMAXEnergyScan: Aborting execution, File already exists on disk {}".format(
                    energy_scan_filename
                )
            )
            self.scan_command_aborted()
            raise Exception(
                "File already exists on disk {}".format(energy_scan_filename)
            )

    def adjust_run_number(self, directory, prefix):
        energy_scan_file_prefix = str(os.path.join(directory, prefix))

        if os.path.exists(energy_scan_file_prefix + ".h5"):
            i = 1
            while os.path.exists(energy_scan_file_prefix + "_%d.h5" % i):
                i = i + 1
            energy_scan_file_prefix += "_%d" % i
            prefix += "_%d" % i

        return prefix

    def energy_values(self, central_energy):
        # if energy value is not given
        if central_energy == 0:
            central_energy = HWR.beamline.energy.get_current_energy()  # units?
        # defining energy range around the edge energy
        Es = central_energy - 50
        Ef = central_energy + 50
        # checking that the scan doesn't pass over harmonic change
        for x in self.Eh:
            if x > Es and x < Ef:
                if x - Es < 30:
                    Es = x + 1
                    logging.getLogger("HWR").warning(
                        "Scan between %s and %s to avoid a harmonic jump.", Es, Ef
                    )
                elif Ef - x < 30:
                    Ef = x
                    logging.getLogger("HWR").warning(
                        "Scan between %s and %s to avoid a harmonic jump.", Es, Ef
                    )
                else:
                    logging.getLogger("HWR").error(
                        "The absorption edge is too close to a harmonic jump."
                    )

        return Es, Ef

    def escan_prepare(self):
        """
        Set the nesessary equipment in position for the scan. No need to know the escan paramets.
        """

        self.initial_transmission_value = HWR.beamline.transmission.get_att_factor()
        self.initial_energy_value = HWR.beamline.energy.get_current_energy()

        # ensure proper MD3 phase
        if HWR.beamline.diffractometer.get_current_phase() != "DataCollection":
            HWR.beamline.diffractometer.set_phase("DataCollection", wait=True)

        # and move to the centred positions after phase change
        if self.cpos:
            logging.getLogger("HWR").info("Moving to centring position")
            try:
                HWR.beamline.diffractometer.move_to_motors_positions(
                    self.cpos.as_dict(), wait=True
                )
            except ValueError as ex:
                logging.getLogger("HWR").warning(
                    "Could not move to centring position, {}".format(ex)
                )

        else:
            logging.getLogger("HWR").warning("Valid centring position not found")

        try:
            HWR.beamline.collect.open_safety_shutter()
        except Exception as ex:
            logging.getLogger("HWR").error("Open safety shutter: error %s" % str(ex))

        HWR.beamline.diffractometer.move_fluo_in()
        element = self.energy_scan_parameters["element"]
        edge = self.energy_scan_parameters["edge"]

        edge_energy, emission = self.calculate_emission_and_edge_energy(element, edge)
        Es, Ef = self.energy_values(edge_energy)
        self.energy_scan_parameters["Es"] = Es
        self.energy_scan_parameters["Ef"] = Ef

        logging.getLogger("HWR").info("closing the colibri shutter")
        self.pandabox.CloseShutter()
        # opening the fast shutter of MD3 as colibri shutter is now closed
        logging.getLogger("HWR").info("Openning MD3 fast shutter")
        HWR.beamline.diffractometer.open_fast_shutter()

        self.energy_scan_parameters[
            "transmissionFactor"
        ] = HWR.beamline.transmission.get_att_factor()
        self.energy_scan_parameters[
            "exposureTime"
        ] = 0.009  # defined in the sardana macro
        directory = self.energy_scan_parameters["directory"]
        prefix = self.adjust_run_number(
            directory, self.energy_scan_parameters["prefix"]
        )
        self.energy_scan_parameters["prefix"] = prefix
        file_name = prefix + ".h5"
        full_file_path = str(os.path.join(directory, file_name))
        self.energy_scan_parameters["filename"] = full_file_path  # dir + file name + h5
        self.scan_data = []

        logging.getLogger("HWR").info(
            "Energy scan info: %s", str(self.energy_scan_parameters)
        )
        self.prepare_directory(directory)

        self.prepare_panda(self.energy_scan_parameters["exposureTime"])

    def execute_energy_scan(self, energy_scan_parameters):
        """
        Execute the raw scan sequence. Here is where you pass whatever
        parameters you need to run the raw scan (e.g start/end energy,
        counting time, energy step...).
        """
        try:
            try:
                logging.getLogger("HWR").info(
                    "Setting start energy %s"
                    % str(self.energy_scan_parameters["Es"] / 1000)
                )
                HWR.beamline.energy.start_move_energy(
                    self.energy_scan_parameters["Es"] / 1000, check_beam=True
                )
            except Exception as ex:
                logging.getLogger("HWR").error(
                    "EnergyScan: cannot set scan Energy %s" % ex
                )
                return False

            self.stop_pid_controllers()

            logging.getLogger("HWR").info("Running sardana macro")
            self.run_sardana_macro(
                energy_scan_parameters["Es"],
                energy_scan_parameters["Ef"],
                energy_scan_parameters["filename"],
                energy_scan_parameters["directory"],
            )
        except Exception as ex:
            logging.getLogger("HWR").error(
                "EnergyScan: error in executing energy scan command %s" % ex
            )
            self.emit("energyScanFailed", ("Error in executing energy scan command",))
            self.scan_command_failed()

    def escan_postscan(self):
        """
        set the nesessary equipment in position after the scan
        """
        self.closure()

        logging.getLogger("HWR").info(
            "Setting original energy %s" % str(self.initial_energy_value)
        )
        HWR.beamline.energy.start_move_energy(
            self.initial_energy_value, check_beam=False
        )
        logging.getLogger("HWR").info(
            "Setting original transmission %s" % str(self.initial_transmission_value)
        )
        HWR.beamline.transmission.set_value(
            float(self.initial_transmission_value), wait=True
        )

        self.scan_command_finished(
            self.energy_scan_parameters["prefix"],
            self.energy_scan_parameters["directory"],
        )

    def cancel_energy_scan(self, *args):
        """
        Descript. :
        """
        self.scan_command_aborted()

    def escan_cleanup(self):
        self.closure()

    def scan_command_failed(self, *args):
        """
        Descript. :
        """
        logging.getLogger("HWR").error("BIOMAXEnergyScan: energy scan failed")
        self.energy_scan_parameters["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        logging.getLogger("HWR").info("Stopping Energy")
        HWR.beamline.energy.cancel_move_energy()
        logging.getLogger("HWR").info("Stopping Transmission")
        HWR.beamline.transmission.stop()

        self.closure()

        self.emit("energyScanFailed", ())
        self.ready_event.set()

    def scan_command_aborted(self, *args):
        """
        Descript. :
        """
        logging.getLogger("HWR").error("BIOMAXEnergyScan: energy scan aborted")
        self.closure()

        self.emit("energyScanFailed", ())
        self.ready_event.set()

    def closure(self):
        """
        Descript. :
        """
        HWR.beamline.diffractometer.wait_device_ready()
        logging.getLogger("HWR").info("Closing fast shutter")
        HWR.beamline.diffractometer.close_fast_shutter()
        logging.getLogger("HWR").info("Moving out fluorescence detector")
        HWR.beamline.diffractometer.move_fluo_out(wait=False)
        logging.getLogger("HWR").info("Opening Colibri shutter")
        self.pandabox.OpenShutter()
        logging.getLogger("HWR").info("Startig PID controllers")
        try:
            self.start_pid_controllers()
        except tango.DevFailed:
            logging.getLogger("HWR").error("Cannot start PID controllers")

    def read_raw_data(self, filename):
        logging.getLogger("HWR").info("Waiting for result file %s" % filename)

        with gevent.Timeout(20, Exception("Timeout waiting for scan result file")):
            while not os.path.exists(filename):
                gevent.sleep(0.5)

        try:
            file = h5py.File(filename)
            measurement = file.get(list(file.keys())[0]).get("measurement")
            energy = measurement.get("pcap_energy_av")[()]
            counts = measurement.get("xspress3_mini_ct_dtc_1")[()]
            self.scan_data = np.column_stack((energy, counts))
        except Exception as ex:
            logging.getLogger("HWR").error("Error reading data file: %s" % str(ex))
            self.scan_data = []
        finally:
            file.close()

        try:
            if len(self.scan_data) != 0:
                txt_path = os.path.join(filename + ".txt")
                logging.getLogger("HWR").info(
                    "Saving scan data to txt file %s" % txt_path
                )
                np.savetxt(txt_path, self.scan_data, fmt=["%d", "%d"])
        except Exception as ex:
            logging.getLogger("HWR").error("Error saving txt data file: %s" % str(ex))

    def scan_command_finished(self, prefix, directory):
        """
        Descript. :
        """
        self.energy_scan_parameters["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        logging.getLogger("HWR").debug("BIOMAXFlyEnergyScan: energy scan finished")

        self.read_raw_data(self.energy_scan_parameters["filename"])
        self.energy_scan_parameters["startEnergy"] = self.scan_data[0][0] / 1000
        self.energy_scan_parameters["endEnergy"] = self.scan_data[-1][0] / 1000
        beam_size = HWR.beamline.beam.get_beam_size()
        self.energy_scan_parameters["beamSizeHorizontal"] = int(beam_size[0] * 1000)
        self.energy_scan_parameters["beamSizeVertical"] = int(beam_size[1] * 1000)
        try:
            self.energy_scan_parameters["flux"] = HWR.beamline.flux.estimate_flux()
        except:
            self.energy_scan_parameters["flux"] = 0.0

        filename = self.energy_scan_parameters["filename"]
        if "h5" not in filename:
            energy_scan_raw_file_name = os.path.extsep.join((filename, "h5"))
            energy_scan_png_file_name = os.path.extsep.join((filename, "png"))
        else:
            energy_scan_raw_file_name = filename
            _tmp = filename.split(".h5")[0]
            energy_scan_png_file_name = os.path.extsep.join((_tmp, "png"))

        self.energy_scan_parameters["scanFileFullPath"] = str(energy_scan_raw_file_name)

        plt.plot(*zip(*self.scan_data))
        plt.savefig(energy_scan_png_file_name)
        plt.close()
        try:
            self.store_energy_scan()
        except Exception as ex:
            logging.getLogger("HWR").error(ex)
        self.emit("energyScanFinished", (self.energy_scan_parameters,))
        logging.getLogger("HWR").debug(
            "energyScanFinished signal emitted %r", self.energy_scan_parameters
        )

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
        Descript. : returns energy scan data.
                    List contains tuples of (energy, counts)
        """
        return self.scan_data

    def store_energy_scan(self):
        """
        Descript. :
        """
        logging.getLogger("HWR").debug(
            "EnergyScan info %r", self.energy_scan_parameters
        )

        blsampleid = self.energy_scan_parameters.get("blSampleId", None)
        if blsampleid:
            self.energy_scan_parameters.pop("blSampleId")
        if HWR.beamline.lims:
            self.energy_scan_parameters["startTime"] = str(
                self.energy_scan_parameters["startTime"]
            )
            self.energy_scan_parameters["endTime"] = str(
                self.energy_scan_parameters["endTime"]
            )
            db_status = None
            try:
                db_status = HWR.beamline.lims.storeEnergyScan(
                    self.energy_scan_parameters
                )
            except Exception as ex:
                logging.getLogger("HWR").warning(
                    "Energy scan store in lims failed %s" % str(ex)
                )
            if db_status:
                energyscanid = int(db_status["energyScanId"])
            else:
                energyscanid = -1
            self.energy_scan_parameters["energyScanId"] = energyscanid
            logging.getLogger("HWR").debug(
                "EnergyScan info %r", self.energy_scan_parameters
            )

            if blsampleid is not None:
                try:
                    asoc = {"blSampleId": blsampleid, "energyScanId": energyscanid}
                    HWR.beamline.lims.associateBLSampleAndEnergyScan(asoc)
                except Exception as ex:
                    logging.getLogger("HWR").warning(
                        "Energy scan store in lims failed %s" % str(ex)
                    )

    def calculate_remote_energy(self, elt, edge):
        for line in self.remote_energy_table:
            if line.startswith("#"):
                continue
            fields = line.split()
            if elt == fields[0] and edge == fields[1]:
                self.remote_energy_table.seek(0)
                return float(fields[2]), float(fields[3]), float(fields[4])
        self.remote_energy_table.seek(0)
        return None

    # flake8: noqa: C901
    def do_chooch(self, elt, edge, scan_directory, archive_directory, prefix):
        logging.getLogger("HWR").info(
            "Doing Chooch, scan directory %s, prefix  %s" % (scan_directory, prefix)
        )
        # self.adjust_run_number() may update the prefix, so we use the prefix attribute instead
        archive_file_prefix = str(os.path.join(archive_directory, prefix))
        data_filename = os.path.join(scan_directory, prefix)
        if "h5" not in data_filename:
            data_filename = data_filename + ".h5"
        archive_file_efs_filename = os.path.extsep.join((archive_file_prefix, "efs"))
        if "h5" not in archive_file_prefix:
            archive_file_png_filename = os.path.extsep.join(
                (archive_file_prefix, "png")
            )
        else:
            _tmp = archive_file_prefix.split(".h5")[0]
            archive_file_png_filename = os.path.extsep.join((_tmp, "png"))

        scanData = []
        x_array = []
        y_array = []
        for i in range(len(self.scan_data)):
            x = float(self.scan_data[i][0])
            # x = x < 1000 and x * 1000.0 or x
            y = float(self.scan_data[i][1])
            scanData.append((x, y))
            x_array.append(x)
            y_array.append(y)

        # print "=============================== chooch %s" % str(x_array)
        rm, rmfprime, rmfdoubleprime = self.calculate_remote_energy(elt, edge)
        # if the element edge combination is not in the lookup table
        if rm is None:
            rm, rmfprime, rmfdoubleprime = 0.0

        try:
            pk, fppPeak, fpPeak, ip, fppInfl, fpInfl, chooch_graph_data = PyChooch.calc(
                tuple(zip(x_array, y_array)), elt, edge, archive_file_efs_filename
            )
        except Exception:
            self.store_energy_scan()
            traceback.print_exc()
            logging.getLogger("HWR").error("Energy scan: Chooch failed")
            return None, None, None, None, None, None, None, [], [], [], None
        time.sleep(0.1)
        pk = pk / 1000.0
        ip = ip / 1000.0
        comm = ""
        try:
            # saving results into h5 file
            logging.getLogger("HWR").info(
                "Energy scan: saving chooch results into file %s" % data_filename
            )
            file = h5py.File(data_filename, "a")
            entry = file.keys()[0]
            dset = file.create_dataset("/{}/results/peak_energy".format(entry), data=pk)
            dset.attrs["unit"] = "keV"
            dset = file.create_dataset(
                "/{}/results/inflection_energy".format(entry), data=ip
            )
            dset.attrs["unit"] = "keV"
            dset = file.create_dataset(
                "/{}/results/remote_energy".format(entry), data=rm
            )
            dset.attrs["unit"] = "keV"
            file.close()
        except Exception as ex:
            logging.getLogger("HWR").error(
                "Energy scan: cannot save chooch results to file: %s" % ex
            )
        edge_energy, emission = self.calculate_emission_and_edge_energy(elt, edge)
        self.energy_scan_parameters["edgeEnergy"] = edge_energy
        self.th_edge = self.energy_scan_parameters["edgeEnergy"]

        self.energy_scan_parameters["peakEnergy"] = pk
        self.energy_scan_parameters["inflectionEnergy"] = ip
        self.energy_scan_parameters["remoteEnergy"] = rm
        self.energy_scan_parameters["remoteFPrime"] = rmfprime
        self.energy_scan_parameters["remoteFDoublePrime"] = rmfdoubleprime
        self.energy_scan_parameters["peakFPrime"] = fpPeak
        self.energy_scan_parameters["peakFDoublePrime"] = fppPeak
        self.energy_scan_parameters["inflectionFPrime"] = fpInfl
        self.energy_scan_parameters["inflectionFDoublePrime"] = fppInfl
        self.energy_scan_parameters["comments"] = comm
        self.energy_scan_parameters["choochFileFullPath"] = archive_file_efs_filename
        self.energy_scan_parameters["workingDirectory"] = archive_directory

        chooch_graph_x = []
        chooch_graph_y1 = []
        chooch_graph_y2 = []
        try:
            for row in chooch_graph_data:
                chooch_graph_x.append(row[0])
                chooch_graph_y1.append(row[1])
                chooch_graph_y2.append(row[2])
        except Exception:
            pass

        chooch_graph_x = list(chooch_graph_x)
        try:
            title = "Chooch Analysis"
            # fig = plt.figure( figsize=(15, 11))
            title = "%s\n%s" % (archive_file_efs_filename, title)
            # plt.title(title)
            fig, subplots = plt.subplots(2, 1, figsize=(15, 11))
            subplots[0].set_title(title)
            subplots[0].plot(x_array, y_array, **{"color": "black"})
            subplots[0].grid(True)
            subplots[0].set_xlabel("Energy (eV)")
            subplots[0].set_ylabel("MCA counts")

            subplots[1].plot(chooch_graph_x, chooch_graph_y1, color="blue")
            subplots[1].plot(chooch_graph_x, chooch_graph_y2, color="red")
            subplots[1].grid(True)
            subplots[1].set_xlabel("Energy (eV)")
            subplots[1].set_ylabel("")
            subplots[1].axvline(pk * 1000, linestyle="--", color="blue")
            subplots[1].axvline(ip * 1000, linestyle="--", color="red")
            plt.tight_layout()
        except Exception as ex:
            print(ex)
            logging.getLogger("HWR").debug(ex)

        try:
            # saving processing results into h5 file
            logging.getLogger("HWR").info(
                "Energy scan: saving chooch processing results into file %s"
                % data_filename
            )
            file = h5py.File(data_filename, "a")
            entry = file.keys()[0]
            dset = file.create_dataset(
                "/{}/results/chooch_x".format(entry), data=chooch_graph_x
            )
            dset.attrs["unit"] = "eV"
            dset = file.create_dataset(
                "/{}/results/chooch_y1".format(entry), data=chooch_graph_y1
            )
            dset.attrs["unit"] = ""
            dset = file.create_dataset(
                "/{}/results/chooch_y2".format(entry), data=chooch_graph_y2
            )
            dset.attrs["unit"] = ""
            file.close()
        except Exception as ex:
            logging.getLogger("HWR").error(
                "Energy scan: cannot save chooch processing results to file: %s" % ex
            )

        self.energy_scan_parameters["jpegChoochFileFullPath"] = str(
            archive_file_png_filename
        )
        try:
            logging.getLogger("HWR").info(
                "Saving energy scan to archive directory for ISPyB : %s",
                archive_file_png_filename,
            )
            dirname = os.path.dirname(archive_file_png_filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            fig.savefig(archive_file_png_filename, dpi=80)
            plt.close()
        except BaseException as ex:
            print(ex)
            logging.getLogger("HWR").exception("could not save figure %s" % ex)

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

    def get_elements(self):
        """
        Return list of dicts with element and energy level
            [
                {'symbol': 'Mn', 'energy': 'K'},
                {'symbol': 'Fe', 'energy': 'K'
            ]
        """
        elements = []
        try:
            for el in self["elements"]:
                elements.append({"symbol": el.symbol, "energy": el.energy})
        except IndexError:
            pass
        return elements
