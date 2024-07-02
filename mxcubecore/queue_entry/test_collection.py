from pydantic import BaseModel, Field
from devtools import debug

from mxcubecore import HardwareRepository as HWR
from mxcubecore.queue_entry.base_queue_entry import BaseQueueEntry

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
    num_images: int = Field(0, description="")
    exp_time: float = Field(100e-6, gt=0, lt=1, description="s")

    class Config:
        extra: "ignore"


class TestCollectionTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: TestUserCollectionParameters
    legacy_parameters: LegacyParameters

    @staticmethod
    def update_dependent_fields(field_data):
        return {}


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

    def __init__(self, view, data_model: TestCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)

    def execute(self):
        super().execute()
        debug(self._data_model._task_data)

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()
