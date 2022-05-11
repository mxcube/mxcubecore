from pydantic import BaseModel, Field
from devtools import debug

from mxcubecore import HardwareRepository as HWR

from mxcubecore.HardwareObjects.queue_entry.base_queue_entry import (
    BaseQueueEntry,
)

from mxcubecore.HardwareObjects.queue_model_objects import (
    TaskNode,
)


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class SSXCollectionParameters(BaseModel):
    first_image: int
    kappa: float
    kappa_phi: float
#    numRows: int
#    numCols: int
    beam_size: float
    shutterless: bool
    shape: str

    class Config:
        extra: "ignore"

class SSXUserCollectionParameters(BaseModel):
    exp_time: float = Field(10, gt=0, lt=100)
    osc_start: float
    osc_range: float
    num_images: int
    energy: float
    transmission: float
    resolution: float

    class Config:
        extra: "ignore"


class CommonCollectionParamters(BaseModel):
    skip_existing_images: bool
    take_snapshots: int
    type: str
    label: str


class PathParameters(BaseModel):
    #prefixTemplate: str
    #subDirTemplate: str
    prefix: str
    subdir: str

    class Config:
        extra: "ignore"


class LegacyParameters(BaseModel):
    take_dark_current: int
#    detector_mode: int
    inverse_beam: bool
    num_passes: int
    overlap: float

    class Config:
        extra: "ignore"

class SsxChipColletionTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: SSXCollectionParameters
    user_collection_parameters: SSXUserCollectionParameters
    legacy_parameters: LegacyParameters


class SsxChipCollectionQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """
    DATA_MODEL = SsxChipColletionTaskParameters
    NAME = "SSXCollection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    # New style queue entry does not take view argument,
    # adding kwargs for compatability, but they are unsued
    def __init__(self, data: SsxChipColletionTaskParameters, view=None, **kwargs):
        super().__init__(view=view, data_model=TaskNode(data))


    def execute(self):
        super().execute()
        debug(self._data_model._task_data)

        HWR.beamline.detector.prepare_acquisition()
        HWR.beamline.detector.wait_ready()

        HWR.beamline.diffractometer.ssx_chip_scan(
            self._data_model
        )

        # autoAlignSSXBlock(int row, int col)
        # startSSXScan(int subsampling)

        HWR.beamline.diffractometer.wait_ready()

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        super().stop()
