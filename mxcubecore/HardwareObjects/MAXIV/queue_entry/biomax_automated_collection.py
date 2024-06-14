#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.
import gevent
from pydantic import BaseModel, Field
import json
import os
from mxcubecore import HardwareRepository as HWR
from mxcubecore.model import queue_model_objects
from mxcubecore.model.queue_model_objects import DataCollection, XrayCentering

from mxcubecore.HardwareObjects.SampleView import Grid, Line, Point

from mxcubecore.model.common import (
    CommonCollectionParamters,
    PathParameters,
    LegacyParameters,
    StandardCollectionParameters,
)
from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
    QUEUE_ENTRY_STATUS,
    QueueExecutionException,
    QueueAbortedException,
    center_before_collect,
)

from mxcubecore.model.queue_model_enumerables import (
    EXPERIMENT_TYPE,
    COLLECTION_ORIGIN_STR,
)
from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
)
from mxcubecore.queue_entry.data_collection import DataCollectionQueueEntry
from .biomax_xray_centering import BiomaxXrayCenteringQueueEntry


class BiomaxAutomatedCollectionParameters(BaseModel):
    exp_time: float = Field(100e-4, gt=0, lt=1, title="Exposure time (s)")
    num_images: int = Field(1000, gt=0, lt=10000000, title="Number of images")
    energy: float = Field()
    resolution: float = Field()


class BiomaxAutomatedQueueModel(DataCollection):
    pass


class BiomaxAutomatedTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: BiomaxAutomatedCollectionParameters
    legacy_parameters: LegacyParameters

    @staticmethod
    def update_dependent_fields(field_data):
        return field_data

    @staticmethod
    def ui_schema():
        print("ui_schema")
        schema = json.dumps(
            {
                "ui:order": [
                    "num_images",
                    "exp_time",
                    "resolution",
                    "energy",
                    "*",
                ],
                "ui:submitButtonOptions": {
                    "norender": "true",
                },
            }
        )
        print(schema)
        return schema


class BiomaxAutomatedCollectionQueueEntry(DataCollectionQueueEntry):
    """
    BioMAX Automated collection queue entry
    """

    QMO = BiomaxAutomatedQueueModel
    DATA_MODEL = BiomaxAutomatedTaskParameters
    NAME = "BioMAX Automated Collection"
    REQUIRES = ["no_shape"]

    def execute(self):
        BaseQueueEntry.execute(self)
        data_collection = self.get_data_model()

        if data_collection:
            acq_params = data_collection.acquisitions[0].acquisition_parameters
            cpos = acq_params.centred_position
            xr_qe = BiomaxXrayCenteringQueueEntry(data_model=data_collection)
            try:
                xr_node = XrayCentering()
                parent = self.get_data_model().get_parent()
                sample = parent.get_parent()
                xr_node._parent = parent

                q = self.get_queue_controller()
                parent_entry = q.get_entry_with_model(parent)
                xr_qe.set_data_model(xr_node)
                xr_qe.shapes = HWR.beamline.sample_view
                parent_entry.enqueue(xr_qe)
            except Exception as e:
                import sys

                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]

            try:
                xr_qe.pre_execute()
                xr_qe.execute()
            except Exception as e:
                import sys

                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]

            self.collect_dc(data_collection, self.get_view())

        if HWR.beamline.sample_view:
            HWR.beamline.sample_view.de_select_all()
