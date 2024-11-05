import logging

from devtools import debug

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.ESRF.queue_entry.mx_base_queue_entry import (
    BaseUserCollectionParameters,
    MXBaseQueueEntry,
    MXBaseQueueTaskParameters,
)
from mxcubecore.model.queue_model_objects import DataCollection

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class FastCharUserCollectionParameters(BaseUserCollectionParameters):
    class Config:
        extra: "ignore"


class FastCharCollectionTaskParameters(MXBaseQueueTaskParameters):
    user_collection_parameters: FastCharUserCollectionParameters

    @staticmethod
    def update_dependent_fields(field_data):
        new_data = {}
        return new_data


class FastCharCollectionQueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class FastCharCollectionQueueEntry(MXBaseQueueEntry):
    """
    Defines the behaviour of a data collection.
    """

    QMO = FastCharCollectionQueueModel
    DATA_MODEL = FastCharCollectionTaskParameters
    NAME = "Fast characterisation"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    def __init__(self, view, data_model: FastCharCollectionQueueModel):
        super().__init__(view=view, data_model=data_model)

    def execute(self):
        super().execute()
        debug(self._data_model._task_data)
        data_path = self.get_data_path()

        number_of_images = 10
        number_of_scans = 4
        angle = 90
        exptime = 0.1
        osc_range = 1
        osc_start = 0

        HWR.beamline.diffractometer.set_phase("DataCollection")

        logging.getLogger("user_level_log").info(f"Preparing acqusisition")
        HWR.beamline.detector.prepare_acquisition(
            0,
            osc_start,
            osc_range,
            exptime / number_of_images,
            None,
            int(number_of_images * number_of_scans),
            "",
            True,
            0,
        )

        logging.getLogger("user_level_log").info(f"Setting file path to {data_path}")
        HWR.beamline.detector.set_detector_filenames(1, 1, data_path)

        HWR.beamline.diffractometer.wait_ready()
        logging.getLogger("user_level_log").info(f"Phase changed to data collection")

        HWR.beamline.detector.start_acquisition()
        logging.getLogger("user_level_log").info(f"Acquiring ...")
        HWR.beamline.diffractometer.characterisation_scan(
            osc_start,
            osc_range,
            number_of_images,
            exptime,
            number_of_scans,
            angle,
            wait=True,
        )

        HWR.beamline.diffractometer.wait_ready()
        HWR.beamline.detector.wait_ready()
        logging.getLogger("user_level_log").info(f"Finished fast characterisation")

    def pre_execute(self):
        super().pre_execute()

    def post_execute(self):
        super().post_execute()

    def stop(self):
        super().stop()
