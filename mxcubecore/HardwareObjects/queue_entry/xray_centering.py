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

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects import queue_model_objects

from mxcubecore.HardwareObjects.queue_entry.base_queue_entry import (
    BaseQueueEntry,
)

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class XrayCenteringQueueEntry(BaseQueueEntry):
    """
    Defines the behaviour of an Advanced scan
    """

    def __init__(self, view=None, data_model=None, view_set_queue_entry=True):

        BaseQueueEntry.__init__(self, view, data_model, view_set_queue_entry)
        self.mesh_qe = None
        self.helical_qe = None
        self.in_queue = False

    def execute(self):
        BaseQueueEntry.execute(self)

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        xray_centering = self.get_data_model()
        reference_image_collection = xray_centering.reference_image_collection
        reference_image_collection.grid = HWR.beamline.sample_view.create_auto_grid()
        reference_image_collection.acquisitions[
            0
        ].acquisition_parameters.centred_position = (
            reference_image_collection.grid.get_centred_position()
        )

        # Trick to make sure that the reference collection has a sample.
        reference_image_collection._parent = xray_centering.get_parent()
        xray_centering.line_collection._parent = xray_centering.get_parent()

        gid = self.get_data_model().get_parent().lims_group_id
        reference_image_collection.lims_group_id = gid

        # Enqueue the reference mesh scan collection
        mesh_qe = DataCollectionQueueEntry(
            self.get_view(), reference_image_collection, view_set_queue_entry=False
        )
        mesh_qe.set_enabled(True)
        mesh_qe.in_queue = self.in_queue
        self.mesh_qe = mesh_qe

        # Creat e a helical data collection based on the first collection
        helical_qe = DataCollectionQueueEntry(
            self.get_view(), reference_image_collection, view_set_queue_entry=False
        )

        # helical_model = helical_qe.get_data_model()
        # @helical_model.set_experiment_type(EXPERIMENT_TYPE.HELICAL)
        # @helical_model.grid = None

        acq_two = queue_model_objects.Acquisition()
        helical_model.acquisitions.append(acq_two)
        helical_model.acquisitions[0].acquisition_parameters.num_images = 100
        helical_model.acquisitions[0].acquisition_parameters.num_lines = 1
        helical_acq_path_template = helical_model.acquisitions[0].path_template
        helical_acq_path_template.base_prefix = (
            "line_" + helical_acq_path_template.base_prefix
        )
        helical_qe._data_model = helical_model

        helical_qe.set_enabled(True)
        helical_qe.in_queue = self.in_queue
        self.helical_qe = helical_qe

        advanced_connector_qe = AdvancedConnectorQueueEntry(
            self.get_view(), reference_image_collection, view_set_queue_entry=False
        )
        advanced_connector_qe.first_qe = mesh_qe
        advanced_connector_qe.second_qe = helical_qe
        advanced_connector_qe.set_enabled(True)

        self.enqueue(mesh_qe)
        self.enqueue(advanced_connector_qe)
        self.enqueue(helical_qe)

    def post_execute(self):
        if self.helical_qe:
            self.status = self.helical_qe.status
        else:
            self.status = self.mesh_qe
        BaseQueueEntry.post_execute(self)
