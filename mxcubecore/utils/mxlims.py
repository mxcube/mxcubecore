#! /usr/bin/env python
# encoding: utf-8
#
"""

License:

This file is part of the MXLIMS collaboration.

MXLIMS models and code are free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

MXLIMS is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with MXLIMS. If not, see <https://www.gnu.org/licenses/>.
"""

__copyright__ = """ Copyright © 2024 -  2024 MXLIMS collaboration."""
__author__ = "rhfogh"
__date__ = "05/11/2024"

from mxlims.pydantic import crystallography as mxmodel
from mxcubecore.model import queue_model_objects as qmo
from mxlims.pydantic.crystallography import MXExperiment


def create_mxexperiment(datamodel: qmo.TaskNode) -> mxmodel.MXExperiment:
    """Create MXExperiment mxlims record from datamodel"""

    sample = datamodel.get_sample_node()

    if isinstance(datamodel, qmo.GphlWorkflow):
        # Initialise MXExperiment from GPhL workflow
        prefix = "GPhL."
        settings = datamodel.strategy_settings
        short_name = settings.get("short_name", settings.get("strategy_type"))
        result = MXExperiment(experiment_strategy = prefix+short_name)
    elif isinstance(datamodel, qmo.DataCollection):
        # Initialise MXExperimnent from single Acquisition
        result = MXExperiment(experiment_strategy = datamodel.experiemnt_type)
    else:
        raise ValueError("Unsupported queue_model_object: %s" % self)
    #
    return result

def add_sweep(mxexperiment: mxmodel.MXExperiment, acquisition: qmo.Acquisition):
    """Add CollectionSweep record to MXExperiment"""
    pass

def export_mxexperiment(mxexperiment: mxmodel.MXExperiment,
                        datamodel: qmo.TaskNode):
    """Export MXExperiment mxlims record to JSON file"""
    pass