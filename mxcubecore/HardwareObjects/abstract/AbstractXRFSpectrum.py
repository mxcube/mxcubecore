# encoding: utf-8
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Abstract XRF spectrum class. Compliant with queue_entry/xrf_spectrum.py"""

import abc
import logging
import time
from pathlib import Path

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractXRFSpectrum(HardwareObject):
    """Abstract XRFSpectrum procedure.

    Emits:
        stateChanged: ("stateChanged", (state))
        xrfSpectrumStatusChanged: ("xrfSpectrumStatusChanged", (error_msg)

    Attributes:
        default_integration_time (float): Time [s]
        spectrum_info_dict (dict): keys defined by the lims model.
        lims: reference to the lims hardware object

    States:
        HardwareObjectStates: READY, BUSY, FAULT

    Note:
        _execute_spectrum and spectrum_analyse are hooks to be overloaded
        for specific implementation.
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        super().__init__(name)
        self.lims = None
        self.spectrum_info_dict = {}
        self.default_integration_time = None
        self.cpos = None

    def init(self):
        """Initialisation"""
        self.default_integration_time = self.get_property("default_integration_time", 3)
        self.file_suffix = self.get_property("file_suffix", "dat")
        self.lims = HWR.beamline.lims
        if not self.lims:
            logging.getLogger().warning("XRFSpectrum: no lims set")

    def start_spectrum(
        self,
        integration_time: float | None = None,
        data_dir: str | None = None,
        prefix: str | None = None,
        archive_dir: str | None = None,
        session_id: int | None = None,
        blsample_id: int | None = None,
        cpos: dict | None = None,
    ):
        """Start the procedure. Called by the queue_model.

        Args:
            integration_time: Inregration time [s].
            data_dir: Directory to save the data (full path).
            archive_dir: Directory to save the archive data (full path).
            prefix: File prefix
            session_id: Session ID number (from ISpyB)
            blsample_id: Sample ID number (from ISpyB)
            cpos: The centred position motors and their values.
        """
        self.cpos = cpos
        self.spectrum_info_dict = {"sessionId": session_id, "blSampleId": blsample_id}
        integration_time = integration_time or self.default_integration_time
        self.spectrum_info_dict["exposureTime"] = integration_time
        self.spectrum_info_dict["filename"] = ""

        # Create the data and the archive directory (if needed) and files
        if data_dir:
            if not self.create_directory(data_dir):
                self.update_state(self.STATES.FAULT)
                return False
            filename = self.get_filename(data_dir, prefix)
            self.spectrum_info_dict["filename"] = filename + "." + self.file_suffix
        if archive_dir:
            if not self.create_directory(archive_dir):
                self.update_state(self.STATES.FAULT)
                return False
            filename = self.get_filename(archive_dir, prefix)
            self.spectrum_info_dict["scanFileFullPath"] = (
                filename + "." + self.file_suffix
            )
            self.spectrum_info_dict["jpegScanFileFullPath"] = filename + ".png"
            self.spectrum_info_dict["annotatedPymcaXfeSpectrum"] = filename + ".html"
            self.spectrum_info_dict["fittedDataFileFullPath"] = filename + "_peaks.csv"

        self.spectrum_info_dict["startTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.update_state(self.STATES.BUSY)

        gevent.spawn(
            self.execute_spectrum,
            integration_time,
            self.spectrum_info_dict["filename"],
        )
        return True

    def execute_spectrum(
        self,
        integration_time: float | None = None,
        filename: str | None = None,
    ):
        """Do the acquisition.

        Args:
            integration_time: MCA integration time [s].
            filename: Data file (full path).
        Raises:
            RuntimeError: Cannot acquire data.
        """
        if filename:
            self.spectrum_info_dict["filename"] = filename

        integration_time = integration_time or self.default_integration_time

        try:
            if self._execute_spectrum(integration_time, filename):
                self.spectrum_command_finished()
        except RuntimeError as err:
            msg = f"XRFSpectrum: could not acquire spectrum, {err}"
            logging.getLogger("user_level_log").exception(msg)
            self.spectrum_status_change(msg)
            self.update_state(self.STATES.FAULT)

    @abc.abstractmethod
    def _execute_spectrum(
        self,
        integration_time: float | None = None,
        filename: str | None = None,
    ) -> bool:
        """Specific XRF acquisition procedure"""
        return True

    def create_directory(self, directory: str) -> bool:
        """Create a directory, if needed.
        Args:
            directory: Directory to save the data (full path).
        Returns:
           ``True`` if directory created or already exists, ``False`` if error.
        """
        if not Path(directory).is_dir():
            msg = f"XRFSpectrum: directory creating {directory}"
            try:
                if not Path(directory).exists():
                    logging.getLogger("user_level_log").debug(msg)
                    Path(directory).mkdir(parents=True)
                return True
            except OSError as err:
                msg += f": {err}"
                logging.getLogger().error(msg)
                self.spectrum_status_change("Error creating directory")
                self.spectrum_command_aborted()
                return False
        return True

    def get_filename(self, directory: str, prefix: str) -> str:
        """Create file template.
        Args:
            directory(str): directory name (full path)
        Returns:
            (str): File template
        """
        _pattern = f"{prefix}_{time.strftime('%d_%b_%Y')}_%02d_xrf"
        filename = Path(directory) / (_pattern % 1)

        i = 2
        while Path(filename).is_file():
            filename = Path(directory) / (_pattern % i)
            i += 1

        return str(filename)

    def spectrum_status_change(self, status_msg: str):
        """Emit the signal xrfSpectrumStatusChanged with appropriate message.
        Args:
            status_msg(str): Message to send.
        """
        self.emit("xrfSpectrumStatusChanged", (status_msg,))

    def spectrum_command_finished(self):
        """Actions to do if spectrum acquired."""
        self.spectrum_info_dict["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if HWR.beamline.transmission:
            self.spectrum_info_dict["beamTransmission"] = (
                HWR.beamline.transmission.get_value()
            )
        if HWR.beamline.energy:
            self.spectrum_info_dict["energy"] = HWR.beamline.energy.get_value()
        if HWR.beamline.flux:
            self.spectrum_info_dict["flux"] = HWR.beamline.flux.get_value()
        if HWR.beamline.beam:
            size = HWR.beamline.beam.get_value()
            self.spectrum_info_dict["beamSizeHorizontal"] = size[0]
            self.spectrum_info_dict["beamSizeVertical"] = size[1]
        self.spectrum_analyse()
        if self.lims:
            self.spectrum_store_lims()
        self.update_state(self.STATES.READY)

    def spectrum_analyse(self):
        """Get the spectrum data. Do analysis and save fitted data.
        The method has to be implemented as specific for each site, but
        is only optional.
        """

    def spectrum_command_aborted(self):
        """Spectrum aborted actions"""
        self.update_state(self.STATES.READY)

    def spectrum_command_failed(self):
        """Spectrum failed actions"""
        self.spectrum_info_dict["endTime"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.lims:
            self.spectrum_store_lims()
        self.update_state(self.STATES.FAULT)

    def spectrum_store_lims(self):
        """Store the data in lims, according to the existing data model."""
        if self.spectrum_info_dict.get("sessionId"):
            self.lims.store_xfe_spectrum(self.spectrum_info_dict)
