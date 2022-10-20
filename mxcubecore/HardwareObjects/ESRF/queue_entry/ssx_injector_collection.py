import os
import logging
import time
import contextlib

from pydantic import BaseModel, Field
from devtools import debug

from mxcubecore import HardwareRepository as HWR
from mxcubecore.model.common import (
    CommonCollectionParamters,
    PathParameters,
    LegacyParameters,
    StandardCollectionParameters,
)
from mxcubecore.utils import nicoproc

from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
)

from mxcubecore.model.queue_model_objects import (
    DataCollection,
)


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


@contextlib.contextmanager
def jungfrau_visualization(session, jungfrau_name, active=True):
    if not hasattr(session, "start_monitor"):
        session.load_script("jungfrau.py")
    jungfrau = getattr(session, jungfrau_name)
    set_colormap_args = dict(lut="viridis", vmin=0, vmax=100000, autoscale=False)
    monitor = session.start_monitor(
        jungfrau,
        "last_image",
        active=active,
        set_colormap_args=set_colormap_args,
        refresh_time=0.1,
        mode="accumulate",
    )
    try:
        yield monitor
    finally:
        monitor.active = False


class InjectorUserCollectionParameters(BaseModel):
    exp_time: float = Field(100e-6, gt=0, lt=1)
    num_images: int = Field(1000, gt=0, lt=10000000)
    take_pedestal: bool = Field(True)
    sub_sampling: float = Field(4, gt=0, lt=100)

    class Config:
        extra: "ignore"


class InjectorColletionTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: InjectorUserCollectionParameters
    legacy_parameters: LegacyParameters


class LimsParamters(BaseModel):
    pass


class SsxInjectorCollectionQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    DATA_MODEL = InjectorColletionTaskParameters
    NAME = "SSXInjectorCollection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    # New style queue entry does not take view argument,
    # adding kwargs for compatability, but they are unsued
    def __init__(self, data: InjectorColletionTaskParameters, view=None, **kwargs):
        super().__init__(view=view, data_model=DataCollection(task_data=data))

    def execute(self):
        super().execute()
        debug(self._data_model._task_data)
        params = self._data_model._task_data.user_collection_parameters

        beamline_values = HWR.beamline.lims.pyispyb.get_current_beamline_values()

        # if HWR.beamline.control.safshut_oh2.state.name == "DISABLE":
        #    raise RuntimeError(HWR.beamline.control.safshut_oh2.state.value)

        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        fname_prefix = self._data_model._task_data.path_parameters.prefix
        num_images = self._data_model._task_data.user_collection_parameters.num_images
        sub_sampling = (
            self._data_model._task_data.user_collection_parameters.sub_sampling
        )

        MAX_FREQ = 1387.5

        if params.take_pedestal:
            HWR.beamline.control.safshut_oh2.close()
            if not hasattr(HWR.beamline.control, "jungfrau_pedestal_scans"):
                HWR.beamline.control.load_script("jungfrau.py")
            HWR.beamline.control.jungfrau_pedestal_scans(
                HWR.beamline.control.jungfrau4m, exp_time, 1000, MAX_FREQ / sub_sampling
            )

        HWR.beamline.control.jungfrau4m.camera.img_src = "GAIN_PED_CORR"

        data_root_path = os.path.join(
            HWR.beamline.session.get_base_image_directory(),
            self._data_model._task_data.path_parameters.subdir,
        )

        process_path = os.path.join(
            HWR.beamline.session.get_base_process_directory(),
            self._data_model._task_data.path_parameters.subdir,
        )

        HWR.beamline.detector.stop_acquisition()
        HWR.beamline.detector.prepare_acquisition(
            num_images, exp_time, data_root_path, fname_prefix
        )

        nicoproc.start_ssx(
            beamline_values,
            self._data_model._task_data,
            data_root_path,
            experiment_type="INJECTOR",
        )

        HWR.beamline.detector.wait_ready()

        with jungfrau_visualization(HWR.beamline.control, "jungfrau4m") as monitor:
            HWR.beamline.diffractometer.set_phase("DataCollection")
            HWR.beamline.diffractometer.wait_ready()

            logging.getLogger("user_level_log").info(f"Acquiring ...")
            HWR.beamline.detector.start_acquisition()
            HWR.beamline.diffractometer.start_still_ssx_scan(num_images, sub_sampling)

            if HWR.beamline.control.safshut_oh2.state.name != "OPEN":
                logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
                HWR.beamline.control.safshut_oh2.open()

            logging.getLogger("user_level_log").info(
                f"Waiting for acqusition to finish ..."
            )
            time.sleep(num_images * exp_time)

            HWR.beamline.diffractometer.wait_ready()
            HWR.beamline.detector.wait_ready()
            logging.getLogger("user_level_log").info(f"Acquired {num_images} images")

        # HWR.beamline.lims.pyispyb.create_ssx_collection(
        #    self._data_model._task_data,
        #    beamline_values,
        # )

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()
        if HWR.beamline.control.safshut_oh2.state.name == "OPEN":
            logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
            HWR.beamline.control.safshut_oh2.close()

    def stop(self):
        super().stop()
