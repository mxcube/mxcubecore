import os
import subprocess

from pydantic import BaseModel, Field
from devtools import debug
from typing_extensions import Literal

from mxcubecore import HardwareRepository as HWR

from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
)

from mxcubecore.model.common import (
    CommonCollectionParamters,
    PathParameters,
    LegacyParameters,
    StandardCollectionParameters,
)

from mxcubecore.model.queue_model_objects import (
    DataCollection,
)


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class TestUserCollectionParameters(BaseModel):
    sub_sampling: float = Field(2, gt=0, lt=100)
    take_pedestal: bool = Field(True)
    exp_time: float = Field(100e-6, gt=0, lt=1)

    _chip_name_tuple = tuple(
        HWR.beamline.diffractometer.get_head_configuration().available.keys()
    )
    _current_chip = HWR.beamline.diffractometer.get_head_configuration().current
    test: Literal[_chip_name_tuple] = Field(_current_chip)
    class Config:
        extra: "ignore"


class TestCollectionTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: TestUserCollectionParameters
    legacy_parameters: LegacyParameters


class TestCollectionQueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class TestCollectionQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    QMO = TestCollectionQueueModel
    DATA_MODEL = TestCollectionTaskParameters
    NAME = "TestCollection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    # New style queue entry does not take view argument,
    # adding kwargs for compatability, but they are unsued
    def __init__(self, view, data_model: TestCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)

        TestUserCollectionParameters.__fields__[
            "test"
        ].default = data_model.task_data.user_collection_parameters.test

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

        import pdb

        pdb.set_trace()

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
