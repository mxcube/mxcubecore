# encoding: utf-8
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.
"""Pydantic models for the queue client wire format.

See JSON_FORMAT.md in this package for the full JSON format documentation
"""

import re

from pydantic import BaseModel, Field, field_validator, model_validator

from mxcubecore.queuelib.constants import UNCOLLECTED

VALID_PREFIX_TEMPLATE_FIELDS = ("{PREFIX}", "{POSITION}")
VALID_SUBDIR_TEMPLATE_FIELDS = ("{ACRONYM}", "{NAME}", "{POSITION}")


def validate_safe_string(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")

    value = value.strip()

    invalid_char = re.search(r"[^a-zA-Z0-9:+_. -]", value)
    if invalid_char:
        raise ValueError(
            f"{field_name} contains invalid character: {invalid_char.group(0)!r}"
        )

    return value


def validate_safe_template_prefix(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("prefix must be a string")

    value = value.strip()
    literal_value = value

    for field in VALID_PREFIX_TEMPLATE_FIELDS:
        literal_value = literal_value.replace(field, "")

    validate_safe_string(literal_value, "prefix")
    return value


def validate_safe_template_subdir(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("subdir must be a string")

    value = value.strip()
    literal_value = value

    for field in VALID_SUBDIR_TEMPLATE_FIELDS:
        literal_value = literal_value.replace(field, "")

    invalid_template = re.search(r"\{[^{}]*\}", literal_value)
    if invalid_template:
        raise ValueError(
            f"subdir contains invalid template variable: {invalid_template.group(0)!r}"
        )

    for part in literal_value.split("/"):
        validate_safe_string(part, "subdir")

    return value


def validate_position(value: str | int) -> str | int:
    if value in ("", None):
        return ""

    if value == -1:
        return value

    if not isinstance(value, str):
        raise ValueError(
            "shape must be -1 or a single letter followed by one or more digits"
        )

    value = value.strip()

    if value == "-1":
        return value

    if re.fullmatch(r"2DP(?:[0-9]+)?", value) or re.fullmatch(r"[a-zA-Z][0-9]+", value):
        return value

    raise ValueError(
        "shape must be -1 or a single letter followed by one or more digits"
    )


def validate_path(path: str) -> str:
    """Validate a path without requiring it to exist.

    Self-contained copy of mxcubeweb.core.models.generic.validate_path, kept
    in sync deliberately rather than imported, so this package has no
    dependency on mxcubeweb.
    """
    if not isinstance(path, str):
        raise ValueError("Path must be a string")

    if "\x00" in path:
        raise ValueError("Path contains a null byte")

    path = path.strip()

    if not path:
        return ""

    if "//" in path:
        raise ValueError("Path contains consecutive slashes")

    parts = path.split("/")

    if any(part == ".." for part in parts):
        raise ValueError("Relative path traversal is not allowed")

    return path


class TaskDataPathModel(BaseModel):
    shape: str | int = ""
    directory: str = ""
    process_directory: str = ""
    xds_dir: str = ""
    base_prefix: str = ""
    mad_prefix: str = ""
    reference_image_prefix: str = ""
    wedge_prefix: str = ""
    run_number: int = 0
    suffix: str = ""
    precision: int = 0
    start_num: int = 0
    num_files: int = 0
    compression: bool = False
    path: str = ""
    prefix: str = ""

    # Optional added by mxcubeweb, used but the frontend
    fileName: str | None = ""  # noqa: N815
    fullPath: str | None = ""  # noqa: N815
    subdir: str = ""

    model_config = {
        "validate_assignment": True,
        "extra": "ignore",
        "str_strip_whitespace": True,
        "use_enum_values": True,
    }

    @field_validator("directory", "path", "process_directory", "xds_dir", mode="before")
    @classmethod
    def validate_path_fields(cls, value: str) -> str:
        return validate_path(value)

    @field_validator(
        "base_prefix",
        "mad_prefix",
        "reference_image_prefix",
        "wedge_prefix",
        "suffix",
        mode="before",
    )
    @classmethod
    def validate_safe_string_fields(cls, value: str, info) -> str:
        return validate_safe_string(value, info.field_name)

    @field_validator("prefix", mode="before")
    @classmethod
    def validate_prefix(cls, value: str) -> str:
        return validate_safe_template_prefix(value)

    @field_validator("subdir", mode="before")
    @classmethod
    def validate_subdir(cls, value: str) -> str:
        return validate_safe_template_subdir(value)

    @field_validator("shape", mode="before")
    @classmethod
    def validate_shape(cls, value: str | int) -> str | int:
        return validate_position(value)


class XRFParameters(TaskDataPathModel):
    # From mxcbecore xrf:
    countTime: float = 0  # noqa: N815


class EnergyScanParameters(TaskDataPathModel):
    # From mxcbecore energy scan:
    element: str = ""
    edge: str = ""

    @field_validator("element", "edge", mode="before")
    @classmethod
    def validate_energy_scan_strings(cls, value: str, info) -> str:
        return validate_safe_string(value, info.field_name)


class WorkflowParameters(TaskDataPathModel):
    beam_size: str | None = None
    cell_count: int | None = None
    doc: str = ""
    label: str = ""
    name: str | None = None
    numCols: int = 0  # noqa: N815
    numRows: int = 0  # noqa: N815
    requires: str | None = None
    type: str = ""
    wfname: str = ""
    wfpath: str = ""

    @field_validator(
        "wfname",
        "wfpath",
        "type",
        "requires",
        "name",
        "label",
        "doc",
        "beam_size",
        mode="before",
    )
    @classmethod
    def validate_energy_scan_strings(cls, value: str, info) -> str:
        return validate_safe_string(value, info.field_name)


def normalize_mesh_range(value):
    if value in (None, "", [], ()):
        return {}

    if isinstance(value, float) or isinstance(value, int):
        return {
            "horizontal_range": 0,
            "vertical_range": 0,
        }

    if isinstance(value, dict):
        return {
            "horizontal_range": float(value.get("horizontal_range", 0)),
            "vertical_range": float(value.get("vertical_range", 0)),
        }

    if isinstance(value, (list, tuple)):
        if len(value) != 2:
            raise ValueError("mesh_range must contain two values")
        return {
            "horizontal_range": float(value[0]),
            "vertical_range": float(value[1]),
        }

    raise ValueError("mesh_range must be a dictionary with horizontal/vertical ranges")


class DataCollectionParameters(TaskDataPathModel):
    # From mxcubecore Datacollection, osc, mesh, helical
    first_image: int = Field(0, description="First image number")
    num_images: int = Field(0, description="Total number of images")
    osc_start: float = Field(0, description="Starting oscillation angle")
    osc_range: float = Field(0, description="Oscillation range per image")
    osc_total_range: float = 0
    overlap: float = 0
    kappa: float | None = 0
    kappa_phi: float | None = 0
    exp_time: float = Field(0, description="Exposure time in seconds")
    num_lines: int = 1
    energy: float = Field(0, description="Energy in keV")
    resolution: float = Field(0, description="Resolution in Angstrom")
    detector_distance: float = 0
    transmission: float = 100
    shutterless: bool = True
    take_snapshots: int = 0
    detector_binning_mode: str | None = None
    detector_roi_mode: int = 0
    mesh_range: dict[str, float] = {}
    num_triggers: int = 0
    num_images_per_trigger: int = 0
    cell_counting: str | None = None
    mesh_center: str | None = None
    cell_spacing: tuple[float, float] | None = None
    sub_wedge_size: int = 10
    disable_processing: bool = False

    # Unit cell parameters, sent by the frontend as cellA/cellB/cellC/
    # cellAlpha/cellBeta/cellGamma
    cellA: float = 0  # noqa: N815
    cellB: float = 0  # noqa: N815
    cellC: float = 0  # noqa: N815
    cellAlpha: float = 0  # noqa: N815
    cellBeta: float = 0  # noqa: N815
    cellGamma: float = 0  # noqa: N815

    # From mxcubeweb"
    helical: bool = False
    mesh: bool = False

    # Only set for Interleaved data collections
    taskIndexList: list[int] | None = None  # noqa: N815
    wedges: list["DataCollectionNodeModel"] = []
    swNumImages: int = 0  # noqa: N815

    @field_validator("mesh_range", mode="before")
    @classmethod
    def validate_mesh_range(cls, value):
        return normalize_mesh_range(value)

    @field_validator(
        "detector_binning_mode",
        "cell_counting",
        "mesh_center",
        mode="before",
    )
    @classmethod
    def validate_safe_string_fields(cls, value: str | None, info) -> str | None:
        return validate_safe_string(value, info.field_name)


class CharacterisationParameters(DataCollectionParameters):
    # From mxcubecore Characterisation
    experiment_type: str = ""
    use_aimed_resolution: float = 0
    use_aimed_multiplicity: float = 0
    aimed_multiplicity: float = 0
    aimed_i_sigma: float = 0
    aimed_completness: float = 0
    strategy_complexity: str = ""
    strategy_program: str = ""
    induce_burn: bool = False
    use_permitted_rotation: bool = False
    permitted_phi_start: float = 0
    permitted_phi_end: float = 0
    low_res_pass_strat: bool = False
    max_crystal_vdim: float = 0
    min_crystal_vdim: float = 0
    max_crystal_vphi: float = 0
    min_crystal_vphi: float = 0
    space_group: str = ""
    use_min_dose: float = 0
    use_min_time: float = 0
    min_dose: float = 0
    min_time: float = 0
    account_rad_damage: bool = False
    auto_res: bool = False
    opt_sad: bool = False
    sad_res: float = 0
    determine_rad_params: bool = False
    burn_osc_start: float = 0
    burn_osc_interval: float = 0
    rad_suscept: float = 0
    beta: float = 0
    gamma: float = 0

    @field_validator(
        "experiment_type", "strategy_program", "space_group", mode="before"
    )
    @classmethod
    def validate_characterisation_strings(cls, value: str, info) -> str:
        return validate_safe_string(value, info.field_name)

    @field_validator("strategy_complexity", mode="before")
    @classmethod
    def strategy_complexity_to_int(cls, value: int | str) -> str:
        if isinstance(value, str):
            return value

        try:
            return [
                "SINGLE",
                "FEW",
                "MANY",
            ][value]
        except (IndexError, TypeError):
            return "SINGLE"


class QueueNodeModel(BaseModel):
    type: str = ""
    queueID: int = -1  # noqa: N815
    checked: bool = False
    state: int = UNCOLLECTED

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, value: str) -> str:
        return validate_safe_string(value, "type")


class TaskNodeModel(QueueNodeModel):
    label: str = ""
    sampleID: str  # noqa: N815
    sampleQueueID: int | None = None  # noqa: N815

    # Only known once queued (given by mxcubecore queue)
    taskIndex: int | None = None  # noqa: N815

    # Optional fields
    diffractionPlan: list["TaskNodeModel"] | None = None  # noqa: N815
    diffractionPlanID: int | None = None  # noqa: N815
    name: str | None = None

    @field_validator("sampleID", "name", mode="before")
    @classmethod
    def validate_task_strings(cls, value: str | None, info) -> str | None:
        return validate_safe_string(value, info.field_name)


class DataCollectionNodeModel(TaskNodeModel):
    parameters: DataCollectionParameters


class CharacterisationNodeModel(TaskNodeModel):
    parameters: CharacterisationParameters


class XRFNodeModel(TaskNodeModel):
    parameters: XRFParameters


class EnergyScanNodeModel(TaskNodeModel):
    parameters: EnergyScanParameters


class WorkflowNodeModel(TaskNodeModel):
    parameters: WorkflowParameters


def build_task_node_model(value: object):
    if not isinstance(value, dict):
        return value

    normalized = dict(value)
    task_type = normalized.get("type")

    if task_type == "Interleaved":
        # Interleaved tasks are shaped like a DataCollection (plus wedges/
        # taskIndexList), so validate against that schema, but restore the
        # original type afterwards so downstream routing (add_interleaved,
        # the interleave swap logic) still recognizes it as "Interleaved".
        normalized["type"] = "DataCollection"
        model = DataCollectionNodeModel.model_validate(normalized)
        model.type = "Interleaved"
        return model

    if task_type == "Characterisation":
        return CharacterisationNodeModel.model_validate(normalized)

    if task_type == "xrf_spectrum":
        return XRFNodeModel.model_validate(normalized)

    if task_type == "energy_scan":
        return EnergyScanNodeModel.model_validate(normalized)

    if task_type in {"Workflow", "GphlWorkflow"}:
        return WorkflowNodeModel.model_validate(normalized)

    return DataCollectionNodeModel.model_validate(normalized)


TaskNodeUnion = (
    DataCollectionNodeModel
    | CharacterisationNodeModel
    | XRFNodeModel
    | EnergyScanNodeModel
    | WorkflowNodeModel
)


class SampleNode(QueueNodeModel):
    sampleID: str  # noqa: N815
    code: str | None = None
    location: str
    cell_no: int = 0
    puck_no: int = 1
    sampleName: str  # noqa: N815
    proteinAcronym: str | None = ""  # noqa: N815
    defaultPrefix: str | None = ""  # noqa: N815
    defaultSubDir: str | None = ""  # noqa: N815
    tasks: list[TaskNodeUnion]

    @model_validator(mode="before")
    @classmethod
    def validate_tasks(cls, value):
        if isinstance(value, dict):
            tasks = value.get("tasks")
            if isinstance(tasks, list):
                normalized = dict(value)
                normalized["tasks"] = [build_task_node_model(task) for task in tasks]
                return normalized

        return value

    @field_validator("sampleID", "code", "location", "defaultPrefix", mode="before")
    @classmethod
    def validate_sample_safe_strings(cls, value: str | None, info) -> str | None:
        return validate_safe_string(value, info.field_name)

    @field_validator("sampleName", "proteinAcronym", mode="before")
    @classmethod
    def validate_sample_strings(cls, value: str, info) -> str:
        if value is None and info.field_name == "proteinAcronym":
            return ""

        return validate_safe_string(value, info.field_name)
