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


class LaserInjectorUserCollectionParameters(BaseUserCollectionParameters):
    num_images: int = Field(1000, gt=0, lt=10000000)
    take_pedestal: bool = Field(True)

    class Config:
        extra: "ignore"
        use_enum_values: True


class LaserInjectorColletionTaskParameters(SsxBaseQueueTaskParameters):
    user_collection_parameters: LaserInjectorUserCollectionParameters


class SsxLaserInjectorCollectionQueueModel(DataCollection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SsxLaserInjectorCollectionQueueEntry(SsxBaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    QMO = SsxLaserInjectorCollectionQueueModel
    DATA_MODEL = LaserInjectorColletionTaskParameters
    NAME = "SSX LaserInjector Collection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    def __init__(self, view, data_model: SsxLaserInjectorCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)
        self.__scanning = False

    def execute(self):
        super().execute()

        exp_time = self._data_model._task_data.user_collection_parameters.exp_time
        fname_prefix = self._data_model._task_data.path_parameters.prefix
        num_images = self._data_model._task_data.user_collection_parameters.num_images
        sub_sampling = (
            self._data_model._task_data.user_collection_parameters.sub_sampling
        )
        reject_empty_frames = (
            self._data_model._task_data.user_collection_parameters.reject_empty_frames
        )

        delay = HWR.beamline.diffractometer.get_ssx_delay()
        ssx_laser_scan_method = HWR.beamline.diffractometer.get_ssx_scan_method()

        data_root_path = self.get_data_path()

        HWR.beamline.diffractometer.set_phase("DataCollection")

        self.take_pedestal()

        HWR.beamline.detector.prepare_acquisition(
            num_images,
            exp_time,
            data_root_path,
            fname_prefix,
            dense_skip_nohits=reject_empty_frames,
        )

        self.start_processing("INJECTOR")

        if HWR.beamline.control.safshut_oh2.state.name != "OPEN":
            logging.getLogger("user_level_log").info(f"Opening OH2 safety shutter")
            HWR.beamline.control.safshut_oh2.open()

        HWR.beamline.diffractometer.wait_ready()
        HWR.beamline.detector.wait_ready()

        logging.getLogger("user_level_log").info(
            f"Laser scan method {ssx_laser_scan_method}"
        )
        logging.getLogger("user_level_log").info(f"Laser delay {delay}")
        logging.getLogger("user_level_log").info(f"Acquiring ...")
        HWR.beamline.detector.start_acquisition()

        try:
            HWR.beamline.diffractometer.start_still_ssx_scan(num_images)
        except:
            err_msg = "Diffractometer scan failed ..."
            logging.getLogger("user_level_log").exception(err_msg)
            HWR.beamline.detector.stop_acquisition()
            raise

        self.__scanning = True

        logging.getLogger("user_level_log").info("Waiting for scan to finish ...")

        try:
            HWR.beamline.diffractometer.wait_ready()
            logging.getLogger("user_level_log").info("Scan finished ...")
        finally:
            self.__scanning = False

            HWR.beamline.detector.wait_ready()
            acquired = HWR.beamline.detector.get_acquired_frames()
            logging.getLogger("user_level_log").info(f"Acquired {acquired} images")

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        if self.__scanning:
            logging.getLogger("user_level_log").info("Stopping diffractometer ...")
            HWR.beamline.diffractometer.abort_cmd()
            gevent.sleep(5)
            HWR.beamline.diffractometer.wait_ready()

        super().stop()
