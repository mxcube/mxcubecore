import json
import logging
from pydantic import BaseModel, Field
from mxcubecore.model.queue_model_objects import DataCollection
from mxcubecore import HardwareRepository as HWR
from mxcubecore.queue_entry.base_queue_entry import QueueExecutionException
from mxcubecore.model.common import (
    CommonCollectionParamters,
    PathParameters,
    LegacyParameters,
    StandardCollectionParameters,
)
from .base import AbstractSsxQueueEntry, restore_beamline


log = logging.getLogger("queue_exec")


class InjectorUserCollectionParameters(BaseModel):
    exp_time: float = Field(100e-4, gt=0, lt=1, title="Exposure time (s)")
    num_images: int = Field(1000, gt=0, lt=10000000, title="Number of images")
    energy: float = Field()
    resolution: float = Field()
    cellA: float = Field(0, title="Cell A")
    cellB: float = Field(0, title="Cell B")
    cellC: float = Field(0, title="Cell C")
    cellAlpha: float = Field(0, title="Cell α")
    cellBeta: float = Field(0, title="Cell β")
    cellGamma: float = Field(0, title="Cell γ")


class SsxInjectorQueueModel(DataCollection):
    pass


class InjectorTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: InjectorUserCollectionParameters
    legacy_parameters: LegacyParameters

    @staticmethod
    def update_dependent_fields(field_data):
        return field_data

    @staticmethod
    def ui_schema():
        return json.dumps(
            {
                "ui:order": [
                    "num_images",
                    "exp_time",
                    "resolution",
                    "energy",
                    "cellA",
                    "cellAlpha",
                    "cellB",
                    "cellBeta",
                    "cellC",
                    "cellGamma",
                    "*",
                ],
                "ui:submitButtonOptions": {
                    "norender": "true",
                },
            }
        )


def _wait_acquisition_done():
    """
    wait unit detector reports that data acquisition have stopped
    """
    detector = HWR.beamline.detector

    log.info("Waiting for acquisition to finish.")

    #
    # deal with different behaviour of Jungfrau vs Eiger hardware objects
    #
    if HWR.beamline.collect.is_jungfrau():
        detector.wait_ready()
    else:
        # we are using eiger detector
        detector.wait_idle()
    log.info("Acquisition is finished.")


class SsxInjectorQueueEntry(AbstractSsxQueueEntry):
    QMO = SsxInjectorQueueModel
    DATA_MODEL = InjectorTaskParameters
    NAME = "SSX Injector Collection"
    REQUIRES = ["point", "line", "no_shape", "chip", "mesh"]

    def _do_data_collection(self):
        self.prepare_data_collection()

        detector = HWR.beamline.detector
        log.info("Sending software trigger to detector.")
        detector.trigger()
        _wait_acquisition_done()

    def execute(self):
        try:
            super().execute()
            self._do_data_collection()
        except Exception as ex:
            raise QueueExecutionException(str(ex), self)
        finally:
            restore_beamline()
