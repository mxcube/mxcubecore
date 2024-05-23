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
from mxcubecore.model import queue_model_objects
from mxcubecore.model.queue_model_enumerables import (
    EXPERIMENT_TYPE,
    COLLECTION_ORIGIN_STR,
)
from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
    QUEUE_ENTRY_STATUS,
    QueueExecutionException,
    QueueAbortedException,
    center_before_collect,
)

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class DataCollectionQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    def __init__(self, view=None, data_model=None, view_set_queue_entry=True):
        BaseQueueEntry.__init__(self, view, data_model, view_set_queue_entry)

        self.collect_task = None
        self.centring_task = None
        self.enable_take_snapshots = True
        self.enable_store_in_lims = True
        self.in_queue = False

    def __setstate__(self, d):
        self.__dict__.update(d)

    def __getstate__(self):
        d = dict(self.__dict__)
        d["collect_task"] = None
        d["centring_task"] = None
        d["shape_history"] = (
            HWR.beamline.config.sample_view.name() if HWR.beamline.config.sample_view else None
        )
        d["session"] = HWR.beamline.config.session.name if HWR.beamline.config.session else None
        d["lims_client_hwobj"] = HWR.beamline.config.lims.name if HWR.beamline.config.lims else None
        return d

    def execute(self):
        BaseQueueEntry.execute(self)
        data_collection = self.get_data_model()

        if data_collection:
            acq_params = data_collection.acquisitions[0].acquisition_parameters
            cpos = acq_params.centred_position

            empty_cpos = all(mpos is None for mpos in cpos.as_dict().values())

            if empty_cpos and data_collection.center_before_collect:
                _p, _s = center_before_collect(
                    self.get_view(),
                    HWR.beamline.config.diffractometer,
                    self.get_queue_controller(),
                    HWR.beamline.config.sample_view,
                )

                acq_params.centred_position = _p

            self.collect_dc(data_collection, self.get_view())

        if HWR.beamline.config.sample_view:
            HWR.beamline.config.sample_view.de_select_all()

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)

        qc = self.get_queue_controller()

        qc.connect(HWR.beamline.config.collect, "collectStarted", self.collect_started)
        qc.connect(
            HWR.beamline.config.collect, "collectNumberOfFrames", self.preparing_collect
        )
        qc.connect(
            HWR.beamline.config.collect, "collectOscillationStarted", self.collect_osc_started
        )
        qc.connect(
            HWR.beamline.config.collect, "collectOscillationFailed", self.collect_failed
        )
        qc.connect(
            HWR.beamline.config.collect, "collectOscillationFinished", self.collect_finished
        )
        qc.connect(HWR.beamline.config.collect, "collectImageTaken", self.image_taken)
        qc.connect(
            HWR.beamline.config.collect, "collectNumberOfFrames", self.collect_number_of_frames
        )

        if HWR.beamline.config.online_processing is not None:
            qc.connect(
                HWR.beamline.config.online_processing,
                "processingFinished",
                self.online_processing_finished,
            )
            qc.connect(
                HWR.beamline.config.online_processing,
                "processingFailed",
                self.online_processing_failed,
            )

        data_model = self.get_data_model()

        if data_model.get_parent():
            gid = data_model.get_parent().lims_group_id
            data_model.lims_group_id = gid

    def post_execute(self):
        BaseQueueEntry.post_execute(self)
        qc = self.get_queue_controller()

        qc.disconnect(HWR.beamline.config.collect, "collectStarted", self.collect_started)
        qc.disconnect(
            HWR.beamline.config.collect, "collectNumberOfFrames", self.preparing_collect
        )
        qc.disconnect(
            HWR.beamline.config.collect, "collectOscillationStarted", self.collect_osc_started
        )
        qc.disconnect(
            HWR.beamline.config.collect, "collectOscillationFailed", self.collect_failed
        )
        qc.disconnect(
            HWR.beamline.config.collect, "collectOscillationFinished", self.collect_finished
        )
        qc.disconnect(HWR.beamline.config.collect, "collectImageTaken", self.image_taken)
        qc.disconnect(
            HWR.beamline.config.collect, "collectNumberOfFrames", self.collect_number_of_frames
        )

        if HWR.beamline.config.online_processing is not None:
            qc.disconnect(
                HWR.beamline.config.online_processing,
                "processingFinished",
                self.online_processing_finished,
            )
            qc.disconnect(
                HWR.beamline.config.online_processing,
                "processingFailed",
                self.online_processing_failed,
            )

        self.get_view().set_checkable(False)

    def collect_dc(self, dc, list_item):
        log = logging.getLogger("user_level_log")

        if HWR.beamline.config.collect:
            acq_1 = dc.acquisitions[0]
            acq_1.acquisition_parameters.in_queue = self.in_queue
            cpos = acq_1.acquisition_parameters.centred_position
            sample = self.get_data_model().get_sample_node()
            HWR.beamline.config.collect.run_offline_processing = dc.run_offline_processing
            HWR.beamline.config.collect.aborted_by_user = None
            self.online_processing_task = None

            try:
                if dc.experiment_type is EXPERIMENT_TYPE.HELICAL:
                    acq_1, acq_2 = (dc.acquisitions[0], dc.acquisitions[1])
                    HWR.beamline.config.collect.set_helical(True)
                    HWR.beamline.config.collect.set_mesh(False)
                    HWR.beamline.config.collect.set_fast_characterisation(False)
                    start_cpos = acq_1.acquisition_parameters.centred_position
                    end_cpos = acq_2.acquisition_parameters.centred_position
                    helical_oscil_pos = {
                        "1": start_cpos.as_dict(),
                        "2": end_cpos.as_dict(),
                    }
                    HWR.beamline.config.collect.set_helical_pos(helical_oscil_pos)
                    # msg = "Helical data collection, moving to start position"
                    # log.info(msg)
                    # list_item.setText(1, "Moving sample")
                elif dc.experiment_type is EXPERIMENT_TYPE.MESH:
                    mesh_nb_lines = acq_1.acquisition_parameters.num_lines
                    mesh_total_nb_frames = acq_1.acquisition_parameters.num_images
                    mesh_range = acq_1.acquisition_parameters.mesh_range
                    mesh_center = acq_1.acquisition_parameters.centred_position
                    HWR.beamline.config.collect.set_mesh_scan_parameters(
                        mesh_nb_lines, mesh_total_nb_frames, mesh_center, mesh_range
                    )
                    HWR.beamline.config.collect.set_helical(False)
                    HWR.beamline.config.collect.set_fast_characterisation(False)
                    HWR.beamline.config.collect.set_mesh(True)
                    # inc_used_for_collection does nothing
                    HWR.beamline.config.sample_view.inc_used_for_collection(
                        self.get_data_model().shape
                    )
                elif dc.experiment_type is EXPERIMENT_TYPE.EDNA_REF:
                    HWR.beamline.config.collect.set_helical(False)
                    HWR.beamline.config.collect.set_mesh(False)
                    HWR.beamline.config.collect.set_fast_characterisation(True)
                else:
                    HWR.beamline.config.collect.set_helical(False)
                    HWR.beamline.config.collect.set_mesh(False)
                    HWR.beamline.config.collect.set_fast_characterisation(False)
                if (
                    dc.run_online_processing
                    and acq_1.acquisition_parameters.num_images > 4
                    and HWR.beamline.config.online_processing is not None
                ):
                    self.online_processing_task = gevent.spawn(
                        HWR.beamline.config.online_processing.run_processing, dc
                    )

                empty_cpos = queue_model_objects.CentredPosition()
                if cpos != empty_cpos:
                    HWR.beamline.config.sample_view.select_shape_with_cpos(cpos)
                else:
                    pos_dict = HWR.beamline.config.diffractometer.get_positions()
                    cpos = queue_model_objects.CentredPosition(pos_dict)
                    snapshot = HWR.beamline.config.sample_view.get_snapshot()
                    acq_1.acquisition_parameters.centred_position = cpos
                    acq_1.acquisition_parameters.centred_position.snapshot_image = (
                        snapshot
                    )

                # inc_used_for_collection does nothing
                HWR.beamline.config.sample_view.inc_used_for_collection(cpos)
                param_list = queue_model_objects.to_collect_dict(
                    dc,
                    HWR.beamline.config.session,
                    sample,
                    cpos if cpos != empty_cpos else None,
                )

                # TODO this is wrong. Rename to something like collect.start_procedure
                self.collect_task = HWR.beamline.config.collect.collect(
                    COLLECTION_ORIGIN_STR.MXCUBE, param_list
                )
                self.collect_task.get()

                if "collection_id" in param_list[0]:
                    dc.id = param_list[0]["collection_id"]

                dc.acquisitions[0].path_template.xds_dir = param_list[0]["xds_dir"]

            except gevent.GreenletExit:
                # log.warning("Collection stopped by user.")
                list_item.setText(1, "Stopped")
                raise QueueAbortedException("queue stopped by user", self)
            except Exception as ex:
                raise QueueExecutionException(str(ex), self)
        else:
            log.error(
                "Could not call the data collection routine,"
                + " check the beamline configuration"
            )
            list_item.setText(1, "Failed")
            msg = (
                "Could not call the data collection"
                + " routine, check the beamline configuration"
            )
            raise QueueExecutionException(msg, self)

    def collect_started(self, owner, num_oscillations):
        logging.getLogger("user_level_log").info("Collection started")
        self.get_view().setText(1, "Collecting...")

    def collect_number_of_frames(self, number_of_images=0, exposure_time=0):
        pass

    def image_taken(self, image_number):
        if image_number > 0:
            num_images = (
                self.get_data_model().acquisitions[0].acquisition_parameters.num_images
            )
            num_images += (
                self.get_data_model().acquisitions[0].acquisition_parameters.first_image
                - 1
            )
            self.get_view().setText(1, str(image_number) + "/" + str(num_images))

    def preparing_collect(self, number_images=0, exposure_time=0):
        self.get_view().setText(1, "Preparing to collecting")

    def collect_failed(self, owner, state, message, *args):
        # this is to work around the remote access problem
        dispatcher.send("collect_finished")
        self.get_view().setText(1, "Failed")
        self.status = QUEUE_ENTRY_STATUS.FAILED
        logging.getLogger("queue_exec").error(message.replace("\n", ";  "))
        # raise QueueExecutionException(message.replace("\n", " "), self)

    def collect_osc_started(
        self, owner, blsampleid, barcode, location, collect_dict, osc_id
    ):
        self.get_view().setText(1, "Preparing")

    def collect_finished(self, owner, state, message, *args):
        # this is to work around the remote access problem
        dispatcher.send("collect_finished")
        self.get_view().setText(1, "Collection done")
        logging.getLogger("user_level_log").info("Collection finished")

        if self.online_processing_task is not None:
            self.get_view().setText(1, "Processing...")
            logging.getLogger("user_level_log").warning("Processing: Please wait...")
            HWR.beamline.config.online_processing.done_event.wait(timeout=120)
            HWR.beamline.config.online_processing.done_event.clear()

    def stop(self):
        BaseQueueEntry.stop(self)
        HWR.beamline.config.collect.stop_collect()
        if self.online_processing_task is not None:
            HWR.beamline.config.online_processing.stop_processing()
            logging.getLogger("user_level_log").error("Processing: Stopped")
        if self.centring_task is not None:
            self.centring_task.kill(block=False)

        self.get_view().setText(1, "Stopped")
        logging.getLogger("queue_exec").info("Calling stop on: " + str(self))
        logging.getLogger("user_level_log").info("Collection stopped")
        # this is to work around the remote access problem
        dispatcher.send("collect_finished")
        raise QueueAbortedException("Queue stopped", self)

    def online_processing_finished(self):
        dispatcher.send("collect_finished")
        self.online_processing_task = None
        # self.get_view().setText(1, "Done")
        logging.getLogger("user_level_log").info("Processing: Done")

    def online_processing_failed(self):
        self.online_processing_task = None
        self.get_view().setText(1, "Processing failed")
        logging.getLogger("user_level_log").error("Processing: Failed")

    def get_type_str(self):
        data_model = self.get_data_model()
        if data_model.is_helical():
            return "Helical"
        elif data_model.is_mesh():
            return "Mesh"
        else:
            return "OSC"

    def add_processing_msg(self, time, method, status, msg):
        data_model = self.get_data_model()
        data_model.add_processing_msg(time, method, status, msg)
        self.get_view().update_tool_tip()
