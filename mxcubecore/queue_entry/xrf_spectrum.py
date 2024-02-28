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

"""
XRF Spectrum queue implementation of pre_execute, execute and post_execute
"""

import logging

from mxcubecore.BaseHardwareObjects import HardwareObjectState
from mxcubecore import HardwareRepository as HWR
from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
    QUEUE_ENTRY_STATUS,
    QueueExecutionException,
    QueueAbortedException,
)

__credits__ = ["MXCuBE collaboration"]
__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class XrfSpectrumQueueEntry(BaseQueueEntry):
    """XRF que handler"""

    def __init__(self, view=None, data_model=None):
        super().__init__(view, data_model)
        self._failed = False

    def __getstate__(self):
        d = dict(self.__dict__)
        d["xrf_spectrum_task"] = None
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)

    def execute(self):
        """Execute"""
        super().execute()

        if HWR.beamline.xrf_spectrum is not None:
            xrf_spectrum = self.get_data_model()
            self.get_view().setText(1, "Starting xrf spectrum")

            path_template = xrf_spectrum.path_template
            HWR.beamline.xrf_spectrum.start_xrf_spectrum(
                integration_time=xrf_spectrum.count_time,
                data_dir=xrf_spectrum.path_template.directory,
                archive_dir=xrf_spectrum.path_template.get_archive_directory(),
                prefix=f"{path_template.get_prefix()}_{path_template.run_number}",
                session_id=HWR.beamline.session.session_id,
                blsample_id=xrf_spectrum._node_id,
            )
        else:
            logging.getLogger("user_level_log").info(
                "XRFSpectrum not defined in beamline setup"
            )
            self.xrf_state_handler(HardwareObjectState.FAULT)

    def pre_execute(self):
        """Pre-execution actions"""
        super().pre_execute()
        self._failed = False
        qctrl = self.get_queue_controller()
        qctrl.connect(
            HWR.beamline.xrf_spectrum,
            "xrfSpectrumStatusChanged",
            self.xrf_spectrum_status_changed,
        )

        qctrl.connect(HWR.beamline.xrf_spectrum, "stateChanged", self.xrf_state_handler)

    def post_execute(self):
        """Post-execution actions"""
        qctrl = self.get_queue_controller()
        qctrl.disconnect(
            HWR.beamline.xrf_spectrum,
            "xrfSpectrumStatusChanged",
            self.xrf_spectrum_status_changed,
        )

        qctrl.disconnect(
            HWR.beamline.xrf_spectrum, "stateChanged", self.xrf_state_handler
        )
        if self._failed:
            raise QueueAbortedException("Queue stopped", self)
        self.get_view().set_checkable(False)
        super().post_execute()


    def xrf_spectrum_status_changed(self, msg):
        """xrfSpectrumStatusChanged handler.
        Args:
            msg (str): Message when xrfSpectrumStatusChanged emited.
        """
        logging.getLogger("user_level_log").info(msg)

    def xrf_state_handler(self, state=None):
        """State handler - signal connected is stateChanged.
        Args:
            state (enum): HardwareObjectState enum member.
        Raises:
             QueueExecutionException: If procedure failed.
        """
        state = state or HWR.beamline.xrf_spectrum.get_state()
        if state == HWR.beamline.xrf_spectrum.STATES.BUSY:
            logging.getLogger("user_level_log").info("XRF spectrum started.")
            self.get_view().setText(1, "In progress")
        if state == HWR.beamline.xrf_spectrum.STATES.READY:
            logging.getLogger("user_level_log").info("XRF spectrum finished.")
            self.get_view().setText(1, "Done")
        if state == HWR.beamline.xrf_spectrum.STATES.FAULT:
            self._failed = True
            self.get_view().setText(1, "Failed")
            self.status = QUEUE_ENTRY_STATUS.FAILED
            logging.getLogger("user_level_log").error("XRF spectrum failed.")
            raise QueueExecutionException("XRF spectrum failed", self)

    def get_type_str(self):
        """???"""
        return "XRF spectrum"
