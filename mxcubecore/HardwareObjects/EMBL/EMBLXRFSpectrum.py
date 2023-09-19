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

import logging
import gevent

from mxcubecore.HardwareObjects.abstract.AbstractXRFSpectrum import (
    AbstractXRFSpectrum,
)
from mxcubecore.BaseHardwareObjects import HardwareObject

from mxcubecore import HardwareRepository as HWR


__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "Task"


class EMBLXRFSpectrum(AbstractXRFSpectrum):
    def __init__(self, name):
        AbstractXRFSpectrum.__init__(self, name)

        self.ready_event = None
        self.spectrum_running = None
        self.spectrum_info = None
        self.config_filename = None
        self.spectrum_data = None
        self.mca_calib = None

        self.chan_spectrum_status = None
        self.chan_spectrum_consts = None
        self.chan_scan_error = None
        self.cmd_spectrum_start = None
        self.cmd_adjust_transmission = None

    def init(self):
        self.ready_event = gevent.event.Event()

        self.cmd_spectrum_start = self.get_command_object("cmdSpectrumStart")
        self.cmd_adjust_transmission = self.get_command_object("cmdAdjustTransmission")

        self.chan_spectrum_status = self.get_channel_object("chanSpectrumStatus")
        self.chan_spectrum_status.connect_signal("update", self.spectrum_status_update)
        self.chan_spectrum_consts = self.get_channel_object("chanSpectrumConsts")

        self.chan_scan_error = self.get_channel_object("chanSpectrumError")
        self.chan_scan_error.connect_signal("update", self.scan_error_update)

        self.config_filename = self.get_property("configFile")
        self.write_in_raw_data = False
        self.mca_calib = [
            x / 1000.0 for x in self.chan_spectrum_consts.get_value()
        ]  # converted from eV to keV

    def can_spectrum(self):
        """
        Returns True if one can run spectrum command
        :return:
        """
        return True

    def execute_spectrum_command(self, count_sec, filename, adjust_transmission=True):
        """Sends start command"""
        try:
            self.cmd_spectrum_start((count_sec, adjust_transmission))
        except Exception:
            logging.getLogger().exception("XRFSpectrum: problem in starting spectrum")
            self.emit(
                "xrfSpectrumStatusChanged", ("Error problem in starting spectrum",)
            )
            self.spectrum_command_aborted()

    def spectrum_status_update(self, status):
        """Controls execution"""
        if self.spectrum_running:
            if status == "scaning":
                logging.getLogger("HWR").info("XRF spectrum in progress...")
            elif status == "ready":
                if self.spectrum_running:
                    self.spectrum_data = list(self.cmd_spectrum_start.get())
                    # self.mca_calib = self.chan_spectrum_consts.get_value()[::-1]
                    self.spectrum_command_finished()
                    logging.getLogger("HWR").info("XRF spectrum finished")
            elif status == "aborting":
                if self.spectrum_running:
                    self.spectrum_command_aborted()
                    logging.getLogger("HWR").info("XRF spectrum aborted!")
            elif status == "error":
                self.spectrum_command_failed()
                logging.getLogger("HWR").error("XRF spectrum failed!")

    def cancel_spectrum(self, *args):
        """Cancels acquisition"""
        if self.spectrum_running:
            self.ready_event.set()

    def adjust_transmission(self):
        """Adjusts transmission before executing XRF spectrum"""
        if self.cmd_adjust_transmission is not None:
            self.cmd_adjust_transmission()

    def scan_error_update(self, error_msg):
        """Prints error message

        :param error_msg: error message
        :type error_msg: str
        :return: None
        """
        if len(error_msg) > 0:
            # and self.spectrum_running:
            logging.getLogger("GUI").error("XRF spectrum: %s" % error_msg)
