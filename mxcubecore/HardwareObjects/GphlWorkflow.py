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
import uuid
import time
import datetime
import os
import math
import subprocess
import json
import socket
from collections import OrderedDict

import gevent
import gevent.event
import gevent.queue
import f90nml

from mxcubecore.dispatcher import dispatcher
from mxcubecore.utils import conversion
from mxcubecore.BaseHardwareObjects import HardwareObjectYaml
from mxcubecore.HardwareObjects import queue_model_objects
from mxcubecore.HardwareObjects import queue_model_enumerables
from mxcubecore.HardwareObjects.queue_entry import QUEUE_ENTRY_STATUS
from mxcubecore.HardwareObjects.queue_entry import QueueAbortedException

from mxcubecore.HardwareObjects.Gphl import GphlMessages

from mxcubecore import HardwareRepository as HWR


__copyright__ = """ Copyright © 2016 - 2019 by Global Phasing Ltd. """
__license__ = "LGPLv3+"
__author__ = "Rasmus H Fogh"

# Additional sample/diffraction plan data for GPhL emulation samples.
EMULATION_DATA = {"3n0s": {"radiationSensitivity": 0.9}}

# Centring modes for use in centring mode pulldown.
# The dictionary keys are labels (changeable),
# the values are passed to the program (not changeable)
# The first value is the default
RECENTRING_MODES = OrderedDict(
    (
        ("Re-centre when orientation changes", "sweep"),
        ("Re-centre at the start of each wedge", "scan"),
        ("Re-centre all before acquisition start", "start"),
        ("No manual re-centring, rely on calculated values", "none"),
    )
)


