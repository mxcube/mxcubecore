import json

from pydantic.v1 import (
    BaseModel,
    Field,
)

from mxcubecore.model.common import (
    CommonCollectionParamters,
    LegacyParameters,
    PathParameters,
    StandardCollectionParameters,
)
from mxcubecore.model.queue_model_objects import DataCollection
from mxcubecore.queue_entry.base_queue_entry import BaseQueueEntry, TaskPrerequisite

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class TestUserCollectionParameters(BaseModel):
    num_images: int = Field(0, description="")
    exp_time: float = Field(100e-6, gt=0, lt=1, description="s")
    cell_a: float = Field(0.0, title="Cell A")
    cell_b: float = Field(0.0, title="Cell B")
    cell_c: float = Field(0.0, title="Cell C")
    cell_alpha: float = Field(0.0, title="Cell Alpha")
    cell_beta: float = Field(0.0, title="Cell Beta")
    cell_gamma: float = Field(0.0, title="Cell Gamma")

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

    @staticmethod
    def ui_schema():
        processing_group = {"group": "Processing"}
        col_4 = {"col": 4}
        processing_ui_options = {"ui:options": {**processing_group, **col_4}}
        return json.dumps(
            {
                "cell_a": processing_ui_options,
                "cell_b": processing_ui_options,
                "cell_c": processing_ui_options,
                "cell_alpha": processing_ui_options,
                "cell_beta": processing_ui_options,
                "cell_gamma": processing_ui_options,
            }
        )


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
    REQUIRES = [
        TaskPrerequisite.POINT,
        TaskPrerequisite.LINE,
        TaskPrerequisite.CHIP,
        TaskPrerequisite.MESH,
        TaskPrerequisite.NO_SHAPE_2D,
    ]

    def __init__(self, view, data_model: TestCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)

    def execute(self):
        super().execute()

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()
