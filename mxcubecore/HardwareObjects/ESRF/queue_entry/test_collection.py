import os
import subprocess

from devtools import debug
from pydantic.v1 import (
    BaseModel,
    Field,
)
from typing_extensions import Literal

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.ESRF.queue_entry.ssx_base_queue_entry import (
    BaseUserCollectionParameters,
    SsxBaseQueueEntry,
    SsxBaseQueueTaskParameters,
)
from mxcubecore.model.common import (
    CommonCollectionParamters,
    LegacyParameters,
    PathParameters,
    StandardCollectionParameters,
)
from mxcubecore.model.queue_model_objects import DataCollection

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class TestUserCollectionParameters(BaseUserCollectionParameters):
    class Config:
        extra: "ignore"


class TestCollectionTaskParameters(SsxBaseQueueTaskParameters):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: TestUserCollectionParameters
    legacy_parameters: LegacyParameters

    @staticmethod
    def update_dependent_fields(field_data):
        new_data = {"exp_time": field_data["sub_sampling"] * 2}
        return new_data


class TestCollectionQueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class TestCollectionQueueEntry(SsxBaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    QMO = TestCollectionQueueModel
    DATA_MODEL = TestCollectionTaskParameters
    NAME = "TestCollection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    def __init__(self, view, data_model: TestCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)

    def execute(self):
        super().execute()
        debug(self._data_model._task_data)

        data_root_path = HWR.beamline.session.get_image_directory(
            os.path.join(
                self._data_model._task_data.path_parameters.subdir,
                self._data_model._task_data.path_parameters.experiment_type,
            )
        )

        process_path = os.path.join(
            HWR.beamline.session.get_base_process_directory(),
            self._data_model._task_data.path_parameters.subdir,
        )

        subprocess.Popen(
            "mkdir --parents %s" % (data_root_path),
            shell=True,
            stdin=None,
            stdout=None,
            stderr=None,
            close_fds=True,
        ).wait()

        dcg = HWR.beamline.lims.pyispyb.create_ssx_data_collection_group()
        HWR.beamline.lims.pyispyb.create_ssx_data_collection(dcg)

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        super().stop()
