import os
import logging
import contextlib
import enum
import subprocess
from pydantic import BaseModel, Field
from devtools import debug

from mxcubecore import HardwareRepository as HWR

from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
)

from mxcubecore.model.queue_model_objects import (
    DataCollection,
)


from mxcubecore.model.common import (
    CommonCollectionParamters,
    PathParameters,
    LegacyParameters,
    StandardCollectionParameters,
)


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class SSXUserCollectionParameters(BaseModel):
    sub_sampling: float = Field(4, gt=0, lt=100)
    exp_time: float = Field(100e-6, gt=0, lt=1)
    take_pedestal: bool = Field(True)
    align_chip: bool = Field(True)

    class Config:
        extra: "ignore"


class SsxChipColletionTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: SSXUserCollectionParameters
    legacy_parameters: LegacyParameters


class SsxChipCollectionQueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SsxChipCollectionQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    QMO = SsxChipCollectionQueueModel
    DATA_MODEL = SsxChipColletionTaskParameters
    NAME = "SSX Chip Collection (Lima1)"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    def __init__(self, view, data_model: SsxChipCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)

    def execute(self):
        super().execute()
        params = self._data_model._task_data.user_collection_parameters
        self._data_model._task_data.collection_parameters.num_images = 400
        data_root_path, _ = self.get_data_path()
        self.take_pedestal()

        selected_regions = self._data_model._task_data.collection_parameters.selection
        selected_regions = selected_regions if selected_regions else [[0, 0]]

        for region in selected_regions:
            fname_prefix = self._data_model._task_data.path_parameters.prefix
            fname_prefix += f"_block_{region[0]}_{region[1]}_"

            HWR.beamline.config.diffractometer.set_phase("Centring", wait=True, timeout=120)
            # HWR.beamline.config.diffractometer.wait_ready()
            logging.getLogger("user_level_log").info(f"Acquiring {region} ...")

            if params.align_chip:
                logging.getLogger("user_level_log").info(f"Aligning block {region}")
                HWR.beamline.config.diffractometer.auto_align_ssx_block(region[0], region[1])
                logging.getLogger("user_level_log").info(f"Aligned block {region}")

            logging.getLogger("user_level_log").info("Preparing detector")

            HWR.beamline.config.detector.stop_acquisition()
            HWR.beamline.config.detector.prepare_acquisition(
                400, params.exp_time, data_root_path, fname_prefix
            )

            HWR.beamline.config.detector.wait_ready()

            HWR.beamline.config.detector.start_acquisition()
            logging.getLogger("user_level_log").info(
                "Detector ready, waiting for trigger ..."
            )
            HWR.beamline.config.diffractometer.wait_ready()

            logging.getLogger("user_level_log").info(f"Preparing data collection")
            HWR.beamline.config.diffractometer.set_phase(
                "DataCollection", wait=True, timeout=120
            )

            if HWR.beamline.config.control.safshut_oh2.state.name != "OPEN":
                logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
                HWR.beamline.config.control.safshut_oh2.open()

            logging.getLogger("user_level_log").info(f"Scanning {region} ...")
            HWR.beamline.config.diffractometer.start_ssx_scan(params.sub_sampling)
            HWR.beamline.config.diffractometer.wait_ready()

            if HWR.beamline.config.control.safshut_oh2.state.name == "OPEN":
                HWR.beamline.config.control.safshut_oh2.close()
                logging.getLogger("user_level_log").info("shutter closed")

            HWR.beamline.config.detector.wait_ready()
            logging.getLogger("user_level_log").info(f"Acquired {region}")

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        super().stop()
