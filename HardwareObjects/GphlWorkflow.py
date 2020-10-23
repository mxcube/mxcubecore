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
along with MXCuBE.  If not, see <https://www.gnu.org/licenses/>.
"""
from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

import logging
import uuid
import time
import datetime
import os
import subprocess
import socket
from collections import OrderedDict

import gevent
import gevent.event
import gevent._threading

import f90nml

from HardwareRepository.dispatcher import dispatcher
from HardwareRepository import ConvertUtils
from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareObjects import queue_model_objects
from HardwareRepository.HardwareObjects import queue_model_enumerables
from HardwareRepository.HardwareObjects.queue_entry import QUEUE_ENTRY_STATUS

from HardwareRepository.HardwareObjects import GphlMessages

from HardwareRepository import HardwareRepository as HWR


__copyright__ = """ Copyright © 2016 - 2019 by Global Phasing Ltd. """
__license__ = "LGPLv3+"
__author__ = "Rasmus H Fogh"

States = queue_model_enumerables.States

# Used to pass to priorInformation when no wavelengths are set (DiffractCal)
DUMMY_WAVELENGTH = 999.999


class GphlWorkflow(HardwareObject, object):
    """Global Phasing workflow runner.
    """

    # object states
    valid_states = [
        States.OFF,  # Not active
        States.ON,  # Active, awaiting execution order
        States.OPEN,  # Active, awaiting input
        States.RUNNING,  # Active, executing workflow
    ]

    def __init__(self, name):
        super(GphlWorkflow, self).__init__(name)
        self._state = States.OFF

        # HO that handles connection to GPhL workflow runner
        self._workflow_connection = None

        # Needed to allow methods to put new actions on the queue
        # And as a place to get hold of other objects
        self._queue_entry = None

        # Current data colelction group. Different for characterisation and collection
        self._data_collection_group = None

        # event to handle waiting for parameter input
        self._return_parameters = None

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

        # Dose budget pulldown labels and default
        self.dose_budgets = OrderedDict()
        self.default_dose_budget_label = None

    def _init(self):
        super(GphlWorkflow, self)._init()

    def init(self):
        super(GphlWorkflow, self).init()

        # Get dose budget data
        default_dose_budget_label = None
        xx0 = next(self.getObjects("dose_budgets"))
        for pulldown_item in xx0.getObjects("pulldown_item"):
            dd0 = pulldown_item.getProperties()
            self.dose_budgets[dd0["label"]] = float(dd0["value"])
            if default_dose_budget_label is None or dd0.get("is_default"):
                default_dose_budget_label = dd0["label"]
        self.default_dose_budget_label = default_dose_budget_label

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

    def setup_workflow_object(self):
        """Necessary as this set-up cannot be done at init,
        when the hwobj are still incomplete. Must be called externally
        TODO This still necessary?"""

        # Set standard configurable file paths
        file_paths = self.file_paths
        ss0 = HWR.beamline.gphl_connection.software_paths["gphl_beamline_config"]
        file_paths["gphl_beamline_config"] = ss0
        file_paths["transcal_file"] = os.path.join(ss0, "transcal.nml")
        file_paths["diffractcal_file"] = os.path.join(ss0, "diffractcal.nml")
        file_paths["instrumentation_file"] = fp0 = os.path.join(
            ss0, "instrumentation.nml"
        )
        dd0 = f90nml.read(fp0)["sdcp_instrument_list"]
        self.rotation_axis_roles = dd0["gonio_axis_names"]
        self.translation_axis_roles = dd0["gonio_centring_axis_names"]

    def pre_execute(self, queue_entry):

        self._queue_entry = queue_entry

        if self.get_state() == States.OFF:
            HWR.beamline.gphl_connection.open_connection()
            self.set_state(States.ON)

    def shutdown(self):
        """Shut down workflow and connection. Triggered on program quit."""
        workflow_connection = HWR.beamline.gphl_connection
        if workflow_connection is not None:
            workflow_connection.workflow_ended()
            workflow_connection.close_connection()

    def get_available_workflows(self):
        """Get list of workflow description dictionaries."""

        # TODO this could be cached for speed

        result = OrderedDict()
        if self.hasObject("workflow_properties"):
            properties = self["workflow_properties"].getProperties().copy()
        else:
            properties = {}
        if self.hasObject("invocation_properties"):
            invocation_properties = self["invocation_properties"].getProperties().copy()
        else:
            invocation_properties = {}

        if self.hasObject("all_workflow_options"):
            all_workflow_options = self["all_workflow_options"].getProperties().copy()
            if "beamline" in all_workflow_options:
                pass
            elif HWR.beamline.gphl_connection.hasObject("ssh_options"):
                # We are running workflow through ssh - set beamline url
                all_workflow_options["beamline"] = "py4j:%s:" % socket.gethostname()
            else:
                all_workflow_options["beamline"] = "py4j::"
        else:
            all_workflow_options = {}

        acq_workflow_options = all_workflow_options.copy()
        acq_workflow_options.update(self["acq_workflow_options"].getProperties())
        # Add options for target directories:
        process_root = HWR.beamline.session.get_base_process_directory()
        acq_workflow_options["appdir"] = process_root

        mx_workflow_options = acq_workflow_options.copy()
        mx_workflow_options.update(self["mx_workflow_options"].getProperties())

        for wf_node in self["workflows"]:
            name = wf_node.name()
            strategy_type = wf_node.getProperty("strategy_type")
            wf_dict = {
                "name": name,
                "strategy_type": strategy_type,
                "application": wf_node.getProperty("application"),
                "documentation": wf_node.getProperty("documentation", default_value=""),
                "interleaveOrder": wf_node.getProperty(
                    "interleave_order", default_value=""
                ),
            }
            result[name] = wf_dict

            if strategy_type.startswith("transcal"):
                wf_dict["options"] = dd0 = all_workflow_options.copy()
                if wf_node.hasObject("options"):
                    dd0.update(wf_node["options"].getProperties())
                    relative_file_path = dd0.get("file")
                    if relative_file_path is not None:
                        # Special case - this option must be modified before use
                        dd0["file"] = os.path.join(
                            self.file_paths["gphl_beamline_config"], relative_file_path
                        )

            elif strategy_type.startswith("diffractcal"):
                wf_dict["options"] = dd0 = acq_workflow_options.copy()
                if wf_node.hasObject("options"):
                    dd0.update(wf_node["options"].getProperties())

            else:
                wf_dict["options"] = dd0 = mx_workflow_options.copy()
                if wf_node.hasObject("options"):
                    dd0.update(wf_node["options"].getProperties())
                if wf_node.hasObject("beam_energies"):
                    wf_dict["beam_energies"] = dd0 = OrderedDict()
                    for wavelength in wf_node["beam_energies"]:
                        dd0[wavelength.getProperty("role")] = wavelength.getProperty(
                            "value"
                        )

            wf_dict["properties"] = dd0 = properties.copy()
            if wf_node.hasObject("properties"):
                dd0.update(wf_node["properties"].getProperties())
            # Program-specific properties
            devmode = dd0.get("co.gphl.wf.devMode")
            if devmode and devmode[0] not in "fFnN":
                # We are in developer mode. Add parameters
                dd0["co.gphl.wf.stratcal.opt.--strategy_type"] = strategy_type

            wf_dict["invocation_properties"] = dd0 = invocation_properties.copy()
            if wf_node.hasObject("invocation_properties"):
                dd0.update(wf_node["invocation_properties"].getProperties())
        #
        return result

    def get_state(self):
        return self._state

    def set_state(self, value):
        if value in self.valid_states:
            self._state = value
            self.emit("stateChanged", (value,))
        else:
            raise RuntimeError("GphlWorlflow set to invalid state: s" % value)

    def workflow_end(self):
        """
        The workflow has finished, sets the state to 'ON'
        """

        self._queue_entry = None
        self._data_collection_group = None
        # if not self._gevent_event.is_set():
        #     self._gevent_event.set()
        self.set_state(States.ON)
        self._server_subprocess_names.clear()
        if HWR.beamline.gphl_connection is not None:
            HWR.beamline.gphl_connection.workflow_ended()

    def abort(self, message=None):
        logging.getLogger("HWR").info("MXCuBE aborting current GPhL workflow")
        if HWR.beamline.gphl_connection is not None:
            HWR.beamline.gphl_connection.abort_workflow(message=message)

    def execute(self):

        try:
            self.set_state(States.RUNNING)

            workflow_queue = gevent._threading.Queue()
            # Fork off workflow server process
            if HWR.beamline.gphl_connection is not None:
                HWR.beamline.gphl_connection.start_workflow(
                    workflow_queue, self._queue_entry.get_data_model()
                )

            while True:
                while workflow_queue.empty():
                    time.sleep(0.1)

                tt0 = workflow_queue.get_nowait()
                if tt0 is StopIteration:
                    break

                message_type, payload, correlation_id, result_list = tt0
                func = self._processor_functions.get(message_type)
                if func is None:
                    logging.getLogger("HWR").error(
                        "GPhL message %s not recognised by MXCuBE. Terminating...",
                        message_type,
                    )
                    break
                else:
                    logging.getLogger("HWR").info(
                        "GPhL queue processing %s", message_type
                    )
                    response = func(payload, correlation_id)
                    if result_list is not None:
                        result_list.append((response, correlation_id))

        except Exception:
            self.workflow_end()
            logging.getLogger("HWR").error(
                "Uncaught error during GPhL workflow execution", exc_info=True
            )
            raise

    def _add_to_queue(self, parent_model_obj, child_model_obj):
        # There should be a better way, but apparently there isn't
        HWR.beamline.queue_model.add_child(parent_model_obj, child_model_obj)

    # Message handlers:

    def workflow_aborted(self, payload, correlation_id):
        logging.getLogger("user_level_log").info("GPhL Workflow aborted.")

    def workflow_completed(self, payload, correlation_id):
        logging.getLogger("user_level_log").info("GPhL Workflow completed.")

    def workflow_failed(self, payload, correlation_id):
        logging.getLogger("user_level_log").info("GPhL Workflow failed.")

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

    def query_collection_strategy(self, geometric_strategy, default_energy):
        """Display collection strategy for user approval,
        and query parameters needed"""

        data_model = self._queue_entry.get_data_model()

        isInterleaved = geometric_strategy.isInterleaved
        allowed_widths = geometric_strategy.allowedWidths
        if allowed_widths:
            default_width_index = geometric_strategy.defaultWidthIdx or 0
        else:
            allowed_widths = [
                float(x) for x in self.getProperty("default_image_widths").split()
            ]
            val = allowed_widths[0]
            allowed_widths.sort()
            default_width_index = allowed_widths.index(val)
            logging.getLogger("HWR").info(
                "No allowed image widths returned by strategy - use defaults"
            )

        # NBNB TODO userModifiable

        # NBNB The geometric strategy is only given for ONE beamsetting
        # The strategy is (for now) repeated identical for all wavelengths
        # When this changes, more info will become available

        axis_names = self.rotation_axis_roles

        orientations = OrderedDict()
        strategy_length = 0
        for sweep in geometric_strategy.get_ordered_sweeps():
            strategy_length += sweep.width
            rotation_id = sweep.goniostatSweepSetting.id_
            sweeps = orientations.setdefault(rotation_id, [])
            sweeps.append(sweep)

        char_budget_fraction = data_model.get_characterisation_budget_fraction()
        relative_sensitivity = data_model.get_relative_rad_sensitivity()
        full_dose_budget = data_model.get_dose_budget() / relative_sensitivity
        lines = ["Geometric strategy   :"]
        if data_model.lattice_selected:
            # Data collection TODO: Use workflow info to distinguish
            beam_energies = data_model.get_beam_energies()
            total_strategy_length = strategy_length * len(beam_energies)
            # NB We no longer use the actual energies, only the tags
            # TODO clean up the configs to match
            energies = [default_energy, default_energy + 0.01, default_energy - 0.01]
            for ii, tag in enumerate(beam_energies):
                beam_energies[tag] = energies[ii]

            for tag, energy in beam_energies.items():
                # NB beam_energies is an ordered dictionary
                lines.append("- %-18s %6.1f degrees" % (tag, strategy_length))
            lines.append(
                "%-18s:  %6.1f degrees" % ("Total rotation", total_strategy_length)
            )
            # This is not characterisation but acuisition
            dose_budget = full_dose_budget = full_dose_budget * (
                1 - char_budget_fraction
            )

        else:
            # Charcterisation TODO: Use workflow info to distinguish h_o
            beam_energies = OrderedDict((("Characterisation", default_energy),))
            lines.append("    - Total rotation : %7.1f degrees" % strategy_length)
            total_strategy_length = strategy_length
            dose_budget = char_budget_fraction * full_dose_budget

        # For calculating dose-budget transmission
        std_dose_rate = HWR.beamline.flux.get_dose_rate()
        if std_dose_rate:
            std_dose_rate = (
                std_dose_rate * 100.0 / HWR.beamline.transmission.get_value()
            )
            # Convert from KGy/s to MGy/s
            std_dose_rate /= 1000

        for rotation_id, sweeps in orientations.items():
            goniostatRotation = sweeps[0].goniostatSweepSetting
            axis_settings = goniostatRotation.axisSettings
            scan_axis = goniostatRotation.scanAxis
            ss0 = "\nOrientation: " + ", ".join(
                "%s= %6.1f" % (x, axis_settings.get(x))
                for x in axis_names
                if x != scan_axis
            )
            lines.append(ss0)
            for sweep in sweeps:
                start = sweep.start
                width = sweep.width
                ss0 = "    - sweep %s=%8.1f, width= %s degrees" % (
                    scan_axis,
                    start,
                    width,
                )
                lines.append(ss0)
        info_text = "\n".join(lines)

        acq_parameters = HWR.beamline.get_default_acquisition_parameters()
        # For now return default values

        default_image_width = float(allowed_widths[default_width_index])
        default_exposure = acq_parameters.exp_time
        exposure_limits = HWR.beamline.detector.get_exposure_time_limits()
        experiment_time = total_strategy_length * default_exposure / default_image_width
        if std_dose_rate:
            transmission = 100.0 * dose_budget / (std_dose_rate * experiment_time)
            transmission = min(transmission, 100.0)

            def update_function(field_widget, experiment_length=total_strategy_length):
                """Function to update rotation_rate and budget_used fields
                In parameter popup"""
                parameters = field_widget.get_parameters_map()
                exposure_time = float(parameters.get("exposure", 0))
                image_width = float(parameters.get("imageWidth", 0))
                dose_budget = float(parameters.get("dose_budget", 0))
                transmission = float(parameters.get("transmission", 0))
                if image_width and exposure_time:
                    rotation_rate = image_width / exposure_time
                    experiment_time = experiment_length / rotation_rate
                else:
                    rotation_rate = experiment_time = 0.0
                if dose_budget:
                    budget_required = (
                        experiment_time * std_dose_rate * transmission / dose_budget
                    )
                else:
                    budget_required = 0

                dd0 = {
                    "rotation_rate": rotation_rate,
                    "experiment_time": experiment_time,
                    "budget_required": budget_required,
                }
                field_widget.set_values(dd0)

        else:
            update_function = None
            transmission = acq_parameters.transmission

        field_list = [
            {
                "variableName": "_info",
                "uiLabel": "Data collection plan",
                "type": "textarea",
                "defaultValue": info_text,
            },
            {
                "variableName": "imageWidth",
                "uiLabel": "Oscillation range",
                "type": "combo",
                "defaultValue": str(default_image_width),
                "textChoices": [str(x) for x in allowed_widths],
                "update_function": update_function,
            },
            {
                "variableName": "exposure",
                "uiLabel": "Exposure Time (s)",
                "type": "floatstring",
                "defaultValue": default_exposure,
                # NBNB TODO fill in from config ??
                "lowerBound": exposure_limits[0],
                "upperBound": exposure_limits[1],
                "decimals": 4,
                "update_function": update_function,
            },
            # NB Transmission is in % in UI, but in 0-1 in workflow
            {
                "variableName": "transmission",
                "uiLabel": "Transmission (%)",
                "type": "floatstring",
                "defaultValue": transmission,
                "lowerBound": 0.0,
                "upperBound": 100.0,
                "decimals": 2,
                "update_function": update_function,
            },
            {
                "variableName": "experiment_time",
                "uiLabel": "Experiment duration (s)",
                "type": "floatstring",
                "defaultValue": experiment_time,
                "decimals": 1,
                "readOnly": True,
            },
            {
                "variableName": "rotation_rate",
                "uiLabel": "Rotation speed (deg/s)",
                "type": "floatstring",
                "defaultValue": (float(default_image_width / default_exposure)),
                "decimals": 1,
                "readOnly": True,
            },
            {
                "variableName": "dose_budget",
                "uiLabel": "Dose budget (MGy)",
                "type": "floatstring",
                "defaultValue": full_dose_budget,
                "lowerBound": 0.0,
                "decimals": 1,
                "readOnly": True,
            },
            {
                "variableName": "budget_required",
                "uiLabel": "% of dose budget required",
                "type": "floatstring",
                "defaultValue": 0.0,
                "lowerBound": 0.0,
                "upperBound": 100.0,
                "decimals": 2,
                "readOnly": True,
            },
        ]

        field_list[-1]["NEW_COLUMN"] = "True"

        resolution = HWR.beamline.resolution.get_value()
        field_list.append(
            {
                "variableName": "resolution",
                "uiLabel": "Detector resolution (A)",
                "type": "floatstring",
                "defaultValue": resolution,
                "lowerBound": 0.0,
                "upperBound": 9.0,
                "decimals": 3,
            }
        )

        ll0 = []
        for tag, val in beam_energies.items():
            ll0.append(
                {
                    "variableName": tag,
                    "uiLabel": "%s beam energy (keV)" % tag,
                    "type": "floatstring",
                    "defaultValue": val,
                    "lowerBound": 4.0,
                    "upperBound": 20.0,
                    "decimals": 4,
                }
            )
        if self.getProperty("disable_energy_change", False):
            # Use current energy and disallow changes
            ll0[0]["defaultValue"] = HWR.beamline.energy.get_value()
            ll0[0]["readOnly"] = True
        field_list.extend(ll0)

        if (
            data_model.lattice_selected
            or "calibration" in data_model.get_type().lower()
        ):

            if isInterleaved:
                field_list.append(
                    {
                        "variableName": "wedgeWidth",
                        "uiLabel": "Wedge width (deg)",
                        "type": "text",
                        "defaultValue": (
                            "%s" % self.getProperty("default_wedge_width", 15)
                        ),
                        "lowerBound": 0,
                        "upperBound": 7200,
                        "decimals": 1,
                    }
                )

            field_list.append(
                {
                    "variableName": "centre_at_start",
                    "uiLabel": "(Re)centre crystal before acquisition start?",
                    "type": "boolean",
                    "defaultValue": bool(self.getProperty("centre_at_start")),
                }
            )

            if len(orientations) > 1:
                field_list.append(
                    {
                        "variableName": "centre_before_sweep",
                        "uiLabel": "(Re)centre crystal when orientation changes?",
                        "type": "boolean",
                        "defaultValue": bool(self.getProperty("centre_before_sweep")),
                    }
                )
            if isInterleaved:
                field_list.append(
                    {
                        "variableName": "centre_before_scan",
                        "uiLabel": "(Re)centre crystal at the start of each scan?",
                        "type": "boolean",
                        "defaultValue": bool(self.getProperty("centre_before_scan")),
                    }
                )
            if data_model.get_snapshot_count():
                field_list.append(
                    {
                        "variableName": "centring_snapshots",
                        "uiLabel": "Collect snapshots after each centring?",
                        "type": "boolean",
                        "defaultValue": False,
                    }
                )

        self._return_parameters = gevent.event.AsyncResult()
        responses = dispatcher.send(
            "gphlParametersNeeded", self, field_list, self._return_parameters
        )
        if not responses:
            self._return_parameters.set_exception(
                RuntimeError("Signal 'gphlParametersNeeded' is not connected")
            )

        params = self._return_parameters.get()
        self._return_parameters = None
        result = {}
        tag = "imageWidth"
        value = params.get(tag)
        if value:
            image_width = result[tag] = float(value)
        else:
            image_width = self.getProperty("default_image_width", 15)
        tag = "exposure"
        value = params.get(tag)
        if value:
            result[tag] = float(value)
        tag = "transmission"
        value = params.get(tag)
        if value:
            # Convert from % to fraction
            result[tag] = float(value) / 100
        tag = "wedgeWidth"
        value = params.get(tag)
        if value:
            result[tag] = int(float(value) / image_width)
        tag = "resolution"
        value = params.get(tag)
        if value:
            value = float(value)
            result["resolution"] = value

        if isInterleaved:
            result["interleaveOrder"] = data_model.get_interleave_order()

        for tag in beam_energies:
            beam_energies[tag] = float(params.get(tag, 0))
        result["beam_energies"] = beam_energies

        for tag in (
            "centre_before_sweep",
            "centre_at_start",
            "centre_before_scan",
            "centring_snapshots",
        ):
            # This defaults to False if parameter is not queried
            result[tag] = bool(params.get(tag))

        if not data_model.lattice_selected:
            # About to collect characterisation or calibration data
            # Update char_budget_fraction to reflect remaining dose budget
            budget_used = float(params.get("budget_required", 0.0))
            data_model.set_characterisation_budget_fraction(budget_used / 100.0)

        return result

    def setup_data_collection(self, payload, correlation_id):
        geometric_strategy = payload

        gphl_workflow_model = self._queue_entry.get_data_model()

        # enqueue data collection group
        if gphl_workflow_model.lattice_selected:
            # Data collection TODO: Use workflow info to distinguish
            new_dcg_name = "GPhL Data Collection"
        else:
            new_dcg_name = "GPhL Characterisation"
        new_dcg_model = queue_model_objects.TaskGroup()
        new_dcg_model.set_enabled(True)
        new_dcg_model.set_name(new_dcg_name)
        new_dcg_model.set_number(
            gphl_workflow_model.get_next_number_for_name(new_dcg_name)
        )
        self._data_collection_group = new_dcg_model
        self._add_to_queue(gphl_workflow_model, new_dcg_model)

        # Preset energy
        beamSetting = geometric_strategy.defaultBeamSetting
        if beamSetting and not self.getProperty("disable_energy_change"):
            # First set beam_energy and give it time to settle,
            # so detector distance will trigger correct resolution later
            default_energy = ConvertUtils.H_OVER_E / beamSetting.wavelength
            # TODO NBNB put in wait-till ready to make sure value settles
            HWR.beamline.energy.set_value(default_energy)
        else:
            default_energy = HWR.beamline.energy.get_value()

        # Preset detector distance and resolution
        detectorSetting = geometric_strategy.defaultDetectorSetting
        if detectorSetting:
            # NBNB If this is ever set to editable, distance and resolution
            # must be varied in sync
            HWR.beamline.detector.distance.set_value(
                detectorSetting.axisSettings.get("Distance")
            )
        # TODO NBNB put in wait-till-ready to make sure value settles
        HWR.beamline.detector.wait_ready()
        strategy_resolution = HWR.beamline.resolution.get_value()
        # Put resolution value in workflow model object
        gphl_workflow_model.set_detector_resolution(strategy_resolution)

        # Get modified parameters and confirm acquisition
        # Run before centring, as it also does confirm/abort
        parameters = self.query_collection_strategy(geometric_strategy, default_energy)
        user_modifiable = geometric_strategy.isUserModifiable
        if user_modifiable:
            # Query user for new rotationSetting and make it,
            logging.getLogger("HWR").warning(
                "User modification of sweep settings not implemented. Ignored"
            )

        # Set up centring and recentring
        goniostatTranslations = []
        recen_parameters = {}
        queue_entries = []
        sweeps = geometric_strategy.get_ordered_sweeps()
        transcal_parameters = self.load_transcal_parameters()

        # First sweep in list for a given sweepSetting
        first_sweeps = []
        aset = set()
        for sweep in sweeps:
            sweepSettingId = sweep.goniostatSweepSetting.id_
            if sweepSettingId not in aset:
                first_sweeps.append(sweep)
                aset.add(sweepSettingId)

        # Decide whether to centre before individual sweeps
        centre_at_start = parameters.pop("centre_at_start", False)
        centring_snapshots = parameters.pop("centring_snapshots", False)
        centre_before_sweep = parameters.pop("centre_before_sweep", False)
        centre_before_scan = parameters.pop("centre_before_scan", False)
        gphl_workflow_model.set_centre_before_sweep(centre_before_sweep)
        gphl_workflow_model.set_centre_before_scan(centre_before_scan)
        if not (
            centre_before_sweep
            or centre_before_scan
            or centre_at_start
            or transcal_parameters
        ):
            centre_at_start = True

        # Loop over first sweep occurrences and (re)centre
        # NB we do it reversed so the first to acquire is the last to centre
        if centre_at_start:
            # If we centre at start, we want the first one to be centred last
            first_sweeps.reverse()
        for sweep in first_sweeps:
            sweepSetting = sweep.goniostatSweepSetting
            requestedRotationId = sweepSetting.id_
            translation = sweepSetting.translation
            initial_settings = sweep.get_initial_settings()

            if translation is not None:
                # We already have a centring passed in (from stratcal, in practice)
                if centre_at_start:
                    qe = self.enqueue_sample_centring(motor_settings=initial_settings)
                    queue_entries.append(
                        (qe, sweepSetting, requestedRotationId, initial_settings)
                    )

            elif recen_parameters:
                # We have parameters for recentring (from previous orientation)
                okp = tuple(initial_settings[x] for x in self.rotation_axis_roles)
                dd0 = self.calculate_recentring(okp, **recen_parameters)
                logging.getLogger("HWR").debug(
                    "GPHL Recentring. okp, motors, %s, %s" + okp + sorted(dd0.items())
                )
                if centre_at_start:
                    motor_settings = initial_settings.copy()
                    motor_settings.update(dd0)
                    qe = self.enqueue_sample_centring(motor_settings=motor_settings)
                    queue_entries.append(
                        (qe, sweepSetting, requestedRotationId, motor_settings)
                    )
                else:
                    # Creating the Translation adds it to the Rotation
                    translation = GphlMessages.GoniostatTranslation(
                        rotation=sweepSetting,
                        requestedRotationId=requestedRotationId,
                        **dd0
                    )
                    logging.getLogger("HWR").debug(
                        "Recentring. okp=%s, %s", okp, sorted(dd0.items())
                    )
                    goniostatTranslations.append(translation)

            else:
                # No centring or recentring info
                if transcal_parameters:
                    # We can make recentring parameters.
                    # Centre now regardless and use parametters for successive sweeps
                    recen_parameters = transcal_parameters
                    qe = self.enqueue_sample_centring(motor_settings=initial_settings)
                    translation = self.execute_sample_centring(
                        qe, sweepSetting, requestedRotationId
                    )
                    if centring_snapshots:
                        dd0 = dict(
                            (x, initial_settings[x]) for x in self.rotation_axis_roles
                        )
                        self.collect_centring_snapshots(dd0)
                    goniostatTranslations.append(translation)
                    recen_parameters["ref_xyz"] = tuple(
                        translation.axisSettings[x] for x in self.translation_axis_roles
                    )
                    recen_parameters["ref_okp"] = tuple(
                        initial_settings[x] for x in self.rotation_axis_roles
                    )
                    logging.getLogger("HWR").debug(
                        "Recentring set-up. Parameters are: %s",
                        sorted(recen_parameters.items()),
                    )
                elif centre_at_start:
                    # Put on recentring queue
                    qe = self.enqueue_sample_centring(motor_settings=initial_settings)
                    queue_entries.append(
                        (qe, sweepSetting, requestedRotationId, initial_settings)
                    )

        for qe, goniostatRotation, requestedRotationId, settings in queue_entries:
            goniostatTranslations.append(
                self.execute_sample_centring(qe, goniostatRotation, requestedRotationId)
            )
            if centring_snapshots:
                dd0 = dict((x, settings[x]) for x in self.rotation_axis_roles)
                self.collect_centring_snapshots(dd0)

        # Set beamline to match parameters, and return SampleCentred message
        # get wavelengths
        h_over_e = ConvertUtils.H_OVER_E
        beam_energies = parameters.pop("beam_energies")
        wavelengths = list(
            GphlMessages.PhasingWavelength(wavelength=h_over_e / val, role=tag)
            for tag, val in beam_energies.items()
        )
        # set to wavelength of first energy
        # necessary so that resolution setting below gives right detector distance
        HWR.beamline.energy.set_wavelength(wavelengths[0].wavelength)
        # TODO ensure that move is finished before resolution is set

        # get BcsDetectorSetting
        new_resolution = parameters.pop("resolution")
        if new_resolution == strategy_resolution:
            id_ = detectorSetting.id_
        else:
            # TODO Clarify if set_position does not have a built-in wait
            # TODO whether you need towait for somethign else too, ...

            HWR.beamline.resolution.set_position(new_resolution)
            # TODO it should be set_position, fix TineMotor (resolution at EMBL)
            # HWR.beamline.resolution.set_value(new_resolution)
            HWR.beamline.detector.wait_ready()
            # NBNB Wait till value has settled
            id_ = None
        # orgxy = collect_hwobj.get_beam_centre_pix()
        orgxy = HWR.beamline.collect.get_beam_centre()
        detectorSetting = GphlMessages.BcsDetectorSetting(
            new_resolution,
            id_=id_,
            orgxy=orgxy,
            Distance=HWR.beamline.detector.distance.get_value(),
        )

        sampleCentred = GphlMessages.SampleCentred(
            goniostatTranslations=goniostatTranslations,
            wavelengths=wavelengths,
            detectorSetting=detectorSetting,
            **parameters
        )
        return sampleCentred

    def load_transcal_parameters(self):
        """Load home_position and cross_sec_of_soc from transcal.nml"""
        fp0 = self.file_paths.get("transcal_file")
        if os.path.isfile(fp0):
            try:
                transcal_data = f90nml.read(fp0)["sdcp_instrument_list"]
            except Exception:
                logging.getLogger("HWR").error(
                    "Error reading transcal.nml file: %s", fp0
                )
            else:
                result = {}
                result["home_position"] = transcal_data.get("trans_home")
                result["cross_sec_of_soc"] = transcal_data.get("trans_cross_sec_of_soc")
                if None in result.values():
                    logging.getLogger("HWR").warning("load_transcal_parameters failed")
                else:
                    return result
        else:
            logging.getLogger("HWR").warning("transcal.nml file not found: %s", fp0)
        # If we get here reading failed
        return {}

    def calculate_recentring(
        self, okp, home_position, cross_sec_of_soc, ref_okp, ref_xyz
    ):
        """Add predicted traslation values using recen
        okp is the omega,gamma,phi tuple of the target position,
        home_position is the translation calibration home position,
        and cross_sec_of_soc is the cross-section of the sphere of confusion
        ref_okp and ref_xyz are the reference omega,gamma,phi and the
        corresponding x,y,z translation position"""

        # Make input file
        gphl_workflow_model = self._queue_entry.get_data_model()
        infile = os.path.join(
            gphl_workflow_model.path_template.process_directory, "temp_recen.in"
        )
        recen_data = OrderedDict()
        indata = {"recen_list": recen_data}

        fp0 = self.file_paths.get("instrumentation_file")
        instrumentation_data = f90nml.read(fp0)["sdcp_instrument_list"]
        diffractcal_data = instrumentation_data

        fp0 = self.file_paths.get("diffractcal_file")
        try:
            diffractcal_data = f90nml.read(fp0)["sdcp_instrument_list"]
        except Exception:
            logging.getLogger("HWR").debug(
                "diffractcal file not present - using instrumentation.nml %s", fp0
            )
        ll0 = diffractcal_data["gonio_axis_dirs"]
        recen_data["omega_axis"] = ll0[:3]
        recen_data["kappa_axis"] = ll0[3:6]
        recen_data["phi_axis"] = ll0[6:]
        ll0 = instrumentation_data["gonio_centring_axis_dirs"]
        recen_data["trans_1_axis"] = ll0[:3]
        recen_data["trans_2_axis"] = ll0[3:6]
        recen_data["trans_3_axis"] = ll0[6:]
        recen_data["cross_sec_of_soc"] = cross_sec_of_soc
        recen_data["home"] = home_position
        #
        f90nml.write(indata, infile, force=True)

        # Get program locations
        recen_executable = HWR.beamline.gphl_connection.get_executable("recen")
        # Get environmental variables
        envs = {"BDG_home": HWR.beamline.gphl_connection.software_paths["BDG_home"]}
        # Run recen
        command_list = [
            recen_executable,
            "--input",
            infile,
            "--init-xyz",
            "%s %s %s" % ref_xyz,
            "--init-okp",
            "%s %s %s" % ref_okp,
            "--okp",
            "%s %s %s" % okp,
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
                    for ii, tag in enumerate(self.translation_axis_roles):
                        result[tag] = float(ll0[ii])
                    break

            elif ss0 == "NORMAL termination":
                terminated_ok = True
        else:
            logging.getLogger("HWR").error(
                "Recen failed with normal termination=%s. Output was:\n" % terminated_ok
                + output
            )
        #
        return result

    def collect_data(self, payload, correlation_id):
        collection_proposal = payload
        queue_manager = self._queue_entry.get_queue_controller()

        # NBNB creation and use of master_path_template is NOT in testing version yet
        gphl_workflow_model = self._queue_entry.get_data_model()
        master_path_template = gphl_workflow_model.path_template
        relative_image_dir = collection_proposal.relativeImageDir

        sample = gphl_workflow_model.get_sample_node()
        # There will be exactly one for the kinds of collection we are doing
        crystal = sample.crystals[0]
        if (
            gphl_workflow_model.lattice_selected
            or "calibration" in gphl_workflow_model.get_type().lower()
        ):
            snapshot_count = gphl_workflow_model.get_snapshot_count()
        else:
            # Do not make snapshots during chareacterisation
            snapshot_count = 0
        centre_before_scan = bool(gphl_workflow_model.get_centre_before_scan())
        enqueue_centring = (
            bool(gphl_workflow_model.get_centre_before_sweep()) or centre_before_scan
        )
        data_collections = []
        snapshot_counts = dict()
        found_orientations = set()
        for scan in collection_proposal.scans:
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
            acq_parameters.detector_distance = sweep.detectorSetting.axisSettings.get(
                "Distance"
            )
            acq_parameters.resolution = 0.0  # Use detector distance
            acq_parameters.energy = ConvertUtils.H_OVER_E / sweep.beamSetting.wavelength
            acq_parameters.transmission = scan.exposure.transmission * 100
            acq_parameters.inverse_beam = False

            # Edna also sets screening_id
            # Edna also sets osc_end

            # Path_template
            path_template = queue_model_objects.PathTemplate()
            # Naughty, but we want a clone, right?
            # NBNB this ONLY works because all the attributes are immutable values
            path_template.__dict__.update(master_path_template.__dict__)
            if relative_image_dir:
                path_template.directory = os.path.join(
                    path_template.directory, relative_image_dir
                )
                path_template.process_directory = os.path.join(
                    path_template.process_directory, relative_image_dir
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
            prefix = filename_params.get("prefix", "")
            ib_component = filename_params.get("inverse_beam_component_sign", "")
            ll0 = []
            if prefix:
                ll0.append(prefix)
            if ib_component:
                ll0.append(ib_component)
            path_template.base_prefix = "_".join(ll0)
            beam_setting_index = filename_params.get("beam_setting_index") or ""
            path_template.mad_prefix = beam_setting_index
            path_template.wedge_prefix = (
                filename_params.get("gonio_setting_index") or ""
            )
            path_template.start_num = acq_parameters.first_image
            path_template.num_files = acq_parameters.num_images

            goniostatRotation = sweep.goniostatSweepSetting
            if (
                enqueue_centring and goniostatRotation.id_ not in found_orientations
            ) or centre_before_scan:
                # Put centring on queue and collect using the resulting position
                # NB this means that the actual translational axis positions
                # will NOT be known to the workflow
                self.enqueue_sample_centring(
                    motor_settings=sweep.get_initial_settings()
                )
            else:
                # Collect using precalculated centring position
                dd0 = sweep.get_initial_settings()
                dd0[goniostatRotation.scanAxis] = scan.start
                acq_parameters.centred_position = queue_model_objects.CentredPosition(
                    dd0
                )
            found_orientations.add(goniostatRotation.id_)

            count = snapshot_counts.get(sweep, snapshot_count)
            acq_parameters.take_snapshots = count
            if (
                ib_component
                or beam_setting_index
                or not gphl_workflow_model.lattice_selected
            ):
                # Only snapshots first time a sweep is encountered
                # When doing inverse beam or wavelength interleaving
                # or canned strategies
                snapshot_counts[sweep] = 0

            data_collection = queue_model_objects.DataCollection([acq], crystal)
            data_collections.append(data_collection)

            data_collection.set_enabled(True)
            data_collection.set_name(path_template.get_prefix())
            data_collection.set_number(path_template.run_number)
            self._add_to_queue(self._data_collection_group, data_collection)

        data_collection_entry = queue_manager.get_entry_with_model(
            self._data_collection_group
        )
        queue_manager.execute_entry(data_collection_entry)
        self._data_collection_group = None

        if data_collection_entry.status == QUEUE_ENTRY_STATUS.FAILED:
            # TODO NBNB check if these status codes are corerct
            status = 1
        else:
            status = 0

        # NB, uses last path_template,
        # but directory should be the same for all
        return GphlMessages.CollectionDone(
            status=status,
            proposalId=collection_proposal.id_,
            # Only if you want to override prior information rootdir, which we do not
            # imageRoot=path_template.directory
        )

    def select_lattice(self, payload, correlation_id):
        choose_lattice = payload

        solution_format = choose_lattice.lattice_format

        # Must match bravaisLattices column
        lattices = choose_lattice.lattices

        # First letter must match first letter of BravaisLattice
        crystal_system = choose_lattice.crystalSystem

        # Color green (figuratively) if matches lattices,
        # or otherwise if matches crystalSystem

        dd0 = self.parse_indexing_solution(solution_format, choose_lattice.solutions)

        field_list = [
            {
                "variableName": "_cplx",
                "uiLabel": "Select indexing solution:",
                "type": "selection_table",
                "header": dd0["header"],
                "colours": None,
                "defaultValue": (dd0["solutions"],),
            }
        ]

        # colour matching lattices green
        colour_check = lattices
        if crystal_system and not colour_check:
            colour_check = (crystal_system,)
        if colour_check:
            colours = [None] * len(dd0["solutions"])
            for ii, line in enumerate(dd0["solutions"]):
                if any(x in line for x in colour_check):
                    colours[ii] = "LIGHT_GREEN"
            field_list[0]["colours"] = colours

        self._return_parameters = gevent.event.AsyncResult()
        responses = dispatcher.send(
            "gphlParametersNeeded", self, field_list, self._return_parameters
        )
        if not responses:
            self._return_parameters.set_exception(
                RuntimeError("Signal 'gphlParametersNeeded' is not connected")
            )

        params = self._return_parameters.get()
        ll0 = ConvertUtils.text_type(params["_cplx"][0]).split()
        if ll0[0] == "*":
            del ll0[0]
        #
        self._queue_entry.get_data_model().lattice_selected = True
        return GphlMessages.SelectedLattice(
            lattice_format=solution_format, solution=ll0
        )

    def parse_indexing_solution(self, solution_format, text):

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

        # find headers lines
        solutions = []
        if solution_format == "IDXREF":
            lines = text.splitlines()
            for indx, line in enumerate(lines):
                if "BRAVAIS-" in line:
                    # Used as marker for first header line
                    header = ["%s\n%s" % (line, lines[indx + 1])]
                    break
            else:
                raise ValueError("Substring 'BRAVAIS-' missing in %s indexing solution")

            for line in lines[indx:]:
                ss0 = line.strip()
                if ss0:
                    # we are skipping blank line at the start
                    if solutions or ss0[0] == "*":
                        # First real line will start with a '*
                        # Subsequent non-empty lines will also be used
                        solutions.append(line)
                elif solutions:
                    # we have finished - empty non-initial line
                    break

            #
            return {"header": header, "solutions": solutions}
        else:
            raise ValueError(
                "GPhL: Indexing format %s is not known" % repr(solution_format)
            )

    def process_centring_request(self, payload, correlation_id):
        # Used for transcal only - anything else is data collection related
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
            new_dcg_name = "GPhL Translational calibration"
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
                ll0 = zoom_motor.getPredefinedPositionsList()
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
                        "defaultValue": info_text,
                    }
                ]
                self._return_parameters = gevent.event.AsyncResult()
                responses = dispatcher.send(
                    "gphlParametersNeeded", self, field_list, self._return_parameters
                )
                if not responses:
                    self._return_parameters.set_exception(
                        RuntimeError("Signal 'gphlParametersNeeded' is not connected")
                    )

                # We do not need the result, just to end they waiting
                self._return_parameters.get()
                self._return_parameters = None

        settings = goniostatRotation.axisSettings.copy()
        if goniostatTranslation is not None:
            settings.update(goniostatTranslation.axisSettings)
        centring_queue_entry = self.enqueue_sample_centring(motor_settings=settings)
        goniostatTranslation = self.execute_sample_centring(
            centring_queue_entry, goniostatRotation
        )

        if request_centring.currentSettingNo >= request_centring.totalRotations:
            returnStatus = "DONE"
        else:
            returnStatus = "NEXT"
        #
        return GphlMessages.CentringDone(
            returnStatus,
            timestamp=time.time(),
            goniostatTranslation=goniostatTranslation,
        )

    def enqueue_sample_centring(self, motor_settings):

        queue_manager = self._queue_entry.get_queue_controller()

        centring_model = queue_model_objects.SampleCentring(
            name="Centring (GPhL)", motor_positions=motor_settings
        )
        self._add_to_queue(self._data_collection_group, centring_model)
        centring_entry = queue_manager.get_entry_with_model(centring_model)

        return centring_entry

    def collect_centring_snapshots(self, motor_settings):

        filename_template = "%s_%s_%s_%s_%s.jpeg"

        gphl_workflow_model = self._queue_entry.get_data_model()
        snapshot_directory = os.path.join(
            gphl_workflow_model.path_template.get_archive_directory(),
            "centring_snapshots",
        )
        number_of_snapshots = gphl_workflow_model.get_snapshot_count()
        if number_of_snapshots:
            logging.getLogger("user_level_log").info(
                "Post-centring: Taking %d sample snapshot(s)", number_of_snapshots
            )
            HWR.beamline.diffractometer.move_motors(motor_settings)
            okp = tuple(int(motor_settings[x]) for x in self.rotation_axis_roles)
            timestamp = datetime.datetime.now().isoformat().split(".")[0]
            summed_angle = 0.0
            for snapshot_index in range(number_of_snapshots):
                if snapshot_index:
                    HWR.beamline.diffractometer.move_omega_relative(90)
                    summed_angle += 90
                snapshot_filename = filename_template % (
                    okp + (timestamp, snapshot_index + 1)
                )
                snapshot_filename = os.path.join(snapshot_directory, snapshot_filename)
                logging.getLogger("HWR").debug(
                    "Centring snapshot stored at %s", snapshot_filename
                )
                HWR.beamline.collect._take_crystal_snapshot(snapshot_filename)
            if summed_angle:
                HWR.beamline.diffractometer.move_omega_relative(-summed_angle)

    def execute_sample_centring(
        self, centring_entry, goniostatRotation, requestedRotationId=None
    ):

        queue_manager = self._queue_entry.get_queue_controller()
        queue_manager.execute_entry(centring_entry)

        centring_result = centring_entry.get_data_model().get_centring_result()
        if centring_result:
            positionsDict = centring_result.as_dict()
            dd0 = dict((x, positionsDict[x]) for x in self.translation_axis_roles)
            return GphlMessages.GoniostatTranslation(
                rotation=goniostatRotation,
                requestedRotationId=requestedRotationId,
                **dd0
            )
        else:
            self.abort("No Centring result found")

    def prepare_for_centring(self, payload, correlation_id):

        # TODO Add pop-up confirmation box ('Ready for centring?')

        return GphlMessages.ReadyForCentring()

    def obtain_prior_information(self, payload, correlation_id):

        workflow_model = self._queue_entry.get_data_model()
        sample_model = workflow_model.get_sample_node()

        cell_params = workflow_model.get_cell_parameters()
        if cell_params:
            unitCell = GphlMessages.UnitCell(*cell_params)
        else:
            unitCell = None

        obj = queue_model_enumerables.SPACEGROUP_MAP.get(
            workflow_model.get_space_group()
        )
        space_group = obj.number if obj else None

        crystal_system = workflow_model.get_crystal_system()
        if crystal_system:
            crystal_system = crystal_system.upper()

        # NB Expected resolution is deprecated.
        # It is set to the current resolution value, for now
        userProvidedInfo = GphlMessages.UserProvidedInfo(
            scatterers=(),
            lattice=crystal_system,
            pointGroup=workflow_model.get_point_group(),
            spaceGroup=space_group,
            cell=unitCell,
            expectedResolution=HWR.beamline.resolution.get_value(),
            isAnisotropic=None,
        )
        ll0 = ["PriorInformation"]
        for tag in (
            "expectedResolution",
            "isAnisotropic",
            "lattice",
            "pointGroup",
            "scatterers",
            "spaceGroup",
        ):
            val = getattr(userProvidedInfo, tag)
            if val:
                ll0.append("%s=%s" % (tag, val))
        if cell_params:
            ll0.append("cell_parameters=%s" % (cell_params,))
        logging.getLogger("HWR").debug(", ".join(ll0))

        # Look for existing uuid
        for text in sample_model.lims_code, sample_model.code, sample_model.name:
            if text:
                try:
                    sampleId = uuid.UUID(text)
                except Exception:
                    # The error expected if this goes wrong is ValueError.
                    # But whatever the error we want to continue
                    pass
                else:
                    # Text was a valid uuid string. Use the uuid.
                    break
        else:
            sampleId = uuid.uuid1()

        image_root = HWR.beamline.session.get_base_image_directory()

        if not os.path.isdir(image_root):
            # This direstory must exist by the time the WF software checks for it
            try:
                os.makedirs(image_root)
            except Exception:
                # No need to raise error - program will fail downstream
                logging.getLogger("HWR").error(
                    "Could not create image root directory: %s", image_root
                )

        priorInformation = GphlMessages.PriorInformation(
            sampleId=sampleId,
            sampleName=(
                sample_model.name
                or sample_model.code
                or sample_model.lims_code
                or workflow_model.path_template.get_prefix()
                or ConvertUtils.text_type(sampleId)
            ),
            rootDirectory=image_root,
            userProvidedInfo=userProvidedInfo,
        )
        #
        return priorInformation
