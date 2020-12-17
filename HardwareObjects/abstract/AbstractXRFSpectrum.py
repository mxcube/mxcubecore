"""
Represents Abstract XRF spectrum (name could be discussed) Abstract class is
compatible with queue_entry and emits these signals during the spectrum:
 - xrfSpectrumStarted
 - xrfSpectrumFinished
 - xrfSpectrumFailed
 - xrfSpectrumStatusChanged

Functions that needs a reimplementation:
- execute_spectrum_command : actual execution command
- cancel_spectrum
"""

import os
import logging
import time
import gevent
import gevent.event
import numpy
import abc
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from mx3core.TaskUtils import cleanup
from mx3core import HardwareRepository as HWR


class AbstractXRFSpectrum(object):
    """
    Descript.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self):
        """
        Descript. :
        """
        self.ready_event = None
        self.spectrum_info = None
        self.spectrum_data = None
        self.mca_calib = (10, 20, 0)
        self.spectrum_running = None
        self.config_filename = ""
        self.write_in_raw_data = True

        self.ready_event = gevent.event.Event()
        self.startXrfSpectrum = self.start_spectrum

    def start_spectrum(
        self,
        ct,
        spectrum_directory,
        archive_directory,
        prefix,
        session_id=None,
        blsample_id=None,
        adjust_transmission=True,
    ):
        """
        Descript. :
        """
        if not self.can_spectrum:
            self.spectrum_command_aborted()
            return False
        self.spectrum_info = {"sessionId": session_id, "blSampleId": blsample_id}

        if self.write_in_raw_data and not os.path.isdir(spectrum_directory):
            logging.getLogger("HWR").debug(
                "XRFSpectrum: creating directory %s" % spectrum_directory
            )
            try:
                if not os.path.exists(spectrum_directory):
                    os.makedirs(spectrum_directory)
            except OSError as diag:
                logging.getLogger().error(
                    "XRFSpectrum: error creating directory %s (%s)"
                    % (spectrum_directory, str(diag))
                )
                self.emit("xrfSpectrumStatusChanged", ("Error creating directory",))
                self.spectrum_command_aborted()
                return False

        if not os.path.isdir(archive_directory):
            try:
                if not os.path.exists(archive_directory):
                    os.makedirs(archive_directory)
            except OSError as diag:
                logging.getLogger().error(
                    "XRFSpectrum: error creating directory %s (%s)"
                    % (archive_directory, str(diag))
                )
                self.emit("xrfSpectrumStatusChanged", ("Error creating directory",))
                self.spectrum_command_aborted()
                return False

        archive_file_template = os.path.join(archive_directory, prefix)
        spectrum_file_template = os.path.join(spectrum_directory, prefix)
        if os.path.exists(archive_file_template + ".dat"):
            i = 1
            while os.path.exists(archive_file_template + "%d.dat" % i):
                i = i + 1
            archive_file_template += "_%d" % i
            spectrum_file_template += "_%d" % i
            prefix += "_%d" % i

        spectrum_file_dat_filename = os.path.extsep.join(
            (spectrum_file_template, "dat")
        )
        archive_file_dat_filename = os.path.extsep.join((archive_file_template, "dat"))
        archive_file_png_filename = os.path.extsep.join((archive_file_template, "png"))
        archive_file_html_filename = os.path.extsep.join(
            (archive_file_template, "html")
        )

        self.spectrum_info["filename"] = prefix
        self.spectrum_info["workingDirectory"] = archive_directory
        self.spectrum_info["scanFilePath"] = spectrum_file_dat_filename
        self.spectrum_info["scanFileFullPath"] = archive_file_dat_filename
        self.spectrum_info["jpegScanFileFullPath"] = archive_file_png_filename
        self.spectrum_info["exposureTime"] = ct
        self.spectrum_info["annotatedPymcaXfeSpectrum"] = archive_file_html_filename
        self.spectrum_info["htmldir"] = archive_directory
        self.spectrum_command_started()
        logging.getLogger("HWR").debug(
            "XRFSpectrum: spectrum dat file is %s", spectrum_file_dat_filename
        )
        logging.getLogger("HWR").debug(
            "XRFSpectrum: archive file is %s", archive_file_dat_filename
        )

        self.execute_spectrum_command(
            ct, spectrum_file_dat_filename, adjust_transmission
        )

    def can_spectrum(self):
        return

    def execute_spectrum_command(self, count_time, filename, adjust_transmission=True):
        """
        Descript. :
        """
        pass

    def cancel_spectrum(self, *args):
        """
        Descript. :
        """
        pass

    def spectrum_command_ready(self):
        """
        Descript. :
        """
        if not self.spectrum_running:
            self.emit("xrfSpectrumReady", (True,))

    def spectrum_command_not_ready(self):
        """
        Descript. :
        """
        if not self.spectrum_running:
            self.emit("xrfSpectrumReady", (False,))

    def spectrum_command_started(self, *args):
        """
        Descript. :
        """
        self.spectrum_info["startTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.spectrum_running = True
        self.emit("xrfSpectrumStarted", ())

    def spectrum_command_failed(self, *args):
        """
        Descript. :
        """
        self.spectrum_info["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.spectrum_running = False
        self.store_xrf_spectrum()
        self.emit("xrfSpectrumFailed", ())
        self.ready_event.set()

    def spectrum_command_aborted(self, *args):
        """
        Descript. :
        """
        self.spectrum_running = False
        self.emit("xrfSpectrumFailed", ())
        self.ready_event.set()

    def spectrum_command_finished(self):
        """
        Descript. :
        """
        with cleanup(self.ready_event.set):
            self.spectrum_info["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.spectrum_running = False

            xmin = 0
            xmax = 20
            mca_data = []
            calibrated_data = []

            spectrum_file_raw = None
            archive_file_raw = None

            if self.write_in_raw_data:
                try:
                    spectrum_file_raw = open(self.spectrum_info["scanFilePath"], "w")
                except Exception:
                    logging.getLogger("HWR").exception(
                        "XRFSpectrum: could not create spectrum result raw file %s"
                        % self.spectrum_info["scanFilePath"]
                    )

            try:
                archive_file_raw = open(self.spectrum_info["scanFileFullPath"], "w")
            except Exception:
                logging.getLogger("HWR").exception(
                    "XRFSpectrum: could not create spectrum result raw file %s"
                    % self.spectrum_info["scanFileFullPath"]
                )

            for n, value in enumerate(self.spectrum_data):
                energy = (
                    self.mca_calib[2]
                    + self.mca_calib[1] * n
                    + self.mca_calib[0] * n * n
                ) / 1000
                if energy < 20:
                    # if energy > xmax:
                    #    xmax = value
                    # if energy < xmin:
                    #    xmin = value
                    calibrated_data.append([energy, value])
                    mca_data.append((n / 1000.0, value))
                    if spectrum_file_raw:
                        spectrum_file_raw.write("%f,%f\r\n" % (energy, value))
                    if archive_file_raw:
                        archive_file_raw.write("%f,%f\r\n" % (energy, value))
            if spectrum_file_raw:
                spectrum_file_raw.close()
            if archive_file_raw:
                archive_file_raw.close()
            calibrated_array = numpy.array(calibrated_data)

            if HWR.beamline.transmission is not None:
                self.spectrum_info[
                    "beamTransmission"
                ] = HWR.beamline.transmission.get_value()
            self.spectrum_info["energy"] = self.get_current_energy()
            if HWR.beamline.beam is not None:
                beam_size_hor, beam_size_ver = HWR.beamline.beam.get_beam_size()
                self.spectrum_info["beamSizeHorizontal"] = int(beam_size_hor * 1000)
                self.spectrum_info["beamSizeVertical"] = int(beam_size_ver * 1000)

            mca_config = {}
            mca_config["legend"] = self.spectrum_info["filename"]
            mca_config["file"] = self.config_filename
            mca_config["min"] = xmin
            mca_config["max"] = xmax
            mca_config["htmldir"] = self.spectrum_info["htmldir"]
            self.spectrum_info.pop("htmldir")
            self.spectrum_info.pop("scanFilePath")

            self.emit("xrfSpectrumFinished", (mca_data, self.mca_calib, mca_config))

            fig = Figure(figsize=(15, 11))
            ax = fig.add_subplot(111)
            ax.set_title(self.spectrum_info["jpegScanFileFullPath"])
            ax.grid(True)

            ax.plot(*(zip(*calibrated_array)), **{"color": "black"})
            ax.set_xlabel("Energy")
            ax.set_ylabel("Counts")
            canvas = FigureCanvasAgg(fig)
            logging.getLogger().info(
                "XRFSpectrum: Rendering spectrum to PNG file : %s",
                self.spectrum_info["jpegScanFileFullPath"],
            )
            canvas.print_figure(self.spectrum_info["jpegScanFileFullPath"], dpi=80)
            # logging.getLogger().debug("Copying .fit file to: %s", a_dir)
            # tmpname=filename.split(".")
            # logging.getLogger().debug("finished %r", self.spectrum_info)
            self.store_xrf_spectrum()
            # self.emit("xrfSpectrumFinished", (mca_data, self.mca_calib, mca_config))

    def spectrum_status_changed(self, status):
        """
        Descript. :
        """
        self.emit("xrfSpectrumtatusChanged", (status,))

    def store_xrf_spectrum(self):
        """
        Descript. :
        """
        logging.getLogger().debug("XRFSpectrum info %r", self.spectrum_info)
        if HWR.beamline.lims:
            try:
                session_id = int(self.spectrum_info["sessionId"])
            except Exception:
                return
            blsampleid = self.spectrum_info["blSampleId"]
            HWR.beamline.lims.storeXfeSpectrum(self.spectrum_info)

    def get_current_energy(self):
        """
        Descript. :
        """
        if HWR.beamline.energy is not None:
            try:
                return HWR.beamline.energy.get_value()
            except Exception:
                logging.getLogger("HWR").exception("XRFSpectrum: couldn't read energy")
