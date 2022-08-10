import os

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
    selection: list = Field([])

    class Config:
        extra: "ignore"

class SSXUserCollectionParameters(BaseModel):
    sub_sampling: float = Field(2, gt=0, lt=100)
    take_pedestal: bool = Field(True)

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
    exp_time: float = Field(10, gt=0, lt=100)
    osc_start: float
    osc_range: float
    num_images: int
    energy: float
    transmission: float
    resolution: float

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
    NAME = "SSXChipCollection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    # New style queue entry does not take view argument,
    # adding kwargs for compatability, but they are unsued
    def __init__(self, data: SsxChipColletionTaskParameters, view=None, **kwargs):
        super().__init__(view=view, data_model=TaskNode(data))


    def execute(self):
        super().execute()

        debug(self._data_model._task_data)

        selected_regions = self._data_model._task_data.collection_parameters.selection
        selected_regions = selected_regions if selected_regions else [[0, 0]]

        for region in selected_regions:
            data_root_path = os.path.join(
                HWR.beamline.session.get_base_image_directory(),
                self._data_model._task_data.path_parameters.subdir
            )

            process_path = os.path.join(
                HWR.beamline.session.get_base_process_directory(),
                self._data_model._task_data.path_parameters.subdir
            )

            fname_prefix = self._data_model._task_data.path_parameters.prefix
            fname_prefix += f"_block_{region[0]}_{region[1]}_"

            HWR.beamline.detector.stop_acquisition()
            HWR.beamline.detector.prepare_acquisition(
                400, 10e-6, data_root_path, fname_prefix
            )
            HWR.beamline.detector.wait_ready()
            HWR.beamline.detector.start_acquisition()

            HWR.beamline.diffractometer.auto_align_ssx_block(
                region[0],
                region[1]
            )
            HWR.beamline.diffractometer.wait_ready()
            HWR.beamline.diffractometer.start_ssx_scan(2)
            HWR.beamline.diffractometer.wait_ready()

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        super().stop()
