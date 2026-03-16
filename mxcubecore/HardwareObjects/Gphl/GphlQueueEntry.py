#
#  Project name: MXCuBE
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

"""
Module contains Gphl specific queue entries
"""

import logging

from mxcubecore import HardwareRepository as HWR
from mxcubecore.queue_entry.base_queue_entry import BaseQueueEntry
from mxcubecore.utils import mxutils

__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "queue"


class GphlWorkflowQueueEntry(BaseQueueEntry):
    def execute(self):
        BaseQueueEntry.execute(self)

        msg = "Starting GPhL workflow (%s), please wait." % (
            self.get_data_model().strategy_name
        )
        logging.getLogger("user_level_log").info(msg)
        HWR.beamline.gphl_workflow.execute()

    def pre_execute(self):
        BaseQueueEntry.pre_execute(self)
        if not HWR.beamline.gphl_workflow.is_ready():
            logging.getLogger("user_level_log").warning(
                "WARNING: GPhL workflow was not ready - cleaning up"
            )
            HWR.beamline.gphl_workflow.post_execute()
        HWR.beamline.gphl_workflow.pre_execute(self)
        logging.getLogger("HWR").debug("Done GphlWorkflowQueueEntry.pre_execute")

    def post_execute(self):
        self.finalize_mxlims()
        BaseQueueEntry.post_execute(self)
        msg = "Finishing GPhL workflow (%s)" % (self.get_data_model().strategy_name)
        logging.getLogger("user_level_log").info(msg)
        HWR.beamline.gphl_workflow.post_execute()

    def stop(self):
        HWR.beamline.gphl_workflow.workflow_aborted("Dummy", "Dummy")
        BaseQueueEntry.stop(self)
        logging.getLogger("user_level_log").info(
            "MXCuBE aborting current GPhL workflow"
        )
        self.get_view().setText(1, "Stopped")

    def init_mxlims(self):
        """Initialise MXLIMS MxExperimentMessage if it is not already set"""

        if self.get_mxlims_job() is None:
            data_model = self.get_data_model()
            self._mxlims_job, mxlims_sample = mxutils.make_mx_experiment(
                sample=data_model.get_sample_node(),
                tracking_data=data_model.tracking_data,
                measured_flux=HWR.beamline.flux.get_value(),
            )
    def finalize_mxlims(self):
        """Finalize MXLIMS MxExperimentMessage setting information  at end of execution
        """
        mx_experiment = self.get_mxlims_job()
        if not mx_experiment:
            # Only happens if there was an error upstream anyway
            return
        data_model = self.get_data_model()
        workflow_name = data_model.workflow_name
        if not mx_experiment.experiment_strategy:
            mx_experiment.experiment_strategy = workflow_name
        mx_experiment.radiation_dose = data_model.total_radiation_dose
        mx_experiment.selected_space_group_name = data_model.space_group
        cell_parameters = data_model.cell_parameters
        if cell_parameters:
            unit_cell = mxutils.make_unit_cell(*cell_parameters)
            if unit_cell:
                mx_experiment.selected_unit_cell = unit_cell
        extensions = mx_experiment.extensions
        if not extensions:
            extensions = mx_experiment.extensions = {}
        gphl_extensions = extensions.setdefault(data_model.GPHL_WORKFLOW_EXTENSION, {})
        gphl_extensions.update(data_model.strategy_options)
        gphl_extensions["experiment_strategy"] = workflow_name

