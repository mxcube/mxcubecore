import json
import logging
import math

import gevent
from devtools import debug
from pydantic.v1 import Field

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.ESRF.queue_entry.ssx_base_queue_entry import (
    BaseUserCollectionParameters,
    SsxBaseQueueEntry,
    SsxBaseQueueTaskParameters,
    SSXPathParameters,
)
from mxcubecore.model.common import (
    CommonCollectionParamters,
    LegacyParameters,
    StandardCollectionParameters,
)
from mxcubecore.model.queue_model_objects import DataCollection

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class SSXUserCollectionParameters(BaseUserCollectionParameters):
    num_images: int = Field(0, description="")
    horizontal_spacing: float = Field(20, gt=0, lt=1000, unit="um")
    vertical_spacing: float = Field(20, gt=0, lt=1000, unit="um")

    #    _chip_name_tuple = tuple(
    #        HWR.beamline.diffractometer.get_head_configuration().available.keys()
    #    )
    #    _current_chip = HWR.beamline.diffractometer.get_head_configuration().current
    #    chip_type: Literal[_chip_name_tuple] = Field(_current_chip)

    class Config:
        extra = "ignore"


class SsxCustomFoilCollectionTaskParameters(SsxBaseQueueTaskParameters):
    path_parameters: SSXPathParameters
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
        horizontal_spacing = field_data.get("horizontal_spacing", 0)
        vertical_spacing = field_data.get("vertical_spacing", 0)
        sub_sampling = field_data["sub_sampling"]

        num_images, _, _ = (
            SsxCustomFoilCollectionTaskParameters.calculate_number_of_images(
                horizontal_spacing, vertical_spacing, sub_sampling
            )
        )

        return {"num_images": num_images}

    @staticmethod
    def calculate_number_of_images(horizontal_spacing, vertical_spacing, sub_sampling):
        chip_data = HWR.beamline.diffractometer.get_head_configuration().available[
            "CUSTOM_FOIL"
        ]

        chip_width = (
            chip_data.sections[0].calibration_data.top_right[0]
            - chip_data.sections[0].calibration_data.top_left[0]
        )
        chip_height = (
            chip_data.sections[0].calibration_data.bottom_left[1]
            - chip_data.sections[0].calibration_data.top_left[1]
        )

        nb_samples_per_line = math.floor(
            chip_width / ((horizontal_spacing / 1000) * sub_sampling)
        )
        nb_lines = math.floor(chip_height / (vertical_spacing / 1000))

        num_images = (
            math.floor((nb_samples_per_line * nb_lines) / 2)
            * 2
            * len(chip_data.sections)
        )

        return num_images, nb_lines, nb_samples_per_line


class SsxCustomFoilCollectionQueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SsxCustomFoilCollectionQueueEntry(SsxBaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    QMO = SsxCustomFoilCollectionQueueModel
    DATA_MODEL = SsxCustomFoilCollectionTaskParameters
    NAME = "SSX Foil LLNL Collection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    # New style queue entry does not take view argument,
    # adding kwargs for compatability, but they are unsued
    def __init__(self, view, data_model: SsxCustomFoilCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)
        self.__scanning = False
        params = self._data_model._task_data.user_collection_parameters
        (
            num_images,
            _nb_lines,
            _nb_samples_per_line,
        ) = SsxCustomFoilCollectionTaskParameters.calculate_number_of_images(
            params.horizontal_spacing, params.vertical_spacing, params.sub_sampling
        )
        self._data_model._task_data.collection_parameters.num_images = num_images
        self._data_model._task_data.user_collection_parameters.num_images = num_images

    def execute(self):
        super().execute()

        debug(self._data_model._task_data)

        enforce_centring_phase = False

        params = self._data_model._task_data.user_collection_parameters
        exp_time = params.exp_time
        chip_data = HWR.beamline.diffractometer.get_head_configuration().available[
            "CUSTOM_FOIL"
        ]

        fname_prefix = self._data_model._task_data.path_parameters.prefix
        data_root_path = self.get_data_path()
        reject_empty_frames = (
            self._data_model._task_data.user_collection_parameters.reject_empty_frames
        )

        (
            num_images,
            nb_lines,
            nb_samples_per_line,
        ) = SsxCustomFoilCollectionTaskParameters.calculate_number_of_images(
            params.horizontal_spacing, params.vertical_spacing, params.sub_sampling
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
        fname_prefix += "_foil_"

        if HWR.beamline.control.safshut_oh2.state.name != "OPEN":
            logging.getLogger("user_level_log").info("Opening OH2 safety shutter")
            HWR.beamline.control.safshut_oh2.open()

        HWR.beamline.detector.wait_ready()
        HWR.beamline.detector.start_acquisition()
        logging.getLogger("user_level_log").info(
            "Detector ready, waiting for trigger ..."
        )

        for section in chip_data.sections:
            logging.getLogger("user_level_log").info(
                f"Collecting region {chip_data.sections.index(section) + 1} of {len(chip_data.sections)}"
            )
            region = (
                section.calibration_data.top_left[0],
                section.calibration_data.top_left[1],
                section.calibration_data.top_left[2],
                section.calibration_data.top_right[0],
                section.calibration_data.top_right[1],
                section.calibration_data.top_right[2],
                section.calibration_data.bottom_left[0],
                section.calibration_data.bottom_left[1],
                section.calibration_data.bottom_left[2],
            )

            self.start_processing("FOIL")

            logging.getLogger("user_level_log").info(f"Defining region {region}")

            HWR.beamline.diffractometer.prepare_ssx_grid_scan(
                *region, nb_samples_per_line, nb_lines
            )

            HWR.beamline.diffractometer.wait_ready()

            logging.getLogger("user_level_log").info(f"Acquiring region {region}")
            logging.getLogger("user_level_log").info(
                f"Sub sampling is {params.sub_sampling}"
            )
            logging.getLogger("user_level_log").info(
                f"Acquiring {num_images / len(chip_data.sections)} images ({nb_lines} lines x {nb_samples_per_line} samples per line)"
            )
            logging.getLogger("user_level_log").info(
                f"Data path: {data_root_path}{fname_prefix}*.h5"
            )

            try:
                HWR.beamline.diffractometer.start_ssx_scan(enforce_centring_phase)
            except:
                msg = "Diffractometer start failed! Stopping the detector"
                logging.getLogger("user_level_log").exception(msg)
                HWR.beamline.detector.stop_acquisition()
                return

            logging.getLogger("user_level_log").info("Waiting for scan to finish ...")
            HWR.beamline.diffractometer.wait_ready()
            logging.getLogger("user_level_log").info("Scan finished ...")
            logging.getLogger("user_level_log").info(f"Acquired {region}")

        try:
            HWR.beamline.diffractometer.wait_ready()
        finally:
            HWR.beamline.detector.wait_ready()
            acquired = HWR.beamline.detector.get_acquired_frames()
            logging.getLogger("user_level_log").info(
                f"Acquired {len(chip_data.sections)} regions"
            )
            logging.getLogger("user_level_log").info(
                f"Acquired total: {acquired} images"
            )

            HWR.beamline.diffractometer.wait_ready()
            HWR.beamline.diffractometer.set_phase("Transfer", wait=True, timeout=120)
            logging.getLogger("user_level_log").info("set to Transfer phase")

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        logging.getLogger("user_level_log").info("Stopping diffractometer ...")
        HWR.beamline.diffractometer.abort_cmd()
        gevent.sleep(5)
        HWR.beamline.diffractometer.wait_ready()

        super().stop()
