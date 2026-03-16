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
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Optional, Tuple, Union

from mxlims.mxpydantic.datatypes.Scan import Scan
from mxlims.mxpydantic.datatypes.UnitCell import UnitCell
from mxlims.mxpydantic.messages.MxlimsMessage import MxlimsMessage
from mxlims.mxpydantic.objects.CollectionSweep import CollectionSweep
from mxlims.mxpydantic.objects.Crystal import Crystal
from mxlims.mxpydantic.objects.MacromoleculeSample import MacromoleculeSample
from mxlims.mxpydantic.objects.MxExperiment import MxExperiment
from mxlims.mxpydantic.objects.MxProcessing import MxProcessing

from mxcubecore.model import queue_model_objects as qmo


def make_mx_experiment(  # noqa: C901, PLR0912, PLR0915
    sample: qmo.Sample,
    tracking_data: qmo.TrackingData,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    job_status: Optional[str] = None,
    **parameters,
) -> Tuple[MxExperiment, MacromoleculeSample]:
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
    if end_time:
        end_time = end_time.astimezone(timezone.utc)
    if start_time:
        start_time = start_time.astimezone(timezone.utc)
    else:
        start_time = datetime.now(timezone.utc)
    crystal = sample.crystals[0] if sample.crystals else None
    diffraction_plan = sample.diffraction_plan
    sampledata = {
        "name": sample.name or sample.get_name() or (crystal and crystal.acronym),
    }

    jobdata = {
        "start_time": start_time,
        "end_time": end_time,
        "job_status": job_status,
        "uuid": tracking_data.uuid,
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
            jobdata["expected_space_group_name"] = space_group_name
        unit_cell = make_unit_cell(
            crystal.cell_a,
            crystal.cell_b,
            crystal.cell_c,
            crystal.cell_alpha,
            crystal.cell_beta,
            crystal.cell_gamma,
        )
        if unit_cell:
            jobdata["expected_unit_cell"] = unit_cell

    # Set parameters from diffraction plan
    if diffraction_plan:
        # It is not clear if diffraction_plan is a dict or an object,
        # and if so which kind
        if hasattr(diffraction_plan, "radiationSensitivity"):
            radiation_sensitivity = diffraction_plan.radiationSensitivity
        else:
            radiation_sensitivity = diffraction_plan.get("radiationSensitivity")
        if radiation_sensitivity:
            jobdata["radiation_sensitivity"] = radiation_sensitivity

    sample = MacromoleculeSample(uuid=uuid.uuid1(), **sampledata)

    if crystal:
        # Crystal.uuid is unfortunately not a uuid, but a name string
        crystal_name = crystal.crystal_uuid
        if crystal_name:
            mxlims_crystal = Crystal(
                uuid=uuid.uuid1(), sample_id=sample.uuid, name=crystal_name
            )
            jobdata["logistical_sample_id"] = mxlims_crystal.uuid
    jobdata["sample_id"] = sample.uuid
    experiment = MxExperiment(**jobdata)
    return experiment, sample

def make_unit_cell(a, b, c, alpha, beta, gamma):
    """Make UnitCell object"""
    dd1 = {
        "a": a,
        "b": b,
        "c": c,
        "alpha": alpha,
        "beta": beta,
        "gamma": gamma,
    }
    unit_cell = UnitCell(**dd1) if all(dd1.values()) else None
    return unit_cell

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
    scan = Scan(
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
            sweep.axis_positions_start[scan_axis],
            axis_pos_start,
        )
        sweep.axis_positions_end[scan_axis] = max(
            sweep.axis_positions_end[scan_axis],
            axis_pos_end,
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
            "axis_positions_end": {scan_axis: axis_pos_end},
        }

        # NBNB how do we get the detector type?
        # NBNB do we use MXCuBE axis names or standardised names?

        sweepdata.update(parameters)
        return CollectionSweep(**sweepdata)


def export_mxjob(  # noqa: C901
    mxlims_job: Union[MxExperiment, MxProcessing],
    path_template: Optional[qmo.PathTemplate] = None,
):
    """Export MxExperiment mxlims record with linked objects to JSON file"""
    if path_template:
        template = "MXExperiment_%s_%s.json"
        file_name = template % (path_template.get_prefix(), path_template.run_number)
        path = Path(path_template.directory) / file_name
    else:
        path = None

    jobs = [mxlims_job]
    objects_by_uuid = {}
    for job in jobs:
        objects_by_uuid[job.uuid] = job
        jobs.extend(job.subjobs)
        for obj in job.results:
            objects_by_uuid[obj.uuid] = obj
            path = Path(obj.path) / "MxExperiment.json"
        for tag in ("template_data", "reference_data"):
            for obj in getattr(job, tag):
                objects_by_uuid[obj.uuid] = obj
        if hasattr(job, "input_data"):
            for obj in job.input_data:
                objects_by_uuid[obj.uuid] = obj
    for obj in list(objects_by_uuid.values()):
        sample = getattr(obj, "sample", None)
        if sample is not None:
            objects_by_uuid[sample.uuid] = sample
        logistical_sample = getattr(obj, "logistical_sample", None)
        if logistical_sample is not None:
            objects_by_uuid[logistical_sample.uuid] = logistical_sample
            sample = getattr(logistical_sample, "sample", None)
            if sample is not None:
                objects_by_uuid[sample.uuid] = sample
    if path is None:
        logging.getLogger("user_level_log").debug(
            "Job has no results; MXLIMS not exported"
        )
    else:
        message = MxlimsMessage.from_pydantic_objects(list(objects_by_uuid.values()))
        print("WRITING MXLIMS JSON TO", path)  # noqa: T201
        message.export_message(path)


if __name__ == "__main__":
    # Test file loading
    from argparse import ArgumentParser, RawTextHelpFormatter

    parser = ArgumentParser(
        prog="generate_mxlims.py",
        formatter_class=RawTextHelpFormatter,
        prefix_chars="--",
        description="""
MXLIMS code generation. Assumes standard directory structure""",
    )

    parser.add_argument(
        "--filename",
        metavar="filename",
        default=None,
        help="Input file\n",
    )

    argsobj = parser.parse_args()
    options_dict = vars(argsobj)

    message = MxlimsMessage.from_message_file(Path(options_dict["filename"]))
    text = message.model_dump_json(
        indent=4,
        by_alias=True,
        exclude_none=True,
        serialize_as_any=True,
    )
    Path(options_dict["filename"] + "_out").write_text(text)
