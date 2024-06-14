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
from mxcubecore.model.queue_model_objects import DataCollection

from mxcubecore.HardwareObjects.SampleView import Grid, Line, Point

from mxcubecore.model.common import (
    CommonCollectionParamters,
    PathParameters,
    LegacyParameters,
    StandardCollectionParameters,
)

from mxcubecore.model.queue_model_enumerables import (
    EXPERIMENT_TYPE,
)
from mxcubecore.queue_entry.base_queue_entry import (
    BaseQueueEntry,
)
from mxcubecore.queue_entry.data_collection import (
    DataCollectionQueueEntry,
)
from mxcubecore.queue_entry.data_collection import DataCollectionQueueEntry


class XRayCenteringUserCollectionParameters(BaseModel):
    exp_time: float = Field(100e-4, gt=0, lt=1, title="Exposure time (s)")
    num_images: int = Field(1000, gt=0, lt=10000000, title="Number of images")
    energy: float = Field()
    resolution: float = Field()


class XrayCenteringQueueModel(DataCollection):
    pass


class XrayCenteringTaskParameters(BaseModel):
    path_parameters: PathParameters
    common_parameters: CommonCollectionParamters
    collection_parameters: StandardCollectionParameters
    user_collection_parameters: XRayCenteringUserCollectionParameters
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


