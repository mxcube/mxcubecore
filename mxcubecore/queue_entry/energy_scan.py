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

from mxcubecore import HardwareRepository as HWR
from mxcubecore.dispatcher import dispatcher

from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
    QUEUE_ENTRY_STATUS,
    QueueExecutionException,
    QueueAbortedException,
)

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class EnergyScanQueueEntry(BaseQueueEntry):
    def __init__(self, view=None, data_model=None):
        BaseQueueEntry.__init__(self, view, data_model)
        self.energy_scan_task = None
        self._failed = False

    def __getstate__(self):
        d = dict(self.__dict__)
        d["energy_scan_task"] = None
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)

    def execute(self):
        BaseQueueEntry.execute(self)

        if HWR.beamline.energy_scan:
            energy_scan = self.get_data_model()
            self.get_view().setText(1, "Starting energy scan")

            sample_model = self.get_data_model().get_sample_node()

            sample_lims_id = sample_model.lims_id

            # No sample id, pass None to start_energy_scan
            if sample_lims_id == -1:
                sample_lims_id = None

            self.energy_scan_task = gevent.spawn(
                HWR.beamline.energy_scan.start_energy_scan,
                energy_scan.element_symbol,
                energy_scan.edge,
                energy_scan.path_template.directory,
                energy_scan.path_template.get_prefix(),
                HWR.beamline.session.session_id,
                sample_lims_id,
            )

        HWR.beamline.energy_scan.ready_event.wait()
        HWR.beamline.energy_scan.ready_event.clear()

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        self._failed = False

        qc = self.get_queue_controller()

        qc.connect(
            HWR.beamline.energy_scan,
            "scanStatusChanged",
            self.energy_scan_status_changed,
        )

        qc.connect(
            HWR.beamline.energy_scan, "energyScanStarted", self.energy_scan_started
        )

        qc.connect(
            HWR.beamline.energy_scan, "energyScanFinished", self.energy_scan_finished
        )

        qc.connect(
            HWR.beamline.energy_scan, "energyScanFailed", self.energy_scan_failed
        )

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        qc = self.get_queue_controller()

        qc.disconnect(
            HWR.beamline.energy_scan,
            "scanStatusChanged",
            self.energy_scan_status_changed,
        )

        qc.disconnect(
            HWR.beamline.energy_scan, "energyScanStarted", self.energy_scan_started
        )

        qc.disconnect(
            HWR.beamline.energy_scan, "energyScanFinished", self.energy_scan_finished
        )

        qc.disconnect(
            HWR.beamline.energy_scan, "energyScanFailed", self.energy_scan_failed
        )

        if self._failed:
            raise QueueAbortedException("Queue stopped", self)
        self.get_view().set_checkable(False)

    def energy_scan_status_changed(self, msg):
        logging.getLogger("user_level_log").info(msg)

    def energy_scan_started(self, *args):
        logging.getLogger("user_level_log").info("Energy scan started.")
        self.get_view().setText(1, "In progress")

    def energy_scan_finished(self, scan_info):
        self.get_view().setText(1, "Done")

        energy_scan = self.get_data_model()

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
        ) = HWR.beamline.energy_scan.do_chooch(
            energy_scan.element_symbol,
            energy_scan.edge,
            energy_scan.path_template.directory,
            energy_scan.path_template.get_archive_directory(),
            "%s_%d"
            % (
                energy_scan.path_template.get_prefix(),
                energy_scan.path_template.run_number,
            ),
        )
        # scan_file_archive_path,
        # scan_file_path)

        # Trying to get the sample from the EnergyScan model instead through
        # the view. Keeping the old way fore backward compatability
        if energy_scan.sample:
            sample = energy_scan.sample
        else:
            sample = self.get_view().parent().parent().get_model()

        sample.crystals[0].energy_scan_result.peak = pk
        sample.crystals[0].energy_scan_result.inflection = ip
        sample.crystals[0].energy_scan_result.first_remote = rm
        sample.crystals[0].energy_scan_result.second_remote = None

        energy_scan.result.pk = pk
        energy_scan.result.fppPeak = fppPeak
        energy_scan.result.fpPeak = fpPeak
        energy_scan.result.ip = ip
        energy_scan.result.fppInfl = fppInfl
        energy_scan.result.fpInfl = fpInfl
        energy_scan.result.rm = rm
        energy_scan.result.chooch_graph_x = chooch_graph_x
        energy_scan.result.chooch_graph_y1 = chooch_graph_y1
        energy_scan.result.chooch_graph_y2 = chooch_graph_y2
        energy_scan.result.title = title
        try:
            energy_scan.result.data = HWR.beamline.energy_scan.get_scan_data()
        except Exception:
            pass

        if (
            sample.crystals[0].energy_scan_result.peak
            and sample.crystals[0].energy_scan_result.inflection
        ):
            logging.getLogger("user_level_log").info(
                "Energy scan: Result peak: %.4f, inflection: %.4f"
                % (
                    sample.crystals[0].energy_scan_result.peak,
                    sample.crystals[0].energy_scan_result.inflection,
                )
            )

        self.get_view().setText(1, "Done")
        self._queue_controller.emit("energy_scan_finished", (pk, ip, rm, sample))

    def energy_scan_failed(self):
        self._failed = True
        self.get_view().setText(1, "Failed")
        self.status = QUEUE_ENTRY_STATUS.FAILED
        logging.getLogger("user_level_log").error("Energy scan: failed")
        raise QueueExecutionException("Energy scan failed", self)

    def stop(self):
        BaseQueueEntry.stop(self)

        try:
            # self.get_view().setText(1, 'Stopping ...')
            HWR.beamline.energy_scan.cancelEnergyScan()

            if self.centring_task:
                self.centring_task.kill(block=False)
        except gevent.GreenletExit:
            raise

        self.get_view().setText(1, "Stopped")
        logging.getLogger("queue_exec").info("Calling stop on: " + str(self))
        # this is to work around the remote access problem
        dispatcher.send("collect_finished")
        raise QueueAbortedException("Queue stopped", self)

    def get_type_str(self):
        return "Energy scan"
