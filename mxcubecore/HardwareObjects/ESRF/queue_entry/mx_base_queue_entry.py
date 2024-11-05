import errno
import json
import logging
import os
import time

import gevent
from devtools import debug
from pydantic.v1 import (
    BaseModel,
    Field,
)
from typing_extensions import (
    Literal,
    Union,
)

from mxcubecore import HardwareRepository as HWR
from mxcubecore.model.common import (
    CommonCollectionParamters,
    ISPYBCollectionParameters,
    LegacyParameters,
    PathParameters,
    StandardCollectionParameters,
)
from mxcubecore.queue_entry.base_queue_entry import BaseQueueEntry

DEFAULT_MAX_FREQ = 925


class MXPathParameters(PathParameters):
    use_experiment_name: bool = Field(
        False, description="Whether to use the experiment name in the data path"
    )


class BaseUserCollectionParameters(BaseModel):
    exp_time: float = Field(95e-6, gt=0, lt=1, description="s")


class MXBaseQueueTaskParameters(BaseModel):
    path_parameters: MXPathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    legacy_parameters: LegacyParameters
    lims_parameters: Union[ISPYBCollectionParameters, None]

    def update_dependent_fields(field_data):
        return {}

    @staticmethod
    def ui_schema():
        return json.dumps(
            {
                "ui:order": [
                    "num_images",
                    "exp_time",
                    "osc_range",
                    "osc_start",
                    "resolution",
                    "transmission",
                    "energy",
                    "*",
                ],
                "ui:submitButtonOptions": {
                    "norender": "true",
                },
            }
        )


class MXBaseQueueEntry(BaseQueueEntry):
    """
    Defines common MX collection methods.
    """

    def __init__(self, view, data_model):
        super().__init__(view=view, data_model=data_model)
        self._beamline_values = None

    def get_data_directory(self):
        return self.get_data_model().get_path_template().directory

    def get_data_path(self):
        return self.get_data_model().get_path_template().get_image_path()

    def _check_file(self, fname, wait_time=60):
        if not os.path.isfile(fname):
            logging.getLogger("HWR").info("File {fname} not yet written")
            logging.getLogger("HWR").info("Checking for file {fname}...")

            for i in range(1, 3):
                time.sleep(60)

                if os.path.isfile(fname):
                    break

                logging.getLogger("HWR").info(
                    "{fname} still not found after {3-i} retries"
                )

            logging.getLogger("HWR").warning("File {fname} not found")

    def monitor_progress(self):
        num_images = self._data_model._task_data.collection_parameters.num_images
        exp_time = self._data_model._task_data.collection_parameters.exp_time
        images_per_file = HWR.beamline.detector.images_per_file
        num_files = num_images // images_per_file
        dp = 100 / num_files
        total_progress = 0

        pt = self.get_data_model().get_path_template()
        h5_master_path = pt.get_image_file_name()

        for i in range(1, num_files):
            time.sleep(images_per_file * exp_time)

            current_file = pt.get_actual_file_path(
                h5_master_path, i * images_per_file - 1
            )

            gevent.spwan(self._check_file, current_file)

            total_progress += dp
            self.emit_progress(total_progress)

    def create_directory(self):
        try:
            os.makedirs(self.get_data_directory())
        except os.error as e:
            if e.errno != errno.EEXIST:
                raise

    def start_processing(self, exp_type):
        data_root_path = self.get_data_path()

    def prepare_acquisition(self):
        pass

    def execute(self):
        super().execute()
        debug(self._data_model._task_data)

    def pre_execute(self):
        super().pre_execute()
        self.create_directory()

        self.emit_progress(0)

    def post_execute(self):
        super().post_execute()
        self.emit_progress(1)

    def emit_progress(self, progress):
        HWR.beamline.collect.emit_progress(progress)

    def stop(self):
        super().stop()
        HWR.beamline.detector.stop_acquisition()
