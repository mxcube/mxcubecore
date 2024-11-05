import json
import logging
import math

import gevent
from devtools import debug
from pydantic.v1 import Field
from typing_extensions import Literal

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


class SSXUserCollectionParameters(BaseUserCollectionParameters):
    num_images: int = Field(0, description="")
    horizontal_spacing: float = Field(20, gt=0, lt=1000, description="um")
    vertical_spacing: float = Field(20, gt=0, lt=1000, description="um")

    _chip_name_tuple = tuple(
        HWR.beamline.diffractometer.get_head_configuration().available.keys()
    )
    _current_chip = HWR.beamline.diffractometer.get_head_configuration().current
    chip_type: Literal[_chip_name_tuple] = Field(_current_chip)

    class Config:
        extra: "ignore"


class SsxFoilColletionTaskParameters(SsxBaseQueueTaskParameters):
    user_collection_parameters: SSXUserCollectionParameters

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
        horizontal_spacing = field_data.get("horizontal_spacing", 0)
        vertical_spacing = field_data.get("vertical_spacing", 0)
        sub_sampling = field_data["sub_sampling"]
        chip_type = field_data["chip_type"]

        num_images, _, _ = SsxFoilColletionTaskParameters.calculate_number_of_images(
            horizontal_spacing, vertical_spacing, sub_sampling, chip_type
        )

        new_data = {"num_images": num_images}

        return new_data

    @staticmethod
    def calculate_number_of_images(
        horizontal_spacing, vertical_spacing, sub_sampling, chip_type
    ):
        chip_data = HWR.beamline.diffractometer.get_head_configuration().available[
            chip_type
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

        return num_images, nb_lines, nb_samples_per_line


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
        self.__scanning = False
        params = self._data_model._task_data.user_collection_parameters
        (
            num_images,
            nb_lines,
            nb_samples_per_line,
        ) = SsxFoilColletionTaskParameters.calculate_number_of_images(
            params.horizontal_spacing,
            params.vertical_spacing,
            params.sub_sampling,
            params.chip_type,
        )
        self._data_model._task_data.collection_parameters.num_images = num_images
        self._data_model._task_data.user_collection_parameters.num_images = num_images

    def execute(self):
        super().execute()

        debug(self._data_model._task_data)
        params = self._data_model._task_data.user_collection_parameters
        enforce_centring_phase = False
        packet_fifo_depth = 20000

        (
            num_images,
            nb_lines,
            nb_samples_per_line,
        ) = SsxFoilColletionTaskParameters.calculate_number_of_images(
            params.horizontal_spacing,
            params.vertical_spacing,
            params.sub_sampling,
            params.chip_type,
        )

        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        chip_data = HWR.beamline.diffractometer.get_head_configuration().available[
            params.chip_type
        ]

        self._data_model._task_data.lims_parameters.number_of_rows = nb_lines
        self._data_model._task_data.lims_parameters.number_of_columns = (
            nb_samples_per_line
        )

        fname_prefix = self._data_model._task_data.path_parameters.prefix
        data_root_path = self.get_data_path()
        reject_empty_frames = (
            self._data_model._task_data.user_collection_parameters.reject_empty_frames
        )

        HWR.beamline.diffractometer.wait_ready()
        HWR.beamline.diffractometer.set_phase("DataCollection")

        self.take_pedestal()

        logging.getLogger("user_level_log").info("Preparing detector")
        HWR.beamline.detector.prepare_acquisition(
            num_images,
            exp_time,
            data_root_path,
            fname_prefix,
            dense_skip_nohits=reject_empty_frames,
        )

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

        HWR.beamline.diffractometer.prepare_ssx_grid_scan(
            *region, nb_samples_per_line, nb_lines
        )

        if HWR.beamline.control.safshut_oh2.state.name != "OPEN":
            logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
            HWR.beamline.control.safshut_oh2.open()

        HWR.beamline.diffractometer.wait_ready()
        HWR.beamline.detector.wait_ready()

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
            HWR.beamline.diffractometer.start_ssx_scan(enforce_centring_phase)
        except:
            msg = "Diffractometer start failed! Stopping the detector"
            logging.getLogger("user_level_log").error(msg)
            HWR.beamline.detector.stop_acquisition()
            return

        self.__scanning = True

        logging.getLogger("user_level_log").info("Waiting for scan to finish ...")

        try:
            HWR.beamline.diffractometer.wait_ready()
            logging.getLogger("user_level_log").info("Scan finished ...")
            logging.getLogger("user_level_log").info(f"Acquired {region}")
        finally:
            self.__scanning = False

            HWR.beamline.detector.wait_ready()
            acquired = HWR.beamline.detector.get_acquired_frames()
            logging.getLogger("user_level_log").info(f"Acquired {acquired} images")

            HWR.beamline.diffractometer.wait_ready()
            HWR.beamline.diffractometer.set_phase("Transfer", wait=True, timeout=120)
            logging.getLogger("user_level_log").info(f"set to Transfer phase")

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        if self.__scanning:
            logging.getLogger("user_level_log").info("Stopping diffractometer ...")
            HWR.beamline.diffractometer.abort_cmd()
            gevent.sleep(5)
            HWR.beamline.diffractometer.wait_ready()

        super().stop()
