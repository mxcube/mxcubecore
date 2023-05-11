import json
import logging
import math

from typing_extensions import Literal

from pydantic import Field
from devtools import debug

from mxcubecore.model.common import (
    CommonCollectionParamters,
    PathParameters,
    LegacyParameters,
    StandardCollectionParameters,
)

from mxcubecore import HardwareRepository as HWR

from mxcubecore.HardwareObjects.ESRF.queue_entry.ssx_base_queue_entry import (
    SsxBaseQueueEntry,
    SsxBaseQueueTaskParameters,
    BaseUserCollectionParameters,
)

from mxcubecore.model.queue_model_objects import DataCollection


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class SSXUserCollectionParameters(BaseUserCollectionParameters):
    horizontal_spacing: float = Field(8, gt=0, lt=1000, description="um")
    vertical_spacing: float = Field(8, gt=0, lt=1000, description="um")

    try:
        _chip_name_tuple = tuple(
            HWR.beamline.diffractometer.get_head_configuration().available.keys()
        )
        _current_chip = HWR.beamline.diffractometer.get_head_configuration().current
    except AttributeError:
        _chip_name_tuple = tuple("")
        _current_chip = ""

    chip_type: Literal[_chip_name_tuple] = Field(_current_chip)

    class Config:
        extra: "ignore"


class SsxFoilColletionTaskParameters(SsxBaseQueueTaskParameters):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: SSXUserCollectionParameters
    legacy_parameters: LegacyParameters

    @staticmethod
    def ui_schema():
        schema = json.loads(SsxBaseQueueTaskParameters.ui_schema())
        schema.update(
            {
                "sub_sampling": {"ui:readonly": "true"},
            }
        )
        return json.dumps(schema)

    @staticmethod
    def update_dependent_fields(field_data):
        horizontal_spacing = field_data["horizontal_spacing"]
        vertical_spacing = field_data["vertical_spacing"]
        sub_sampling = field_data["sub_sampling"]
        chip_type = field_data["chip_type"]

        chip_name = chip_type
        chip_data = HWR.beamline.diffractometer.get_head_configuration().available[
            chip_name
        ]

        chip_width = (
            chip_data.calibration_data.top_right[0]
            - chip_data.calibration_data.top_left[0]
        )
        chip_height = (
            chip_data.calibration_data.bottom_left[1]
            - chip_data.calibration_data.top_left[1]
        )

        nb_samples_per_line = math.floor(
            chip_width / ((horizontal_spacing / 1000) * sub_sampling)
        )
        nb_lines = math.floor(chip_height / (vertical_spacing / 1000))

        num_images = math.floor((nb_samples_per_line * nb_lines) / 2) * 2

        new_data = {"num_images": num_images}
        return new_data


class SsxFoilCollectionQueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SsxFoilCollectionQueueEntry(SsxBaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    QMO = SsxFoilCollectionQueueModel
    DATA_MODEL = SsxFoilColletionTaskParameters
    NAME = "SSX Foil Collection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    # New style queue entry does not take view argument,
    # adding kwargs for compatability, but they are unsued
    def __init__(self, view, data_model: SsxFoilCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)

    def execute(self):
        super().execute()
        debug(self._data_model._task_data)
        params = self._data_model._task_data.user_collection_parameters

        MAX_FREQ = 925.0
        packet_fifo_depth = 20000

        chip_name = params.chip_type
        chip_data = HWR.beamline.diffractometer.get_head_configuration().available[
            chip_name
        ]

        chip_width = (
            chip_data.calibration_data.top_right[0]
            - chip_data.calibration_data.top_left[0]
        )
        chip_height = (
            chip_data.calibration_data.bottom_left[1]
            - chip_data.calibration_data.top_left[1]
        )

        nb_samples_per_line = math.floor(
            chip_width / ((params.horizontal_spacing / 1000) * params.sub_sampling)
        )
        nb_lines = math.floor(chip_height / (params.vertical_spacing / 1000))

        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        num_images = math.floor((nb_samples_per_line * nb_lines) / 2) * 2

        self._data_model._task_data.collection_parameters.num_images = num_images
        fname_prefix = self._data_model._task_data.path_parameters.prefix
        data_root_path, _ = self.get_data_path()

        self.take_pedestal(MAX_FREQ)

        logging.getLogger("user_level_log").info("Preparing detector")
        HWR.beamline.detector.prepare_acquisition(
            num_images, exp_time, data_root_path, fname_prefix
        )

        HWR.beamline.detector.wait_ready()

        fname_prefix = self._data_model._task_data.path_parameters.prefix
        fname_prefix += f"_foil_"

        region = (
            chip_data.calibration_data.top_left[0],
            chip_data.calibration_data.top_left[1],
            chip_data.calibration_data.top_left[2],
            chip_data.calibration_data.top_right[0],
            chip_data.calibration_data.top_right[1],
            chip_data.calibration_data.top_right[2],
            chip_data.calibration_data.bottom_left[0],
            chip_data.calibration_data.bottom_left[1],
            chip_data.calibration_data.bottom_left[2],
        )

        self.start_processing("FOIL")

        logging.getLogger("user_level_log").info(f"Defining region {region}")

        HWR.beamline.diffractometer.define_ssx_scan_region(
            *region, nb_samples_per_line, nb_lines
        )

        HWR.beamline.diffractometer.wait_ready()
        HWR.beamline.diffractometer.set_phase("DataCollection", wait=True, timeout=120)

        if HWR.beamline.control.safshut_oh2.state.name != "OPEN":
            logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
            HWR.beamline.control.safshut_oh2.open()

        HWR.beamline.detector.start_acquisition()
        logging.getLogger("user_level_log").info(
            "Detector ready, waiting for trigger ..."
        )

        logging.getLogger("user_level_log").info(f"Acquiring region {region}")
        logging.getLogger("user_level_log").info(
            f"Sub sampling is {params.sub_sampling}"
        )
        logging.getLogger("user_level_log").info(
            f"Acquiring {num_images} images ({nb_lines} lines x {nb_samples_per_line} samples per line)"
        )
        logging.getLogger("user_level_log").info(
            f"Data path: {data_root_path}{fname_prefix}*.h5"
        )

        try:
            HWR.beamline.diffractometer.start_ssx_scan(params.sub_sampling)
            HWR.beamline.diffractometer.wait_ready()
        except:
            msg = "Diffractometer failed! Waiting for detector to finish"
            logging.getLogger("user_level_log").error(msg)
            HWR.beamline.detector.wait_ready()
            raise

        if HWR.beamline.control.safshut_oh2.state.name == "OPEN":
            HWR.beamline.control.safshut_oh2.close()
            logging.getLogger("user_level_log").info("shutter closed")

        HWR.beamline.detector.wait_ready()
        logging.getLogger("user_level_log").info(f"Acquired {region}")

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        super().stop()