class BiomaxXrayCenteringQueueEntry(DataCollectionQueueEntry):
    """
    BioMAX XRayCentering queue entry
    """

    QMO = XrayCenteringQueueModel
    DATA_MODEL = XrayCenteringTaskParameters
    NAME = "BioMAX XRAY Centring"
    REQUIRES = ["grid"]

    def __init__(self, view=None, data_model=None, view_set_queue_entry=True):
        BaseQueueEntry.__init__(self, view, data_model, view_set_queue_entry)
        self.mesh_model = data_model  ## Datacollection model
        self.in_queue = False
        self.shapes = None
        self.collect_hwobj = None
        self.shape_history = None
        self.diffractometer_hwobj = None
        self.mesh_enqueued = False
        self.helical_enqueued = False

    def create_line(self, cpos_1, cpos_2):
        x1, y1 = self.diffractometer_hwobj.motor_positions_to_screen(cpos_1)
        x2, y2 = self.diffractometer_hwobj.motor_positions_to_screen(cpos_2)

        line = Line([cpos_1, cpos_2], [x1, y1, x2, y2])
        try:
            self.shape_history.add_shape(line)
        except Exception as ex:
            print(ex)
        return line

    def execute(self):
        BaseQueueEntry.execute(self)
        try:
            self.mesh_qe.pre_execute()
            self.mesh_qe.execute()

            # maybe should add a check of the result to see if it should continue or not
            print(self.diffractometer_hwobj, dir(self.diffractometer_hwobj))
            # self.diffractometer_hwobj.phi.set_value_relative(90)
            self.diffractometer_hwobj.omega.set_value_relative(90)
            self.diffractometer_hwobj.wait_device_ready(5)
            print(HWR.beamline.beam, dir(HWR.beamline.beam))
            # bx, by = HWR.beamline.beam.get_beam_position()
            bx, by = HWR.beamline.beam.get_beam_position_on_screen()
            beam_pos = self.diffractometer_hwobj.get_centred_point_from_coord(
                bx, by, return_by_names=True
            )
            extend_grid = 15
            # use the same the beam_size as in mesh
            mesh_id = self.mesh_model.shape
            mesh_shape = self.shape_history.get_shape(mesh_id).as_dict()
            beam_width = mesh_shape.get("beam_width") or 0.02
            distance = (extend_grid - 0.5) * beam_width
            try:
                self.diffractometer_hwobj.move_cent_vertical_relative(-distance)
            except:
                print("does not exists in mockup")
            start_pos = self.diffractometer_hwobj.get_positions()
            try:
                self.diffractometer_hwobj.move_cent_vertical_relative(distance * 2)
            except:
                print("does not exists in mockup")
            end_pos = self.diffractometer_hwobj.get_positions()

            # now we recreate the helical positions
            acq_1 = queue_model_objects.Acquisition()
            acq_1.acquisition_parameters.set_from_dict({"centred_position": end_pos})
            acq_2 = queue_model_objects.Acquisition()
            acq_2.acquisition_parameters.set_from_dict({"centred_position": start_pos})
            path_template = self.mesh_model.acquisitions[0].path_template
            acq_1.path_template = path_template
            acq_2.path_template = path_template
            self.helical_model.acquisitions = [acq_1, acq_2]
            self.helical_qe.set_enabled(True)
            line = self.create_line(start_pos, end_pos)
            self.helical_model.shape = line.id
            # inherit some params from mesh
            acq_mesh_params = self.mesh_model.acquisitions[0].acquisition_parameters
            acq_1.acquisition_parameters.energy = acq_mesh_params.energy
            # here we have fixed values to not exceed motor limit
            acq_1.acquisition_parameters.exp_time = 0.1
            acq_1.acquisition_parameters.transmission = (
                acq_mesh_params.transmission
                * acq_mesh_params.exp_time
                / acq_1.acquisition_parameters.exp_time
            )
            acq_1.acquisition_parameters.resolution = acq_mesh_params.resolution
            acq_1.acquisition_parameters.osc_range = acq_mesh_params.osc_range
            acq_1.acquisition_parameters.num_images = extend_grid * 2
            acq_1.acquisition_parameters.osc_start = start_pos["phi"]
            acq_1.path_template.run_number += 1
            self.helical_qe.pre_execute()
            self.helical_qe.execute()

            # wait for results, whihc would be a single float
            # convert to motor pos and move there (i would be a horizontal move only, so maybe juts use the virtual horizontal)
            # self.diffractometer_hwobj.save_centered_position()
            # why do we need to save the positions?
            # self.collect_hwobj.create_point_from_current_pos()
            point = Point([self.diffractometer_hwobj.get_positions()], (bx, by))
            self.shape_history.add_shape(point)
            # self.shape_history.add_shape_from_mpos(self.diffractometer_hwobj.get_positions(), (bx, by), 'P')
            mesh_omega = mesh_shape.get("motor_positions").get("phi", 0)
            self.diffractometer_hwobj.omega.set_value(mesh_omega)
        except Exception as e:
            print(e)
            import sys

            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
        self.mesh_qe.set_enabled(False)
        self.helical_qe.set_enabled(False)

    def pre_execute(self):
        try:
            BaseQueueEntry.pre_execute(self)
        except Exception as ex:
            print(ex)
        try:
            self.lims_client_hwobj = HWR.beamline.lims
            self.collect_hwobj = HWR.beamline.collect
            self.diffractometer_hwobj = HWR.beamline.diffractometer
            self.shape_history = HWR.beamline.sample_view
            self.session = HWR.beamline.session
        except Exception as ex:
            print(ex)

        from mock import Mock

        q = self.get_queue_controller()
        parent = self.get_data_model().get_parent()
        parent_entry = q.get_entry_with_model(parent)
        self.mesh_qe = DataCollectionQueueEntry(Mock(), self.mesh_model)
        self.mesh_qe.set_enabled(True)
        self.mesh_qe.in_queue = True
        self.enqueue(self.mesh_qe)
        self.mesh_qe.xray = False
        self.mesh_enqueued = True

        # We create an helical entry
        self.helical_qe = DataCollectionQueueEntry(view=Mock())

        self.enqueue(self.helical_qe)
        self.helical_model = queue_model_objects.DataCollection()
        self.helical_model._parent = self.get_data_model().get_parent()
        self.helical_qe.xray = False

        self.helical_model.set_experiment_type(EXPERIMENT_TYPE.LINE_SCAN)
        self.helical_qe.set_data_model(self.helical_model)

    def post_execute(self):
        if self.helical_qe:
            self.status = self.helical_qe.status
        else:
            self.status = self.mesh_qe
        BaseQueueEntry.post_execute(self)

    def get_type_str(self):
        return "X-ray centring"
