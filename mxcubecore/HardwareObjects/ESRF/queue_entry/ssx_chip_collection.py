import enum
import logging
import os
import subprocess

import gevent
from devtools import debug
from pydantic.v1 import (
    BaseModel,
    Field,
)

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.ESRF.queue_entry.ssx_base_queue_entry import (
    BaseUserCollectionParameters,
    SsxBaseQueueEntry,
    SsxBaseQueueTaskParameters,
)
from mxcubecore.model.queue_model_objects import DataCollection

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"

ALL_BLOCKS = [
    [0, 0],
    [0, 1],
    [0, 2],
    [0, 3],
    [0, 4],
    [0, 5],
    [0, 6],
    [0, 7],
    [1, 0],
    [1, 1],
    [1, 2],
    [1, 3],
    [1, 4],
    [1, 5],
    [1, 6],
    [1, 7],
    [2, 0],
    [2, 1],
    [2, 2],
    [2, 3],
    [2, 4],
    [2, 5],
    [2, 6],
    [2, 7],
    [3, 0],
    [3, 1],
    [3, 2],
    [3, 3],
    [3, 4],
    [3, 5],
    [3, 6],
    [3, 7],
    [4, 0],
    [4, 1],
    [4, 2],
    [4, 3],
    [4, 4],
    [4, 5],
    [4, 6],
    [4, 7],
    [5, 0],
    [5, 1],
    [5, 2],
    [5, 3],
    [5, 4],
    [5, 5],
    [5, 6],
    [5, 7],
    [6, 0],
    [6, 1],
    [6, 2],
    [6, 3],
    [6, 4],
    [6, 5],
    [6, 6],
    [6, 7],
    [7, 0],
    [7, 1],
    [7, 2],
    [7, 3],
    [7, 4],
    [7, 5],
    [7, 6],
    [7, 7],
]


class SSXUserCollectionParameters(BaseUserCollectionParameters):
    # align_chip: bool = Field(True)

    class Config:
        extra: "ignore"


class SsxChipColletionTaskParameters(SsxBaseQueueTaskParameters):
    user_collection_parameters: SSXUserCollectionParameters


class SsxChipCollectionLima2QueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SsxChipCollectionQueueEntry(SsxBaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    QMO = SsxChipCollectionLima2QueueModel
    DATA_MODEL = SsxChipColletionTaskParameters
    NAME = "SSX Chip Collection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    def __init__(self, view, data_model: SsxChipCollectionLima2QueueModel):
        super().__init__(view=view, data_model=data_model)
        self.__stop_req = False
        self.__stop_done = True

    def execute(self):
        super().execute()

        self.__stop_req = False
        self.__stop_done = False

        params = self._data_model._task_data.user_collection_parameters
        data_root_path = self.get_data_path()
        fname_prefix = self._data_model._task_data.path_parameters.prefix
        enforce_centring_phase = False
        reject_empty_frames = (
            self._data_model._task_data.user_collection_parameters.reject_empty_frames
        )

        self.take_pedestal()
        self.start_processing("CHIP")

        selected_regions = self._data_model._task_data.collection_parameters.selection
        selected_regions = selected_regions if selected_regions else ALL_BLOCKS
        self._data_model._task_data.collection_parameters.selection = selected_regions

        logging.getLogger("user_level_log").info(f"Preparing data collection")
        HWR.beamline.diffractometer.set_phase("DataCollection")

        if HWR.beamline.control.safshut_oh2.state.name != "OPEN":
            logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
            HWR.beamline.control.safshut_oh2.open()

        logging.getLogger("user_level_log").info("Preparing detector")

        self._data_model._task_data.collection_parameters.num_images = 400 * len(
            selected_regions
        )

        HWR.beamline.detector.stop_acquisition()
        gevent.sleep(10)
        HWR.beamline.detector.prepare_acquisition(
            400 * len(selected_regions),
            params.exp_time,
            data_root_path,
            self._data_model._task_data.path_parameters.prefix,
            dense_skip_nohits=reject_empty_frames,
        )

        HWR.beamline.detector.start_acquisition()
        logging.getLogger("user_level_log").info(
            "Detector ready, waiting for trigger ..."
        )

        for region in selected_regions:
            if self.__stop_req:
                self.__stop_done = True
                logging.getLogger("user_level_log").info("Stopped sequence")
                break

            logging.getLogger("user_level_log").info(f"Acquiring {region} ...")

            logging.getLogger("user_level_log").info(f"Aligning block {region}")
            HWR.beamline.diffractometer.prepare_ssx_grid_scan(
                region[0], region[1], False
            )
            logging.getLogger("user_level_log").info(f"Aligned block {region}")

            HWR.beamline.diffractometer.wait_ready()

            try:
                logging.getLogger("user_level_log").info(f"Scanning {region} ...")
                HWR.beamline.diffractometer.start_ssx_scan(False)
            except:
                err_msg = "Diffractometer scan failed ..."
                logging.getLogger("user_level_log").exception(err_msg)
                HWR.beamline.detector.stop_acquisition()
                raise

            HWR.beamline.diffractometer.wait_ready()
            logging.getLogger("user_level_log").info(f"Acquired {region}")

        HWR.beamline.detector.wait_ready()
        HWR.beamline.diffractometer.set_phase("Transfer", wait=True, timeout=120)
        logging.getLogger("user_level_log").info(f"set to transfer phase")

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        self.__stop_req = True
        super().stop()
