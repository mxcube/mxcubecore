import os
import logging
import contextlib
from pydantic import BaseModel, Field
from devtools import debug

from mxcubecore import HardwareRepository as HWR

from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
)

from mxcubecore.model.queue_model_objects import (
    DataCollection,
)


from mxcubecore.model.common import (
    CommonCollectionParamters,
    PathParameters,
    LegacyParameters,
    StandardCollectionParameters,
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


class SSXUserCollectionParameters(BaseModel):
    sub_sampling: float = Field(4, gt=0, lt=100)
    exp_time: float = Field(100e-6, gt=0, lt=1)
    take_pedestal: bool = Field(True)
    align_chip: bool = Field(True)

    class Config:
        extra: "ignore"


class SsxChipColletionTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: SSXUserCollectionParameters
    legacy_parameters: LegacyParameters


class SsxChipCollectionQueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SsxChipCollectionQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    QMO = SsxChipCollectionQueueModel
    DATA_MODEL = SsxChipColletionTaskParameters
    NAME = "SSXChipCollection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    # New style queue entry does not take view argument,
    # adding kwargs for compatability, but they are unsued
    def __init__(self, data_model: SsxChipCollectionQueueModel, view=None):
        super().__init__(view=view, data_model=data_model)

    def execute(self):
        super().execute()
        debug(self._data_model._task_data)
        params = self._data_model._task_data.user_collection_parameters

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
                HWR.beamline.control.jungfrau4m, params.exp_time, 1000, 500
            )

        HWR.beamline.control.jungfrau4m.camera.img_src = "GAIN_PED_CORR"

        selected_regions = self._data_model._task_data.collection_parameters.selection
        selected_regions = selected_regions if selected_regions else [[0, 0]]

        jv = jungfrau_visualization(HWR.beamline.control, "jungfrau4m")
        with jv as monitor:
            for region in selected_regions:
                data_root_path = os.path.join(
                    HWR.beamline.session.get_base_image_directory(),
                    self._data_model._task_data.path_parameters.subdir,
                )

                process_path = os.path.join(
                    HWR.beamline.session.get_base_process_directory(),
                    self._data_model._task_data.path_parameters.subdir,
                )

                fname_prefix = self._data_model._task_data.path_parameters.prefix
                fname_prefix += f"_block_{region[0]}_{region[1]}_"

                HWR.beamline.diffractometer.set_phase(
                    "Centring", wait=True, timeout=120
                )
                # HWR.beamline.diffractometer.wait_ready()
                logging.getLogger("user_level_log").info(f"Acquiring {region} ...")

                if params.align_chip:
                    logging.getLogger("user_level_log").info(f"Aligning block {region}")
                    HWR.beamline.diffractometer.auto_align_ssx_block(
                        region[0], region[1]
                    )

                logging.getLogger("user_level_log").info("Preparing detector")
                HWR.beamline.detector.stop_acquisition()

                HWR.beamline.detector.prepare_acquisition(
                    400, params.exp_time, data_root_path, fname_prefix
                )
                HWR.beamline.detector.wait_ready()

                HWR.beamline.detector.start_acquisition()
                logging.getLogger("user_level_log").info(
                    "Detector ready, waiting for trigger ..."
                )
                HWR.beamline.diffractometer.wait_ready()
                logging.getLogger("user_level_log").info(f"Aligned block {region}")
                logging.getLogger("user_level_log").info(f"Scanning {region} ...")

                HWR.beamline.diffractometer.set_phase(
                    "DataCollection", wait=True, timeout=120
                )
                # HWR.beamline.diffractometer.wait_ready()

                if HWR.beamline.control.safshut_oh2.state.name != "OPEN":
                    logging.getLogger("user_level_log").info(
                        f"Opening OH2 safety shutter"
                    )
                    HWR.beamline.control.safshut_oh2.open()

                HWR.beamline.diffractometer.start_ssx_scan(params.sub_sampling)
                HWR.beamline.diffractometer.wait_ready()

                if HWR.beamline.control.safshut_oh2.state.name == "OPEN":
                    HWR.beamline.control.safshut_oh2.close()
                    logging.getLogger("user_level_log").info("shutter closed")

                HWR.beamline.detector.wait_ready()
                logging.getLogger("user_level_log").info(f"Acquired {region}")

                # dcg = HWR.beamline.lims.pyispyb.create_ssx_data_collection_group(
                #     session_id=HWR.beamline.session.session_id
                # )
                # HWR.beamline.lims.pyispyb.create_ssx_data_collection(
                #     dcg
                # )

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
