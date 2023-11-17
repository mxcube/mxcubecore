#! /usr/bin/env python
# encoding: utf-8

"""Workflow runner, interfacing to external workflow engine
using Abstract Beamline Interface messages

License:

This file is part of MXCuBE.

MXCuBE is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

MXCuBE is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with MXCuBE. If not, see <https://www.gnu.org/licenses/>.
"""
from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import copy
import logging
import enum
import time
import datetime
import os
import math
import subprocess
import socket
from collections import OrderedDict

import gevent
import gevent.event
import gevent.queue
import f90nml

from mxcubecore.dispatcher import dispatcher
from mxcubecore.BaseHardwareObjects import HardwareObjectYaml
from mxcubecore.model import queue_model_objects
from mxcubecore.model import crystal_symmetry
from mxcubecore.queue_entry import QUEUE_ENTRY_STATUS
from mxcubecore.queue_entry import QueueAbortedException

from mxcubecore.HardwareObjects.Gphl import GphlMessages
from mxcubecore.HardwareObjects.Gphl.Transcal2MiniKappa import make_home_data
from mxcubecore import HardwareRepository as HWR


@enum.unique
class GphlWorkflowStates(enum.Enum):
    """
    BUSY = "Workflow is executing"
    READY = "Workflow is idle and ready to start"
    FAULT = "Workflow shutting down from an error"
    ABORTED = "HWorkflow shutting down after an abort or stop command
    COMPLETED = "Workflow has finished successfully"
    UNKNOWN = "Workflow state unknown"
    """

    BUSY = 0
    READY = 1
    FAULT = 2
    ABORTED = 3
    COMPLETED = 4
    UNKNOWN = 5


__copyright__ = """ Copyright © 2016 - 2019 by Global Phasing Ltd. """
__license__ = "LGPLv3+"
__author__ = "Rasmus H Fogh"

# Additional sample/diffraction plan data for GPhL emulation samples.
EMULATION_DATA = {
    "3n0s": {"radiationSensitivity": 0.9},
    "4j8p": {"radiationSensitivity": 1.1},
}

# Centring modes for use in centring mode pulldown.
# The dictionary keys are labels (changeable),
# the values are passed to the program (not changeable)
# The first value is the default
RECENTRING_MODES = OrderedDict(
    (
        ("Re-centre when orientation changes", "sweep"),
        ("Re-centre at the start of each wedge", "scan"),
        ("Re-centre all before acquisition start", "start"),
        ("No manual re-centring, rely on automatic recentring", "none"),
    )
)
# Lattice to point groups,
# Used for GPhL UI pulldowns, hence the combined point groups, like '4|422'
# The list of keys, plus "", defines the GPhL lattices pulldown.
lattice2point_group_tags = OrderedDict(
    aP=("1",),
    Triclinic=("2",),
    mP=("2",),
    mC=("2",),
    mI=("2",),
    Monoclinic=("2",),
    oP=("222",),
    oC=("222",),
    oF=("222",),
    oI=("222",),
    Orthorhombic=("222",),
    tP=("4", "422", "4|422"),
    tI=("4", "422", "4|422"),
    Tetragonal=("4", "422", "4|422"),
    hP=("3", "312", "321", "3|32", "6", "622", "6|622", "3|32|6|622"),
    hR=("3", "32", "3|32"),
    Hexagonal=(
        "3",
        "312",
        "321",
        "32",
        "3|32",
        "6",
        "622",
        "6|622",
        "3|32|6|622",
    ),
    cP=("23", "432", "23|432"),
    cF=("23", "432", "23|432"),
    cI=("23", "432", "23|432"),
    Cubic=("23", "432", "23|432"),
)

all_point_group_tags = []
for tag in (
    "Triclinic",
    "Monoclinic",
    "Orthorhombic",
    "Tetragonal",
    "Hexagonal",
    "Cubic",
):
    all_point_group_tags += lattice2point_group_tags[tag]

# Allowed altervative lattices for a given lattice
alternative_lattices = {}
for ll0 in (
    ["aP", "Triclinic"],
    ["mP", "mC", "mI", "Monoclinic"],
    ["oP", "oC", "oF", "oI", "Orthorhombic"],
    ["tP", "tI", "Tetragonal"],
    ["hP", "hR", "Hexagonal"],
    ["cP", "cF", "cI", "Cubic"],
):
    for tag in ll0:
        alternative_lattices[tag] = ll0


