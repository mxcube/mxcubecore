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
BIOMAXXRFSpectrum
"""
import tango
import logging
import time
import os
import gevent
from gevent import monkey
import matplotlib.pyplot as plt
import numpy as np
import h5py

try:
    from detecta import detect_peaks

    peaks_available = True
except ImportError:
    peaks_available = False
from mxcubecore.HardwareObjects.abstract.AbstractXRFSpectrum import AbstractXRFSpectrum
from mxcubecore.TaskUtils import cleanup
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR

monkey.patch_all(thread=False)

MAX_TRANSMISSION = 100


class BIOMAXXRFSpectrum(AbstractXRFSpectrum, HardwareObject):
    """
    Descript.
    """

    def __init__(self, name):
        """
        Descript. :
        """
        AbstractXRFSpectrum.__init__(self, name)
        HardwareObject.__init__(self, name)

        self.ready_event = None
        self.stop_flag = False
        self.spectrum_running = None
        self.spectrum_info = None
        self.config_filename = None

        self.energy_hwobj = None
        self.transmission_hwobj = None
        self.safety_shutter_hwobj = None

        self.chan_spectrum_status = None
        self.chan_spectrum_consts = None
        self.cmd_spectrum_start = None
        self.cmd_adjust_transmission = None
        self.transmission_steps = [0.2, 0.4, 0.8, 1.6, 3, 6, 12, 24, 48, 96, 100]

    def init(self):
        """
        Descript. :
        """
        self.ready_event = gevent.event.Event()

        self.energy_hwobj = self.get_object_by_role("energy")
        self.safety_shutter_hwobj = self.get_object_by_role("safety_shutter")
        self.beam_info_hwobj = self.get_object_by_role("beam_info")
        self.transmission_hwobj = self.get_object_by_role("transmission")
        if self.transmission_hwobj is None:
            logging.getLogger("HWR").warning("Transmission hwobj not defined")
        self.flux_hwobj = self.get_object_by_role("flux")
        self.db_connection_hwobj = self.get_object_by_role("lims_client")
        self.diffractometer_hwobj = self.get_object_by_role("diffractometer")
        self.current_phi = None
        try:
            self.xspress3 = tango.DeviceProxy("b311a-e/dia/xfs-01")
            self.can_scan = True
        except tango.DevFailed:
            self.can_scan = False
            logging.getLogger("HWR").error(
                "BIOMAXEnergyScan: unable to connect to Counter Device"
            )

        try:
            self.pandabox = tango.DeviceProxy("b311a/tim/panda-01")
        except tango.DevFailed:
            self.can_scan = False
            logging.getLogger("HWR").error("Unable to connect to pandabox")

        # The xray_table file contains absorption edges and emission energies
        self.xray_table = open(
            "/mxn/groups/biomax/amptek/maxlab_macros/energy_edges.dat", "r"
        )

    def prepare_detector(self):
        # acquisition
        self.xspress3.Init()
        self.xspress3.Window1_Ch0 = [0, 4095]
        # to be triggered by panda
        self.xspress3.TriggerMode = "EXTERNAL_MULTI_GATE"
        self.xspress3.nTriggers = 1
        self.xspress3.nFramesPerTrigger = 1
        # saving attributes
        self.xspress3.WriteHdf5 = True
        # save the image at the user directory
        self.xspress3.DestinationFileName = self.spectrum_info["scanFileFullPath"]

    def prepare_panda(self, trig_time):
        """
        preparing the pandabox for triggering the shutter and detector
        """
        # trigger based on time
        self.pandabox.TriggerDomain = "TIME"
        self.pandabox.EncInUse = False
        self.pandabox.ExposureTime = trig_time
        self.pandabox.LatencyTime = 0
        self.pandabox.nPoints = 1
        # 4ms delay to start measuring when the shutter is fully open
        self.pandabox.ShutterDelay = 0.004
        self.pandabox.Arm()
        self.pandabox.CloseShutter()

    def acq_detector(self, wait=True):
        """
        Start xspress3 device for the acquisition.

        Here we use the trigger signal from self.dgpandabox to both trigger the detector
        and open the colibri shutter for acquisition
        """
        self.xspress3.arm()

        with gevent.Timeout(10, Exception("Timeout waiting for xspress3 to be ready")):
            while self.xspress3.State().name != "RUNNING":
                gevent.sleep(0.2)

        # this trigger opens the colibri shutter for the acquisition, as well as triggering the xspress3
        self.pandabox.Start()

        if wait:
            with gevent.Timeout(
                10, Exception("Timeout waiting for acquisition to finish")
            ):
                while self.xspress3.State().name == "RUNNING":
                    gevent.sleep(0.2)

    def prepare_directories(self, ct, spectrum_directory, archive_directory, prefix):
        if not os.path.isdir(archive_directory):
            logging.getLogger("user_level_log").info(
                "XRFSpectrum: creating directory %s" % archive_directory
            )
            logging.getLogger("HWR").debug(
                "XRFSpectrum: creating directory %s" % archive_directory
            )
            try:
                if not os.path.exists(archive_directory):
                    os.makedirs(archive_directory)
                if not os.path.exists(spectrum_directory):
                    os.makedirs(spectrum_directory)
            except OSError as diag:
                logging.getLogger("HWR").error(
                    "XRFSpectrum: error creating directory %s (%s)"
                    % (archive_directory, str(diag))
                )
                logging.getLogger("user_level_log").error(
                    "XRFSpectrum: error creating directory %s (%s)"
                    % (archive_directory, str(diag))
                )
                self.emit("xrfSpectrumStatusChanged", ("Error creating directory",))
                raise Exception(diag)

        archive_file_template = os.path.join(archive_directory, prefix)
        spectrum_file_template = os.path.join(spectrum_directory, prefix)
        if os.path.exists(archive_file_template + ".h5"):
            i = 1
            while os.path.exists(archive_file_template + "%d.h5" % i):
                i = i + 1
            archive_file_template += "_%d" % i
            spectrum_file_template += "_%d" % i
            prefix += "_%d" % i

        spectrum_file_dat_filename = os.path.extsep.join((spectrum_file_template, "h5"))
        archive_file_dat_filename = os.path.extsep.join((archive_file_template, "h5"))
        archive_file_png_filename = os.path.extsep.join((archive_file_template, "png"))
        archive_file_html_filename = os.path.extsep.join(
            (archive_file_template, "html")
        )

        self.spectrum_info["filename"] = prefix
        self.spectrum_info["scanFileFullPath"] = spectrum_file_dat_filename
        self.spectrum_info["jpegScanFileFullPath"] = archive_file_png_filename
        self.spectrum_info["exposureTime"] = ct
        self.spectrum_info["annotatedPymcaXfeSpectrum"] = archive_file_html_filename
        logging.getLogger("HWR").debug(
            "XRFSpectrum: spectrum data file is %s", spectrum_file_dat_filename
        )
        logging.getLogger("HWR").debug(
            "XRFSpectrum: archive file is %s", archive_file_dat_filename
        )

    def prepare_transmission(self, ct):
        """
        Starting at low transmission, scan the transmission until optimal counts are read from the detector
        """
        # self.current_energy = self.energy_hwobj.get_current_energy()
        logging.getLogger("HWR").info("Calculating optimal transmission")
        logging.getLogger("user_level_log").info("Calculating optimal transmission")

        # prepare detector as prepare_detector() function is not called by now
        # prevent writing to the file

        self.xspress3.Window1_Ch0 = [0, 4095]
        self.xspress3.TriggerMode = "EXTERNAL_MULTI_GATE"
        self.xspress3.nTriggers = 1
        self.xspress3.nFramesPerTrigger = 1
        self.xspress3.WriteHdf5 = False

        self.transmission_hwobj.set_value(0.1, True)
        # closes colibri shutter by default

        self.prepare_panda(0.01)
        # opening the fast shutter of MD3 as colibri shutter is now closed
        self.diffractometer_hwobj.open_fast_shutter()

        counts = 0
        step_index = 0
        new_transmission = self.transmission_steps[step_index]

        while (
            self.transmission_hwobj.get_value() <= MAX_TRANSMISSION and step_index <= 10
        ):
            if self.stop_flag:
                break
            self.acq_detector()
            # dead time corrected and raw counts
            counts = self.xspress3.ReadRawCounts_Window1([0, 1, 1])[
                0
            ]  # channel 1 frames from 1 to 1
            corrected_counts = self.xspress3.ReadDtcCounts_Window1([0, 1, 1])[0]
            _dtc = corrected_counts / counts

            logging.getLogger("HWR").debug(
                "Counts: {}, corrected: {}, dtc: {}".format(
                    counts, corrected_counts, _dtc
                )
            )
            # counts = self.roicounter.readCounters(0)[2]
            # dead time correction
            # _scalers = self.xspress3.ReadScalers([0,0])
            # _dtc = _scalers[10]
            # corrected_counts = counts * _dtc

            if _dtc < 1.08:  # corrected_counts/counts
                # move transmission again
                new_transmission = self.transmission_steps[step_index]
                if new_transmission < MAX_TRANSMISSION:
                    logging.getLogger("HWR").debug(
                        "Setting new transmission %s" % new_transmission
                    )
                    self.transmission_hwobj.set_value(new_transmission, True)
                else:
                    logging.getLogger("HWR").warning(
                        "Transmission adjusted but optimal value not found"
                    )
                    logging.getLogger("user_level_log").warning(
                        "Transmission adjusted but optimal value not found"
                    )
                    self.transmission_hwobj.set_value(MAX_TRANSMISSION, True)
                    break
            else:
                # go back to previous transmission and stay there
                if step_index > 1:
                    new_transmission = self.transmission_steps[step_index - 2]
                else:
                    new_transmission = float(self.transmission_hwobj.getAttFactor()) / 2

                logging.getLogger("HWR").debug(
                    "Setting new transmission %s" % new_transmission
                )
                self.transmission_hwobj.set_value(new_transmission, True)
                break

            step_index += 1

        final_transmission = self.transmission_hwobj.get_value()
        logging.getLogger("HWR").info(
            "Transmission adjusted at %s" % str(final_transmission)
        )
        logging.getLogger("user_level_log").info(
            "Transmission adjusted at %s" % str(final_transmission)
        )

    def startXrfSpectrum(
        self,
        ct,
        spectrum_directory,
        archive_directory,
        prefix,
        session_id=None,
        blsample_id=None,
        cpos=None,
        adjust_transmission=True,
    ):
        """
        Descript. :
        """
        self.ready_event.clear()
        self.stop_flag = False
        self.spectrum_running = True

        filename = os.path.join(spectrum_directory, prefix) + ".h5"
        if os.path.exists(filename):
            logging.getLogger("HWR").debug(
                "XRF Sprectrum aborted, file already exists on disk {}".format(filename)
            )
            self.spectrum_command_aborted()
            raise Exception(
                "XRF Sprectrum aborted, file already exists on disk {}".format(filename)
            )

        # ensure proper MD3 phase
        if self.diffractometer_hwobj.get_current_phase() != "DataCollection":
            self.diffractometer_hwobj.set_phase(
                "DataCollection", wait=True, timeout=200
            )

        # and move to the centred positions after phase change
        if cpos:
            logging.getLogger("HWR").info("Moving to centring position")
            self.diffractometer_hwobj.move_to_motors_positions(cpos, wait=True)
        else:
            logging.getLogger("HWR").warning("Valid centring position not found")

        try:
            self.open_safety_shutter()
        except Exception as ex:
            logging.getLogger("HWR").error("Open safety shutter: error %s" % str(ex))

        if ct <= 0:
            ct = 0.1

        logging.getLogger("HWR").info(
            "Starting XRF Spectrum with parameters ct: %s \
         spectrum_directory %s,\
         archive_directory %s,\
         prefix %s\
         session_id %s \
         blsample_id %s \
         adjust_transmission %s"
            % (
                ct,
                spectrum_directory,
                archive_directory,
                prefix,
                session_id,
                blsample_id,
                adjust_transmission,
            )
        )

        self.spectrum_info = {"sessionId": session_id, "blSampleId": blsample_id}
        try:
            self.prepare_directories(ct, spectrum_directory, archive_directory, prefix)

            self.diffractometer_hwobj.move_fluo_in()

            if adjust_transmission:
                self.prepare_transmission(ct)

            logging.getLogger("HWR").info("Preparing fluorescence detector")
            logging.getLogger("user_level_log").info("Preparing fluorescence detector")

            # this time we save data to disk
            self.prepare_detector()  # change defaults in mxcube UI
            self.prepare_panda(ct)
            # colibri shutter is closed at this point, but we need to open the fast shutter of the md3
            self.diffractometer_hwobj.open_fast_shutter()

            self.spectrum_command_started()

            self.execute_spectrum_command(
                ct, self.spectrum_info["scanFileFullPath"], adjust_transmission
            )
        except Exception as ex:
            logging.getLogger("HWR").error("XRFSpectrum: error %s" % str(ex))
            self.spectrum_command_aborted()

        self.closure()

        self.spectrum_command_finished()

    def execute_spectrum_command(self, count_sec, filename, adjust_transmission=True):
        logging.getLogger("HWR").info("Acquiring spectrum")
        logging.getLogger("user_level_log").info("Acquiring spectrum")
        try:
            self.acq_detector()
        except Exception:
            logging.getLogger("HWR").exception(
                "XRFSpectrum: problem in starting spectrum"
            )
            self.emit(
                "xrfSpectrumStatusChanged", ("Error problem in starting spectrum",)
            )
            self.spectrum_command_aborted()

    def spectrum_command_finished(self):
        """
        Descript. :
        """
        logging.getLogger("HWR").info("Sprectrum acquired, launching analysis")
        with cleanup(self.ready_event.set):
            self.spectrum_info["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.spectrum_running = False

            # We do not want to look at anything higher than the exciting energy
            # Or the inelastic scattering peak below the exciting energy
            upperlim = int(self.energy_hwobj.get_current_energy() * 100) - 150
            # The minimum energy is phosphor emission (ca. 2000 eV)
            lowerlim = 180
            output = ""
            data_folder = self.spectrum_info["scanFileFullPath"]
            logging.getLogger("HWR").info("Reading data from {}".format(data_folder))
            time.sleep(5)
            #           try:
            # 	        with gevent.Timeout(5, Exception("Timeout waiting for data file")):
            # 		    while not os.path.exists(data_folder):
            # 		        gevent.sleep(0.5)
            #            except Exception as ex:
            #                logging.getLogger("HWR").error(ex)
            #                raise

            with h5py.File(data_folder, "r") as spectrum_file:
                # reading the spectrum h5 file from the saved directory
                self.spectrum_data = spectrum_file["entry"]["instrument"]["xspress3"][
                    "data"
                ][0, 0, :]
            if peaks_available:
                peaks = detect_peaks.detect_peaks(
                    self.spectrum_data[lowerlim:upperlim], mph=8, mpd=40, threshold=4
                )
                logging.getLogger("HWR").info("Peaks: {}".format(peaks))

                # Ana : script for peak location
                # Skip first line with table headers
                for peak in peaks:
                    peak = 10 * (peak + lowerlim)
                    self.xray_table.seek(0)
                    next(self.xray_table)
                    for line in self.xray_table:
                        fields = line.split()
                        element = fields[1]
                        kalpha1 = float(fields[4])
                        lalpha1 = float(fields[9])
                        lbeta1 = float(fields[11])
                        laelement = 0
                        emission = [kalpha1, lalpha1, lbeta1]

                        for energies in emission:
                            if abs(energies - peak) < 100.0:
                                inner_output = "  " + str(peak) + " eV:"
                                if energies == kalpha1:
                                    kelement = element
                                    inner_output = (
                                        inner_output
                                        + " "
                                        + kelement
                                        + " Kalpha ("
                                        + str(energies)
                                        + " eV)"
                                    )
                                elif energies == lalpha1:
                                    laelement = element
                                    inner_output = (
                                        inner_output
                                        + " "
                                        + laelement
                                        + " Lalpha ("
                                        + str(energies)
                                        + " eV)"
                                    )
                                elif energies == lbeta1:
                                    if laelement == element:
                                        inner_output = (
                                            inner_output
                                            + " "
                                            + element
                                            + " Lbeta ("
                                            + str(energies)
                                            + " eV)"
                                        )
                                    else:
                                        inner_output = ""
                                if inner_output != "":
                                    output = output + inner_output + "\n"
                                logging.getLogger("HWR").info(output)
            # end of script
            else:
                peaks = []
            try:
                prop = data_folder.split("/")[4]
                sample = data_folder.split("raw")[1]
                tt = "Prop: {}\n".format(prop)
                tt += "Sample: {}\n".format(sample)
            except Exception:
                tt = ""
            if len(peaks) > 0 and len(output) > 0:
                tt += "Peak matches:\n{}".format(output)
                # energies = (peaks * 0.01) + 5 # offset from data above
                # tt += 'Peaks:\n'
            # for e in energies:
            # tt += (format(e, '.2f')+' keV \n')
            # TODO: calibrate
            self.mca_calib = []
            mca_config = {}
            # TODO: find peaks

            self.spectrum_info[
                "beamTransmission"
            ] = self.transmission_hwobj.getAttFactor()
            self.spectrum_info["energy"] = self.get_current_energy()
            beam_size = self.beam_info_hwobj.get_beam_size()
            self.spectrum_info["beamSizeHorizontal"] = int(beam_size[0] * 1000)
            self.spectrum_info["beamSizeVertical"] = int(beam_size[1] * 1000)

            self.spectrum_info["flux"] = self.flux_hwobj.estimate_flux()
            x = np.arange(5, 20, 0.01)
            plt.plot(x, self.spectrum_data[500:2000])
            plt.xlabel("Energy (keV)")
            plt.ylabel("counts")
            plt.title = self.spectrum_info["jpegScanFileFullPath"]
            ymin, ymax = plt.ylim()
            plt.text(12, 0.4 * ymax, tt)
            plt.savefig(self.spectrum_info["jpegScanFileFullPath"])
            # and save as well into data folder
            data_folder = os.path.dirname(self.spectrum_info["scanFileFullPath"])
            plt.savefig(os.path.join(data_folder, self.spectrum_info["filename"]))

            logging.getLogger("HWR").info(
                "XRFSpectrum: Rendering spectrum to PNG file : %s",
                self.spectrum_info["jpegScanFileFullPath"],
            )
            plt.close()
            status = self.store_xrf_spectrum()
            self.emit(
                "xrfSpectrumFinished",
                (
                    self.spectrum_data,
                    self.mca_calib,
                    mca_config,
                    status["xfeFluorescenceSpectrumId"],
                ),
            )
        logging.getLogger("HWR").info("XRF spectrum finished")
        logging.getLogger("user_level_log").info("XRF spectrum finished")

    def spectrum_command_failed(self, *args):
        """
        Descript. :
        """
        logging.getLogger("HWR").error("BIOMAXEnergyScan: XRF scan failed")
        self.spectrum_info["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.spectrum_running = False
        self.stop_flag = True
        self.closure()
        self.emit("xrfSpectrumFailed", ())
        self.ready_event.set()

    def spectrum_command_aborted(self, *args):
        """
        Descript. :
        """
        logging.getLogger("HWR").error("BIOMAXEnergyScan: XRF scan aborted")
        self.spectrum_running = False
        self.stop_flag = True
        self.closure()
        self.emit("xrfSpectrumFailed", ())
        self.ready_event.set()

    def closure(self):
        """
        Descript. :close things down and open the colibri shutter
        """
        self.diffractometer_hwobj.wait_device_ready()
        logging.getLogger("HWR").info("Closing fast shutter")
        self.diffractometer_hwobj.close_fast_shutter()
        logging.getLogger("HWR").info("Moving out fluorescence detector")
        self.diffractometer_hwobj.move_fluo_out(wait=False)
        logging.getLogger("HWR").info("Opening Colibri shutter")
        self.pandabox.OpenShutter()

    def cancel_spectrum(self, *args):
        """
        Descript. :
        """
        if self.spectrum_running:
            self.spectrum_command_aborted()
            # self.doSpectrum.abort()
            self.ready_event.set()

    def open_safety_shutter(self):
        """
        Descript. :
        """
        # todo add time out? if over certain time, then stop acquisiion and
        # popup an error message
        if self.safety_shutter_hwobj.getShutterState() == "opened":
            return
        timeout = 5
        count_time = 0
        logging.getLogger("HWR").info("Opening the safety shutter.")
        self.safety_shutter_hwobj.openShutter()
        while (
            self.safety_shutter_hwobj.getShutterState() == "closed"
            and count_time < timeout
        ):
            time.sleep(0.1)
            count_time += 0.1
        if self.safety_shutter_hwobj.getShutterState() == "closed":
            logging.getLogger("HWR").exception("Could not open the safety shutter")
            raise Exception("Could not open the safety shutter")

    def store_xrf_spectrum(self):
        """
        Descript. :
        """
        logging.getLogger("HWR").debug("XRFSpectrum info %r", self.spectrum_info)
        if self.db_connection_hwobj:
            return self.db_connection_hwobj.storeXfeSpectrum(self.spectrum_info)
