import os
import logging
import contextlib
from fileinput import filename
from pydantic import BaseModel, Field
from devtools import debug

from mxcubecore import HardwareRepository as HWR

from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
)

from mxcubecore.model.queue_model_objects import (
    TaskNode,
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
    sub_sampling: float = Field(4, gt=0, lt=100)
    exp_time: float = Field(100e-6, gt=0, lt=1)

    motor_top_left_x: float = Field(18, gt=-100, lt=100)
    motor_top_left_y: float = Field(15.8, gt=-100, lt=100)
    motor_top_left_z: float = Field(-0.1, gt=-100, lt=100)

    motor_top_right_x: float = Field(22, gt=-100, lt=100)
    motor_top_right_y: float = Field(15.8, gt=-100, lt=100)
    motor_top_right_z: float = Field(-0.1, gt=-100, lt=100)

    motor_bottom_left_x: float = Field(18, gt=-100, lt=100)
    motor_bottom_left_y: float = Field(24, gt=-100, lt=100)
    motor_bottom_left_z: float = Field(-0.1, gt=-100, lt=100)

    nb_samples_per_line: int = Field(20, gt=0, lt=1000)
    nb_lines: int = Field(20, gt=0, lt=1000)
    take_pedestal: bool = Field(True)

    class Config:
        extra: "ignore"


class CommonCollectionParamters(BaseModel):
    skip_existing_images: bool
    take_snapshots: int
    type: str
    label: str


class PathParameters(BaseModel):
    # prefixTemplate: str
    # subDirTemplate: str
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


class SsxFoilCollectionQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    DATA_MODEL = SsxChipColletionTaskParameters
    NAME = "SSXFoilCollection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    # New style queue entry does not take view argument,
    # adding kwargs for compatability, but they are unsued
    def __init__(self, data: SsxChipColletionTaskParameters, view=None, **kwargs):
        super().__init__(view=view, data_model=TaskNode(data))

    def execute(self):
        super().execute()
        debug(self._data_model._task_data)
        params = self._data_model._task_data.user_collection_parameters
        exp_time = params.exp_time

        # if HWR.beamline.control.safshut_oh2.state.name == "DISABLE":
        #    raise RuntimeError(HWR.beamline.control.safshut_oh2.state.value)

        debug(f"type(HWR.beamline.control)={type(HWR.beamline.control)}")
        if hasattr(HWR.beamline.control, "SCAN_DISPLAY"):
            HWR.beamline.control.SCAN_DISPLAY.auto = True

        if params.take_pedestal:
            HWR.beamline.control.safshut_oh2.close()
            if not hasattr(HWR.beamline.control, "jungfrau_pedestal_scans"):
                HWR.beamline.control.load_script("jungfrau.py")
            HWR.beamline.control.jungfrau_pedestal_scans(
                HWR.beamline.control.jungfrau4m, exp_time, 1000, 500
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

        fname_prefix = self._data_model._task_data.path_parameters.prefix
        fname_prefix += f"_foil_"

        region = (
            params.motor_top_left_x,
            params.motor_top_left_y,
            params.motor_top_left_z,
            params.motor_top_right_x,
            params.motor_top_right_y,
            params.motor_top_right_z,
            params.motor_bottom_left_x,
            params.motor_bottom_left_y,
            params.motor_bottom_left_z,
        )

        logging.getLogger("user_level_log").info(f"Defining region {region}")

        HWR.beamline.diffractometer.define_ssx_scan_region(
            *region, params.nb_samples_per_line, params.nb_lines
        )

        logging.getLogger("user_level_log").info("Preparing detector")
        HWR.beamline.detector.stop_acquisition()

        num_images = params.nb_samples_per_line * params.nb_lines
        HWR.beamline.detector.prepare_acquisition(
            num_images, exp_time, data_root_path, fname_prefix
        )

        HWR.beamline.detector.wait_ready()

        jv = jungfrau_visualization(HWR.beamline.control, "jungfrau4m")
        with jv as monitor:
            HWR.beamline.detector.start_acquisition()
            logging.getLogger("user_level_log").info(
                "Detector ready, waiting for trigger ..."
            )

            HWR.beamline.diffractometer.wait_ready()
            HWR.beamline.diffractometer.set_phase(
                "DataCollection", wait=True, timeout=120
            )
            # HWR.beamline.diffractometer.wait_ready()

            if HWR.beamline.control.safshut_oh2.state.name != "OPEN":
                logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
                HWR.beamline.control.safshut_oh2.open()

            logging.getLogger("user_level_log").info(f"Acquiring {num_images}")

            try:
                HWR.beamline.diffractometer.start_ssx_scan(params.sub_sampling)
                HWR.beamline.diffractometer.wait_ready(360)
            except:
                msg = "Diffractometer failed! Waiting for detector to finish"
                logging.getLogger("user_level_log").error(msg)
                HWR.beamline.detector.wait_ready()
                raise

            if HWR.beamline.control.safshut_oh2.state.name == "OPEN":
                HWR.beamline.control.safshut_oh2.close()
                logging.getLogger("user_level_log").info("shutter closed")

            HWR.beamline.detector.wait_ready()
            logging.getLogger("user_level_log").info(f"Acquired {region}")

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()
        if HWR.beamline.control.safshut_oh2.state.name == "OPEN":
            HWR.beamline.control.safshut_oh2.close()
            logging.getLogger("user_level_log").info("shutter closed")

        HWR.beamline.detector.stop_acquisition()

    def stop(self):
        super().stop()
        if HWR.beamline.control.safshut_oh2.state.name == "OPEN":
            HWR.beamline.control.safshut_oh2.close()
            logging.getLogger("user_level_log").info("shutter closed")

        HWR.beamline.detector.stop_acquisition()
