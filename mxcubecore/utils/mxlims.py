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
from datetime import datetime

from typing import Optional
from uuid import uuid1

from mxcubecore.HardwareObjects.Native import xmlrpc_prefix
from mxlims.pydantic import mxmodel
from mxcubecore.model import queue_model_objects as qmo


def create_mxrecord(
    sample: qmo.Sample,
    tracking_data: dict,
    start_time: datetime = None,
    end_time: datetime = None,
    job_status: str = None,
    **parameters
) -> mxmodel.MxExperimentMessage:
    """Create MxExperimentMessage mxlims record from datamodel

    Args:
        sample: QueueModelObject representing sample
        tracking_data: Dictionary with uuid etc. connecting sweeps and workflows
        start_time: Experiment start time
        end_time: Experiment end time
        job_status: Job status (enumerated string)
        **parameters: dict of parameters overriding/supplementing MxExperimentData

    Returns:

    """
    start_time = start_time or datetime.now()
    crystal = sample.crystals[0] if sample.crystals else None
    diffraction_plan = sample.diffraction_plan
    jobuuid = tracking_data.uuid
    workflow_name = tracking_data.workflow_name
    if not workflow_name:
        if diffraction_plan:
            if hasattr(diffraction_plan, "experimentType"):
                workflow_name = diffraction_plan.experimentType
            else:
                workflow_name = diffraction_plan.get("experimentType")
    if not workflow_name:
        workflow_name = parameters.pop("experiment_type", None)
    jobpars = {"experiment_strategy": workflow_name}

    if diffraction_plan:
        # It is not clear if diffraction_plan is a dict or an object,
        # and if so which kind

        if hasattr(diffraction_plan, "aimedResolution"):
            resolution = diffraction_plan.aimedResolution
        else:
            resolution = diffraction_plan.get("aimedResolution")
        if resolution:
            jobpars["expected_resolution"] = resolution

        if hasattr(diffraction_plan, "requiredCompleteness"):
            completeness = diffraction_plan.requiredCompleteness
        else:
            completeness = diffraction_plan.get("requiredCompleteness")
        if completeness:
            jobpars["target_completeness"] = completeness

        if hasattr(diffraction_plan, "requiredMultiplicity"):
            multiplicity = diffraction_plan.requiredMultiplicity
        else:
            multiplicity = diffraction_plan.get("requiredMultiplicity")
        if multiplicity:
            jobpars["target_multiplicity"] = multiplicity
    jobpars.update(parameters)
    jobdata = mxmodel.MxExperimentData(**jobpars)

    # CrystallographicSample
    crystal_form = None
    samplepars = {}
    samplepars["name"] = (
        sample.name or sample.get_name() or (crystal and crystal.acronym)
    )
    if crystal:
        space_group_name = crystal.space_group
        dd1 = {
            "a": crystal.cell_a,
            "b": crystal.cell_b,
            "c": crystal.cell_c,
            "alpha": crystal.cell_alpha,
            "beta": crystal.cell_beta,
            "gamma": crystal.cell_gamma,
        }
        unit_cell = mxmodel.UnitCell(**dd1) if  all(dd1.values()) else None
        if space_group_name or unit_cell:
            samplepars["crystal_form"] = mxmodel.CrystalForm(
                space_group_name=space_group_name, crystal_form=crystal_form
            )

        # LogisticalSample, not really modeled yet, so not much to put in
        crystal_uuid = crystal.crystal_uuid
    else:
        crystal_uuid = None
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
    sampledata = mxmodel.CrystallographicSampleData(**samplepars)
    sample = mxmodel.CrystallographicSample(uuid=uuid1(), data=sampledata)

    crystaldata = mxmodel.CrystalData()
    if crystal_uuid:
        logistical_sample = mxmodel.Crystal(
            uuid=crystal_uuid, sample_id=sample.uuid, data=crystaldata
        )
    else:
        logistical_sample = mxmodel.Crystal(uuid=uuid1(), sample_id=sample.uuid, data=crystaldata)

    experiment = mxmodel.MxExperiment(
        uuid=jobuuid,
        data=jobdata,
        start_time=start_time,
        end_time=end_time,
        job_status=job_status,
        sample_id=sample.uuid,
        logistical_sample_id=logistical_sample.uuid
    )
    #
    return mxmodel.MxExperimentMessage(
        job=experiment, sample=sample, logistical_sample=logistical_sample
    )