class GphlWorkflow(HardwareObjectYaml):
    """Global Phasing workflow runner.
    """

    TEST_SAMPLE_PREFIX = "emulate"

    def __init__(self, name):
        super(GphlWorkflow, self).__init__(name)

        # Needed to allow methods to put new actions on the queue
        # And as a place to get hold of other objects
        self._queue_entry = None

        # Configuration data - set when queried
        self.workflows = {}
        self.settings = {}

        # Current data collection group. Different for characterisation and collection
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

    def _init(self):
        super(GphlWorkflow, self)._init()

    def init(self):
        super(GphlWorkflow, self).init()

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

        detector = HWR.beamline.detector
        if "Mockup" in detector.__class__.__name__:
            # We are in mock  mode
            # - set detector centre to match instrumentaiton.nml
            # NB this sould be done with isinstance, but that seems to fail,
            # probably because of import path mix-ups.
            detector._set_beam_centre(
                (instrument_data["det_org_x"], instrument_data["det_org_y"])
            )

        # Adapt configuration data - must be done after file_paths setting
        if HWR.beamline.gphl_connection.ssh_options:
            # We are running workflow through ssh - set beamline url
            beamline_hook ="py4j:%s:" % socket.gethostname()
        else:
            beamline_hook = "py4j::"

        # Consolidate workflow options
        for title, workflow in self.workflows.items():
            workflow["wfname"] = title

            opt0 = workflow.get("options", {})
            opt0["beamline"] = beamline_hook
            default_strategy_name = None
            for strategy in workflow["strategies"]:
                if default_strategy_name is None:
                    default_strategy_name = workflow["strategy_name"] = (
                        strategy["title"]
                    )
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

    def shutdown(self):
        """Shut down workflow and connection. Triggered on program quit."""
        workflow_connection = HWR.beamline.gphl_connection
        if workflow_connection is not None:
            workflow_connection.workflow_ended()
            workflow_connection.close_connection()

    def get_settings(self):
        """Get dictionary of workflow settings"""
        return copy.deepcopy(self.settings)

    def get_available_workflows(self):
        """Get list of workflow description dictionaries."""
        return copy.deepcopy(self.workflows)

    def query_pre_strategy_params(self, data_model, choose_lattice=None):
        """
        choose_lattice is the Message object, passed in at teh select_lattice stage
        """
        #
        return {}

    def query_pre_collection_params(self, data_model):
        """
        """
        #
        return {}


    def pre_execute(self, queue_entry):

        if self.is_ready():
            self.update_state(self.STATES.BUSY)
        else:
            raise RuntimeError(
                "Cannot execute workflow - GphlWorkflow HardwareObject is not ready"
            )
        self._queue_entry = queue_entry
        data_model = queue_entry.get_data_model()
        self._workflow_queue = gevent.queue.Queue()
        HWR.beamline.gphl_connection.open_connection()
        if not data_model.automation_mode:
            # SIGNAL TO GET Pre-strategy parameters here
            # NB set defaults from data_model
            # NB consider whether to override on None
            params = self.query_pre_strategy_params(data_model)
            data_model.set_pre_strategy_params(**params)
        if data_model.detector_setting is None:
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
                logging.getLogger("HWR").debug("GPhL queue StopIteration")
                break

            message_type, payload, correlation_id, result_list = tt0
            func = self._processor_functions.get(message_type)
            if func is None:
                logging.getLogger("HWR").error(
                    "GPhL message %s not recognised by MXCuBE. Terminating...",
                    message_type,
                )
                break
            elif message_type != "String":
            # else:
                logging.getLogger("HWR").info("GPhL queue processing %s", message_type)
                response = func(payload, correlation_id)
                if result_list is not None:
                    result_list.append((response, correlation_id))

    def post_execute(self):
        """
        The workflow has finished, sets the state to 'READY'
        """

        self._queue_entry = None
        self._data_collection_group = None
        self.update_state(self.STATES.READY)
        self._server_subprocess_names.clear()
        self._workflow_queue = None
        if HWR.beamline.gphl_connection is not None:
            HWR.beamline.gphl_connection.workflow_ended()

    def return_parameters(self, queueu_entry):
        self._return_parameters.set(queueu_entry)

    # def stop_iteration(self):
    #     self._return_parameters.set(StopIteration)

    def _add_to_queue(self, parent_model_obj, child_model_obj):
        HWR.beamline.queue_model.add_child(parent_model_obj, child_model_obj)

    # Message handlers:

    def workflow_aborted(self, payload, correlation_id):
        logging.getLogger("user_level_log").warning("GPhL Workflow aborted.")
        self._workflow_queue.put_nowait(StopIteration)

    def workflow_completed(self, payload, correlation_id):
        logging.getLogger("user_level_log").info("GPhL Workflow completed.")
        self._workflow_queue.put_nowait(StopIteration)

    def workflow_failed(self, payload, correlation_id):
        logging.getLogger("user_level_log").warning("GPhL Workflow failed.")
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

    def query_collection_strategy(self, geometric_strategy, initial_energy):
        """Display collection strategy for user approval,
        and query parameters needed"""

        data_model = self._queue_entry.get_data_model()
        wf_parameters = data_model.get_workflow_parameters()

        orientations = OrderedDict()
        strategy_length = 0
        axis_setting_dicts = OrderedDict()
        for sweep in geometric_strategy.get_ordered_sweeps():
            strategy_length += sweep.width
            rotation_id = sweep.goniostatSweepSetting.id_
            if rotation_id in orientations:
                orientations[rotation_id].append(sweep)
            else:
                orientations[rotation_id] = [sweep]
                axis_settings = sweep.goniostatSweepSetting.axisSettings.copy()
                axis_settings.pop(sweep.goniostatSweepSetting.scanAxis, None)
                axis_setting_dicts[rotation_id] = axis_settings

        # Make info_text and do some setting up
        axis_names = self.rotation_axis_roles
        if (
            data_model.characterisation_done
            or wf_parameters.get("strategy_type") == "diffractcal"
        ):
            lines = ["%s strategy" % self._queue_entry.get_data_model().get_type()]
            lines.extend(("-" * len(lines[0]), ""))
            # Data collection TODO: Use workflow info to distinguish
            beam_energies = OrderedDict()
            energies = [initial_energy, initial_energy + 0.01, initial_energy - 0.01]
            for ii, tag in enumerate(data_model.get_beam_energy_tags()):
                beam_energies[tag] = energies[ii]
            budget_use_fraction = 1.0
            dose_label = "Total dose (MGy)"

        else:
            # Characterisation
            lines = ["Characterisation strategy"]
            lines.extend(("=" * len(lines[0]), ""))
            beam_energies = OrderedDict((("Characterisation", initial_energy),))
            budget_use_fraction = data_model.get_characterisation_budget_fraction()
            dose_label = "Charcterisation dose (MGy)"
            if not self.settings.get("recentre_before_start"):
                # replace planned orientation with current orientation
                current_pos_dict = HWR.beamline.diffractometer.get_motor_positions()
                dd0 = list(axis_setting_dicts.values())[0]
                for tag in dd0:
                    pos = current_pos_dict.get(tag)
                    if pos is not None:
                        dd0[tag] = pos

        if len(beam_energies) > 1:
            lines.append(
                "Experiment length: %s * %6.1f°" % (len(beam_energies), strategy_length)
            )
        else:
            lines.append("Experiment length: %6.1f°" % strategy_length)

        for rotation_id, sweeps in orientations.items():
            axis_settings = axis_setting_dicts[rotation_id]
            ss0 = "\nSweep :     " + ",  ".join(
                "%s= %6.1f°" % (x, axis_settings.get(x))
                for x in axis_names
                if x in axis_settings
            )
            ll1 = []
            for sweep in sweeps:
                start = sweep.start
                width = sweep.width
                ss1 = "%s= %6.1f°,  sweep width= %6.1f°" % (
                    sweep.goniostatSweepSetting.scanAxis, start, width
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
            decay_limit=data_model.get_decay_limit(),
            relative_sensitivity=data_model.get_relative_rad_sensitivity(),
        )
        default_image_width = float(allowed_widths[default_width_index])
        default_exposure = acq_parameters.exp_time
        exposure_limits = HWR.beamline.detector.get_exposure_time_limits()
        total_strategy_length = strategy_length * len(beam_energies)
        experiment_time = total_strategy_length * default_exposure / default_image_width
        proposed_dose = max(dose_budget * budget_use_fraction, 0.0)

        # For calculating dose-budget transmission
        flux_density = HWR.beamline.flux.get_average_flux_density(transmission=100.0)
        if flux_density:
            std_dose_rate = (
                HWR.beamline.flux.get_dose_rate_per_photon_per_mmsq(initial_energy)
                * flux_density
                * 1.0e-6  # convert to MGy/s
            )
        else:
            std_dose_rate = 0
        transmission = acq_parameters.transmission

        # define update functions

        def update_function(field_widget):
            """When image_width or exposure_time change,
             update rotation_rate, experiment_time and either use_dose or transmission
            In parameter popup"""
            parameters = field_widget.get_parameters_map()
            exposure_time = float(parameters.get("exposure", 0))
            image_width = float(parameters.get("imageWidth", 0))
            use_dose = float(parameters.get("use_dose", 0))
            transmission = float(parameters.get("transmission", 0))

            if image_width and exposure_time:
                rotation_rate = image_width / exposure_time
                experiment_time = total_strategy_length / rotation_rate
                dd0 = {
                    "rotation_rate": rotation_rate,
                    "experiment_time": experiment_time,
                }

                if std_dose_rate:
                    if use_dose:
                        use_dose -= data_model.get_dose_consumed()
                        transmission = (
                            100 * use_dose / (std_dose_rate * experiment_time)
                        )
                        if transmission > 100:
                            dd0["transmission"] = 100
                            dd0["use_dose"] = (
                                use_dose * 100 / transmission
                                + data_model.get_dose_consumed()
                            )
                        else:
                            dd0["transmission"] = transmission
                    elif transmission:
                        use_dose = std_dose_rate * experiment_time * transmission / 100
                        dd0["use_dose"] = use_dose + data_model.get_dose_consumed()
                field_widget.set_values(**dd0)

        def update_transmission(field_widget):
            """When transmission changes, update use_dose
            In parameter popup"""
            parameters = field_widget.get_parameters_map()
            exposure_time = float(parameters.get("exposure", 0))
            image_width = float(parameters.get("imageWidth", 0))
            transmission = float(parameters.get("transmission", 0))
            if image_width and exposure_time and std_dose_rate:
                experiment_time = exposure_time * total_strategy_length / image_width
                use_dose = std_dose_rate * experiment_time * transmission / 100
                field_widget.set_values(
                    use_dose=use_dose + data_model.get_dose_consumed()
                )

        def update_resolution(field_widget):

            parameters = field_widget.get_parameters_map()
            resolution = float(parameters.get("resolution"))
            dbg = self.resolution2dose_budget(
                resolution,
                decay_limit=data_model.get_decay_limit(),
                relative_sensitivity=data_model.get_relative_rad_sensitivity(),
            )
            field_widget.set_values(dose_budget=dbg)
            use_dose = dbg * budget_use_fraction
            if use_dose < std_dose_rate * experiment_time:
                field_widget.set_values(use_dose=use_dose)
                update_dose(field_widget)
            else:
                field_widget.set_values(transmission=100)
                update_transmission(field_widget)

        def update_dose(field_widget):
            """When use_dose changes, update transmission and/or exposure_time
            In parameter popup"""
            parameters = field_widget.get_parameters_map()
            exposure_time = float(parameters.get("exposure", 0))
            image_width = float(parameters.get("imageWidth", 0))
            use_dose = float(parameters.get("use_dose", 0))

            if image_width and exposure_time and std_dose_rate and use_dose:
                experiment_time = exposure_time * total_strategy_length / image_width
                # NB set_values causes successive upate calls for changed values
                use_dose -= data_model.get_dose_consumed()
                transmission = 100 * use_dose / (std_dose_rate * experiment_time)
                if transmission <= 100:
                    field_widget.set_values(transmission=transmission)
                else:
                    # Tranmision over max; adjust exposure_time to compensate
                    exposure_time = exposure_time * transmission / 100
                    if (
                        exposure_limits[1] is None
                        or exposure_time <= exposure_limits[1]
                    ):
                        field_widget.set_values(
                            exposure=exposure_time, transmission=100
                        )
                    else:
                        # exposure_time over max; set does to highest achievable
                        exposure_time = exposure_limits[1]
                        experiment_time = (
                            exposure_time * total_strategy_length / image_width
                        )
                        use_dose = std_dose_rate * experiment_time
                        field_widget.set_values(
                            exposure=exposure_time,
                            transmission=100,
                            use_dose=use_dose + data_model.get_dose_consumed(),
                        )

        reslimits = HWR.beamline.resolution.get_limits()
        if None in reslimits:
            reslimits = (0.5, 5.0)
        if std_dose_rate:
            use_dose_start = proposed_dose
            use_dose_frozen = False
        else:
            use_dose_start = 0
            use_dose_frozen = True
            logging.getLogger("user_level_log").warning(
                "Dose rate cannot be calculated - dose bookkeeping disabled"
            )

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
                "lowerBound": exposure_limits[0],
                "upperBound": exposure_limits[1],
                "decimals": 6,
                "update_function": update_function,
            },
            {
                "variableName": "dose_budget",
                "uiLabel": "Total dose budget (MGy)",
                "type": "floatstring",
                "defaultValue": dose_budget,
                "lowerBound": 0.0,
                "decimals": 4,
                "readOnly": True,
            },
            {
                "variableName": "use_dose",
                "uiLabel": dose_label,
                "type": "floatstring",
                "defaultValue": use_dose_start,
                "lowerBound": 0.01,
                "decimals": 4,
                "update_function": update_dose,
                "readOnly": use_dose_frozen,
            },
            # NB Transmission is in % in UI, but in 0-1 in workflow
            {
                "variableName": "transmission",
                "uiLabel": "Transmission (%)",
                "type": "floatstring",
                "defaultValue": transmission,
                "lowerBound": 0.0001,
                "upperBound": 100.0,
                "decimals": 4,
                "update_function": update_transmission,
            },
        ]
        # Add third column of non-edited values
        field_list[-1]["NEW_COLUMN"] = "True"
        field_list.append(
            {
                "variableName": "resolution",
                "uiLabel": "Detector resolution (A)",
                "type": "floatstring",
                "defaultValue": resolution,
                "lowerBound": reslimits[0],
                "upperBound": reslimits[1],
                "decimals": 3,
                "readOnly": False,
            }
        )
        if data_model.characterisation_done:
            field_list[-1]["readOnly"] = True
        else:
            field_list[-1]["update_function"] = update_resolution
        field_list.extend(
            [
                {
                    "variableName": "experiment_lengh",
                    "uiLabel": "Experiment length (°)",
                    "type": "text",
                    "defaultValue": str(int(total_strategy_length)),
                    "readOnly": True,
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
                    "uiLabel": "Rotation speed (°/s)",
                    "type": "floatstring",
                    "defaultValue": (float(default_image_width / default_exposure)),
                    "decimals": 1,
                    "readOnly": True,
                },
            ]
        )

        if data_model.characterisation_done and data_model.get_interleave_order():
            # NB We do not want the wedgeWdth widget for Diffractcal
            field_list.append(
                {
                    "variableName": "wedgeWidth",
                    "uiLabel": "Wedge width (deg)",
                    "type": "text",
                    "defaultValue": (
                        "%s" % self.settings.get("default_wedge_width", 15)
                    ),
                    "lowerBound": 0.1,
                    "upperBound": 7200,
                    "decimals": 2,
                }
            )

        field_list[-1]["NEW_COLUMN"] = "True"

        ll0 = []
        for tag, val in beam_energies.items():
            ll0.append(
                {
                    "variableName": tag,
                    "uiLabel": "%s beam energy (keV)" % tag,
                    "type": "floatstring",
                    "defaultValue": val,
                    "lowerBound": 2.0,
                    "upperBound": 30.0,
                    "decimals": 4,
                }
            )
        ll0[0]["readOnly"] = True
        field_list.extend(ll0)

        field_list.append(
            {
                "variableName": "snapshot_count",
                "uiLabel": "Number of snapshots",
                "type": "combo",
                "defaultValue": str(data_model.get_snapshot_count()),
                "textChoices": ["0", "1", "2", "4"],
            }
        )

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
        if data_model.get_interleave_order():
            use_modes.append("scan")
        if self.load_transcal_parameters() and (
            data_model.characterisation_done
            or wf_parameters.get("strategy_type") == "diffractcal"
        ):
            # Not Characteisation
            use_modes.append("none")
        for indx in range (len(modes) -1, -1, -1):
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
        if len(modes) > 1:
            field_list.append(
                {
                    "variableName": "recentring_mode",
                    "type": "dblcombo",
                    "defaultValue": default_label,
                    "textChoices": labels,
                }
            )

        self._return_parameters = gevent.event.AsyncResult()
        responses = dispatcher.send(
            "gphlParametersNeeded",
            self,
            field_list,
            self._return_parameters,
            update_function,
        )
        if not responses:
            self._return_parameters.set_exception(
                RuntimeError("Signal 'gphlParametersNeeded' is not connected")
            )

        params = self._return_parameters.get()
        self._return_parameters = None

        if params is StopIteration:
            result = StopIteration

        else:
            result = {}
            tag = "imageWidth"
            value = params.get(tag)
            if value:
                image_width = result[tag] = float(value)
            else:
                image_width = self.settings.get("default_image_width", 15)
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
            else:
                # If not set is likely not used, but we want a default value anyway
                result[tag] = 150
            tag = "resolution"
            value = params.get(tag)
            if value:
                result[tag] = float(value)

            tag = "snapshot_count"
            value = params.get(tag)
            if value:
                result[tag] = int(value)

            if geometric_strategy.isInterleaved:
                result["interleaveOrder"] = data_model.get_interleave_order()

            for tag in beam_energies:
                beam_energies[tag] = float(params.get(tag, 0))
            result["beam_energies"] = beam_energies

            tag = "recentring_mode"
            result[tag] = (
                RECENTRING_MODES.get(params.get(tag)) or default_recentring_mode
            )

            data_model.set_dose_budget(float(params.get("dose_budget", 0)))
            # Register the dose (about to be) consumed
            if std_dose_rate:
                data_model.set_dose_consumed(float(params.get("use_dose", 0)))
        #
        return result

    def setup_data_collection(self, payload, correlation_id):
        geometric_strategy = payload

        gphl_workflow_model = self._queue_entry.get_data_model()

        # MOCK ONLY! to reduce file size
        if (
            gphl_workflow_model.automation_mode
            and gphl_workflow_model.characterisation_done
        ):
            print ('@~@~ WARNING - step inserting image width to 1.0')
            gphl_workflow_model.image_width = 1.0
        strategy_type = gphl_workflow_model.get_workflow_parameters()[
            "strategy_type"
        ]
        sweeps = geometric_strategy.get_ordered_sweeps()
        # Calculate dose budget and default transimission
        gphl_workflow_model.strategy_length = len(gphl_workflow_model.wavelengths) * sum(
            sweep.width for sweep in sweeps
        )
        # if strategy_type == "diffractcal" or gphl_workflow_model.characterisation_done:
        #     resolution = gphl_workflow_model.detector_setting.resolution
        # else:
        #     resolution = gphl_workflow_model.char_detector_setting.resolution
        # NB dose_budget cnnot be pre-set, as it is overridden here
        dose_budget = gphl_workflow_model.get_default_dose_budget()
        if gphl_workflow_model.characterisation_done:
            dose_budget -= gphl_workflow_model.dose_consumed
        elif strategy_type != "diffractcal":
            dose_budget *= gphl_workflow_model.characterisation_budget_fraction
        gphl_workflow_model.dose_budget = dose_budget
        gphl_workflow_model.reset_transmission()

        if not gphl_workflow_model.automation_mode:
            # SiGNAL TO GET Pre-collection parameters here
            # NB set defaults from data_model
            # NB consider whether to override on None
            # NB update functions will be needed in UI
            params = self.query_pre_collection_params(gphl_workflow_model, geometric_strategy)
            gphl_workflow_model.set_pre_acquisition_params(**params)
            raise NotImplementedError()

            # NB from here to end of 'if' we now have old code that needs replacing

            # NB for any type of acquisition, energy and resolution are set before this point

            bst = geometric_strategy.defaultBeamSetting
            if bst and self.settings.get("starting_beamline_energy") == "configured":
                # Preset energy
                # First set beam_energy and give it time to settle,
                # so detector distance will trigger correct resolution later
                # TODO NBNB put in wait-till ready to make sure value settles
                HWR.beamline.energy.set_wavelength(bst.wavelength, timeout=30)
            initial_energy = HWR.beamline.energy.get_value()

            # NB - now pre-setting of detector has been removed, this gets
            # the current resolution setting, whatever it is
            initial_resolution = HWR.beamline.resolution.get_value()
            # Put resolution value in workflow model object
            gphl_workflow_model.set_detector_resolution(initial_resolution)

            # Get modified parameters from UI and confirm acquisition
            # Run before centring, as it also does confirm/abort
            parameters = self.query_collection_strategy(geometric_strategy, initial_energy)
            if parameters is StopIteration:
                return StopIteration
            user_modifiable = geometric_strategy.isUserModifiable
            if user_modifiable:
                # Query user for new rotationSetting and make it,
                logging.getLogger("HWR").warning(
                    "User modification of sweep settings not implemented. Ignored"
                )

            gphl_workflow_model.set_exposure_time(parameters.get("exposure" or 0.0))
            gphl_workflow_model.set_image_width(parameters.get("imageWidth" or 0.0))

            # Set transmission, detector_disance/resolution to final (unchanging) values
            # Also set energy to first energy value, necessary to get resolution consistent

            # Set beam_energies to match parameters
            # get wavelengths
            HC_OVER_E = conversion.HC_OVER_E
            beam_energies = parameters.pop("beam_energies")
            wavelengths = tuple(
                GphlMessages.PhasingWavelength(wavelength=HC_OVER_E / val, role=tag)
                for tag, val in beam_energies.items()
            )
            gphl_workflow_model.wavelengths = wavelengths

            transmission = parameters["transmission"]
            logging.getLogger("GUI").info(
                "GphlWorkflow: setting transmission to %7.3f %%" % (100.0 * transmission)
            )
            HWR.beamline.transmission.set_value(100 * transmission)
            gphl_workflow_model.transmission = transmission

            new_resolution = parameters.pop("resolution")
            if (
                new_resolution != initial_resolution
                and not gphl_workflow_model.characterisation_done
            ):
                logging.getLogger("GUI").info(
                    "GphlWorkflow: setting detector distance for resolution %7.3f A"
                    % new_resolution
                )
                # timeout in seconds: max move is ~2 meters, velocity 4 cm/sec
                HWR.beamline.resolution.set_value(new_resolution, timeout=60)

            snapshot_count = parameters.pop("snapshot_count", None)
            if snapshot_count is not None:
                gphl_workflow_model.set_snapshot_count(snapshot_count)

            gphl_workflow_model.recentring_mode = parameters.pop("recentring_mode")

        recentring_mode = gphl_workflow_model.recentring_mode

        if gphl_workflow_model.characterisation_done:
            # Data collection TODO: Use workflow info to distinguish
            new_dcg_name = "GPhL Data Collection"
        elif strategy_type == "diffractcal":
            new_dcg_name = "GPhL DiffractCal"
        else:
            new_dcg_name = "GPhL Characterisation"
        logging.getLogger("HWR").debug("setup_data_collection %s" % new_dcg_name)
        new_dcg_model = queue_model_objects.TaskGroup()
        new_dcg_model.set_enabled(True)
        new_dcg_model.set_name(new_dcg_name)
        new_dcg_model.set_number(
            gphl_workflow_model.get_next_number_for_name(new_dcg_name)
        )
        self._data_collection_group = new_dcg_model
        self._add_to_queue(gphl_workflow_model, new_dcg_model)

        recen_parameters = self.load_transcal_parameters()
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

        # For recentring mode start do settings in reverse order
        if recentring_mode == "start":
            sweepSettings.reverse()

        pos_dict = HWR.beamline.diffractometer.get_motor_positions()
        sweepSetting = sweepSettings[0]

        if (
            self.settings.get("recentre_before_start")
            and not gphl_workflow_model.characterisation_done
        ):
            # Sample has never been centred reliably.
            # Centre it at sweepsetting and put it into goniostatTranslations
            settings = dict(sweepSetting.axisSettings)
            qe = self.enqueue_sample_centring(motor_settings=settings)
            translation, current_pos_dict = self.execute_sample_centring(
                qe, sweepSetting
            )
            goniostatTranslations.append(translation)
            gphl_workflow_model.current_rotation_id = sweepSetting.id_
        else:
            # Sample was centred already, possibly during earlier characterisation
            # - use current position for recentring
            current_pos_dict = HWR.beamline.diffractometer.get_motor_positions()
        current_okp = tuple(current_pos_dict[role] for role in self.rotation_axis_roles)
        current_xyz = tuple(
            current_pos_dict[role] for role in self.translation_axis_roles
        )

        if recen_parameters:
            # Currrent position is now centred one way or the other
            # Update recentring parameters
            recen_parameters["ref_xyz"] = current_xyz
            recen_parameters["ref_okp"] = current_okp
            logging.getLogger("HWR").debug(
                "Recentring set-up. Parameters are: %s",
                sorted(recen_parameters.items()),
            )

        if goniostatTranslations:
            # We had recentre_before_start and already have the goniosatTranslation
            # matching the sweepSetting
            pass

        elif gphl_workflow_model.characterisation_done or strategy_type == "diffractcal":
            # Acquisition or diffractcal; crystal is already centred
            settings = dict(sweepSetting.axisSettings)
            okp = tuple(settings.get(x, 0) for x in self.rotation_axis_roles)
            maxdev = max(abs(okp[1] - current_okp[1]), abs(okp[2] - current_okp[2]))

            if recen_parameters:
                # recentre first sweep from okp
                translation_settings = self.calculate_recentring(
                    okp, **recen_parameters
                )
                logging.getLogger("HWR").debug(
                    "GPHL Recentring. okp, motors, %s, %s"
                    % (okp, sorted(translation_settings.items()))
                )
            else:
                # existing centring - take from current position
                translation_settings = dict(
                    (role, current_pos_dict.get(role))
                    for role in self.translation_axis_roles
                )

            tol = (
                self.settings.get("angular_tolerance", 1.0) if recen_parameters else 0.1
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
                    if recen_parameters:
                        translation = GphlMessages.GoniostatTranslation(
                            rotation=sweepSetting, **translation_settings
                        )
                        goniostatTranslations.append(translation)
                    else:
                        raise RuntimeError(
                            "Coding error, mode 'none' requires recen_parameters"
                        )
                else:
                    settings.update(translation_settings)
                    qe = self.enqueue_sample_centring(motor_settings=settings)
                    translation, dummy = self.execute_sample_centring(qe, sweepSetting)
                    goniostatTranslations.append(translation)
                    gphl_workflow_model.current_rotation_id = sweepSetting.id_
                    if recentring_mode == "start":
                        # We want snapshots in this mode,
                        # and the first sweepmis skipped in the loop below
                        okp = tuple(
                            int(settings.get(x, 0)) for x in self.rotation_axis_roles
                        )
                        self.collect_centring_snapshots("%s_%s_%s" % okp)

        elif not self.settings.get("recentre_before_start"):
            # Characterisation, and current position was pre-centred
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
        if not goniostatTranslations:
            raise RuntimeError(
                "Coding error, first sweepSetting should have been set here"
            )
        for sweepSetting in sweepSettings[1:]:
            settings = sweepSetting.get_motor_settings()
            if recen_parameters:
                # Update settings
                okp = tuple(settings.get(x, 0) for x in self.rotation_axis_roles)
                centring_settings = self.calculate_recentring(okp, **recen_parameters)
                logging.getLogger("HWR").debug(
                    "GPHL Recentring. okp, motors, %s, %s"
                    % (okp, sorted(centring_settings.items()))
                )
                settings.update(centring_settings)

            if recentring_mode == "start":
                # Recentre now, using updated values if available
                qe = self.enqueue_sample_centring(motor_settings=settings)
                translation, dummy = self.execute_sample_centring(qe, sweepSetting)
                goniostatTranslations.append(translation)
                gphl_workflow_model.current_rotation_id = sweepSetting.id_
                okp = tuple(int(settings.get(x, 0)) for x in self.rotation_axis_roles)
                self.collect_centring_snapshots("%s_%s_%s" % okp)
            elif recen_parameters:
                # put recalculated translations back to workflow
                translation = GphlMessages.GoniostatTranslation(
                    rotation=sweepSetting, **centring_settings
                )
                goniostatTranslations.append(translation)
            else:
                # Not supposed to centre, no recentring parameters
                # NB PK says 'just provide the centrings you actually have'
                # raise NotImplementedError(
                #     "For now must have recentring or mode 'start' or single sweep"
                # )
                # We do NOT have any sensible translation settings
                # Take the current settings because we need something.
                # Better to have a calibration, actually
                translation_settings = dict(
                    (role, pos_dict[role]) for role in self.translation_axis_roles
                )
                translation = GphlMessages.GoniostatTranslation(
                    rotation=sweepSetting, **translation_settings
                )
                goniostatTranslations.append(translation)

        gphl_workflow_model.goniostat_translations = goniostatTranslations

        # orgxy = HWR.beamline.detector.get_beam_position()
        # resolution = HWR.beamline.resolution.get_value()
        # distance = HWR.beamline.detector.distance.get_value()
        # dds = geometric_strategy.defaultDetectorSetting
        # if distance == dds.axisSettings.get("Distance"):
        #     id_ = dds._id
        # else:
        #     id_ = None
        # detectorSetting = GphlMessages.BcsDetectorSetting(
        #     resolution, id_=id_, orgxy=orgxy, Distance=distance
        # )
        # gphl_workflow_model.detector_setting = detectorSetting

        # Return SampleCentred message
        sampleCentred = GphlMessages.SampleCentred(gphl_workflow_model)
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
        software_paths = HWR.beamline.gphl_connection.software_paths
        infile = os.path.join(software_paths["GPHL_WDIR"], "temp_recen.in")
        recen_data = OrderedDict()
        indata = {"recen_list": recen_data}

        fp0 = self.file_paths.get("instrumentation_file")
        instrumentation_data = f90nml.read(fp0)["sdcp_instrument_list"]
        diffractcal_data = instrumentation_data

        fp0 = self.file_paths.get("diffractcal_file")
        try:
            diffractcal_data = f90nml.read(fp0)["sdcp_instrument_list"]
        except BaseException:
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
        envs = {"BDG_home":software_paths["BDG_home"]}
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

        gphl_workflow_model = self._queue_entry.get_data_model()

        if (
            gphl_workflow_model.automation_mode == "MASSIF1"
            and gphl_workflow_model.strategy_options["strategy_type"] != "diffractcal"
            and not gphl_workflow_model.characterisation_done
        ):
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
        # wf_parameters = gphl_workflow_model.get_workflow_parameters()
        # if (
        #     gphl_workflow_model.characterisation_done
        #     or wf_parameters.get("strategy_type") == "diffractcal"
        # ):
        #     snapshot_count = gphl_workflow_model.get_snapshot_count()
        # else:
        #     # Do not make snapshots during chareacterisation
        #     snapshot_count = 0
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
                    " scan count %s does not match repreat count %s"
                    % (scan_count, repeat_count)
                )
            # treat only the first scan
            scans = scans[:1]

        sweeps = set()
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
            acq_parameters.wavelength = wavelength
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
                    HWR.beamline.session.get_base_process_directory(), relative_image_dir
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

            goniostatRotation = sweep.goniostatSweepSetting
            rotation_id = goniostatRotation.id_
            initial_settings = sweep.get_initial_settings()
            if sweeps and (
                recentring_mode == "scan"
                or (
                    recentring_mode == "sweep"
                    and rotation_id != gphl_workflow_model.current_rotation_id
                )
            ):
                # Put centring on queue and collect using the resulting position
                # NB this means that the actual translational axis positions
                # will NOT be known to the workflow
                self.enqueue_sample_centring(
                    motor_settings=initial_settings, in_queue=True
                )
            else:
                # Collect using precalculated centring position
                initial_settings[goniostatRotation.scanAxis] = scan.start
                acq_parameters.centred_position = queue_model_objects.CentredPosition(
                    initial_settings
                )

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

            sweeps.add(sweep)


            if repeat_count and sweep_offset and self.settings.get("use_multitrigger"):
                # Multitrigger sweep - add in parameters.
                # NB if we are here ther can be only one scan
                acq_parameters.num_triggers = scan_count
                acq_parameters.num_images_per_trigger =  acq_parameters.num_images
                acq_parameters.num_images *= scan_count
                # NB this assumes sweepOffset is the offset between starting points
                acq_parameters.overlap = (
                    acq_parameters.num_images_per_trigger * acq_parameters.osc_range
                    - sweep_offset
                )
            data_collection = queue_model_objects.DataCollection([acq], crystal)
            data_collections.append(data_collection)

            data_collection.set_enabled(True)
            data_collection.set_name(path_template.get_prefix())
            data_collection.set_number(path_template.run_number)
            self._add_to_queue(self._data_collection_group, data_collection)
            if scan is not scans[-1]:
                dc_entry = queue_manager.get_entry_with_model(data_collection)
                dc_entry.in_queue = True

        data_collection_entry = queue_manager.get_entry_with_model(
            self._data_collection_group
        )

        dispatcher.send("gphlStartAcquisition", self, gphl_workflow_model)
        try:
            queue_manager.execute_entry(data_collection_entry)
        finally:
            dispatcher.send("gphlDoneAcquisition", self, gphl_workflow_model)
        self._data_collection_group = None

        if data_collection_entry.status == QUEUE_ENTRY_STATUS.FAILED:
            # TODO NBNB check if these status codes are corerct
            status = 1
        else:
            status = 0

        return GphlMessages.CollectionDone(
            status=status,
            proposalId=collection_proposal.id_,
        )

    def auto_select_solution(self, choose_lattice):
        """Select indeing solution automatically"""
        data_model = self._queue_entry.get_data_model()
        solution_format = choose_lattice.lattice_format

        # Must match bravaisLattices column
        lattices = choose_lattice.lattices

        # First letter must match first letter of BravaisLattice
        crystal_system = choose_lattice.crystalSystem
        if lattices and not crystal_system:
            # Get rom lattices if not set directly
            aset = set(lattice[0] for lattice in lattices)
            if len(aset) == 1:
                crystal_system = aset.pop()

        dd0 = self.parse_indexing_solution(solution_format, choose_lattice.solutions)
        starred = None
        system_fit = None
        lattice_fit = None
        for line in dd0["solutions"]:
            if "*" in  line:
                starred = line
                if crystal_system and crystal_system in line:
                    system_fit = line
                if lattices and any(x in line for x in lattices):
                    lattice_fit = line
        useline = lattice_fit or system_fit or starred
        if useline:
            logging.getLogger("user_level_log").info(
                "Selected iudexing solution", useline
            )
            solution = useline.split()
            if solution[0] == "*":
                del solution[0]
            return solution
        raise ValueError("No indexing solution found")

    def select_lattice(self, payload, correlation_id):

        choose_lattice = payload

        data_model = self._queue_entry.get_data_model()
        data_model.characterisation_done = True

        if data_model.automation_mode:
            solution = self.auto_select_solution(choose_lattice)

            if data_model.automation_mode == "MASSIF1":
                if not data_model.aimed_resolution:
                    raise ValueError(
                        "aimed_resolution must be set in MASSIF1 auto mode"
                    )
                # Resets detector_setting to match aimed_resolution
                data_model.detector_setting = None
                # NB resets detector_setting
                data_model.set_pre_strategy_params()
                distance = data_model.detector_setting.axisSettings["Distance"]
                HWR.beamline.detector.distance.set_value(distance, timeout=30)
            return GphlMessages.SelectedLattice(
                data_model,
                lattice_format=choose_lattice.lattice_format,
                solution=solution,
            )
        else:
            # SIGNAL TO GET Pre-strategy parameters here
            # NB set defaults from data_model
            # NB consider whether to override on None
            params = self.query_pre_strategy_params(data_model, choose_lattice)
            data_model.set_pre_strategy_params(**params)
            raise NotImplementedError()


        # solution_format = choose_lattice.lattice_format
        #
        # # Must match bravaisLattices colu_m
        # lattices = choose_lattice.lattices
        #
        # # First letter must match first letter of BravaisLattice
        # crystal_system = choose_lattice.crystalSystem

        # # Color green (figuratively) if matches lattices,
        # # or otherwise if matches crystalSystem
        #
        # dd0 = self.parse_indexing_solution(solution_format, choose_lattice.solutions)
        #
        # reslimits = HWR.beamline.resolution.get_limits()
        # resolution = HWR.beamline.resolution.get_value()
        # if None in reslimits:
        #     reslimits = (0.5, 5.0)
        # field_list = [
        #     {
        #         "variableName": "_cplx",
        #         "uiLabel": "Select indexing solution:",
        #         "type": "selection_table",
        #         "header": dd0["header"],
        #         "colours": None,
        #         "defaultValue": (dd0["solutions"],),
        #     },
        #     {
        #         "variableName": "resolution",
        #         "uiLabel": "Detector resolution (A)",
        #         "type": "floatstring",
        #         "defaultValue":resolution,
        #         "lowerBound": reslimits[0],
        #         "upperBound": reslimits[1],
        #         "decimals": 3,
        #         "readOnly": False,
        #     }
        # ]
        #
        # # colour matching lattices green
        # colour_check = lattices
        # if crystal_system and not colour_check:
        #     colour_check = (crystal_system,)
        # if colour_check:
        #     colours = [None] * len(dd0["solutions"])
        #     for ii, line in enumerate(dd0["solutions"]):
        #         if any(x in line for x in colour_check):
        #             colours[ii] = "LIGHT_GREEN"
        #     field_list[0]["colours"] = colours
        #
        # self._return_parameters = gevent.event.AsyncResult()
        # responses = dispatcher.send(
        #     "gphlParametersNeeded", self, field_list, self._return_parameters, None
        # )
        # if not responses:
        #     self._return_parameters.set_exception(
        #         RuntimeError("Signal 'gphlParametersNeeded' is not connected")
        #     )
        #
        # params = self._return_parameters.get()
        # if params is StopIteration:
        #     return StopIteration
        #
        # kwArgs = {}
        #
        # # NB We do not reset the wavelength at this point. We could, later
        # kwArgs["strategyWavelength"] = HWR.beamline.energy.get_wavelength()
        #
        # new_resolution = float(params.pop("resolution", 0))
        # if new_resolution:
        #     if new_resolution != resolution:
        #         logging.getLogger("GUI").info(
        #             "GphlWorkflow: setting detector distance for resolution %7.3f A"
        #             % new_resolution
        #         )
        #         # timeout in seconds: max move is ~2 meters, velocity 4 cm/sec
        #         HWR.beamline.resolution.set_value(new_resolution, timeout=60)
        #         resolution = new_resolution
        # kwArgs["strategyResolution"] = resolution
        #
        # ll0 = conversion.text_type(params["_cplx"][0]).split()
        # if ll0[0] == "*":
        #     del ll0[0]
        #
        # options = {}
        # maximum_chi = self.settings.get("maximum_chi")
        # if maximum_chi:
        #     options["maxmum_chi"] = float(maximum_chi)
        #
        # kwArgs["options"] = json.dumps(options, indent=4, sort_keys=True)
        # #
        # return GphlMessages.SelectedLattice(
        #     lattice_format=solution_format, solution=ll0
        # )

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
                        "defaultValue": info_text,
                    }
                ]
                self._return_parameters = gevent.event.AsyncResult()
                responses = dispatcher.send(
                    "gphlParametersNeeded",
                    self,
                    field_list,
                    self._return_parameters,
                    None,
                )
                if not responses:
                    self._return_parameters.set_exception(
                        RuntimeError("Signal 'gphlParametersNeeded' is not connected")
                    )

                # We do not need the result, just to end the waiting
                response = self._return_parameters.get()
                self._return_parameters = None
                if response is StopIteration:
                    return StopIteration

        settings = goniostatRotation.axisSettings.copy()
        if goniostatTranslation is not None:
            settings.update(goniostatTranslation.axisSettings)
        centring_queue_entry = self.enqueue_sample_centring(motor_settings=settings)
        goniostatTranslation, dummy = self.execute_sample_centring(
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

    def enqueue_sample_centring(self, motor_settings, in_queue=False):

        queue_manager = self._queue_entry.get_queue_controller()

        task_label = "Centring (kappa=%0.1f,phi=%0.1f)" % (
            motor_settings.get("kappa"),
            motor_settings.get("kappa_phi"),
        )
        centring_model = queue_model_objects.SampleCentring(
            name=task_label, motor_positions=motor_settings
        )
        self._add_to_queue(self._data_collection_group, centring_model)
        centring_entry = queue_manager.get_entry_with_model(centring_model)
        centring_entry.in_queue = in_queue

        return centring_entry

    def collect_centring_snapshots(self, file_name_prefix="snapshot"):
        """

        :param file_name_prefix: str
        :return:
        """

        gphl_workflow_model = self._queue_entry.get_data_model()
        number_of_snapshots = gphl_workflow_model.get_snapshot_count()
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
        queue_manager.execute_entry(centring_entry)

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
            self.abort("No Centring result found")

    def prepare_for_centring(self, payload, correlation_id):

        # TODO Add pop-up confirmation box ('Ready for centring?')

        return GphlMessages.ReadyForCentring()

    def obtain_prior_information(self, payload, correlation_id):

        workflow_model = self._queue_entry.get_data_model()

        # NBNB TODO check this is also OK in MXCuBE3
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

        priorInformation = GphlMessages.PriorInformation(workflow_model, image_root)
        #
        return priorInformation

    # Utility functions

    def resolution2dose_budget(self, resolution, decay_limit, relative_sensitivity=1.0):
        """

        Args:
            resolution (float): resolution in A
            decay_limit (float): min. intensity at resolution edge at experiment end (%)
            relative_sensitivity (float) : relative radiation sensitivity of crystal

        Returns (float): Dose budget (MGy)

        """
        """Get resolution-dependent dose budget using configured values"""
        max_budget = self.settings.get("maximum_dose_budget", 20)
        result = 2 * resolution * resolution * math.log(100.0 / decay_limit)
        #
        return min(result, max_budget) / relative_sensitivity

    def get_emulation_samples(self):
        """ Get list of lims_sample informatoin dictionaries for mock/emulation

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
                        for ii, tag in enumerate(("cellA", "cellB", "cellC")):
                            data[tag] = cell_lengths[ii]
                    if cell_angles:
                        for ii, tag in enumerate(
                            ("cellAlpha", "cellBeta", "cellGamma")
                        ):
                            data[tag] = cell_angles[ii]
                    if space_group:
                        data["crystalSpaceGroup"] = space_group

                    data["experimentType"] = "Default"
                    # data["proteinAcronym"] = self.TEST_SAMPLE_PREFIX
                    data["smiles"] = None
                    data["sampleId"] = 100000 + serial

                    # ISPyB docs:
                    # experimentKind: enum('Default','MAD','SAD','Fixed','OSC',
                    # 'Ligand binding','Refinement', 'MAD - Inverse Beam','SAD - Inverse Beam',
                    # 'MXPressE','MXPressF','MXPressO','MXPressP','MXPressP_SAD','MXPressI','MXPressE_SAD','MXScore','MXPressM',)
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

    def get_emulation_crystal_data(self, sample_name=None):
        """If sample is a test data set for emulation, get crystal data

        Returns:
            Optional[dict]
        """
        if sample_name is None:
            sample_name = (
                self._queue_entry.get_data_model().get_sample_node().get_name()
            )
        crystal_data = None
        hklfile = None
        if sample_name:
            sample_dir = HWR.beamline.gphl_connection.software_paths.get(
                "gphl_test_samples"
            )
            if not sample_dir:
                raise ValueError("Test sample requires gphl_test_samples dir specified")
            sample_dir = os.path.join(sample_dir, sample_name)
            if not os.path.isdir(sample_dir):
                raise RuntimeError("No emulation data found for ", sample_name)
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
        #
        return crystal_data, hklfile
