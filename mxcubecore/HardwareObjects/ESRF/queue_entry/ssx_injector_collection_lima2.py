import logging
import time
import enum

from pydantic import BaseModel, Field
from devtools import debug

from mxcubecore import HardwareRepository as HWR
from mxcubecore.model.common import (
    CommonCollectionParamters,
    PathParameters,
    LegacyParameters,
    StandardCollectionParameters,
)

from mxcubecore.HardwareObjects.ESRF.queue_entry.ssx_base_queue_entry import (
    SsxBaseQueueEntry,
)

from mxcubecore.model.queue_model_objects import (
    DataCollection,
)


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class InjectorUserCollectionParameters(BaseModel):
    exp_time: float = Field(100e-6, gt=0, lt=1)
    num_images: int = Field(1000, gt=0, lt=10000000)
    take_pedestal: bool = Field(True)
    sub_sampling: float = Field(4, gt=0, lt=100)

    class Config:
        extra: "ignore"
        use_enum_values: True


class InjectorColletionTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: InjectorUserCollectionParameters
    legacy_parameters: LegacyParameters


class SsxInjectorCollectionQueueModel(DataCollection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SsxInjectorCollectionLima2QueueEntry(SsxBaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    QMO = SsxInjectorCollectionQueueModel
    DATA_MODEL = InjectorColletionTaskParameters
    NAME = "SSX Injector Collection (Lima2)"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    def __init__(self, view, data_model: SsxInjectorCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)

    def execute(self):
        super().execute()
        MAX_FREQ = 925.0
        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        fname_prefix = self._data_model._task_data.path_parameters.prefix
        num_images = self._data_model._task_data.user_collection_parameters.num_images
        sub_sampling = (
            self._data_model._task_data.user_collection_parameters.sub_sampling
        )
        self._data_model._task_data.collection_parameters.num_images = num_images
        data_root_path, _ = self.get_data_path()

        self.take_pedestal_lima2(MAX_FREQ)

        HWR.beamline.detector.prepare_acquisition(
            num_images, exp_time, data_root_path, fname_prefix
        )
        HWR.beamline.detector.wait_ready()

        self.start_processing("INJECTOR")

        HWR.beamline.diffractometer.set_phase("DataCollection")
        HWR.beamline.diffractometer.wait_ready()

        if HWR.beamline.control.safshut_oh2.state.name != "OPEN":
            logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
            HWR.beamline.control.safshut_oh2.open()

        logging.getLogger("user_level_log").info(f"Acquiring ...")
        HWR.beamline.detector.start_acquisition()
        HWR.beamline.diffractometer.start_still_ssx_scan(num_images, sub_sampling)

        logging.getLogger("user_level_log").info(
            f"Waiting for acqusition to finish ..."
        )
        time.sleep(num_images * exp_time)

        HWR.beamline.diffractometer.wait_ready()
        HWR.beamline.detector.wait_ready()
        logging.getLogger("user_level_log").info(f"Acquired {num_images} images")

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        super().stop()