class GphlWorkflow(HardwareObjectYaml):
    """Global Phasing workflow runner."""

    SPECIFIC_STATES = GphlWorkflowStates

    TEST_SAMPLE_PREFIX = "emulate"

    # Signals
    PARAMETERS_NEEDED = "GphlJsonParametersNeeded"
    PARAMETER_RETURN_SIGNAL = "GphlParameterReturn"
    PARAMETER_UPDATE_SIGNAL = "GphlUpdateUiParameters"
    PARAMETERS_READY = "PARAMETERS_READY"
    PARAMETERS_CANCELLED = "PARAMETERS_CANCELLED"

    def __init__(self, name):
        super().__init__(name)

        # Needed to allow methods to put new actions on the queue
        # And as a place to get hold of other objects
        self._queue_entry = None

        # Configuration data - set on load
        self.workflows = OrderedDict()
        self.settings = {}
        self.test_crystals = {}
        # auxiliary data structure from configuration. Set in init
        self.workflow_strategies = OrderedDict()

        # Current data collection task group.
        # Different for characterisation and collection
        self._data_collection_group = None

        # event to handle waiting for parameter input
        self._return_parameters = None

        # Queue to read messages from GphlConnection
        self._workflow_queue = None

        # Message - processing function map
        self._processor_functions = {}

        # Subprocess names to track which subprocess is getting info
        self._server_subprocess_names = {}

        # Rotation axis role names, ordered from holder towards sample
        self.rotation_axis_roles = []

        # Translation axis role names
        self.translation_axis_roles = []

        # Switch for 'move-to-fine-zoom' message for translational calibration
        self._use_fine_zoom = False

        # Configurable file paths
        self.file_paths = {}

        self.recentring_file = None

        # # TEST mxcubeweb UI
        # self.gevent_event = gevent.event.Event()
        # self.params_dict = {}

    def init(self):
        super().init()

        # Set up processing functions map
        self._processor_functions = {
            "String": self.echo_info_string,
            "SubprocessStarted": self.echo_subprocess_started,
            "SubprocessStopped": self.echo_subprocess_stopped,
            "RequestConfiguration": self.get_configuration_data,
            "GeometricStrategy": self.setup_data_collection,
            "CollectionProposal": self.collect_data,
            "ChooseLattice": self.select_lattice,
            "RequestCentring": self.process_centring_request,
            "PrepareForCentring": self.prepare_for_centring,
            "ObtainPriorInformation": self.obtain_prior_information,
            "WorkflowAborted": self.workflow_aborted,
            "WorkflowCompleted": self.workflow_completed,
            "WorkflowFailed": self.workflow_failed,
        }

        # Set standard configurable file paths
        file_paths = self.file_paths
        ss0 = HWR.beamline.gphl_connection.software_paths["gphl_beamline_config"]
        file_paths["gphl_beamline_config"] = ss0
        file_paths["transcal_file"] = os.path.join(ss0, "transcal.nml")
        file_paths["diffractcal_file"] = os.path.join(ss0, "diffractcal.nml")
        file_paths["instrumentation_file"] = fp0 = os.path.join(
            ss0, "instrumentation.nml"
        )
        instrument_data = f90nml.read(fp0)["sdcp_instrument_list"]
        self.rotation_axis_roles = instrument_data["gonio_axis_names"]
        self.translation_axis_roles = instrument_data["gonio_centring_axis_names"]

        # Adapt configuration data - must be done after file_paths setting
        if HWR.beamline.gphl_connection.ssh_options:
            # We are running workflow through ssh - set beamline url
            beamline_hook = "py4j:%s:" % socket.gethostname()
        else:
            beamline_hook = "py4j::"

        # Consolidate workflow options
        for title, workflow in self.workflows.items():
            workflow["wfname"] = title

            opt0 = workflow.get("options", {})
            opt0["beamline"] = beamline_hook
            default_strategy_name = None
            for strategy in workflow["strategies"]:
                title = strategy["title"]
                self.workflow_strategies[title] = strategy
                strategy["wftype"] = workflow["wftype"]
                strategy["wfname"] = workflow["wfname"]
                if default_strategy_name is None:
                    default_strategy_name = workflow["strategy_name"] = title
                dd0 = opt0.copy()
                dd0.update(strategy.get("options", {}))
                strategy["options"] = dd0
                if workflow["wftype"] == "transcal":
                    relative_file_path = strategy["options"].get("file")
                    if relative_file_path is not None:
                        # Special case - this option must be modified before use
                        strategy["options"]["file"] = os.path.join(
                            self.file_paths["gphl_beamline_config"], relative_file_path
                        )

        self.update_state(self.STATES.READY)
        recentring_file = os.path.join(
            HWR.beamline.session.get_base_process_directory(), "recen.nml"
        )
        print ('@~@~ recentring_file', os.path.isfile(recentring_file), recentring_file)
        if os.path.isfile(recentring_file):
            self.recentring_file = recentring_file

    def shutdown(self):
        """Shut down workflow and connection. Triggered on program quit."""
        workflow_connection = HWR.beamline.gphl_connection
        if workflow_connection is not None:
            workflow_connection.workflow_ended()
            workflow_connection.close_connection()

    def get_available_workflows(self):
        """Get list of workflow description dictionaries."""
        return copy.deepcopy(self.workflows)

    def query_pre_strategy_params(self, choose_lattice=None):
        """Query pre_strategy parameters.
        Used for both characterisation, diffractcal, and acquisition

        :param data_model (GphlWorkflow): GphlWorkflow QueueModelObjecy
        :param choose_lattice (ChooseLattice): GphlMessage.ChooseLattice
        :return: -> dict
        """
        data_model = self._queue_entry.get_data_model()
        strategy_settings = data_model.strategy_settings
        space_group = data_model.space_group or ""
        if choose_lattice:
            header, soldict, select_row = self.parse_indexing_solution(choose_lattice)
            lattice = list(soldict.values())[select_row].bravaisLattice
            point_groups = lattice2point_group_tags[lattice]
            point_group = point_groups[-1]
            lattice_tags = alternative_lattices[lattice]
            if space_group:
                info = crystal_symmetry.CRYSTAL_CLASS_MAP[
                    crystal_symmetry.SPACEGROUP_MAP[space_group].crystal_class
                ]
                if info.bravais_lattice == lattice:
                    point_group = info.point_group
                    if point_group == "32" and info.bravais_lattice == "hP":
                        point_group = info.crystal_class[:-1]
                    if point_group not in point_groups:
                        point_group = point_groups[-1]
                    if space_group not in crystal_symmetry.XTAL_SPACEGROUPS:
                        # Non-enantiomeric sace groups not supported in user interface
                        space_group = ""
                else:
                    space_group = ""
        elif space_group:
            crystal_class = crystal_symmetry.SPACEGROUP_MAP[space_group].crystal_class
            info = crystal_symmetry.CRYSTAL_CLASS_MAP[crystal_class]
            lattice = info.bravais_lattice
            point_group = info.point_group
            point_groups = lattice2point_group_tags[lattice]
            if point_group not in point_groups:
                point_group = point_groups[-1]
            lattice_tags = [""] + list(lattice2point_group_tags)
            if space_group not in crystal_symmetry.XTAL_SPACEGROUPS:
                # Non-enantiomeric sace groups not supported in user interface
                space_group = ""
        else:
            lattice = ""
            point_group = ""
            lattice_tags = [""] + list(lattice2point_group_tags)
            point_groups = [""] + all_point_group_tags
        schema = {
            "title": "GΦL Pre-strategy parameters",
            "type": "object",
            "properties": {},
            "definitions": {},
        }
        fields = schema["properties"]
        fields["cell_a"] = {
            "title": "a",
            "type": "number",
            "minimum": 0,
            "readOnly": True,
        }
        fields["cell_b"] = {
            "title": "b",
            "type": "number",
            "minimum": 0,
            "readOnly": True,
        }
        fields["cell_c"] = {
            "title": "c",
            "type": "number",
            "minimum": 0,
            "readOnly": True,
        }
        fields["cell_alpha"] = {
            "title": "α",
            "type": "number",
            "minimum": 0,
            "maximum": 180,
            "readOnly": True,
        }
        fields["cell_beta"] = {
            "title": "β",
            "type": "number",
            "minimum": 0,
            "maximum": 180,
            "readOnly": True,
        }
        fields["cell_gamma"] = {
            "title": "γ",
            "type": "number",
            "minimum": 0,
            "maximum": 180,
            "readOnly": True,
        }
        lattice_dict = OrderedDict((tag, tag) for tag in lattice_tags)
        fields["lattice"] = {
            "title": "Crystal lattice",
            "type": "string",
            "default": lattice,
             "enum": lattice_tags,
            # "$ref": "#/definitions/lattice",
            "value_dict": lattice_dict,
        }
        pg_dict = OrderedDict((tag, tag) for tag in point_groups)
        fields["point_groups"] = {
            "title": "Point Groups",
            "type": "string",
            "default": point_group,
            "enum": point_groups,
            "value_dict": pg_dict,
            "hidden": not choose_lattice,
        }
        sglist = [""] + crystal_symmetry.space_groups_from_params(
            point_groups=point_groups
        )
        sg_dict = OrderedDict((tag, tag) for tag in sglist)
        fields["space_group"] = {
            "title": "Space Group",
            "type": "string",
            "default": space_group,
            "enum": sglist,
            "value_dict": sg_dict,
        }
        fields["input_space_group"] = {
            "title": "Space Group",
            "default": crystal_symmetry.regularise_space_group(
                data_model.input_space_group
            )
            or "",
            "type": "string",
            "readOnly": True,
        }
        fields["relative_rad_sensitivity"] = {
            "title": "Radiation sensitivity",
            "default": data_model.relative_rad_sensitivity or 1.0,
            "type": "number",
            "minimum": 0,
        }
        fields["use_cell_for_processing"] = {
            "title": "Use for indexing",
            "type": "boolean",
            "default": self.settings["defaults"]["use_cell_for_processing"],
        }
        resolution = data_model.aimed_resolution or HWR.beamline.resolution.get_value()
        reslimits = HWR.beamline.resolution.get_limits()
        if None in reslimits:
            reslimits = (0.5, 5.0)
        resolution = max(resolution, reslimits[0])
        resolution = min(resolution, reslimits[1])
        fields["resolution"] = {
            "title": "Resolution",
            "type": "number",
            "default": resolution,
            "minimum": reslimits[0],
            "maximum": reslimits[1],
        }
        fields["strategy"] = {
            "title": "Strategy",
            "type": "string",
            # "$ref": "#/definitions/strategy",
        }
        fields["wf_type"] = {
            "title": "Workflow type",
            "type": "string",
            "default": "GphlWorkflow",
            "readOnly": True,
        }
        # )
        # Handle strategy fields
        if data_model.characterisation_done or data_model.wftype == "diffractcal":
            strategies = strategy_settings["variants"]
            if data_model.wftype == "diffractcal":
                strategies = list(
                    strategy_settings["options"].get("strategy", "") + variant
                    for variant in strategies
                 )
            fields["strategy"]["default"] = strategies[0]
            fields["strategy"]["title"] = "Acquisition strategy"
            fields["strategy"]["enum"] = strategies
            ll0 = strategy_settings.get("beam_energy_tags")
            if ll0:
                energy_tag = ll0[0]
            else:
                energy_tag = self.settings["default_beam_energy_tag"]
        else:
            # Characterisation
            strategies = self.settings["characterisation_strategies"]
            fields["strategy"]["default"] = strategies[0]
            fields["strategy"]["title"] = "Characterisation strategy"
            fields["strategy"]["enum"] = strategies
            energy_tag = "Characterisation"
        # schema["definitions"]["strategy"] = list(
        #     {
        #         "type": "string",
        #         "enum": [tag],
        #         "title": tag,
        #     }
        #     for tag in strategies
        # )
        # Handle energy field
        # NBNB allow for fixed-energy beamlines
        energy_limits = HWR.beamline.energy.get_limits()
        tag = "energy"
        fields[tag] = {
            "title": "%s energy (keV)" % energy_tag,
            "type": "number",
            "default": HWR.beamline.energy.get_value(),
            "minimum": energy_limits[0],
            "maximum": energy_limits[1],
        }
        # Handle cell parameters
        cell_parameters = None
        if choose_lattice:
            unit_cell = choose_lattice.userProvidedCell
            if unit_cell:
                cell_parameters = unit_cell.lengths + unit_cell.angles
        if not cell_parameters:
            cell_parameters = data_model.cell_parameters
        if cell_parameters:
            for tag, val in zip(
                ("cell_a", "cell_b", "cell_c", "cell_alpha", "cell_beta", "cell_gamma"),
                data_model.cell_parameters,
            ):
                fields[tag]["default"] = val
        else:
            for tag in (
                "cell_a", "cell_b", "cell_c", "cell_alpha", "cell_beta", "cell_gamma"
            ):
                fields[tag]["default"] = 0


        # NB update_on_change supports None, "always", and "selected"
        # It controls whether an update signal is sent when a parameter changes
        ui_schema = {
            "wf_type": {"ui:widget": "hidden"},
            "ui:order": ["crystal_data", "parameters"],
            "ui:widget": "vertical_box",
            "ui:options": {
                "return_signal": self.PARAMETER_RETURN_SIGNAL,
                "update_signal": self.PARAMETER_UPDATE_SIGNAL,
                "update_on_change": "selected",
            },
            "crystal_data": {
                "ui:title": "Input Unit Cell",
                "ui:widget": "column_grid",
                "ui:order": [
                    "sgroup",
                    "cella",
                    "cellb",
                    "cellc",
                ],
                "cella": {
                    "ui:order": ["cell_a", "cell_alpha"],
                },
                "cellb": {
                    "ui:order": ["cell_b", "cell_beta"],
                },
                "cellc": {
                    "ui:order": ["cell_c", "cell_gamma"],
                },
                "sgroup": {
                    "ui:order": ["input_space_group", "relative_rad_sensitivity"],
                    "relative_rad_sensitivity": {
                        "ui:options": {
                            "decimals": 2,
                        }
                    },
                },
            },
            "parameters": {
                "ui:title": "Parameters",
                "ui:widget": "column_grid",
                "ui:order": ["column1", "column2"],
                "column1": {
                    "ui:order": [
                        "lattice",
                        "point_groups",
                        "space_group",
                        "use_cell_for_processing",
                    ],
                    "lattice": {
                        "ui:options": {
                            "update_on_change": True,
                        },
                    },
                    "point_groups": {
                        "ui:options": {
                            "update_on_change": True,
                        },
                    },
                    "space_group": {
                        "ui:options": {
                            "update_on_change": True,
                        },
                    },
                },
                "column2": {
                    "ui:order": ["strategy", "resolution", "energy"],
                    "resolution": {
                        "ui:options": {
                            "decimals": 3,
                        },
                    },
                    "energy": {
                        "ui:options": {
                            "decimals": 4,
                        },
                    },
                },
            },
        }

        if data_model.wftype == "diffractcal":
            for tag in (
                "cell_a",
                "cell_b",
                "cell_c",
                "cell_alpha",
                "cell_beta",
                "cell_gamma",
            ):
                fields[tag]["readOnly"] = False
            ui_schema["parameters"]["column1"]["ui:order"].remove("point_groups")

        elif choose_lattice is None:
            # Characterisation
            ui_schema["parameters"]["column1"]["ui:order"].remove("point_groups")
            pass

        else:
            # Acquisition
            fields["relative_rad_sensitivity"]["readOnly"] = True
            fields["indexing_solution"] = {
                "title": "--- Select indexing solution : ---",
                "type": "string",
            }

            # Color green (figuratively) if matches lattices
            # NBNB TBD Redo once ABI has changed
            crystal_classes = (
                choose_lattice.priorCrystalClasses or data_model.crystal_classes
            )
            # Must match bravaisLattices column
            lattices = set(
                crystal_symmetry.CRYSTAL_CLASS_MAP[crystal_class].bravais_lattice
                for crystal_class in crystal_classes
            )
            if "mC" in lattices:
                # NBNB special case. mI non-standard but supported in XDS
                lattices.add("mI")
            highlights = {}
            if lattices:
                for rowno, solution in enumerate(soldict.values()):
                    if any(x == solution.bravaisLattice for x in lattices):
                        highlights[rowno] = {0: "HIGHLIGHT"}

            ui_schema["ui:order"].insert(0, "indexing_solution")
            ui_schema["indexing_solution"] = {
                "ui:widget": "selection_table",
                "ui:options": {
                    "header": [header],
                    "content": [list(soldict)],
                    "select_cell": (select_row, 0),
                    "highlights": highlights,
                    "update_on_change": True,
                },
            }

        self._return_parameters = gevent.event.AsyncResult()

        try:
            dispatcher.connect(
                self.receive_pre_strategy_data,
                self.PARAMETER_RETURN_SIGNAL,
                dispatcher.Any,
            )
            responses = dispatcher.send(
                self.PARAMETERS_NEEDED,
                self,
                schema,
                ui_schema,
            )
            if not responses:
                self._return_parameters.set_exception(
                    RuntimeError("Signal %s is not connected" % self.PARAMETERS_NEEDED)
                )

            params = self._return_parameters.get()
            if params is StopIteration:
                return StopIteration
            solline = params.get("indexing_solution")
            if solline:
                params["indexing_solution"] = soldict[solline]
        finally:
            dispatcher.disconnect(
                self.receive_pre_strategy_data,
                self.PARAMETER_RETURN_SIGNAL,
                dispatcher.Any,
            )
            self._return_parameters = None

        # Convert lattice and pointgroups to crystal class names
        lattice = params.pop("lattice", None)
        lattices = (lattice,) if lattice else ()
        pgvar = params.pop("point_groups", None)
        space_group = params.get("space_group")
        if choose_lattice:
            point_groups = pgvar.split("|") if pgvar else None
            params["crystal_classes"] = crystal_symmetry.crystal_classes_from_params(
                lattices, point_groups, space_group
            )
        else:
            params["crystal_classes"] = crystal_symmetry.crystal_classes_from_params(
                lattices=lattices, space_group=space_group
            )

        # Convert energy field to a single tuple
        params["energies"] = (params.pop("energy"),)
        #
        return params

    def pre_execute(self, queue_entry):
        if self.is_ready():
            self.update_state(self.STATES.BUSY)
        else:
            raise RuntimeError(
                "Cannot execute workflow - GphlWorkflow HardwareObject is not ready"
            )
        self._queue_entry = queue_entry
        data_model = queue_entry.get_data_model()
        default_exposure_time = data_model.exposure_time
        data_model.exposure_time = max(
            default_exposure_time, HWR.beamline.detector.get_exposure_time_limits()[0]
        )


        self._workflow_queue = gevent.queue.Queue()
        HWR.beamline.gphl_connection.open_connection()
        if data_model.automation_mode:
            params = data_model.auto_acq_parameters[0]
            space_group = params.pop("space_group", "")
            crystal_classes = params.pop("crystal_classes", ())
            if space_group and crystal_classes:
                raise ValueError(
                    "Only one of space_group and crystal_classes can be set"
                    "values are: %s, %s" % (space_group, crystal_classes)
                )
            elif space_group or crystal_classes:
                params["space_group"] = space_group
                params["crystal_classes"] = crystal_classes

        else:
            params = self.query_pre_strategy_params()
            if params is StopIteration:
                self.workflow_failed()
                return
            use_preset_spotdir = self.settings.get("use_preset_spotdir")
            if use_preset_spotdir:
                spotdir = self.get_emulation_sample_dir()
                if spotdir:
                    if os.path.isfile(os.path.join(spotdir, "SPOT.XDS")):
                        params["init_spot_dir"] = spotdir
                    else:
                        raise ValueError(
                            "no file SPOT.XDS in %s" % spotdir)
                else:
                    raise ValueError(
                        "use_preset_spotdir was set for non-emulation sample"
                    )


        cell_tags = (
            "cell_a",
            "cell_b",
            "cell_c",
            "cell_alpha",
            "cell_beta",
            "cell_gamma",
        )
        cell_parameters = tuple(params.pop(tag, None) for tag in cell_tags)
        if None not in cell_parameters:
            params["cell_parameters"] = cell_parameters

        data_model.set_pre_strategy_params(**params)
        if data_model.detector_setting is None:
            # NB can only happen in automation mode
            resolution = HWR.beamline.resolution.get_value()
            distance = HWR.beamline.detector.distance.get_value()
            orgxy = HWR.beamline.detector.get_beam_position()
            data_model.detector_setting = GphlMessages.BcsDetectorSetting(
                resolution, orgxy=orgxy, Distance=distance
            )
        else:
            # Set detector distance and resolution
            distance = data_model.detector_setting.axisSettings["Distance"]
            HWR.beamline.detector.distance.set_value(distance, timeout=30)
        # self.test_dialog()

    def execute(self):

        if HWR.beamline.gphl_connection is None:
            raise RuntimeError(
                "Cannot execute workflow - GphlWorkflowConnection not found"
            )

        # Fork off workflow server process
        HWR.beamline.gphl_connection.start_workflow(
            self._workflow_queue, self._queue_entry.get_data_model()
        )

        while True:
            if self._workflow_queue is None:
                # We can only get that value if we have already done post_execute
                # but the mechanics of aborting means we conme back
                # Stop further processing here
                raise QueueAbortedException("Aborting...", self)

            tt0 = self._workflow_queue.get()
            if tt0 is StopIteration:
                logging.getLogger("HWR").debug("GΦL queue StopIteration")
                break

            message_type, payload, correlation_id, result_list = tt0
            func = self._processor_functions.get(message_type)
            if func is None:
                logging.getLogger("HWR").error(
                    "GΦL message %s not recognised by MXCuBE. Terminating...",
                    message_type,
                )
                break
            elif message_type != "String":
                logging.getLogger("HWR").info("GΦL queue processing %s", message_type)
                response = func(payload, correlation_id)
                if result_list is not None:
                    result_list.append((response, correlation_id))

    def post_execute(self):
        """
        The workflow has finished, sets the state to 'READY'
        """
        self.emit("gphl_workflow_finished", self.get_specific_state().name)
        self.update_state(self.STATES.READY)

        self._queue_entry = None
        self._data_collection_group = None
        self._server_subprocess_names.clear()
        self._workflow_queue = None
        if HWR.beamline.gphl_connection is not None:
            HWR.beamline.gphl_connection.workflow_ended()
            # HWR.beamline.gphl_connection.close_connection()

    def update_state(self, state=None):
        """
        Update state, resetting
        """
        super().update_state(state=state)
        tag = self.get_state().name
        if tag in ("BUSY", "READY", "UNKNOWN", "FAULT"):
            self.update_specific_state(getattr(self.SPECIFIC_STATES, tag))

    def _add_to_queue(self, parent_model_obj, child_model_obj):
        HWR.beamline.queue_model.add_child(parent_model_obj, child_model_obj)

    # Message handlers:

    def workflow_aborted(self, payload=None, correlation_id=None):
        logging.getLogger("user_level_log").warning("GΦL Workflow aborted.")
        self.update_specific_state(self.SPECIFIC_STATES.ABORTED)
        self._workflow_queue.put_nowait(StopIteration)

    def workflow_completed(self, payload=None, correlation_id=None):
        logging.getLogger("user_level_log").info("GΦL Workflow completed.")
        self.update_specific_state(self.SPECIFIC_STATES.COMPLETED)
        self._workflow_queue.put_nowait(StopIteration)

    def workflow_failed(self, payload=None, correlation_id=None):
        logging.getLogger("user_level_log").warning("GΦL Workflow failed.")
        self.update_specific_state(self.SPECIFIC_STATES.FAULT)
        self._workflow_queue.put_nowait(StopIteration)

    def echo_info_string(self, payload, correlation_id=None):
        """Print text info to console,. log etc."""
        subprocess_name = self._server_subprocess_names.get(correlation_id)
        if subprocess_name:
            logging.info("%s: %s" % (subprocess_name, payload))
        else:
            logging.info(payload)

    def echo_subprocess_started(self, payload, correlation_id):
        name = payload.name
        if correlation_id:
            self._server_subprocess_names[correlation_id] = name
        logging.info("%s : STARTING", name)

    def echo_subprocess_stopped(self, payload, correlation_id):
        try:
            name = self._server_subprocess_names.pop(correlation_id)
        except KeyError:
            name = "Unknown process"
        logging.info("%s : FINISHED", name)

    def get_configuration_data(self, payload, correlation_id):
        return GphlMessages.ConfigurationData(self.file_paths["gphl_beamline_config"])

    def query_collection_strategy(self, geometric_strategy):
        """Display collection strategy for user approval,
        and query parameters needed"""

        data_model = self._queue_entry.get_data_model()
        strategy_settings = data_model.strategy_settings

        # Number of decimals for rounding use_dose values
        use_dose_decimals = 4

        data_model = self._queue_entry.get_data_model()
        initial_energy = HWR.beamline.energy.calculate_energy(
            data_model.wavelengths[0].wavelength
        )

        sweep_group_counts = {}
        orientations = OrderedDict()
        axis_setting_dicts = OrderedDict()
        for sweep in geometric_strategy.get_ordered_sweeps():
            rotation_id = sweep.goniostatSweepSetting.id_
            if rotation_id in orientations:
                orientations[rotation_id].append(sweep)
            else:
                orientations[rotation_id] = [sweep]
                axis_settings = sweep.goniostatSweepSetting.axisSettings.copy()
                axis_settings.pop(sweep.goniostatSweepSetting.scanAxis, None)
                axis_setting_dicts[rotation_id] = axis_settings
            count = sweep_group_counts.get(sweep.sweepGroup, 0) + 1
            sweep_group_counts[sweep.sweepGroup] = count

        energy_tags = strategy_settings.get("beam_energy_tags") or (
            self.settings["default_beam_energy_tag"],
        )
        # NBNB HACK - this needs to eb done properly
        # Used for determining whether to query wedge width
        is_interleaved = data_model.characterisation_done and (
            len(energy_tags) > 1 or max(sweep_group_counts.values()) > 1
        )

        # Make info_text and do some setting up
        axis_names = self.rotation_axis_roles
        if data_model.characterisation_done or data_model.wftype == "diffractcal":
            title_string = data_model.strategy_name
            lauegrp, ptgrp = crystal_symmetry.strategy_laue_group(
                data_model.crystal_classes,
                phasing=(data_model.strategy_type == "phasing"),
            )
            info_title = "--- %s ---" % title_string
            lines = [
                "Strategy '%s', for symmetry '%s'\n" % (
                    # title_string,
                    data_model.strategy_variant or data_model.strategy_name,
                    ptgrp,
                )
            ]
            beam_energies = OrderedDict()
            energies = [initial_energy, initial_energy + 0.01, initial_energy - 0.01]
            for idx, tag in enumerate(energy_tags):
                beam_energies[tag] = energies[idx]
            dose_label = "Dose/repetition (MGy)"

            # Make strategy-description info_text
            if len(beam_energies) > 1:
                lines.append(
                    "Experiment length (per repetition): %s * %6.1f°"
                    % (len(beam_energies), data_model.strategy_length)
                )
            else:
                lines.append(
                    "Experiment length (per repetition): %6.1f°"
                    % data_model.strategy_length
                )

        else:
            # Characterisation
            title_string = "Characterisation"
            info_title = "--- GΦL Characterisation strategy ---"
            lines = ["Experiment length: %6.1f°" % data_model.strategy_length]
            beam_energies = OrderedDict((("Characterisation", initial_energy),))
            dose_label = "Characterisation dose (MGy)"
            if not self.settings.get("recentre_before_start"):
                # replace planned orientation with current orientation
                current_pos_dict = HWR.beamline.diffractometer.get_positions()
                dd0 = list(axis_setting_dicts.values())[0]
                for tag in dd0:
                    pos = current_pos_dict.get(tag)
                    if pos is not None:
                        dd0[tag] = pos

        for rotation_id, sweeps in orientations.items():
            axis_settings = axis_setting_dicts[rotation_id]
            ss0 = "\nSweep :  " + ",  ".join(
                "%s= %6.1f°" % (x, axis_settings.get(x))
                for x in axis_names
                if x in axis_settings
            )
            ll1 = []
            for sweep in sweeps:
                start = sweep.start
                width = sweep.width
                ss1 = "%s= %6.1f°,  sweep width= %6.1f°" % (
                    sweep.goniostatSweepSetting.scanAxis,
                    start,
                    width,
                )
                ll1.append(ss1)
            lines.append(ss0 + ",  " + ll1[0])
            spacer = " " * (len(ss0) + 2)
            for ss1 in ll1[1:]:
                lines.append(spacer + ss1)
        info_text = "\n".join(lines)

        # Set up image width pulldown
        allowed_widths = geometric_strategy.allowedWidths
        if allowed_widths:
            default_width_index = geometric_strategy.defaultWidthIdx or 0
        else:
            allowed_widths = list(self.settings.get("default_image_widths"))
            val = allowed_widths[0]
            allowed_widths.sort()
            default_width_index = allowed_widths.index(val)
            logging.getLogger("HWR").info(
                "No allowed image widths returned by strategy - use defaults"
            )

        # set starting and unchanging values of parameters
        acq_parameters = HWR.beamline.get_default_acquisition_parameters()

        resolution = HWR.beamline.resolution.get_value()
        dose_budget = self.resolution2dose_budget(
            resolution,
            decay_limit=data_model.decay_limit,
        )
        # NB These default values are set just before this function is called
        default_image_width = data_model.image_width
        default_exposure = data_model.exposure_time
        exposure_limits = HWR.beamline.detector.get_exposure_time_limits()
        total_strategy_length = data_model.strategy_length * len(beam_energies)
        # NB this is the default starting value, so repetition_count is 1 at this point
        experiment_time = total_strategy_length * default_exposure / default_image_width
        # Dose with transmission=100 and current defaults:
        maximum_dose = data_model.calc_maximum_dose(energy=initial_energy)
        if data_model.characterisation_done or data_model.wftype == "diffractcal":
            proposed_dose = dose_budget - data_model.characterisation_dose
        else:
            # Characterisation
            proposed_dose = dose_budget * data_model.characterisation_budget_fraction
            if maximum_dose:
                proposed_dose = min(maximum_dose, proposed_dose)
        proposed_dose = round(max(proposed_dose, 0), use_dose_decimals)

        # For calculating dose-budget transmission
        if maximum_dose:
            use_dose_start = proposed_dose
            use_dose_frozen = False
            transmission = 100 * proposed_dose / maximum_dose
            if transmission > 100:
                use_dose_start = proposed_dose * 100.0 / transmission
                transmission = 100.0
        else:
            transmission = acq_parameters.transmission
            use_dose_start = 0
            use_dose_frozen = True
            logging.getLogger("user_level_log").warning(
                "Dose rate cannot be calculated - dose bookkeeping disabled"
            )

        reslimits = HWR.beamline.resolution.get_limits()
        if None in reslimits:
            reslimits = (0.5, 5.0)

        schema = {
            "title": "GΦL %s parameters" % title_string,
            "type": "object",
            "properties": {},
            "definitions": {},
        }
        fields = schema["properties"]
        # # From here on visible fields
        fields["_info"] = {
            # "title": "Data collection plan",
            "type": "textdisplay",
            "default": info_text,
            "readOnly": True,
        }
        fields["image_width"] = {
            "title": "Oscillation range",
            "type": "string",
            "default": str(default_image_width),
            "$ref": "#/definitions/image_width",
        }
        fields["exposure"] = {
            "title": "Exposure Time (s)",
            "type": "number",
            "default": default_exposure,
            "minimum": exposure_limits[0],
            "maximum": exposure_limits[1],
        }
        fields["dose_budget"] = {
            "title": "Dose budget (MGy)",
            "type": "number",
            "default": dose_budget - data_model.characterisation_dose,
            "minimum": 0.0,
            "readOnly": True,
        }
        fields["use_dose"] = {
            "title": dose_label,
            "type": "number",
            "default": use_dose_start,
            "minimum": 0.000001,
            "readOnly": use_dose_frozen,
        }
        # NB Transmission is in % in UI, but in 0-1 in workflow
        fields["transmission"] = {
            "title": "Transmission (%)",
            "type": "number",
            "default": transmission,
            "minimum": 0.001,
            "maximum": 100.0,
        }
        fields["resolution"] = {
            "title": "Detector resolution (Å)",
            "type": "number",
            "default": resolution,
            "minimum": reslimits[0],
            "maximum": reslimits[1],
            "readOnly": True,
        }
        fields["experiment_time"] = {
            "title": "Experiment duration (s)",
            "type": "number",
            "default": experiment_time,
            "readOnly": True,
        }
        if data_model.characterisation_done:
            fields["repetition_count"] = {
                "title": "Number of repetitions",
                "type": "spinbox",
                "default": 1,
                "lowerBound": 1,
                "upperBound": 99,
                "stepsize": 1,
            }

        if is_interleaved:
            fields["wedge_width"] = {
                "title": "Wedge width (°)",
                "type": "number",
                "default": self.settings.get("default_wedge_width", 15),
                "minimum": 0.1,
                "maximum": 7200,
            }
        readonly = True
        energy_limits = HWR.beamline.energy.get_limits()
        for tag, val in beam_energies.items():
            fields[tag] = {
                "title": "%s beam energy (keV)" % tag,
                "type": "number",
                "default": val,
                "minimum": energy_limits[0],
                "maximum": energy_limits[1],
                "readOnly": readonly,
            }
            readonly = False

        fields["snapshot_count"] = {
            "title": "Number of snapshots",
            "type": "string",
            "default": str(data_model.snapshot_count),
            "$ref": "#/definitions/snapshot_count",
        }

        # recentring mode:
        labels = list(RECENTRING_MODES.keys())
        modes = list(RECENTRING_MODES.values())
        default_recentring_mode = self.settings.get("default_recentring_mode", "sweep")
        if default_recentring_mode == "scan" or default_recentring_mode not in modes:
            raise ValueError(
                "invalid default recentring mode '%s' " % default_recentring_mode
            )
        use_modes = ["sweep"]
        if len(orientations) > 1:
            use_modes.append("start")
            use_modes.append("none")
        if is_interleaved:
            use_modes.append("scan")
        for indx in range(len(modes) - 1, -1, -1):
            if modes[indx] not in use_modes:
                del modes[indx]
                del labels[indx]
        if default_recentring_mode in modes:
            indx = modes.index(default_recentring_mode)
            if indx:
                # Put default at top
                del modes[indx]
                modes.insert(indx, default_recentring_mode)
                default_label = labels.pop(indx)
                labels.insert(indx, default_label)
        else:
            default_recentring_mode = "sweep"
        default_label = labels[modes.index(default_recentring_mode)]
        # if len(modes) > 1:
        fields["recentring_mode"] = {
            # "title": "Recentring mode",
            "type": "string",
            "default": default_label,
            "$ref": "#/definitions/recentring_mode",
        }
        schema["definitions"]["recentring_mode"] = list(
            {
                "type": "string",
                "enum": [label],
                "title": label,
            }
            for label in labels
        )
        schema["definitions"]["snapshot_count"] = list(
            {
                "type": "string",
                "enum": [tag],
                "title": tag,
            }
            for tag in (
                "0",
                "1",
                "2",
                "4",
            )
        )
        schema["definitions"]["image_width"] = list(
            {
                "type": "string",
                "enum": [str(tag)],
                "title": str(tag),
            }
            for tag in allowed_widths
        )

        ui_schema = {
            "ui:order": ["_info", "parameters"],
            "ui:widget": "vertical_box",
            "ui:options": {
                "return_signal": self.PARAMETER_RETURN_SIGNAL,
                "update_signal": self.PARAMETER_UPDATE_SIGNAL,
                "update_on_change": "selected",
            },
            "_info": {
                "ui:title": info_title,
            },
            "parameters": {
                "ui:title": "Parameters",
                "ui:widget": "column_grid",
                "ui:order": ["column1", "column2"],
                "column1": {
                    "ui:order": [
                        "use_dose",
                        "exposure",
                        "image_width",
                        "transmission",
                        "snapshot_count",
                    ],
                    "exposure": {
                        "ui:options": {
                            "update_on_change": True,
                            "decimals": 4,
                        }
                    },
                    "use_dose": {
                        "ui:options": {
                            "decimals": use_dose_decimals,
                            "update_on_change": True,
                        }
                    },
                    "image_width": {
                        "ui:options": {
                            "update_on_change": True,
                        }
                    },
                    "transmission": {
                        "ui:options": {
                            "decimals": 3,
                            "update_on_change": True,
                        }
                    },
                    "repetition_count": {"ui:options": {"update_on_change": True}},
                },
                "column2": {
                    "ui:order": [
                        "dose_budget",
                        "experiment_time",
                        "resolution",
                    ],
                    "dose_budget": {
                        "ui:options": {
                            "decimals": 4,
                        }
                    },
                    "resolution": {
                        "ui:options": {
                            "decimals": 3,
                        }
                    },
                    "experiment_time": {
                        "ui:options": {
                            "decimals": 1,
                        }
                    },
                },
            },
        }
        if is_interleaved:
            ui_schema["parameters"]["column1"]["ui:order"].append("wedge_width")
        if data_model.characterisation_done:
            ui_schema["parameters"]["column1"]["ui:order"].insert(
                -1,
                "repetition_count",
            )

        ll0 = ui_schema["parameters"]["column2"]["ui:order"]
        ll0.extend(list(beam_energies))
        ll0.append("recentring_mode")

        self._return_parameters = gevent.event.AsyncResult()
        try:
            dispatcher.connect(
                self.receive_pre_collection_data,
                self.PARAMETER_RETURN_SIGNAL,
                dispatcher.Any,
            )
            responses = dispatcher.send(
                self.PARAMETERS_NEEDED,
                self,
                schema,
                ui_schema,
            )
            if not responses:
                self._return_parameters.set_exception(
                    RuntimeError("Signal %s is not connected" % self.PARAMETERS_NEEDED)
                )

            result = self._return_parameters.get()
            if result is StopIteration:
                return StopIteration
        finally:
            dispatcher.disconnect(
                self.receive_pre_collection_data,
                self.PARAMETER_RETURN_SIGNAL,
                dispatcher.Any,
            )
            self._return_parameters = None

        tag = "image_width"
        value = result.get(tag)
        if value:
            image_width = float(value)
        else:
            image_width = self.settings.get("default_image_width", default_image_width)
        result[tag] = image_width
        # exposure OK as is
        tag = "repetition_count"
        result[tag] = int(result.get(tag) or 1)
        tag = "transmission"
        value = result.get(tag)
        if value:
            result[tag] = value
        tag = "wedgeWidth"
        value = result.get(tag)
        if value:
            result[tag] = int(value / image_width)
        else:
            # If not set is likely not used, but we want a default value anyway
            result[tag] = 150
        # resolution OK as is

        tag = "snapshot_count"
        value = result.get(tag)
        if value:
            result[tag] = int(value)

        energies = list(result.pop(tag) for tag in beam_energies)
        del energies[0]
        result["energies"] = energies

        tag = "recentring_mode"
        result[tag] = RECENTRING_MODES.get(result.get(tag)) or default_recentring_mode
        #
        return result

    def setup_data_collection(self, payload, correlation_id):
        """Query data collection parameters and return SampleCentred to ASTRA workflow

        :param payload (GphlMessages.GeometricStrategy):
        :param correlation_id (int) Astra workflow correlation ID
        :return (GphlMessages.SampleCentred):
        """
        geometric_strategy = payload

        # Set up
        gphl_workflow_model = self._queue_entry.get_data_model()
        wftype = gphl_workflow_model.wftype
        sweeps = geometric_strategy.get_ordered_sweeps()

        # Set strategy_length
        strategy_length = sum(sweep.width for sweep in sweeps)
        gphl_workflow_model.strategy_length = strategy_length

        allowed_widths = geometric_strategy.allowedWidths
        if allowed_widths:
            default_image_width = float(
                allowed_widths[geometric_strategy.defaultWidthIdx or 0]
            )
        else:
            default_image_width = list(
                self.settings.get("default_image_widths")
            )[0]
        acq_parameters = HWR.beamline.get_default_acquisition_parameters()
        default_exposure_time = acq_parameters.exp_time

        # get parameters and initial transmission/use_dose
        if gphl_workflow_model.automation_mode:
            # Get parameters and transmission/use_dose
            if gphl_workflow_model.characterisation_done:
                parameters = gphl_workflow_model.auto_acq_parameters[-1]
            else:
                parameters = gphl_workflow_model.auto_acq_parameters[0]
            if "dose_budget" in parameters:
                raise ValueError(
                    "'dose_budget' parameter no longer supported. "
                    "Use 'use_dose' or 'transmission' instead"
                )
            if parameters.get("init_spot_dir"):
                transmission = HWR.beamline.transmission.get_value()
                if not parameters["transmission"]:
                    parameters["transmission"] = transmission
                if not(
                    parameters.get("exposure_time") and parameters.get("image_width")
                ):
                    raise ValueError(
                        "exposure_time and image_width must be set when init_spot_dir is set"
                    )
            else:
                image_width = parameters.setdefault("image_width", default_image_width)
                exposure_time = parameters.setdefault(
                    "exposure_time", default_exposure_time
                )
                transmission = parameters.get("transmission")
                if not transmission:
                    use_dose = parameters.get(
                        "use_dose", gphl_workflow_model.recommended_dose_budget()
                    )
                    if gphl_workflow_model.characterisation_done:
                        use_dose -= gphl_workflow_model.characterisation_dose
                    elif wftype != "diffractcal":
                        # This is characterisation
                        use_dose *= gphl_workflow_model.characterisation_budget_fraction
                    maximum_dose = gphl_workflow_model.calc_maximum_dose(
                        image_width=image_width, exposure_time=exposure_time
                    )
                    parameters["transmission"] = min(100 * use_dose / maximum_dose, 100)
        else:
            # set gphl_workflow_model.transmission (initial value for interactive mode)
            use_dose = gphl_workflow_model.recommended_dose_budget()
            if gphl_workflow_model.characterisation_done:
                use_dose -= gphl_workflow_model.characterisation_dose
            elif wftype != "diffractcal":
                # This is characterisation
                use_dose *= gphl_workflow_model.characterisation_budget_fraction
            # Need setting before query
            gphl_workflow_model.image_width = default_image_width
            gphl_workflow_model.exposure_time = default_exposure_time
            maximum_dose = gphl_workflow_model.calc_maximum_dose()
            transmission = 100 * use_dose / maximum_dose
            if transmission > 100:
                if gphl_workflow_model.characterisation_done or wftype == "diffractcal":
                    # We are not in characterisation.
                    # Try to reset exposure time to get desired dose
                    exposure_time = (
                        gphl_workflow_model.exposure_time * transmission / 100
                    )
                    exposure_limits = HWR.beamline.detector.get_exposure_time_limits()
                    if exposure_limits[1]:
                        exposure_time = min(exposure_limits[1], exposure_time)
                    gphl_workflow_model.exposure_time = exposure_time
                transmission = 100
            gphl_workflow_model.transmission = transmission

            # Get modified parameters from UI and confirm acquisition
            # Run before centring, as it also does confirm/abort
            parameters = self.query_collection_strategy(geometric_strategy)
            if parameters is StopIteration:
                return StopIteration
            user_modifiable = geometric_strategy.isUserModifiable
            if user_modifiable:
                # Query user for new rotationSetting and make it,
                logging.getLogger("HWR").warning(
                    "User modification of sweep settings not implemented. Ignored"
                )

        # From here on same for manual and automation
        # First set current transmission and resolution values
        transmission = parameters["transmission"]
        logging.getLogger("GUI").info(
            "GphlWorkflow: setting transmission to %7.3f %%" % transmission
        )
        HWR.beamline.transmission.set_value(transmission)

        # NB - now pre-setting of detector has been removed, this gets
        # the current resolution setting, whatever it is
        initial_resolution = HWR.beamline.resolution.get_value()
        new_resolution = parameters.pop("resolution", initial_resolution)
        if (
            new_resolution != initial_resolution
            and not  parameters.get("init_spot_dir")
            and not gphl_workflow_model.characterisation_done
        ):
            logging.getLogger("GUI").info(
                "GphlWorkflow: setting detector distance for resolution %7.3f A",
                new_resolution,
            )
            # timeout in seconds: max move is ~2 meters, velocity 4 cm/sec
            HWR.beamline.resolution.set_value(new_resolution, timeout=60)

        gphl_workflow_model.set_pre_acquisition_params(**parameters)

        # Update dose consumed to include dose (about to be) acquired.
        new_dose = (
            gphl_workflow_model.calc_maximum_dose() * gphl_workflow_model.transmission / 100
        )
        if (
            gphl_workflow_model.characterisation_done
            or gphl_workflow_model.wftype == "diffractcal"
        ):
            gphl_workflow_model.acquisition_dose = new_dose
        else:
            gphl_workflow_model.characterisation_dose = new_dose

        fmt = "--> %s: %s"
        print("GPHL workflow. Data collection parameters:")
        for item in gphl_workflow_model.parameter_summary().items():
            print(fmt % item)

        # Enqueue data collection
        if gphl_workflow_model.characterisation_done:
            # Data collection TODO: Use workflow info to distinguish
            new_dcg_name = "GΦL Data Collection"
        elif wftype == "diffractcal":
            new_dcg_name = "GΦL DiffractCal"
        else:
            new_dcg_name = "GΦL Characterisation"
        logging.getLogger("HWR").debug("setup_data_collection %s", new_dcg_name)
        new_dcg_model = queue_model_objects.TaskGroup()
        new_dcg_model.set_enabled(True)
        new_dcg_model.set_name(new_dcg_name)
        new_dcg_model.set_number(
            gphl_workflow_model.get_next_number_for_name(new_dcg_name)
        )
        self._data_collection_group = new_dcg_model
        # self._add_to_queue(gphl_workflow_model, new_dcg_model)

        #
        # Set (re)centring behaviour and goniostatTranslations
        #
        recentring_mode = gphl_workflow_model.recentring_mode
        goniostatTranslations = []

        # Get all sweepSettings, in order
        sweepSettings = []
        sweepSettingIds = set()
        for sweep in sweeps:
            sweepSetting = sweep.goniostatSweepSetting
            sweepSettingId = sweepSetting.id_
            if sweepSettingId not in sweepSettingIds:
                sweepSettingIds.add(sweepSettingId)
                sweepSettings.append(sweepSetting)

        # For recentring mode 'start' do settings in reverse order
        if recentring_mode == "start":
            sweepSettings.reverse()

        # Handle centring of first orientation
        pos_dict = HWR.beamline.diffractometer.get_positions()
        sweepSetting = sweepSettings[0]

        # Get current position
        current_pos_dict = HWR.beamline.diffractometer.get_positions()
        current_okp = tuple(current_pos_dict[role] for role in self.rotation_axis_roles)
        current_xyz = tuple(
            current_pos_dict[role] for role in self.translation_axis_roles
        )

        # Check if sample is currently centred, and centre first sweep if not
        if (
            self.settings.get("recentre_before_start")
            and not gphl_workflow_model.characterisation_done
        ):
            # Sample has never been centred reliably.
            # Centre it at sweepsetting and put it into goniostatTranslations
            settings = dict(sweepSetting.axisSettings)
            q_e = self.enqueue_sample_centring(motor_settings=settings)
            translation, current_pos_dict = self.execute_sample_centring(
                q_e, sweepSetting
            )
            # Update current position
            current_okp = tuple(
                current_pos_dict[role] for role in self.rotation_axis_roles
            )
            current_xyz = tuple(
                current_pos_dict[role] for role in self.translation_axis_roles
            )
            goniostatTranslations.append(translation)
            gphl_workflow_model.current_rotation_id = sweepSetting.id_

        elif gphl_workflow_model.characterisation_done or wftype == "diffractcal":
            # Acquisition or diffractcal; crystal is already centred
            settings = dict(sweepSetting.axisSettings)
            okp = tuple(settings.get(x, 0) for x in self.rotation_axis_roles)
            maxdev = max(abs(okp[1] - current_okp[1]), abs(okp[2] - current_okp[2]))

            # Get translation setting from recentring or current (MAY be used)
            if self.recentring_file:
                # calculate first sweep recentring from okp
                tol = self.settings.get("angular_tolerance", 1.0)
                translation_settings = self.calculate_recentring(
                    okp, ref_xyz=current_xyz, ref_okp=current_okp
                )
                logging.getLogger("HWR").debug(
                    "GPHL Recentring. okp, motors, %s, %s"
                    % (okp, sorted(translation_settings.items()))
                )
            else:
                # existing centring - take from current position
                tol = 0.1
                translation_settings = dict(
                    (role, current_pos_dict.get(role))
                    for role in self.translation_axis_roles
                )

            if maxdev <= tol:
                # first orientation matches current, set to current centring
                # Use sweepSetting as is, recentred or very close
                translation = GphlMessages.GoniostatTranslation(
                    rotation=sweepSetting, **translation_settings
                )
                goniostatTranslations.append(translation)
                gphl_workflow_model.current_rotation_id = sweepSetting.id_

            else:

                if recentring_mode == "none":
                    if self.recentring_file:
                        # NB  if no recentring  but  MiniKappaCorrection this still OK
                        translation = GphlMessages.GoniostatTranslation(
                            rotation=sweepSetting, **translation_settings
                        )
                        goniostatTranslations.append(translation)
                else:
                    if self.recentring_file:
                        settings.update(translation_settings)
                    q_e = self.enqueue_sample_centring(motor_settings=settings)
                    translation, dummy = self.execute_sample_centring(q_e, sweepSetting)
                    goniostatTranslations.append(translation)
                    gphl_workflow_model.current_rotation_id = sweepSetting.id_
                    if recentring_mode == "start":
                        # We want snapshots in this mode,
                        # and the first sweepmis skipped in the loop below
                        okp = tuple(
                            int(settings.get(x, 0)) for x in self.rotation_axis_roles
                        )
                        self.collect_centring_snapshots("%s_%s_%s" % okp)

        else:
            # Characterisation, and sample was centred before we got here
            # Do characterisation at current position, not the hardcoded one
            rotation_settings = dict(
                (role, current_pos_dict[role]) for role in sweepSetting.axisSettings
            )
            newRotation = GphlMessages.GoniostatRotation(**rotation_settings)
            translation_settings = dict(
                (role, current_pos_dict.get(role))
                for role in self.translation_axis_roles
            )
            translation = GphlMessages.GoniostatTranslation(
                rotation=newRotation,
                requestedRotationId=sweepSetting.id_,
                **translation_settings
            )
            goniostatTranslations.append(translation)
            gphl_workflow_model.current_rotation_id = newRotation.id_

        # calculate or determine centring for remaining sweeps
        for sweepSetting in sweepSettings[1:]:
            settings = dict(sweepSetting.axisSettings)
            if self.recentring_file:
                # Update settings
                okp = tuple(settings.get(x, 0) for x in self.rotation_axis_roles)
                settings.update(
                    self.calculate_recentring(
                        okp, ref_xyz=current_xyz, ref_okp=current_okp
                    )
                )

            if recentring_mode == "start":
                q_e = self.enqueue_sample_centring(motor_settings=settings)
                logging.getLogger("HWR").debug(
                    "GPHL recenter at : " +
                    ", ".join("%s:%s" % item for item in sorted(settings.items()))
                )
                translation, dummy = self.execute_sample_centring(q_e, sweepSetting)
                goniostatTranslations.append(translation)
                gphl_workflow_model.current_rotation_id = sweepSetting.id_
                okp = tuple(int(settings.get(x, 0)) for x in self.rotation_axis_roles)
                self.collect_centring_snapshots("%s_%s_%s" % okp)
            elif self.recentring_file and not gphl_workflow_model.lattice_selected:
                # Not the first sweep and not gone through stratcal
                # Calculate recentred positions and pass them back
                translation = GphlMessages.GoniostatTranslation(
                    rotation=sweepSetting, **settings
                )
                logging.getLogger("HWR").debug(
                    "GPHL calculate recentring: " +
                    ", ".join("%s:%s" % item for item in sorted(settings.items()))
                )
                goniostatTranslations.append(translation)
        #
        gphl_workflow_model.goniostat_translations = goniostatTranslations

        # Do it here so that any centring actions are enqueued dfirst
        self._add_to_queue(gphl_workflow_model, new_dcg_model)

        # Return SampleCentred message
        sampleCentred = GphlMessages.SampleCentred(gphl_workflow_model)
        return sampleCentred

    def calculate_recentring(self, okp, ref_okp, ref_xyz):
        """Calculate predicted traslation values using recen
        okp is the omega,gamma,phi tuple of the target position,
        ref_okp and ref_xyz are the reference omega,gamma,phi and the
        corresponding x,y,z translation position"""

        # Get program locations
        recen_executable = HWR.beamline.gphl_connection.get_executable("recen")
        # Get environmental variables
        envs = {}
        GPHL_XDS_PATH = HWR.beamline.gphl_connection.software_paths.get("GPHL_XDS_PATH")
        if GPHL_XDS_PATH:
            envs["GPHL_XDS_PATH"] = GPHL_XDS_PATH
        GPHL_CCP4_PATH = HWR.beamline.gphl_connection.software_paths.get(
            "GPHL_CCP4_PATH"
        )
        if GPHL_CCP4_PATH:
            envs["GPHL_CCP4_PATH"] = GPHL_CCP4_PATH
        # Run recen
        command_list = [
            recen_executable,
            "--input",
            self.recentring_file,
            "--init-xyz",
            "%s,%s,%s" % ref_xyz,
            "--init-okp",
            "%s,%s,%s" % ref_okp,
            "--okp",
            "%s,%s,%s" % okp,
        ]
        # NB the universal_newlines has the NECESSARY side effect of converting
        # output from bytes to string (with default encoding),
        # avoiding an explicit decoding step.
        result = {}
        logging.getLogger("HWR").debug(
            "Running Recen command: %s", " ".join(command_list)
        )
        try:
            output = subprocess.check_output(
                command_list,
                env=envs,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )
        except subprocess.CalledProcessError as err:
            logging.getLogger("HWR").error(
                "Recen failed with returncode %s. Output was:\n%s",
                err.returncode,
                err.output,
            )
            return result

        terminated_ok = False
        for line in reversed(output.splitlines()):
            ss0 = line.strip()
            if terminated_ok:
                if "X,Y,Z" in ss0:
                    ll0 = ss0.split()[-3:]
                    for idx, tag in enumerate(self.translation_axis_roles):
                        result[tag] = float(ll0[idx])
                    break

            elif ss0 == "NORMAL termination":
                terminated_ok = True
        else:
            logging.getLogger("HWR").error(
                "Recen failed with normal termination=%s. Output was:\n" % terminated_ok
                + output
            )

        for tag, val in result.items():
            motor = HWR.beamline.diffractometer.get_object_by_role(tag)
            limits = motor.get_limits()
            if limits:
                limit = limits[0]
                if limit is not None and val < limit:
                    logging.getLogger("HWR").warning(
                        "WARNING, centring motor "
                        "%s position %s recentred to below minimum limit %s"
                        % (tag, val, limit)
                    )
                limit = limits[1]
                if limit is not None and val > limit:
                    logging.getLogger("HWR").warning(
                        "WARNING, centring motor "
                        "%s position %s recentred to above maximum limit %s"
                        % (tag, val, limit)
                    )
        #
        return result

    def collect_data(self, payload, correlation_id):
        collection_proposal = payload

        angular_tolerance = float(self.settings.get("angular_tolerance", 1.0))
        queue_manager = self._queue_entry.get_queue_controller()

        gphl_workflow_model = self._queue_entry.get_data_model()

        if gphl_workflow_model.init_spot_dir:
            # Characterisation, where collection and XDS have alredy been run
            return GphlMessages.CollectionDone(
                status=0,
                proposalId=collection_proposal.id_,
                # Only if you want to override prior information rootdir,
                # imageRoot=gphl_workflow_model.characterisation_directory
            )

        master_path_template = gphl_workflow_model.path_template
        relative_image_dir = collection_proposal.relativeImageDir

        sample = gphl_workflow_model.get_sample_node()
        # There will be exactly one for the kinds of collection we are doing
        crystal = sample.crystals[0]
        snapshot_count = gphl_workflow_model.snapshot_count
        recentring_mode = gphl_workflow_model.recentring_mode
        data_collections = []
        scans = collection_proposal.scans

        geometric_strategy = collection_proposal.strategy
        repeat_count = geometric_strategy.sweepRepeat
        sweep_offset = geometric_strategy.sweepOffset
        scan_count = len(scans)

        if repeat_count and sweep_offset and self.settings.get("use_multitrigger"):
            # commpress unrolled multi-trigger sweep
            # NBNB as of 202103 this is only allowed for a single sweep
            #
            # For now this is required
            if repeat_count != scan_count:
                raise ValueError(
                    " scan count %s does not match repeat count %s"
                    % (scan_count, repeat_count)
                )
            # treat only the first scan
            scans = scans[:1]

        sweeps = set()
        last_orientation = ()
        maxdev = -1
        snapshotted_rotation_ids = set()
        for scan in scans:
            sweep = scan.sweep
            acq = queue_model_objects.Acquisition()

            # Get defaults, even though we override most of them
            acq_parameters = HWR.beamline.get_default_acquisition_parameters()
            acq.acquisition_parameters = acq_parameters

            acq_parameters.first_image = scan.imageStartNum
            acq_parameters.num_images = scan.width.numImages
            acq_parameters.osc_start = scan.start
            acq_parameters.osc_range = scan.width.imageWidth
            logging.getLogger("HWR").info(
                "Scan: %s images of %s deg. starting at %s (%s deg)",
                acq_parameters.num_images,
                acq_parameters.osc_range,
                acq_parameters.first_image,
                acq_parameters.osc_start,
            )
            acq_parameters.exp_time = scan.exposure.time
            acq_parameters.num_passes = 1

            ##
            wavelength = sweep.beamSetting.wavelength
            acq_parameters.energy = HWR.beamline.energy.calculate_energy(wavelength)
            detdistance = sweep.detectorSetting.axisSettings["Distance"]
            # not needed when detdistance is set :
            # acq_parameters.resolution = resolution
            acq_parameters.detector_distance = detdistance
            # transmission is not passed from the workflow (yet)
            # it defaults to current value (?), so no need to set it
            # acq_parameters.transmission = transmission*100.0

            # acq_parameters.shutterless = self._has_shutterless()
            # acq_parameters.detector_mode = self._get_roi_modes()
            acq_parameters.inverse_beam = False
            # acq_parameters.take_dark_current = True
            # acq_parameters.skip_existing_images = False

            # Edna also sets screening_id
            # Edna also sets osc_end

            # Path_template
            path_template = HWR.beamline.get_default_path_template()
            # Naughty, but we want a clone, right?
            # NBNB this ONLY works because all the attributes are immutable values
            path_template.__dict__.update(master_path_template.__dict__)
            if relative_image_dir:
                path_template.directory = os.path.join(
                    HWR.beamline.session.get_base_image_directory(), relative_image_dir
                )
                path_template.process_directory = os.path.join(
                    HWR.beamline.session.get_base_process_directory(),
                    relative_image_dir,
                )
            acq.path_template = path_template
            filename_params = scan.filenameParams
            subdir = filename_params.get("subdir")
            if subdir:
                path_template.directory = os.path.join(path_template.directory, subdir)
                path_template.process_directory = os.path.join(
                    path_template.process_directory, subdir
                )
            ss0 = filename_params.get("run")
            path_template.run_number = int(ss0) if ss0 else 1
            path_template.base_prefix = filename_params.get("prefix", "")
            path_template.start_num = acq_parameters.first_image
            path_template.num_files = acq_parameters.num_images

            # Handle orientations and (re) centring
            goniostatRotation = sweep.goniostatSweepSetting
            rotation_id = goniostatRotation.id_
            initial_settings = sweep.get_initial_settings()
            orientation = (
                initial_settings.get("kappa"), initial_settings.get( "kappa_phi")
            )
            if last_orientation:
                maxdev = max(
                    abs(orientation[ind] - last_orientation[ind]) for ind in range(2)
                )
            last_orientation = orientation
            if not sweeps or recentring_mode in ("start", "none"):
                # First sweep (previously centred), or necessary centrings already done
                # Collect using precalculated or stored centring position
                acq_parameters.centred_position = queue_model_objects.CentredPosition(
                    initial_settings
                )
            elif recentring_mode == "sweep" and (
                rotation_id == gphl_workflow_model.current_rotation_id
                or (0 <= maxdev < angular_tolerance)
            ):
                # Use same postion as previous sweep, set only omega start
                acq_parameters.centred_position = queue_model_objects.CentredPosition(
                    {goniostatRotation.scanAxis: scan.start}
                )
            else:
                # New sweep, or recentriong_mode == scan
                # # We need to recentre
                # Put centring on queue and collect using the resulting position
                # NB this means that the actual translational axis positions
                # will NOT be known to the workflow
                self.enqueue_sample_centring(
                    motor_settings=initial_settings, in_queue=True
                )
            sweeps.add(sweep)

            if (
                rotation_id in snapshotted_rotation_ids
                and rotation_id == gphl_workflow_model.current_rotation_id
            ):
                acq_parameters.take_snapshots = 0
            else:
                # Only snapshots at the start or when orientation changes
                # NB the current_rotation_id can be set before acquisition commences
                # as it controls centring
                snapshotted_rotation_ids.add(rotation_id)
                acq_parameters.take_snapshots = snapshot_count
            gphl_workflow_model.current_rotation_id = rotation_id


            if repeat_count and sweep_offset and self.settings.get("use_multitrigger"):
                # Multitrigger sweep - add in parameters.
                # NB if we are here ther can be only one scan
                acq_parameters.num_triggers = scan_count
                acq_parameters.num_images_per_trigger = acq_parameters.num_images
                acq_parameters.num_images *= scan_count
                # NB this assumes sweepOffset is the offset between starting points
                acq_parameters.overlap = (
                    acq_parameters.num_images_per_trigger * acq_parameters.osc_range
                    - sweep_offset
                )
            data_collection = queue_model_objects.DataCollection([acq], crystal)
            data_collections.append(data_collection)

            data_collection.set_enabled(True)
            data_collection.ispyb_group_data_collections = True
            data_collection.set_name(path_template.get_prefix())
            data_collection.set_number(path_template.run_number)
            self._add_to_queue(self._data_collection_group, data_collection)
            if scan is not scans[-1]:
                dc_entry = queue_manager.get_entry_with_model(data_collection)
                dc_entry.in_queue = True

        # debug
        fmt = "--> %s: %s"
        print("GPHL workflow. Collect with parameters:")
        for item in gphl_workflow_model.parameter_summary().items():
            print(fmt % item)
        print(fmt % ("sweep_count", len(sweeps)))

        data_collection_entry = queue_manager.get_entry_with_model(
            self._data_collection_group
        )

        try:
            queue_manager.execute_entry(data_collection_entry)
        except:
            HWR.beamline.queue_manager.emit("queue_execution_failed", (None,))
        self._data_collection_group = None

        if data_collection_entry.status == QUEUE_ENTRY_STATUS.FAILED:
            # TODO NBNB check if these status codes are corerct
            status = 1
        else:
            status = 0

        return GphlMessages.CollectionDone(
            status=status,
            proposalId=collection_proposal.id_,
            procWithLatticeParams=gphl_workflow_model.use_cell_for_processing,
        )

    def select_lattice(self, payload, correlation_id):

        choose_lattice = payload

        data_model = self._queue_entry.get_data_model()
        data_model.characterisation_done = True

        if data_model.automation_mode:

            # Handle resolution
            if not data_model.aimed_resolution:
                raise ValueError("aimed_resolution must be set in automation mode")
            # Resets detector_setting to match aimed_resolution
            data_model.detector_setting = None
            # NB resets detector_setting
            params = data_model.auto_acq_parameters[-1]
            if "resolution" not in params:
                params["resolution"] = (
                    data_model.aimed_resolution
                    or HWR.beamline.get_default_acquisition_parameters().resolution
                )

            # select indexing solution and set space_group, crystal_classes
            header, soldict, select_row = self.parse_indexing_solution(choose_lattice)
            indexing_solution = list(soldict.values())[select_row]
            bravais_lattice = indexing_solution.bravaisLattice
            space_group = choose_lattice.priorSpaceGroupString
            crystal_classes = crystal_symmetry.filter_crystal_classes(
                bravais_lattice, choose_lattice.priorCrystalClasses
            )

            if space_group:
                xtlc = crystal_symmetry.SPACEGROUP_MAP[space_group].crystal_class
                if (
                    crystal_symmetry.CRYSTAL_CLASS_MAP[xtlc].bravais_lattice
                    == bravais_lattice
                ):
                    crystal_classes = (xtlc,)
                else:
                    crystal_classes = ()
                    space_group = ""
            if not crystal_classes:
                crystal_classes = (
                    crystal_symmetry.crystal_classes_from_params(
                        lattices=(bravais_lattice)
                    )
                )
            params["space_group"] = space_group
            params["crystal_classes"] = crystal_classes

        else:
            params = self.query_pre_strategy_params(choose_lattice)
            if params is StopIteration:
                return StopIteration
            indexing_solution = params["indexing_solution"]

        data_model.set_pre_strategy_params(**params)
        distance = data_model.detector_setting.axisSettings["Distance"]
        HWR.beamline.detector.distance.set_value(distance, timeout=30)
        return GphlMessages.SelectedLattice(data_model, solution=indexing_solution)

    def parse_indexing_solution(self, choose_lattice):
        """

        Args:
            choose_lattice GphlMessages.ChooseLattice:

        Returns: tuple

        """

        # Solution table. for format IDXREF will look like
        """
*********** DETERMINATION OF LATTICE CHARACTER AND BRAVAIS LATTICE ***********

 The CHARACTER OF A LATTICE is defined by the metrical parameters of its
 reduced cell as described in the INTERNATIONAL TABLES FOR CRYSTALLOGRAPHY
 Volume A, p. 746 (KLUWER ACADEMIC PUBLISHERS, DORDRECHT/BOSTON/LONDON, 1989).
 Note that more than one lattice character may have the same BRAVAIS LATTICE.

 A lattice character is marked "*" to indicate a lattice consistent with the
 observed locations of the diffraction spots. These marked lattices must have
 low values for the QUALITY OF FIT and their implicated UNIT CELL CONSTANTS
 should not violate the ideal values by more than
 MAXIMUM_ALLOWED_CELL_AXIS_RELATIVE_ERROR=  0.03
 MAXIMUM_ALLOWED_CELL_ANGLE_ERROR=           1.5 (Degrees)

  LATTICE-  BRAVAIS-   QUALITY  UNIT CELL CONSTANTS (ANGSTROEM & DEGREES)
 CHARACTER  LATTICE     OF FIT      a      b      c   alpha  beta gamma

 *  44        aP          0.0      56.3   56.3  102.3  90.0  90.0  90.0
 *  31        aP          0.0      56.3   56.3  102.3  90.0  90.0  90.0
 *  33        mP          0.0      56.3   56.3  102.3  90.0  90.0  90.0
 *  35        mP          0.0      56.3   56.3  102.3  90.0  90.0  90.0
 *  34        mP          0.0      56.3  102.3   56.3  90.0  90.0  90.0
 *  32        oP          0.0      56.3   56.3  102.3  90.0  90.0  90.0
 *  14        mC          0.1      79.6   79.6  102.3  90.0  90.0  90.0
 *  10        mC          0.1      79.6   79.6  102.3  90.0  90.0  90.0
 *  13        oC          0.1      79.6   79.6  102.3  90.0  90.0  90.0
 *  11        tP          0.1      56.3   56.3  102.3  90.0  90.0  90.0
    37        mC        250.0     212.2   56.3   56.3  90.0  90.0  74.6
    36        oC        250.0      56.3  212.2   56.3  90.0  90.0 105.4
    28        mC        250.0      56.3  212.2   56.3  90.0  90.0  74.6
    29        mC        250.0      56.3  125.8  102.3  90.0  90.0  63.4
    41        mC        250.0     212.3   56.3   56.3  90.0  90.0  74.6
    40        oC        250.0      56.3  212.2   56.3  90.0  90.0 105.4
    39        mC        250.0     125.8   56.3  102.3  90.0  90.0  63.4
    30        mC        250.0      56.3  212.2   56.3  90.0  90.0  74.6
    38        oC        250.0      56.3  125.8  102.3  90.0  90.0 116.6
    12        hP        250.1      56.3   56.3  102.3  90.0  90.0  90.0
    27        mC        500.0     125.8   56.3  116.8  90.0 115.5  63.4
    42        oI        500.0      56.3   56.3  219.6 104.8 104.8  90.0
    15        tI        500.0      56.3   56.3  219.6  75.2  75.2  90.0
    26        oF        625.0      56.3  125.8  212.2  83.2 105.4 116.6
     9        hR        750.0      56.3   79.6  317.1  90.0 100.2 135.0
     1        cF        999.0     129.6  129.6  129.6 128.6  75.7 128.6
     2        hR        999.0      79.6  116.8  129.6 118.9  90.0 109.9
     3        cP        999.0      56.3   56.3  102.3  90.0  90.0  90.0
     5        cI        999.0     116.8   79.6  116.8  70.1  39.8  70.1
     4        hR        999.0      79.6  116.8  129.6 118.9  90.0 109.9
     6        tI        999.0     116.8  116.8   79.6  70.1  70.1  39.8
     7        tI        999.0     116.8   79.6  116.8  70.1  39.8  70.1
     8        oI        999.0      79.6  116.8  116.8  39.8  70.1  70.1
    16        oF        999.0      79.6   79.6  219.6  90.0 111.2  90.0
    17        mC        999.0      79.6   79.6  116.8  70.1 109.9  90.0
    18        tI        999.0     116.8  129.6   56.3  64.3  90.0 118.9
    19        oI        999.0      56.3  116.8  129.6  61.1  64.3  90.0
    20        mC        999.0     116.8  116.8   56.3  90.0  90.0 122.4
    21        tP        999.0      56.3  102.3   56.3  90.0  90.0  90.0
    22        hP        999.0      56.3  102.3   56.3  90.0  90.0  90.0
    23        oC        999.0     116.8  116.8   56.3  90.0  90.0  57.6
    24        hR        999.0     162.2  116.8   56.3  90.0  69.7  77.4
    25        mC        999.0     116.8  116.8   56.3  90.0  90.0  57.6
    43        mI        999.0      79.6  219.6   56.3 104.8 135.0  68.8

 For protein crystals the possible space group numbers corresponding  to"""

        solutions = choose_lattice.indexingSolutions
        indexing_format = choose_lattice.indexingFormat
        solutions_dict = OrderedDict()

        if indexing_format == "IDXREF":
            header = """  LATTICE-  BRAVAIS-   QUALITY  UNIT CELL CONSTANTS (ANGSTROEM & DEGREES)
 CHARACTER  LATTICE     OF FIT      a      b      c   alpha  beta gamma"""

            line_format = (
                " %s  %2i        %s %12.1f    %6.1f %6.1f %6.1f %5.1f %5.1f %5.1f"
            )
            consistent_solutions = []
            for solution in solutions:
                if solution.isConsistent:
                    char1 = "*"
                    consistent_solutions.append(solution)
                else:
                    char1 = " "
                tpl = (
                    char1,
                    solution.latticeCharacter,
                    solution.bravaisLattice,
                    solution.qualityOfFit,
                )
                solutions_dict[
                    line_format % (tpl + solution.cell.lengths + solution.cell.angles)
                ] = solution

            crystal_classes = (
                choose_lattice.priorCrystalClasses
                or self._queue_entry.get_data_model().crystal_classes
            )
            # Must match bravaisLattices column
            lattices = frozenset(
                crystal_symmetry.CRYSTAL_CLASS_MAP[crystal_class].bravais_lattice
                for crystal_class in crystal_classes
            )
            select_row = None
            if lattices:
                # Select best solution matching lattices
                for idx, solution in enumerate(consistent_solutions):
                    if solution.bravaisLattice in lattices:
                        select_row = idx
                        break

            if select_row is None:
                # No match found, select on solutions only
                lattice = consistent_solutions[-1].bravaisLattice
                for idx, solution in enumerate(consistent_solutions):
                    if solution.bravaisLattice == lattice:
                        select_row = idx
                        break

        else:
            raise RuntimeError("Indexing format %s not supported" % indexing_format)
        #
        return header, solutions_dict, select_row

    def process_centring_request(self, payload, correlation_id):
        # Used for transcal only - anything else is data collection related

        raise NotImplementedError(
            "This function is currently broken, must eb upgraded to new system"
        )
        request_centring = payload

        logging.getLogger("user_level_log").info(
            "Start centring no. %s of %s",
            request_centring.currentSettingNo,
            request_centring.totalRotations,
        )

        # Rotate sample to RotationSetting
        goniostatRotation = request_centring.goniostatRotation
        goniostatTranslation = goniostatRotation.translation
        #

        if self._data_collection_group is None:
            gphl_workflow_model = self._queue_entry.get_data_model()
            new_dcg_name = "GΦL Translational calibration"
            new_dcg_model = queue_model_objects.TaskGroup()
            new_dcg_model.set_enabled(True)
            new_dcg_model.set_name(new_dcg_name)
            new_dcg_model.set_number(
                gphl_workflow_model.get_next_number_for_name(new_dcg_name)
            )
            self._data_collection_group = new_dcg_model
            self._add_to_queue(gphl_workflow_model, new_dcg_model)

        if request_centring.currentSettingNo < 2:
            # Start without fine zoom setting
            self._use_fine_zoom = False
        elif not self._use_fine_zoom and goniostatRotation.translation is not None:
            # We are moving to having recentered positions -
            # Set or prompt for fine zoom
            self._use_fine_zoom = True
            zoom_motor = HWR.beamline.sample_view.zoom
            if zoom_motor:
                # Zoom to the last predefined position
                # - that should be the largest magnification
                ll0 = zoom_motor.get_predefined_positions_list()
                if ll0:
                    logging.getLogger("user_level_log").info(
                        "Sample re-centering now active - Zooming in."
                    )
                    zoom_motor.moveToPosition(ll0[-1])
                else:
                    logging.getLogger("HWR").warning(
                        "No predefined positions for zoom motor."
                    )
            else:
                # Ask user to zoom
                info_text = """Automatic sample re-centering is now active
    Switch to maximum zoom before continuing"""
                field_list = [
                    {
                        "variableName": "_info",
                        "uiLabel": "Data collection plan",
                        "type": "textarea",
                        "default": info_text,
                    }
                ]
                self._return_parameters = gevent.event.AsyncResult()

                try:
                    responses = dispatcher.send(
                        self.PARAMETERS_NEEDED,
                        self,
                        field_list,
                        self._return_parameters,
                        None,
                    )
                    if not responses:
                        self._return_parameters.set_exception(
                            RuntimeError(
                                "Signal 'gphlParametersNeeded' is not connected"
                            )
                        )

                    # We do not need the result, just to end the waiting
                    response = self._return_parameters.get()
                    self._return_parameters = None
                    if response is StopIteration:
                        return StopIteration
                finally:
                    dispatcher.disconnect(
                        self.receive_pre_strategy_data,
                        self.PARAMETER_RETURN_SIGNAL,
                        dispatcher.Any,
                    )
                    self._return_parameters = None

        settings = goniostatRotation.axisSettings.copy()
        if goniostatTranslation is not None:
            settings.update(goniostatTranslation.axisSettings)
        centring_queue_entry = self.enqueue_sample_centring(motor_settings=settings)
        goniostatTranslation, dummy = self.execute_sample_centring(
            centring_queue_entry, goniostatRotation
        )

        if request_centring.currentSettingNo >= request_centring.totalRotations:
            return_status = "DONE"
        else:
            return_status = "NEXT"
        #
        return GphlMessages.CentringDone(
            return_status,
            timestamp=time.time(),
            goniostatTranslation=goniostatTranslation,
        )

    def enqueue_sample_centring(self, motor_settings, in_queue=False):

        # NBNB Should be refactored later and combined with execute_sample_centring
        # Now in_queue==False implies immediate execution

        queue_manager = self._queue_entry.get_queue_controller()
        data_model = self._queue_entry.get_data_model()
        if in_queue:
            parent = self._data_collection_group
        else:
            parent = data_model
        task_label = "Centring (kappa=%0.1f,phi=%0.1f)" % (
            motor_settings.get("kappa"),
            motor_settings.get("kappa_phi"),
        )
        if data_model.automation_mode:
            # Either TEST or MASSIF1
            # NB Negotiate different location with Olof Svensson
            centring_model = queue_model_objects.addXrayCentring(
                parent, name=task_label, motor_positions=motor_settings, grid_size=None
            )
        else:
            centring_model = queue_model_objects.SampleCentring(
                name=task_label, motor_positions=motor_settings
            )
            self._add_to_queue(parent, centring_model)
        centring_entry = queue_manager.get_entry_with_model(centring_model)
        centring_entry.in_queue = in_queue
        centring_entry.set_enabled(True)

        return centring_entry

    def collect_centring_snapshots(self, file_name_prefix="snapshot"):
        """

        :param file_name_prefix: str
        :return:
        """

        gphl_workflow_model = self._queue_entry.get_data_model()
        number_of_snapshots = gphl_workflow_model.snapshot_count
        if number_of_snapshots:
            filename_template = "%s_%s_%s.jpeg"
            snapshot_directory = os.path.join(
                gphl_workflow_model.path_template.get_archive_directory(),
                "centring_snapshots",
            )

            logging.getLogger("user_level_log").info(
                "Post-centring: Taking %d sample snapshot(s)", number_of_snapshots
            )
            collect_hwobj = HWR.beamline.collect
            timestamp = datetime.datetime.now().isoformat().split(".")[0]
            summed_angle = 0.0
            for snapshot_index in range(number_of_snapshots):
                if snapshot_index:
                    HWR.beamline.diffractometer.move_omega_relative(90)
                    summed_angle += 90
                snapshot_filename = filename_template % (
                    file_name_prefix,
                    timestamp,
                    snapshot_index + 1,
                )
                snapshot_filename = os.path.join(snapshot_directory, snapshot_filename)
                logging.getLogger("HWR").debug(
                    "Centring snapshot stored at %s", snapshot_filename
                )
                collect_hwobj._take_crystal_snapshot(snapshot_filename)
            if summed_angle:
                HWR.beamline.diffractometer.move_omega_relative(-summed_angle)

    def execute_sample_centring(
        self, centring_entry, goniostatRotation, requestedRotationId=None
    ):

        queue_manager = self._queue_entry.get_queue_controller()
        try:
            queue_manager.execute_entry(centring_entry)
        except:
            HWR.beamline.queue_manager.emit("queue_execution_failed", (None,))

        centring_result = centring_entry.get_data_model().get_centring_result()
        if centring_result:
            positionsDict = centring_result.as_dict()
            dd0 = dict((x, positionsDict[x]) for x in self.translation_axis_roles)
            return (
                GphlMessages.GoniostatTranslation(
                    rotation=goniostatRotation,
                    requestedRotationId=requestedRotationId,
                    **dd0
                ),
                positionsDict,
            )
        else:
            raise RuntimeError("Centring gave no result")

    def prepare_for_centring(self, payload, correlation_id):

        # TODO Add pop-up confirmation box ('Ready for centring?')

        return GphlMessages.ReadyForCentring()

    def obtain_prior_information(self, payload, correlation_id):

        workflow_model = self._queue_entry.get_data_model()

        # NBNB TODO check this is also OK in MXCuBE3
        image_root = HWR.beamline.session.get_base_image_directory()

        if not os.path.isdir(image_root):
            # This directory must exist by the time the WF software checks for it
            try:
                os.makedirs(image_root)
            except Exception:
                # No need to raise error - program will fail downstream
                logging.getLogger("HWR").error(
                    "Could not create image root directory: %s", image_root
                )

        priorInformation = GphlMessages.PriorInformation(workflow_model, image_root)
        #
        return priorInformation

    # Utility functions

    def resolution2dose_budget(
        self,
        resolution,
        decay_limit=None,
        maximum_dose_budget=None,
        relative_rad_sensitivity=1.0,
    ):
        """

        Args:
            resolution (float): resolution in A
            decay_limit (float): min. intensity at resolution edge at experiment end (%)
            maximum_dose_budget (float): maximum allowed dose budget
            relative_rad_sensitivity (float) : relative radiation sensitivity of crystal

        Returns (float): Dose budget (MGy)

        Get resolution-dependent dose budget that gives intensity decay_limit%
        at the end of acquisition for reflections at resolution
        assuming an increase in B factor of 1A^2/MGy

        """
        max_budget = maximum_dose_budget or self.settings.get("maximum_dose_budget", 20)
        decay_limit = decay_limit or self.settings.get("decay_limit", 25)
        result = 2 * resolution * resolution * math.log(100.0 / decay_limit)
        #
        return min(result, max_budget) / relative_rad_sensitivity

    @staticmethod
    def maximum_dose_rate(energy=None):
        """Calculate dose rate at average flux density for transmission=100

        NB put here rather than in AbstractFlux as assumptions inherent in
        using averaging to calculate dose rates are felt to be ungeneric

        Args:
            energy (Optional[float]): Beam enrgy in keV. Defaults to current beamline v alue

        Returns:
            float: Maximum dose rate in MGy/s
        """
        energy = energy or HWR.beamline.energy.get_value()
        flux_density = HWR.beamline.flux.get_average_flux_density(transmission=100.0)
        if flux_density:
            return (
                flux_density
                * HWR.beamline.flux.get_dose_rate_per_photon_per_mmsq(energy)
                * 1.0e-6  # convert to MGy
            )
        else:
            return 0


    def get_emulation_samples(self):
        """Get list of lims_sample information dictionaries for mock/emulation

        Returns: LIST[DICT]

        """
        crystal_file_name = "crystal.nml"
        result = []
        sample_dir = HWR.beamline.gphl_connection.software_paths.get(
            "gphl_test_samples"
        )
        serial = 0
        if sample_dir and os.path.isdir(sample_dir):
            for path, dirnames, filenames in sorted(os.walk(sample_dir)):
                if crystal_file_name in filenames:
                    data = {}
                    sample_name = os.path.basename(path)
                    indata = f90nml.read(os.path.join(path, crystal_file_name))[
                        "simcal_crystal_list"
                    ]
                    space_group = indata.get("sg_name")
                    cell_lengths = indata.get("cell_dim")
                    cell_angles = indata.get("cell_ang_deg")
                    resolution = indata.get("res_limit_def")

                    location = (serial // 10 + 1, serial % 10 + 1)
                    serial += 1
                    data["containerSampleChangerLocation"] = str(location[0])
                    data["sampleLocation"] = str(location[1])

                    data["sampleName"] = sample_name
                    if cell_lengths:
                        for idx, tag in enumerate(("cellA", "cellB", "cellC")):
                            data[tag] = cell_lengths[idx]
                    if cell_angles:
                        for idx, tag in enumerate(
                            ("cellAlpha", "cellBeta", "cellGamma")
                        ):
                            data[tag] = cell_angles[idx]
                    if space_group:
                        data["crystalSpaceGroup"] = space_group

                    data["experimentType"] = "Default"
                    # data["proteinAcronym"] = self.TEST_SAMPLE_PREFIX
                    data["smiles"] = None
                    data["sampleId"] = 100000 + serial

                    # ISPyB docs:
                    # experimentKind: enum('Default','MAD','SAD','Fixed','OSC',
                    # 'Ligand binding','Refinement', 'MAD - Inverse Beam','SAD -
                    # Inverse Beam', 'MXPressE','MXPressF','MXPressO','MXPressP',
                    # 'MXPressP_SAD','MXPressI','MXPressE_SAD','MXScore','MXPressM',)
                    #
                    # Use "Mad, "SAD", "OSC"
                    dfp = data["diffractionPlan"] = {
                        # "diffractionPlanId": 457980,
                        "experimentKind": "Default",
                        "numberOfPositions": 0,
                        "observedResolution": 0.0,
                        "preferredBeamDiameter": 0.0,
                        "radiationSensitivity": 1.0,
                        "requiredCompleteness": 0.0,
                        "requiredMultiplicity": 0.0,
                        # "requiredResolution": 0.0,
                    }
                    dfp["aimedResolution"] = resolution
                    dfp["diffractionPlanId"] = 5000000 + serial

                    dd0 = EMULATION_DATA.get(sample_name, {})
                    for tag, val in dd0.items():
                        if tag in data:
                            data[tag] = val
                        elif tag in dfp:
                            dfp[tag] = val
                    #
                    result.append(data)
        #
        return result


    def get_emulation_sample_dir(self, sample_name=None):
        """If sample is a test data set for emulation, get test data directory
        Args:
         sample_name Optional[str]:

        Returns:

        """
        sample_dir = None
        if sample_name is None:
            sample_name = (
                self._queue_entry.get_data_model().get_sample_node().get_name()
            )
        if sample_name:
            if sample_name.startswith(self.TEST_SAMPLE_PREFIX):
                sample_name = sample_name[len(self.TEST_SAMPLE_PREFIX)+1:]
            sample_dir = HWR.beamline.gphl_connection.software_paths.get(
                "gphl_test_samples"
            )
            if not sample_dir:
                raise ValueError("Test sample requires gphl_test_samples dir specified")
            sample_dir = os.path.join(sample_dir, sample_name)
        if not sample_dir:
            logging.getLogger("HWR").warning(
                "No emulation sample dir found for sample %s", sample_name
            )
        #
        return sample_dir

    def get_emulation_crystal_data(self, sample_name=None):
        """If sample is a test data set for emulation, get crystal data

        Returns:
            Optional[str]
        """
        crystal_data = None
        hklfile = None
        sample_dir = self.get_emulation_sample_dir(sample_name=sample_name)
        if os.path.isdir(sample_dir):
            crystal_file = os.path.join(sample_dir, "crystal.nml")
            if not os.path.isfile(crystal_file):
                raise ValueError(
                    "Emulator crystal data file %s does not exist" % crystal_file
                )
            # in spite of the simcal_crystal_list name this returns an OrderdDict
            crystal_data = f90nml.read(crystal_file)["simcal_crystal_list"]
            if isinstance(crystal_data, list):
                crystal_data = crystal_data[0]
            hklfile = os.path.join(sample_dir, "sample.hkli")
            if not os.path.isfile(hklfile):
                raise ValueError("Emulator hkli file %s does not exist" % hklfile)
        else:
            raise RuntimeError(
                "No emulation data found for %s at %s " % (sample_name, sample_dir)
            )
        #
        return crystal_data, hklfile

    #
    # Functions for new version of UI handling

    def receive_pre_strategy_data(self, instruction, parameters):

        if instruction == self.PARAMETERS_READY:
            self._return_parameters.set(parameters)
        elif instruction == self.PARAMETERS_CANCELLED:
            self._return_parameters.set(StopIteration)
        else:
            update_dict = {}
            try:
                if instruction == "indexing_solution":
                    update_dict = self.update_indexing_solution(parameters)
                elif instruction == "lattice":
                    update_dict = self.update_lattice(parameters)
                elif instruction == "point_groups":
                    update_dict = self.update_point_groups(parameters)
                elif instruction == "space_group":
                    update_dict = self.update_space_group(parameters)
            except:
                logging.getLogger("HWR").error(
                    "Error in GΦL parameter update for %s, Continuing ...",
                    instruction,
                )
            finally:
                responses = dispatcher.send(
                    self.PARAMETER_UPDATE_SIGNAL,
                    self,
                    update_dict,
                )
                if not responses:
                    self._return_parameters.set_exception(
                        RuntimeError(
                            "Signal %s is not connected" % self.PARAMETER_UPDATE_SIGNAL
                        )
                    )

    def receive_pre_collection_data(self, instruction, parameters):

        if instruction == self.PARAMETERS_READY:
            self._return_parameters.set(parameters)
        elif instruction == self.PARAMETERS_CANCELLED:
            self._return_parameters.set(StopIteration)
        else:
            update_dict = {}
            try:
                if instruction == "use_dose":
                    update_dict = self.adjust_transmission(parameters)
                elif instruction in (
                    "image_width",
                    "exposure",
                    "repetition_count",
                    "transmission",
                ):
                    update_dict = self.adjust_dose(parameters)
            except:
                logging.getLogger("HWR").error(
                    "Error in GΦL parameter update for %s, Continuing ...",
                    instruction,
                )
            finally:
                responses = dispatcher.send(
                    self.PARAMETER_UPDATE_SIGNAL,
                    self,
                    update_dict,
                )
                if not responses:
                    self._return_parameters.set_exception(
                        RuntimeError(
                            "Signal %s is not connected" % self.PARAMETER_UPDATE_SIGNAL
                        )
                    )

    def update_lattice(self, values):
        """Update pulldowns when crystal lattice changes"""
        lattice = values.get("lattice") or ""
        pgvar = values.get("point_groups")
        space_group = values.get("space_group")
        if lattice:
            pglist = lattice2point_group_tags[lattice]
            pgvalue = pgvar if pgvar and pgvar in pglist else pglist[-1]
            sgoptions = [""] + crystal_symmetry.space_groups_from_params(
                (lattice,), point_groups=pglist[-1].split("|")
            )
            sgvalue = ""
        else:
            pglist = [""] + all_point_group_tags
            pgvalue = ""
            sgoptions = [""] + crystal_symmetry.space_groups_from_params()
            sgvalue = space_group
        result = {
            "point_groups": {
                "value": pgvalue,
                "options": {
                    "value_dict": OrderedDict((tag, tag) for tag in pglist),
                },
            },
            "space_group": {
                "value": sgvalue,
                "options": {
                    "value_dict": OrderedDict((tag, tag) for tag in sgoptions),
                },
            },
        }
        #
        return result

    def update_point_groups(self, values):
        """Update pulldowns when pointgroups change"""
        pgvar = values.get("point_groups") or ""
        lattice = values.get("lattice")
        space_group = values.get("space_group")
        sglist = [""] + crystal_symmetry.space_groups_from_params(
            (lattice,), point_groups=pgvar.split("|")
        )
        value = ""
        result = {
            "space_group": {
                "value": value,
                "options": {
                    "value_dict": OrderedDict((tag, tag) for tag in sglist),
                },
            },
        }
        #
        return result

    def update_space_group(self, values):
        """Update pulldowns when space_group changes"""
        space_group = values.get("space_group")
        lattice0 = values.get("lattice")
        point_groups0 = values.get("point_groups")
        result = {}
        if space_group:
            info = crystal_symmetry.CRYSTAL_CLASS_MAP[
                crystal_symmetry.SPACEGROUP_MAP[space_group].crystal_class
            ]
            lattice = info.bravais_lattice
            if lattice != lattice0:
                values1 = dict(values)
                values1["lattice"] = lattice
                result = self.update_lattice(values1)
                # In case update_lattice changed the space group
                result["space_group"]["value"] = space_group
                point_groups = info.point_group
                if point_groups == "32" and lattice == "hP":
                    point_groups = info.name[:-1]
                if point_groups != point_groups0:
                    result["point_groups"]["value"] = point_groups
        #
        return result

    def update_indexing_solution(self, values):
        """Update pulldowns when selected indexing solution changes"""
        solution = values.get("indexing_solution")
        for lattice in crystal_symmetry.UI_LATTICES:
            if lattice and lattice in solution:
                # values_map.set_values(lattice=lattice)
                values1 = dict(values)
                values1["lattice"] = lattice
                result = self.update_lattice(values1)
                result["lattice"] = {
                    "value": lattice,
                    "options": {
                        "value_dict": OrderedDict(
                            ((tag, tag) for tag in alternative_lattices[lattice])
                        ),
                    },
                }
                break
        else:
            result = {}
        #
        return result

    def adjust_dose(self, values):
        """When transmission, image_width, exposure or repetition_count changes,
        update experiment_time and use_dose in parameter popup, and reset warnings"""
        data_model = self._queue_entry.get_data_model()
        exposure_time = float(values.get("exposure", 0))
        image_width = float(values.get("image_width", 0))
        transmission = float(values.get("transmission", 0))
        dose_budget = float(values.get("dose_budget", 0))
        repetition_count = int(values.get("repetition_count", 1))
        if image_width and exposure_time:
            maximum_dose = data_model.calc_maximum_dose(
                exposure_time=exposure_time, image_width=image_width
            )
            experiment_time = (
                exposure_time * data_model.total_strategy_length / image_width
            )
            result = {"experiment_time": {"value": experiment_time}}
            if maximum_dose and transmission:
                # If we get here, Adjust dose
                # NB dose is calculated for *one* repetition
                use_dose = maximum_dose * transmission / 100
                result["use_dose"] = {"value": use_dose}
                if (
                    use_dose
                    and dose_budget
                    and use_dose * repetition_count > dose_budget
                ):
                    result["use_dose"]["highlight"] = "WARNING"
                    result["dose_budget"] = {"highlight": "WARNING"}
                else:
                    result["use_dose"]["highlight"] = "OK"
                    result["dose_budget"] = {"highlight": "OK"}
            return result
        else:
            return {}

    def adjust_transmission(self, values):
        """When use_dose changes, update transmission and/or exposure_time
        In parameter popup"""
        data_model = self._queue_entry.get_data_model()
        exposure_limits = HWR.beamline.detector.get_exposure_time_limits()
        exposure_time = float(values.get("exposure", 0))
        image_width = float(values.get("image_width", 0))
        use_dose = float(values.get("use_dose", 0))
        dose_budget = float(values.get("dose_budget", 0))
        transmission = float(values.get("transmission", 0))
        repetition_count = int(values.get("repetition_count", 1))

        result = {}
        if image_width and exposure_time:
            maximum_dose = data_model.calc_maximum_dose(
                exposure_time=exposure_time, image_width=image_width
            )
            experiment_time = (
                exposure_time * data_model.total_strategy_length / image_width
            )
            if maximum_dose and use_dose:
                new_transmission = 100 * use_dose / maximum_dose

                if new_transmission > 100.0:
                    # Transmission too high. Try max transmission and longer exposure
                    new_exposure_time = exposure_time * new_transmission / 100
                    new_transmission = 100.0
                    max_exposure = exposure_limits[1]
                    if max_exposure and new_exposure_time > max_exposure:
                        # exposure_time over max; set dose to highest achievable dose
                        new_exposure_time = max_exposure
                    new_experiment_time = (
                        experiment_time * new_exposure_time / exposure_time
                    )
                    use_dose = data_model.calc_maximum_dose(
                        exposure_time=new_exposure_time, image_width=image_width
                    )
                    result = {
                        "exposure": {"value": new_exposure_time,},
                        "transmission": {"value": new_transmission,},
                        "use_dose": {"value": use_dose,},
                        "experiment_time": {"value": new_experiment_time,},
                    }
                elif new_transmission < transmission:
                    # Try reducing exposure time instead
                    new_exposure_time = exposure_time * new_transmission / transmission
                    new_transmission = transmission
                    min_exposure = exposure_limits[0]
                    if min_exposure and new_exposure_time < min_exposure:
                        # exposure_time below min; reduce new transmission to match
                        new_transmission = (
                            transmission * new_exposure_time / min_exposure
                        )
                        new_exposure_time = min_exposure
                    result = {
                        "transmission": {"value":new_transmission},
                        "exposure": {"value":new_exposure_time},
                    }
                else:
                    result = {"transmission": {"value":new_transmission}}
                if (
                    use_dose
                    and dose_budget
                    and use_dose * repetition_count > dose_budget
                ):
                    dd0 = result.setdefault("use_dose", {})
                    dd0["highlight"] = "WARNING"
                    result["dose_budget"] = {"highlight": "WARNING"}
                else:
                    dd0 = result.setdefault("use_dose", {})
                    dd0["highlight"] = "OK"
                    result["dose_budget"] = {"highlight": "OK"}
        #
        return result
