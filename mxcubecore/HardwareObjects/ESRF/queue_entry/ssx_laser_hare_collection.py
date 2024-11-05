import logging

import gevent
from devtools import debug
from pydantic.v1 import (
    BaseModel,
    Field,
)

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.ESRF.queue_entry.ssx_base_queue_entry import (
    BaseUserCollectionParameters,
    SsxBaseQueueEntry,
    SsxBaseQueueTaskParameters,
)
from mxcubecore.model.queue_model_objects import DataCollection

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class SSXLaserHareCollectionParameters(BaseUserCollectionParameters):
    align_chip: bool = Field(True)

    class Config:
        extra: "ignore"


class SsxLaserHareColletionTaskParameters(SsxBaseQueueTaskParameters):
    user_collection_parameters: SSXLaserHareCollectionParameters


class SsxLaserHareCollectionQueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SsxLaserHareCollectionQueueEntry(SsxBaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    QMO = SsxLaserHareCollectionQueueModel
    DATA_MODEL = SsxLaserHareColletionTaskParameters
    NAME = "SSX Laser HARE Collection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    def __init__(self, view, data_model: SsxLaserHareCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)
        self._data_model._task_data.collection_parameters.num_images = 400

        self.__stop_req = False
        self.__stop_done = True

    def execute(self):
        super().execute()

        self.__stop_req = False
        self.__stop_done = False

        params = self._data_model._task_data.user_collection_parameters

        data_root_path = self.get_data_path()
        fname_prefix = self._data_model._task_data.path_parameters.prefix
        enforce_centring_phase = False
        reject_empty_frames = (
            self._data_model._task_data.user_collection_parameters.reject_empty_frames
        )
        delay = HWR.beamline.diffractometer.get_ssx_delay()
        ssx_laser_scan_method = HWR.beamline.diffractometer.get_ssx_scan_method()

        self.take_pedestal()

        self.start_processing("CHIP")

        selected_regions = self._data_model._task_data.collection_parameters.selection
        selected_regions = selected_regions if selected_regions else [[0, 0]]

        for region in selected_regions:
            if self.__stop_req:
                self.__stop_done = True
                logging.getLogger("user_level_log").info("Stopped sequence")
                break

            fname_prefix = self._data_model._task_data.path_parameters.prefix
            fname_prefix += f"_block_{region[0]}_{region[1]}_"

            # HWR.beamline.diffractometer.set_phase("Centring", wait=True, timeout=120)
            logging.getLogger("user_level_log").info(
                f"Laser scan method {ssx_laser_scan_method}"
            )
            logging.getLogger("user_level_log").info(f"Laser delay {delay}")
            logging.getLogger("user_level_log").info(f"Acquiring {region} ...")

            if params.align_chip:
                logging.getLogger("user_level_log").info(f"Aligning block {region}")
                HWR.beamline.diffractometer.set_phase(
                    "Centring", wait=True, timeout=120
                )
                HWR.beamline.diffractometer.prepare_ssx_grid_scan(
                    params.sub_sampling, region[0], region[1], False
                )
                logging.getLogger("user_level_log").info(f"Aligned block {region}")
                enforce_centring_phase = True

            logging.getLogger("user_level_log").info("Preparing detector")

            HWR.beamline.detector.stop_acquisition()
            gevent.sleep(10)
            HWR.beamline.detector.prepare_acquisition(
                400,
                params.exp_time,
                data_root_path,
                fname_prefix,
                dense_skip_nohits=reject_empty_frames,
            )

            HWR.beamline.diffractometer.wait_ready()

            logging.getLogger("user_level_log").info(f"Preparing data collection")
            HWR.beamline.diffractometer.set_phase("DataCollection")

            if HWR.beamline.control.safshut_oh2.state.name != "OPEN":
                logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
                HWR.beamline.control.safshut_oh2.open()

            HWR.beamline.diffractometer.wait_ready()
            HWR.beamline.detector.wait_ready()
            gevent.sleep(5)

            HWR.beamline.detector.start_acquisition()
            logging.getLogger("user_level_log").info(
                "Detector ready, waiting for trigger ..."
            )

            try:
                logging.getLogger("user_level_log").info(f"Scanning {region} ...")
                HWR.beamline.diffractometer.start_ssx_scan(enforce_centring_phase)
            except:
                err_msg = "Diffractometer scan failed ..."
                logging.getLogger("user_level_log").exception(err_msg)
                HWR.beamline.detector.stop_acquisition()
                raise

            try:
                HWR.beamline.diffractometer.wait_ready()
            finally:
                HWR.beamline.detector.wait_ready()

            logging.getLogger("user_level_log").info(f"Acquired {region}")

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        self.__stop_req = True
        super().stop()
