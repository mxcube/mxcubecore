import logging
import math

from devtools import debug
from pydantic.v1 import Field

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


class SsxLineScanCollectionUserParameters(BaseUserCollectionParameters):
    line_range: float = Field(50, gt=0, description="μm")
    num_images: int = Field(0, gt=0, description="#")
    spacing: float = Field(10, gt=0, description="μm")
    # exp_time: float = Field(100e-6, gt=0, lt=1, description='s')

    class Config:
        extra: "ignore"


class SsxLineScanCollectionTaskParameters(SsxBaseQueueTaskParameters):
    user_collection_parameters: SsxLineScanCollectionUserParameters

    @staticmethod
    def update_dependent_fields(field_data):
        # new_data = {"exp_time": field_data["sub_sampling"] * 2}
        return {}


class SsxLineScanCollectionQueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SsxLineScanCollectionQueueEntry(SsxBaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    QMO = SsxLineScanCollectionQueueModel
    DATA_MODEL = SsxLineScanCollectionTaskParameters
    NAME = "SSX Line Scan"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    def __init__(self, view, data_model: SsxLineScanCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)

    def execute(self):
        super().execute()

        enforce_centring_phase = False

        motor_x = HWR.beamline.diffractometer.get_object_by_role("ssx_translation")
        motor_y = HWR.beamline.diffractometer.get_object_by_role("phiy")
        motor_z = HWR.beamline.diffractometer.get_object_by_role("focus")

        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        fname_prefix = self._data_model._task_data.path_parameters.prefix
        num_images = self._data_model._task_data.user_collection_parameters.num_images
        line_range = self._data_model._task_data.user_collection_parameters.line_range
        spacing = self._data_model._task_data.user_collection_parameters.spacing
        sub_sampling = (
            self._data_model._task_data.user_collection_parameters.sub_sampling
        )
        reject_empty_frames = (
            self._data_model._task_data.user_collection_parameters.reject_empty_frames
        )

        self._data_model._task_data.collection_parameters.num_images = num_images
        data_root_path = self.get_data_path()

        num_img_per_rep = line_range // spacing + 1
        num_repetitions = math.ceil(num_images / num_img_per_rep)

        # distance between center and edges (divide by 1000 for μm to mm convertion)
        delta_range = (line_range - (line_range % spacing)) / 2000

        self.take_pedestal()

        HWR.beamline.detector.prepare_acquisition(
            num_images,
            exp_time,
            data_root_path,
            fname_prefix,
            dense_skip_nohits=reject_empty_frames,
        )
        HWR.beamline.detector.wait_ready()

        self.start_processing("LINE-SCAN")

        logging.getLogger("user_level_log").info(f"Preparing scan")

        HWR.beamline.diffractometer.prepare_ssx_line_scan(
            motor_x.get_value() - delta_range,
            motor_y.get_value(),
            motor_z.get_value(),
            motor_x.get_value() + delta_range,
            motor_y.get_value(),
            motor_z.get_value(),
            num_img_per_rep,
            num_repetitions,
        )

        logging.getLogger("user_level_log").info(
            f"Total number of images: {num_images}"
        )
        logging.getLogger("user_level_log").info(f"Images per line: {num_img_per_rep}")
        logging.getLogger("user_level_log").info(
            f"Number of repititions: {num_repetitions}"
        )

        logging.getLogger("user_level_log").info(f"Line range: {delta_range}")
        logging.getLogger("user_level_log").info(
            f"X start: {motor_x.get_value() - delta_range}"
        )
        logging.getLogger("user_level_log").info(
            f"X end: {motor_x.get_value() + delta_range}"
        )

        HWR.beamline.diffractometer.set_phase("DataCollection")
        HWR.beamline.diffractometer.wait_ready()

        if HWR.beamline.control.safshut_oh2.state.name != "OPEN":
            logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
            HWR.beamline.control.safshut_oh2.open()

        logging.getLogger("user_level_log").info(f"Acquiring ...")
        HWR.beamline.detector.start_acquisition()
        HWR.beamline.diffractometer.start_ssx_line_scan(enforce_centring_phase)

        logging.getLogger("user_level_log").info(
            f"Waiting for acqusition to finish ..."
        )

        HWR.beamline.diffractometer.wait_ready()
        HWR.beamline.detector.wait_ready()
        logging.getLogger("user_level_log").info(f"Acquired {num_images} images")

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        super().stop()
