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
from datetime import datetime
from typing import Optional
from uuid import uuid1

from mxlims.pydantic.datatypes import Scan, UnitCell
from mxlims.pydantic.messages import JobMessage
from mxlims.pydantic.objects import CollectionSweep, MxExperiment
from mxlims.pydantic.rawobjects import RawCrystallographicSample

from mxcubecore.model import queue_model_objects as qmo


def create_mxrecord(
    sample: qmo.Sample,
    tracking_data: qmo.TrackingData,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    job_status: Optional[str] = None,
    **parameters,
) -> JobMessage:
    """Create JobMessage record from datamodel

    Args:
        sample: QueueModelObject representing sample
        tracking_data: Dictionary with uuid etc. connecting sweeps and workflows
        start_time: Experiment start time
        end_time: Experiment end time
        job_status: Job status (enumerated string)
        **parameters: dict of parameters overriding/supplementing MxExperimentData

    Returns:

    """
    start_time = start_time or datetime.now()  # noqa: DTZ005
    crystal = sample.crystals[0] if sample.crystals else None
    diffraction_plan = sample.diffraction_plan
    job_uuid = tracking_data.uuid
    workflow_name = tracking_data.workflow_name
    if diffraction_plan and not workflow_name:
        if hasattr(diffraction_plan, "experimentType"):
            workflow_name = diffraction_plan.experimentType
        else:
            workflow_name = diffraction_plan.get("experimentType")
    if not workflow_name:
        workflow_name = parameters.pop("experiment_type", None)
    job_pars = {"experiment_strategy": workflow_name}

    if diffraction_plan:
        # It is not clear if diffraction_plan is a dict or an object,
        # and if so which kind

        if hasattr(diffraction_plan, "aimedResolution"):
            resolution = diffraction_plan.aimedResolution
        else:
            resolution = diffraction_plan.get("aimedResolution")
        if resolution:
            job_pars["expected_resolution"] = resolution

        if hasattr(diffraction_plan, "requiredCompleteness"):
            completeness = diffraction_plan.requiredCompleteness
        else:
            completeness = diffraction_plan.get("requiredCompleteness")
        if completeness:
            job_pars["target_completeness"] = completeness

        if hasattr(diffraction_plan, "requiredMultiplicity"):
            multiplicity = diffraction_plan.requiredMultiplicity
        else:
            multiplicity = diffraction_plan.get("requiredMultiplicity")
        if multiplicity:
            job_pars["target_multiplicity"] = multiplicity
    job_pars.update(parameters)

    # CrystallographicSample
    sample_pars = {
        "name": sample.name or sample.get_name() or (crystal and crystal.acronym),
    }
    if crystal:
        space_group_name = crystal.space_group
        if space_group_name:
            sample_pars["space_group_name"] = space_group_name
        dd1 = {
            "a": crystal.cell_a,
            "b": crystal.cell_b,
            "c": crystal.cell_c,
            "alpha": crystal.cell_alpha,
            "beta": crystal.cell_beta,
            "gamma": crystal.cell_gamma,
        }
        unit_cell = UnitCell.UnitCell(**dd1) if  all(dd1.values()) else None
        if unit_cell:
            sample_pars["unit_cell"] = unit_cell

        # LogisticalSample, not really modeled yet, so not much to put in
        crystal_uuid = crystal.crystal_uuid
        if crystal_uuid:
            job_pars["logisticalSampleId"] = crystal_uuid

    # Set parameters from diffraction plan
    if diffraction_plan:
        # It is not clear if diffraction_plan is a dict or an object,
        # and if so which kind
        if hasattr(diffraction_plan, "radiationSensitivity"):
            radiation_sensitivity = diffraction_plan.radiationSensitivity
        else:
            radiation_sensitivity = diffraction_plan.get("radiationSensitivity")
        if radiation_sensitivity:
            sample_pars["radiation_sensitivity"] = radiation_sensitivity
    sample = RawCrystallographicSample.RawCrystallographicSample(
        uuid=uuid1(), **sample_pars,
    )

    experiment = MxExperiment.MxExperiment(
        uuid=job_uuid,
        start_time=start_time,
        end_time=end_time,
        job_status=job_status,
        sample_id=sample.uuid,
        **job_pars,
    )
    return JobMessage.JobMessage(job=experiment, sample=sample)


def add_data_collection(
    mxrecord: JobMessage.JobMessage,
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

    # Always true in MXCuBE
    scan_axis = "omega"
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
    startpos[scan_axis] = axis_pos_start
    startpos["detector_distance"] = acqparams.detector_distance
    detector_distance = parameters.pop("detector_distance", None)
    if detector_distance is not None:
        startpos["detector_distance"] = detector_distance
    scan = Scan.Scan(
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
        sweep.scans.append(scan)
        sweep.axis_positions_start[scan_axis] = min(
            sweep.axis_positions_start[scan_axis], axis_pos_start,
        )
        sweep.axis_positions_end[scan_axis] = max(
            sweep.axis_positions_end[scan_axis], axis_pos_end,
        )

    else:
        sweepdata = {
            "uuid": sweep_id or tracking_data.uuid,
            "source_id": mxexperiment.uuid,
            "logistical_sample_id": mxexperiment.logistical_sample_id,
            "role": tracking_data.role,
            "scan_axis": scan_axis,
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

        sweepdata["axis_positions_end"] = {scan_axis: axis_pos_end}

        # NBNB how do we get the detector type?
        # NBNB do we use MXCuBE axis names or standardised names?

        sweepdata.update(parameters)
        dataset = CollectionSweep.CollectionSweep(**sweepdata)
        mxexperiment.results.append(dataset)



def export_mxrecord(
    mxrecord: JobMessage.JobMessage,
    path_template: Optional[qmo.PathTemplate] = None,
):
    """Export MxExperiment mxlims record to JSON file"""
    if path_template is None:
        path = mxrecord.job.results[-1].path
        file_name = "MxExperiment.json"
    else:
        template = "MXExperiment_%s_%s.json"
        file_name = template % (path_template.get_prefix(), path_template.run_number)
        path = os.path.join(path_template.directory, file_name)
    path = os.path.join(path, file_name)
    print("WRITING MXLIMS JSON TO", path)
    with open(path, "w") as fp:
        fp.write(mxrecord.model_dump_json(indent=4, by_alias=True, exclude_none=True))
