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
import logging

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
    QUEUE_ENTRY_STATUS,
    QueueExecutionException,
    QueueAbortedException,
)

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class XRFSpectrumQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self._failed = False

    def __getstate__(self):
        d = dict(self.__dict__)
        d["xrf_spectrum_task"] = None
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)

    def execute(self):
        BaseQueueEntry.execute(self)

        if HWR.beamline.xrf_spectrum is not None:
            xrf_spectrum = self.get_data_model()
            self.get_view().setText(1, "Starting xrf spectrum")

            sample_model = self.get_data_model().get_sample_node()
            node_id = xrf_spectrum._node_id

            sample_lims_id = sample_model.lims_id
            # No sample id, pass None to startEnergySpectrum
            if sample_lims_id == -1:
                sample_lims_id = None

            HWR.beamline.xrf_spectrum.startXrfSpectrum(
                xrf_spectrum.count_time,
                xrf_spectrum.path_template.directory,
                xrf_spectrum.path_template.get_archive_directory(),
                "%s_%d"
                % (
                    xrf_spectrum.path_template.get_prefix(),
                    xrf_spectrum.path_template.run_number,
                ),
                HWR.beamline.session.session_id,
                node_id,
            )
            HWR.beamline.xrf_spectrum.ready_event.wait()
            HWR.beamline.xrf_spectrum.ready_event.clear()
        else:
            logging.getLogger("user_level_log").info(
                "XRFSpectrum not defined in beamline setup"
            )
            self.xrf_spectrum_failed()

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        self._failed = False
        qc = self.get_queue_controller()
        qc.connect(
            HWR.beamline.xrf_spectrum,
            "xrfSpectrumStatusChanged",
            self.xrf_spectrum_status_changed,
        )

        qc.connect(
            HWR.beamline.xrf_spectrum, "xrfSpectrumStarted", self.xrf_spectrum_started
        )
        qc.connect(
            HWR.beamline.xrf_spectrum, "xrfSpectrumFinished", self.xrf_spectrum_finished
        )
        qc.connect(
            HWR.beamline.xrf_spectrum, "xrfSpectrumFailed", self.xrf_spectrum_failed
        )

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        qc = self.get_queue_controller()
        qc.disconnect(
            HWR.beamline.xrf_spectrum,
            "xrfSpectrumStatusChanged",
            self.xrf_spectrum_status_changed,
        )

        qc.disconnect(
            HWR.beamline.xrf_spectrum, "xrfSpectrumStarted", self.xrf_spectrum_started
        )

        qc.disconnect(
            HWR.beamline.xrf_spectrum, "xrfSpectrumFinished", self.xrf_spectrum_finished
        )

        qc.disconnect(
            HWR.beamline.xrf_spectrum, "xrfSpectrumFailed", self.xrf_spectrum_failed
        )
        if self._failed:
            raise QueueAbortedException("Queue stopped", self)
        self.get_view().set_checkable(False)

    def xrf_spectrum_status_changed(self, msg):
        logging.getLogger("user_level_log").info(msg)

    def xrf_spectrum_started(self):
        logging.getLogger("user_level_log").info("XRF spectrum started.")
        self.get_view().setText(1, "In progress")

    def xrf_spectrum_finished(self, mcaData, mcaCalib, mcaConfig):
        xrf_spectrum = self.get_data_model()
        spectrum_file_path = os.path.join(
            xrf_spectrum.path_template.directory,
            xrf_spectrum.path_template.get_prefix(),
        )
        spectrum_file_archive_path = os.path.join(
            xrf_spectrum.path_template.get_archive_directory(),
            xrf_spectrum.path_template.get_prefix(),
        )

        xrf_spectrum.result.mca_data = mcaData
        xrf_spectrum.result.mca_calib = mcaCalib
        xrf_spectrum.result.mca_config = mcaConfig

        logging.getLogger("user_level_log").info("XRF spectrum finished.")
        self.get_view().setText(1, "Done")

    def xrf_spectrum_failed(self):
        self._failed = True
        self.get_view().setText(1, "Failed")
        self.status = QUEUE_ENTRY_STATUS.FAILED
        logging.getLogger("user_level_log").error("XRF spectrum failed.")
        raise QueueExecutionException("XRF spectrum failed", self)

    def get_type_str(self):
        return "XRF spectrum"
