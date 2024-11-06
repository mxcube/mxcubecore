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

    # Add MXSample and LogisticalSample
    sample = datamodel.get_sample_node()
    crystal = sample.crystals[0] if sample.crystals else None
    diffraction_plan = sample.diffraction_plan

    # LogisticalSample, not really modeled yet, so not much to put in
    crystal_uuid = crystal.uuid if crystal else None
    if crystal_uuid:
        logistical_sample = mxmodel.LogisticalSample(uuid=crystal_uuid)
    else:
        logistical_sample = mxmodel.LogisticalSample()
    result.logistical_sample = logistical_sample

    # MXSample
    samplepars = {}
    samplepars["name"] = (
        sample.name or sample.get_name() or (crystal and crystal.acronym)
    )
    if crystal:
        space_group_name = crystal.space_group
        if space_group_name:
            samplepars["space_group_name"] = space_group_name
        dd1 = {
            "a": crystal.cell_a,
            "b": crystal.cell_b,
            "c": crystal.cell_c,
            "alpha": crystal.cell_alpha,
            "beta": crystal.cell_beta,
            "gamma": crystal.cell_gamma,
        }
        if all(dd1.values()):
            samplepars["unit_cell"] = mxmodel.UnitCell(**dd1)

    # Set parameters from diffraction plan
    if diffraction_plan:
        # It is not clear if diffraction_plan is a dict or an object,
        # and if so which kind
        if hasattr(diffraction_plan, "radiationSensitivity"):
            radiation_sensitivity = diffraction_plan.radiationSensitivity
        else:
            radiation_sensitivity = diffraction_plan.get("radiationSensitivity")
        if radiation_sensitivity:
            samplepars["radiation_sensitivity"] = radiation_sensitivity

        if hasattr(diffraction_plan, "aimedResolution"):
            resolution = diffraction_plan.aimedResolution
        else:
            resolution = diffraction_plan.get("aimedResolution")
        if resolution:
            samplepars["expected_resolution"] = resolution

        if hasattr(diffraction_plan, "requiredCompleteness"):
            completeness = diffraction_plan.requiredCompleteness
        else:
            completeness = diffraction_plan.get("requiredCompleteness")
        if completeness:
            samplepars["target_completeness"] = completeness

        if hasattr(diffraction_plan, "requiredMultiplicity"):
            multiplicity = diffraction_plan.requiredMultiplicity
        else:
            multiplicity = diffraction_plan.get("requiredMultiplicity")
        if multiplicity:
            samplepars["target_multiplicity"] = multiplicity
    sample = mxmodel.MXSample(**samplepars)

    # Create MXExperiment
    if isinstance(datamodel, qmo.GphlWorkflow):
        # Initialise MXExperiment from GPhL workflow
        prefix = "GPhL."
        settings = datamodel.strategy_settings
        short_name = settings.get("short_name", settings.get("strategy_type"))
        result = MXExperiment(
            uuid=datamodel.enactment_id,
            experiment_strategy=prefix + short_name,
            sample=sample,
            logistical_sample=logistical_sample,
        )

    elif isinstance(datamodel, qmo.DataCollection):
        # Initialise MXExperiment from single Acquisition
        if diffraction_plan:
            if hasattr(diffraction_plan, "experimentType"):
                experiment_strategy = diffraction_plan.experimentType
        else:
            experiment_strategy = diffraction_plan.get("experimentType")
        experiment_strategy = experiment_strategy or datamodel.experiment_type

        result = MXExperiment(
            experiment_strategy=experiment_strategy,
            sample=sample,
            logistical_sample=logistical_sample,
        )

    else:
        raise ValueError("Unsupported queue_model_object: %s" % self)

    #
    return result


def add_sweep(mxexperiment: mxmodel.MXExperiment, acquisition: qmo.Acquisition):
    """Add CollectionSweep record to MXExperiment"""
    pass


def export_mxexperiment(mxexperiment: mxmodel.MXExperiment, datamodel: qmo.TaskNode):
    """Export MXExperiment mxlims record to JSON file"""
    pass