def add_data_collection(
    mxrecord: mxmodel.MxExperimentMessage,
    data_collection: qmo.DataCollection,
    **parameters: dict,
) -> None:
    """Add CollectionSweep record to MxExperiment in mxrecord

    Args:
        mxrecord: container MxExperimentMessage
        data_collection: DataCollection queue_model_object to add
        **parameters: dict of parameters overriding/supplementing MxlimsData

    Returns:

    """

    # ALwsy true in MXCuBE
    SCAN_AXIS = "omega"
    mxexperiment = mxrecord.job

    acquisition = data_collection.acquisitions[0]
    path_template = acquisition.path_template
    acqparams = acquisition.acquisition_parameters
    tracking_data = data_collection.tracking_data
    startpos = dict(
        tpl
        for tpl in acqparams.centred_position.as_dict().items()
        if tpl[1] is not None
    )
    axis_pos_start = acqparams.osc_start
    axis_pos_end = axis_pos_start + acqparams.num_images * acqparams.osc_range
    startpos[SCAN_AXIS] = axis_pos_start
    startpos["detector_distance"] = acqparams.detector_distance
    detector_distance = parameters.pop("detector_distance", None)
    if detector_distance is not None:
        startpos["detector_distance"] = detector_distance
    scan = mxmodel.Scan(
        scan_position_start=axis_pos_start,
        first_image_number=acqparams.first_image,
        number_images=acqparams.num_images,
        ordinal=tracking_data.scan_number or 0,
    )

    sweep_id = tracking_data.sweep_id
    sweep = None
    if not mxexperiment.results:
        mxexperiment.results = []
    for dataset in mxexperiment.results:
        if str(dataset.uuid) == sweep_id:
            sweep = dataset
            break
    if sweep:
        # This is a scan for an existing sweep. Add ane update
        sweep.data.scans.append(scan)
        sweep.data.axis_positions_start[SCAN_AXIS] = min(
            sweep.data.axis_positions_start[SCAN_AXIS], axis_pos_start
        )
        sweep.data.axis_positions_end[SCAN_AXIS] = max(
            sweep.data.axis_positions_end[SCAN_AXIS], axis_pos_end
        )

    else:
        sweep_params = {
            "uuid": sweep_id or tracking_data.uuid,
            "source_id": mxexperiment.uuid,
            "logistical_sample_id": mxrecord.logistical_sample.uuid,
            "role": tracking_data.role,
        }
        sweepdata = {
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
            "axis_positions_start": startpos,
            "scans": [scan],
        }

        sweepdata["axis_positions_end"] = {SCAN_AXIS: axis_pos_end}

        # NBNB how do we get the detector type?
        # NBNB do we use MXCuBE axis names or standardised names?

        sweepdata.update(parameters)
        dataset = mxmodel.CollectionSweep(
            data=mxmodel.CollectionSweepData(**sweepdata),
            **sweep_params
        )
        mxexperiment.results.append(dataset)



def export_mxrecord(
    mxrecord: mxmodel.MxExperimentMessage,
    path_template: Optional[qmo.PathTemplate] = None
):
    """Export MxExperiment mxlims record to JSON file"""
    if path_template is None:
        path = mxrecord.job.results[-1].data.path
        file_name = "MxExperiment.json"
    else:
        template = "MXExperiment_%s_%s.json"
        file_name = template % (path_template.get_prefix(), path_template.run_number)
        path = os.path.join(path_template.directory, file_name)
    path = os.path.join(path, file_name)
    print("@~@~ WRITING JSON TO", path)
    with open(path, "w") as fp:
        fp.write(mxrecord.model_dump_json(indent=4, exclude_none=True))
