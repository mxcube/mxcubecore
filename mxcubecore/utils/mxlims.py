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

import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from mxlims.pydantic.datatypes import Scan, UnitCell
from mxlims.pydantic.objects.CollectionSweep import CollectionSweep
from mxlims.pydantic.objects.CrystallographicSample import CrystallographicSample
from mxlims.pydantic.objects.MxExperiment import MxExperiment

from mxcubecore.model import queue_model_objects as qmo


def make_mx_experiment(  # noqa: C901
    sample: qmo.Sample,
    tracking_data: qmo.TrackingData,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    job_status: Optional[str] = None,
    **parameters,
) -> Tuple[MxExperiment, CrystallographicSample]:
    """Create MxExperiment record from datamodel

    Args:
        sample: QueueModelObject representing sample
        tracking_data: Dictionary with uuid etc. connecting sweeps and workflows
        start_time: Experiment start time
        end_time: Experiment end time
        job_status: Job status (enumerated string)
        **parameters: dict of parameters overriding/supplementing MxExperimentData

    Returns:

    """
    crystal = sample.crystals[0] if sample.crystals else None
    diffraction_plan = sample.diffraction_plan
    sampledata = {
        "name": sample.name or sample.get_name() or (crystal and crystal.acronym),
    }

    jobdata = {
        "start_time": start_time or datetime.now(),  # noqa: DTZ005
        "end_time": end_time,
        "job_status": job_status,
        "uuid":tracking_data.uuid,
    }
    workflow_name = tracking_data.workflow_name
    if diffraction_plan and not workflow_name:
        if hasattr(diffraction_plan, "experimentType"):
            workflow_name = diffraction_plan.experimentType
        else:
            workflow_name = diffraction_plan.get("experimentType")
    if not workflow_name:
        workflow_name = parameters.pop("experiment_type", None)

    jobdata["experiment_strategy"] = workflow_name

    if diffraction_plan:
        # It is not clear if diffraction_plan is a dict or an object,
        # and if so which kind

        if hasattr(diffraction_plan, "aimedResolution"):
            resolution = diffraction_plan.aimedResolution
        else:
            resolution = diffraction_plan.get("aimedResolution")
        if resolution:
            jobdata["expected_resolution"] = resolution

        if hasattr(diffraction_plan, "requiredCompleteness"):
            completeness = diffraction_plan.requiredCompleteness
        else:
            completeness = diffraction_plan.get("requiredCompleteness")
        if completeness:
            jobdata["target_completeness"] = completeness

        if hasattr(diffraction_plan, "requiredMultiplicity"):
            multiplicity = diffraction_plan.requiredMultiplicity
        else:
            multiplicity = diffraction_plan.get("requiredMultiplicity")
        if multiplicity:
            jobdata["target_multiplicity"] = multiplicity
    jobdata.update(parameters)

    # CrystallographicSample
    if crystal:
        space_group_name = crystal.space_group
        if space_group_name:
            sampledata["space_group_name"] = space_group_name
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
            sampledata["unit_cell"] = unit_cell

        # LogisticalSample, not really modeled yet, so not much to put in
        crystal_uuid = crystal.crystal_uuid
        if crystal_uuid:
            jobdata["logistical_sample_id"] = crystal_uuid

    # Set parameters from diffraction plan
    if diffraction_plan:
        # It is not clear if diffraction_plan is a dict or an object,
        # and if so which kind
        if hasattr(diffraction_plan, "radiationSensitivity"):
            radiation_sensitivity = diffraction_plan.radiationSensitivity
        else:
            radiation_sensitivity = diffraction_plan.get("radiationSensitivity")
        if radiation_sensitivity:
            sampledata["radiation_sensitivity"] = radiation_sensitivity

    sample = CrystallographicSample(
        uuid=uuid.uuid1(), **sampledata,
    )
    experiment = MxExperiment(**jobdata)
    return experiment, sample

def add_data_collection(
    mx_experiment: MxExperiment,
    data_collection: qmo.DataCollection,
    **parameters: dict,
) -> Optional[CollectionSweep]:
    """Make CollectionSweep record from DataCollection

    Args:
        mx_experiment: container MxExperimentMessage
        data_collection: DataCollection queue_model_object to add
        **parameters: dict of parameters overriding/supplementing MxlimsData

    Returns:

    """
    scan_axis = "omega"

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
    for dataset in mx_experiment.results:
        if str(dataset.uuid) == sweep_id:
            sweep = dataset
            break
    if sweep:
        # This is a scan for an existing sweep. Add and update
        sweep.scans.append(scan)
        sweep.axis_positions_start[scan_axis] = min(
            sweep.axis_positions_start[scan_axis], axis_pos_start,
        )
        sweep.axis_positions_end[scan_axis] = max(
            sweep.axis_positions_end[scan_axis], axis_pos_end,
        )
        # No new Collection Sweep made
        return None

    else:  # noqa: RET505
        sweepdata = {
            "uuid": sweep_id or tracking_data.uuid,
            "source_id": mx_experiment.uuid,
            "logistical_sample_id": mx_experiment.logistical_sample_id,
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
        return CollectionSweep(**sweepdata)


def export_mxjob(
    mxlims_job: MxExperiment,
    path_template: Optional[qmo.PathTemplate] = None,
):
    print ('@~@~ mro', mxlims_job.__class__.__mro__)
    """Export MxExperiment mxlims record to JSON file"""
    for tag, val in mxlims_job._objects_by_id.items():
        print (f'###############################\n\n\n {tag}\n')
        for tag2, val2 in val.items():
            print ('\n-----------\n{tag2}\n')
            print(
                val2.model_dump_json(
                indent=4, by_alias=True, exclude_none=True, serialize_as_any=True
                )
            )
    if path_template is None:
        path = Path(mxlims_job.results[-1].path)
        file_name = "MxExperiment.json"
    else:
        template = "MXExperiment_%s_%s.json"
        file_name = template % (path_template.get_prefix(), path_template.run_number)
        path = Path(path_template.directory) / file_name
    path = path / file_name
    print("WRITING MXLIMS JSON TO", path)
    path.write_text(
        mxlims_job.model_dump_json(
            indent=4, by_alias=True, exclude_none=True, serialize_as_any=True
        )
    )
