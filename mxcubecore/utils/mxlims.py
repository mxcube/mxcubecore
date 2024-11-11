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

import os
import json

from typing import Optional
from mxlims.pydantic import crystallography as mxmodel
from mxcubecore.model import queue_model_objects as qmo
from mxlims.pydantic import core


def create_mxexperiment(
    datamodel: qmo.TaskNode, **parameters
) -> mxmodel.MXExperiment:
    """Create MXExperiment mxlims record from datamodel

    Args:
        datamodel: QueueModelObject representing experiment
        uuid: String containing globally unique identifier
        **parameters: dict of parameters overriding/supplementing datamodel

    Returns:

    """
    sample = datamodel.get_sample_node()
    tracking_data = datamodel.tracking_data
    crystal = sample.crystals[0] if sample.crystals else None
    diffraction_plan = sample.diffraction_plan
    initpars = {"uuid": tracking_data.uuid}
    workflow_name = tracking_data.workflow_name
    if not workflow_name:
        if diffraction_plan:
            if hasattr(diffraction_plan, "experimentType"):
                workflow_name = diffraction_plan.experimentType
            else:
                workflow_name = diffraction_plan.get("experimentType")
    workflow_name = workflow_name or datamodel.experiment_type

    if diffraction_plan:
        # It is not clear if diffraction_plan is a dict or an object,
        # and if so which kind

        if hasattr(diffraction_plan, "aimedResolution"):
            resolution = diffraction_plan.aimedResolution
        else:
            resolution = diffraction_plan.get("aimedResolution")
        if resolution:
            initpars["expected_resolution"] = resolution

        if hasattr(diffraction_plan, "requiredCompleteness"):
            completeness = diffraction_plan.requiredCompleteness
        else:
            completeness = diffraction_plan.get("requiredCompleteness")
        if completeness:
            initpars["target_completeness"] = completeness

        if hasattr(diffraction_plan, "requiredMultiplicity"):
            multiplicity = diffraction_plan.requiredMultiplicity
        else:
            multiplicity = diffraction_plan.get("requiredMultiplicity")
        if multiplicity:
            initpars["target_multiplicity"] = multiplicity

    # Add MXSample and LogisticalSample

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

    sample = mxmodel.MXSample(**samplepars)
    initpars["sample"] = sample

    # LogisticalSample, not really modeled yet, so not much to put in
    crystal_uuid = crystal.crystal_uuid if crystal else None
    if crystal_uuid:
        logistical_sample = core.LogisticalSample(uuid=crystal_uuid)
    else:
        logistical_sample = core.LogisticalSample()
    logistical_sample.sample_ref = core.LogisticalSampleRef(target_uuid=sample.uuid)
    initpars["logistical_sample"] = logistical_sample
    sample.logistical_sample_refs.append(
        core.LogisticalSampleRef(target_uuid=logistical_sample.uuid)
    )
    initpars["logistical_sample_ref"] = core.LogisticalSampleRef(
        target_uuid=logistical_sample.uuid
    )

    initpars.update(parameters)
    result = mxmodel.MXExperiment(**initpars)
    return result


def add_sweep(
    mxexperiment: mxmodel.MXExperiment,
    sweep: qmo.DataCollection,
    **parameters: dict,
) -> None:
    """

    Args:
        mxexperiment: container MXExperiment
        sweep: DataCollection queue_model_object to add
        uuid: String containing globally unique identifier
        **parameters: dict of parameters overriding/supplementing datamodel

    Returns:

    """
    """Add CollectionSweep record to MXExperiment"""

    # ALwsy true in MXCuBE
    SCAN_AXIS = "omega"

    acquisition = sweep.acquisitions[0]
    path_template = acquisition.path_template
    acqparams = acquisition.acquisition_parameters

    sweep_params = {
        "source_ref": mxmodel.MXExperimentRef(target_uuid=mxexperiment.uuid),
        "scan_axis": SCAN_AXIS,
        "exposure_time": acqparams.exp_time,
        "image_width": acqparams.osc_range,
        "energy": acqparams.energy,
        "transmission": acqparams.transmission,
        "resolution": acqparams.resolution,
        "detector_binning_mode": acqparams.detector_binning_mode,
        "detector_roi_mode": acqparams.detector_roi_mode,
        "overlap": acqparams.overlap,
        "number_triggers": acqparams.num_triggers,
        "number_images_per_trigger": acqparams.num_images_per_trigger,
        "prefix": path_template.get_prefix(),
        "file_type": path_template.suffix,
        "filename_template": path_template.get_image_file_name(),
        "path": path_template.directory,
    }

    sweep_params["axis_positions_start"] = startpos = dict(
        tpl
        for tpl in acqparams.centred_position.as_dict().items()
        if tpl[1] is not None
    )
    startpos[SCAN_AXIS] = acqparams.osc_start
    startpos["detector_distance"] = acqparams.detector_distance

    detector_distance = parameters.pop("detector_distance", None)
    if detector_distance is not None:
        startpos["detector_distance"] = detector_distance
    scan = mxmodel.Scan(
        scan_position_start=startpos[SCAN_AXIS],
        first_image_number=acqparams.first_image,
        number_images=acqparams.num_images,
        ordinal=1,
    )
    sweep_params["scans"] = [scan]
    scan_pos_end = parameters.pop("scan_position_end", None)
    sweep_params["axis_positions_end"] = {SCAN_AXIS: scan_pos_end}

    # NBNB interleaving, split sweeps, split characterisation
    # NBNB cxheck final omega value against start
    # NBNB how do we get the detector type?
    # NBNB do we use MXCuBE axis names or standardised names?
    # detector_type, ,, ,
    # , axis_positions_end,
    # NBNB change from QMO to dict input

    sweep_params.update(parameters)
    mxexperiment.results.append(mxmodel.CollectionSweep(**sweep_params))


def export_mxexperiment(
    mxexperiment: mxmodel.MXExperiment, path_template: Optional[qmo.PathTemplate]=None
):
    """Export MXExperiment mxlims record to JSON file"""
    if path_template is None:
        path = mxexperiment.results[-1].path
        file_name = "MXExperiment.json"
    else:
        template = "MXExperiment_%s_%s.json"
        file_name = template % (path_template.get_prefix(), path_template.run_number)
        path = os.path.join(path_template.directory, file_name)
    path = os.path.join(path, file_name)
    print("@~@~ WRITING TO", path)
    with open(path, "w") as fp:
        json.dump(mxexperiment.model_dump(), fp)
