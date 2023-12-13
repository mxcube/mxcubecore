#! /usr/bin/env python
# encoding: utf-8
"""Workflow connection, interfacing to external workflow engine
using py4j and Abstract Beamline Interface messages

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

import logging
import os
import subprocess
import uuid
import signal
import time
import sys

from py4j import clientserver, java_gateway

from mxcubecore.utils import conversion
from mxcubecore.HardwareObjects.Gphl import GphlMessages
from mxcubecore.model import crystal_symmetry

from mxcubecore.BaseHardwareObjects import HardwareObjectYaml
from mxcubecore import HardwareRepository as HWR

# NB this is patching the original socket module in to avoid the
# monkeypatched version we get from gevent - that causes errors.
# It depends on knowing where in py4j socket is imported
# Hacky, but the best solution to making py4j and gevent compatible

import socket
origsocket = sys.modules.pop("socket")
_origsocket = sys.modules.pop("_socket")
import socket

java_gateway.socket = socket
clientserver.socket = socket
sys.modules["socket"] = origsocket
sys.modules["_socket"] = _origsocket
del origsocket
del _origsocket

try:
    # This file already does the alternative imports plus some tweaking
    # TODO It ought to be moved out as an accessible Util file, but meanwhile
    # Here we take care of the case where it is missing.
    from mxcubecore.dispatcher import dispatcher
except ImportError:
    try:
        from louie import dispatcher
    except ImportError:
        from pydispatch import dispatcher
        from pydispatch import robustapply
        from pydispatch import saferef

        saferef.safe_ref = saferef.safeRef
        robustapply.robust_apply = robustapply.robustApply

__copyright__ = """ Copyright © 2016 - 2019 by Global Phasing Ltd. """
__license__ = "LGPLv3+"
__author__ = "Rasmus H Fogh"


class GphlWorkflowConnection(HardwareObjectYaml):
    """
    This HO acts as a gateway to the Global Phasing workflow engine.
    """

    def __init__(self, name):
        super().__init__(name)
        # Py4J gateway to external workflow program
        self._gateway = None

        # ID for current workflow calculation
        self._enactment_id = None

        # Queue for communicating with MXCuBE HardwareObject
        self.workflow_queue = None
        self._await_result = None
        self._running_process = None
        self.collect_emulator_process = None

        # Configured parameters
        self.directory_locations = {}
        self.ssh_options = {}
        self.gphl_subdir = "GPHL"
        self.gphl_persistname = "persistence"
        self.connection_parameters = {}
        self.software_paths = {}
        self.software_properties = {}

        self.update_state(self.STATES.UNKNOWN)

    def init(self):
        super().init()

        # Adapt connections if we are running via ssh
        if self.ssh_options:
            self.connection_parameters["python_address"] = socket.gethostname()

        # Adapt paths and properties to use directory_locations
        locations = self.directory_locations
        installdir = locations["GPHL_INSTALLATION"]
        paths = self.software_paths
        properties = self.software_properties

        for tag, val in paths.items():
            val2 = val.format(**locations)
            if not os.path.isabs(val2):
                val2 = HWR.get_hardware_repository().find_in_repository(val)
                if val2 is None:
                    raise ValueError("File path %s not recognised" % val)
            paths[tag] = val2
        paths["GPHL_INSTALLATION"] = locations["GPHL_INSTALLATION"]
        if "java_binary" not in paths:
            paths["java_binary"] = "java"
        paths[
            "gphl_java_classpath"
        ] = "%s/ASTRAWorkflows/config:%s/ASTRAWorkflows/lib/*" % (
            installdir,
            installdir,
        )

        for tag, val in properties.items():
            val2 = val.format(**locations)
            if not os.path.isabs(val2):
                val2 = HWR.get_hardware_repository().find_in_repository(val)
                if val2 is None:
                    raise ValueError("File path %s not recognised" % val)
            paths[tag] = properties[tag] = val2

        # Set master location, based on known release directory structure
        properties["co.gphl.wf.bin"] = os.path.join(
            locations["GPHL_INSTALLATION"], "exe"
        )
        if "GPHL_XDS_PATH" in paths:
            properties["co.gphl.wf.xds.bin"] = os.path.join(
                paths["GPHL_XDS_PATH"], "xds_par"
            )

        self.update_state(self.STATES.OFF)

    def to_java_time(self, time_in):
        """Convert time in seconds since the epoch (python time) to Java time value"""
        return self._gateway.jvm.java.lang.Long(int(time_in * 1000))

    def get_executable(self, name):
        """Get location of executable binary for program called 'name'"""
        tag = "co.gphl.wf.%s.bin" % name
        result = self.software_paths.get(tag)
        if not result:
            result = os.path.join(self.software_paths["GPHL_INSTALLATION"], "exe", name)
        #
        return result

    def get_bdg_licence_dir(self, name):
        """Get directory containing specific licence file (if any)
        for program called 'name'"""
        tag = "co.gphl.wf.%s.bdg_licence_dir" % name
        result = self.software_paths.get(tag)
        #
        return result

    def open_connection(self):

        if self._gateway is not None:
            logging.getLogger("HWR").debug("GΦL connection is already open")
            return

        params = self.connection_parameters

        python_parameters = {}
        val = params.get("python_address")
        if val is not None:
            python_parameters["address"] = val
        val = params.get("python_port")
        if val is not None:
            python_parameters["port"] = val

        java_parameters = {"auto_convert": True}
        val = params.get("java_address")
        if val is not None:
            java_parameters["address"] = val
        val = params.get("java_port")
        if val is not None:
            java_parameters["port"] = val

        logging.getLogger("HWR").debug(
            "Opening GΦL connection: %s ",
            (", ".join("%s:%s" % tt0 for tt0 in sorted(params.items()))),
        )

        self._gateway = clientserver.ClientServer(
            java_parameters=clientserver.JavaParameters(**java_parameters),
            python_parameters=clientserver.PythonParameters(**python_parameters),
            python_server_entry_point=self,
        )

    def start_workflow(self, workflow_queue, workflow_model_obj):

        # NBNB All command line option values are put in quotes (repr) when
        # the workflow is invoked remotely through ssh.

        if self.get_state() == self.STATES.UNKNOWN:
            logging.getLogger("HWR").warning(
                "GphlWorkflowConnection not correctly initialised - check for errors"
            )

        elif self.get_state() != self.STATES.OFF:
            # NB, for now workflow is started as the connection is made,
            # so we are never in state 'ON'/STANDBY
            raise RuntimeError("Workflow is already running, cannot be started")

        # Cannot be done in init, where the api.sessions link is not yet ready
        self.software_paths["GPHL_WDIR"] = os.path.join(
            HWR.beamline.session.get_base_process_directory(), self.gphl_subdir
        )

        strategy_settings = workflow_model_obj.strategy_settings
        wf_settings = HWR.beamline.gphl_workflow.settings

        ssh_options = self.ssh_options
        in_shell = bool(ssh_options)
        if in_shell:
            ssh_options = ssh_options.copy()
            host = ssh_options.pop("Host")
            command_list = ["ssh"]
            if "ConfigFile" in ssh_options:
                command_list.extend(("-F", ssh_options.pop("ConfigFile")))
            for tag, val in sorted(ssh_options.items()):
                command_list.extend(("-o", "%s=%s" % (tag, val)))
            command_list.append(host)
        else:
            command_list = []
        command_list.append(self.software_paths["java_binary"])

        # # HACK - debug options REMOVE!
        # import socket
        # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # sock.connect(("8.8.8.8", 80))
        # ss0 = "-agentlib:jdwp=transport=dt_socket,address=%s:8050,server=y,suspend=y"
        # command_list.append(ss0 % sock.getsockname()[0])

        for tag, val in sorted(wf_settings.get("invocation_properties", {}).items()):
            command_list.extend(
                conversion.java_property(tag, val, quote_value=in_shell)
            )

        init_spot_dir = workflow_model_obj.init_spot_dir
        if init_spot_dir:
            command_list.extend(
                conversion.java_property("co.gphl.wf.initSpotDir", init_spot_dir)
            )

        # We must get hold of the options here, as we need wdir for a property
        workflow_options = dict(strategy_settings.get("options", {}))
        calibration_name = workflow_options.get("calibration")
        if calibration_name:
            # Expand calibration base name - to simplify identification.
            workflow_options["calibration"] = "%s_%s" % (
                calibration_name,
                workflow_model_obj.get_name(),
            )
        if workflow_model_obj.wftype in ("acquisition", "diffractcal"):
            workflow_options["strategy"] = workflow_model_obj.initial_strategy

        path_template = workflow_model_obj.get_path_template()
        if "prefix" in workflow_options:
            workflow_options["prefix"] = path_template.base_prefix
        workflow_options["wdir"] = self.software_paths["GPHL_WDIR"]
        workflow_options["persistname"] = self.gphl_persistname

        # Set the workflow root subdirectory parameter from the base image directory
        image_root = os.path.abspath(HWR.beamline.session.get_base_image_directory())
        if strategy_settings["wftype"] != "transcal":
            workflow_options[
                "appdir"
            ] = HWR.beamline.session.get_base_process_directory()
            rootsubdir = path_template.directory[len(image_root) :]
            if rootsubdir.startswith(os.path.sep):
                rootsubdir = rootsubdir[1:]
            if rootsubdir:
                workflow_options["rootsubdir"] = rootsubdir

        # Hardcoded - location for log output
        command_list.extend(
            conversion.java_property(
                "co.gphl.wf.wdir", workflow_options["wdir"], quote_value=in_shell
            )
        )

        ll0 = conversion.command_option(
            "cp", self.software_paths["gphl_java_classpath"], quote_value=in_shell
        )
        command_list.extend(ll0)

        command_list.append(strategy_settings["application"])

        for keyword, value in wf_settings.get("workflow_properties", {}).items():
            command_list.extend(
                conversion.java_property(keyword, value, quote_value=in_shell)
            )
        for keyword, value in self.software_properties.items():
            command_list.extend(
                conversion.java_property(keyword, value, quote_value=in_shell)
            )

        for keyword, value in workflow_options.items():
            command_list.extend(
                conversion.command_option(keyword, value, quote_value=in_shell)
            )
        #
        wdir = workflow_options.get("wdir")
        # NB this creates the appdir as well (wdir is within appdir)
        if not os.path.isdir(wdir):
            try:
                os.makedirs(wdir)
            except:
                # No need to raise error - program will fail downstream
                logging.getLogger("HWR").error(
                    "Could not create GΦL working directory: %s", wdir
                )

        for ss0 in command_list:
            ss0 = ss0.rsplit('=', maxsplit=1)[-1]
            if ss0.startswith("/") and "*" not in ss0 and not os.path.exists(ss0):
                logging.getLogger("HWR").warning("File does not exist : %s", ss0)

        logging.getLogger("HWR").info("GΦL execute :\n%s", " ".join(command_list))

        # Get environmental variables
        envs = os.environ.copy()

        # # Trick to allow unauthorised account (e.g. ESRF: opid30) to run GPhL programs
        # # Any value is OK, just setting it is enough.
        # envs["AutoPROCWorkFlowUser"] = "1"

        # These env variables are needed in some cases for wrapper scripts
        # Specifically for the stratcal wrapper.
        envs["GPHL_INSTALLATION"] = self.software_paths["GPHL_INSTALLATION"]
        GPHL_XDS_PATH = self.software_paths.get("GPHL_XDS_PATH")
        if GPHL_XDS_PATH:
            envs["GPHL_XDS_PATH"] = GPHL_XDS_PATH
        GPHL_CCP4_PATH = self.software_paths.get("GPHL_CCP4_PATH")
        if GPHL_CCP4_PATH:
            envs["GPHL_CCP4_PATH"] = GPHL_CCP4_PATH
        GPHL_AUTOPROC_PATH = self.software_paths.get("GPHL_AUTOPROC_PATH")
        if GPHL_AUTOPROC_PATH:
            envs["GPHL_AUTOPROC_PATH"] = GPHL_AUTOPROC_PATH
        GPHL_MINICONDA_PATH = self.software_paths.get("GPHL_MINICONDA_PATH")
        if GPHL_MINICONDA_PATH:
            envs["GPHL_MINICONDA_PATH"] = GPHL_MINICONDA_PATH

        logging.getLogger("HWR").debug(
            "Executing GΦL workflow, in environment %s", envs
        )
        try:
            self._running_process = subprocess.Popen(command_list, env=envs)
        except Exception:
            logging.getLogger().exception("Error in spawning workflow application")
            raise

        self.workflow_queue = workflow_queue
        logging.getLogger("py4j.clientserver").setLevel(logging.WARNING)
        self.update_state(self.STATES.READY)

        logging.getLogger("HWR").debug(
            "GΦL workflow pid, returncode : %s, %s"
            % (self._running_process.pid, self._running_process.returncode)
        )

    def workflow_ended(self):
        if self.get_state() == self.STATES.OFF:
            # No workflow to abort
            return

        logging.getLogger("HWR").debug("GΦL workflow ended")
        self.update_state(self.STATES.OFF)
        if self._await_result is not None:
            # We are awaiting an answer - give an abort
            self._await_result.append((GphlMessages.BeamlineAbort(), None))
            time.sleep(0.2)
        elif self._running_process is not None:
            self._running_process = None
            # NBNB TODO how do we close down the workflow if there is no answer pending?

        self._enactment_id = None
        self.workflow_queue = None
        self._await_result = None

        xx0 = self.collect_emulator_process
        if xx0 is not None:
            self.collect_emulator_process = "ABORTED"
            try:
                if xx0.poll() is None:
                    xx0.send_signal(signal.SIGINT)
                    time.sleep(3)
                    if xx0.poll() is None:
                        xx0.terminate()
                        time.sleep(9)
                        if xx0.poll() is None:
                            xx0.kill()
            except:
                logging.getLogger("HWR").info(
                    "Exception while terminating external workflow process %s", xx0
                )
                logging.getLogger("HWR").info("Error was:", exc_info=True)

    def close_connection(self):

        logging.getLogger("HWR").debug("GΦL Close connection ")
        xx0 = self._gateway
        self._gateway = None
        if xx0 is not None:
            try:
                # Exceptions 'can easily happen' (py4j docs)
                # Without raise_exception exceptions in the first part of the shutddown
                # will be caught and the rest of the shutdown will continue.
                # which is what we want.
                # xx0.shutdown(raise_exception=True)
                xx0.shutdown()
            except Exception:
                logging.getLogger("HWR").debug(
                    "Exception during py4j gateway shutdown. Ignored"
                )

    def abort_workflow(self, message=None):
        """Abort workflow - may be called from controller in any state"""

        logging.getLogger("HWR").info("Aborting workflow: %s", message)
        logging.getLogger("user_level_log").info("Aborting workflow ...")
        if self._await_result is not None:
            # Workflow waiting for answer - send abort
            self._await_result = [(GphlMessages.BeamlineAbort(), None)]

        # Shut down hardware object
        que = self.workflow_queue
        if que is None:
            self.workflow_ended()
        else:
            # If the queue is running,
            # workflow_ended will be called from post_execute
            que.put_nowait(StopIteration)

    def processText(self, py4j_message):
        """Receive and process info message from workflow server
        Return goes to server

        NB Callled freom external java) workflow"""
        xx0 = self._decode_py4j_message(py4j_message)
        message_type = xx0.message_type
        payload = xx0.payload
        correlation_id = xx0.correlation_id
        enactment_id = xx0.enactment_id

        if not payload:
            logging.getLogger("HWR").warning(
                "GΦL Empty or unparsable information message. Ignored"
            )

        else:
            if not enactment_id:
                logging.getLogger("HWR").warning(
                    "GΦL information message lacks enactment ID:"
                )
            elif self._enactment_id != enactment_id:
                logging.getLogger("HWR").warning(
                    "Workflow enactment ID %s != info message enactment ID %s."
                    % (self._enactment_id, enactment_id)
                )
            if self.workflow_queue is not None:
                # Could happen if we have ended the workflow
                self.workflow_queue.put_nowait(
                    (message_type, payload, correlation_id, None)
                )

    def processMessage(self, py4j_message):
        """Receive and process message from workflow server
        Return goes to server

        NB Callled freom external java) workflow"""
        if self.get_state() is self.STATES.OFF:
            return None

        xx0 = self._decode_py4j_message(py4j_message)
        message_type = xx0.message_type
        payload = xx0.payload
        correlation_id = xx0.correlation_id
        enactment_id = xx0.enactment_id

        if not enactment_id:
            logging.getLogger("HWR").error(
                "GΦL message lacks enactment ID - sending 'Abort' to external workflow"
            )
            return self._response_to_server(
                GphlMessages.BeamlineAbort(), correlation_id
            )

        elif self._enactment_id is None:
            # NB this should be made less primitive
            # once we are past direct function calls
            self._enactment_id = enactment_id

        elif self._enactment_id != enactment_id:
            logging.getLogger("HWR").error(
                "Workflow enactment ID %s != message enactment ID %s"
                " - sending 'Abort' to external workflow"
                % (self._enactment_id, enactment_id)
            )
            return self._response_to_server(
                GphlMessages.BeamlineAbort(), correlation_id
            )

        elif not payload:
            logging.getLogger("HWR").error(
                "GΦL message lacks payload - sending 'Abort' to external workflow"
            )
            return self._response_to_server(
                GphlMessages.BeamlineAbort(), correlation_id
            )

        if message_type in ("SubprocessStarted", "SubprocessStopped"):

            if self.workflow_queue is not None:
                # Could happen if we have ended the workflow
                self.workflow_queue.put_nowait(
                    (message_type, payload, correlation_id, None)
                )
            logging.getLogger("HWR").debug("Subprocess start/stop - return None")
            return None

        elif message_type in (
            "RequestConfiguration",
            "GeometricStrategy",
            "CollectionProposal",
            "ChooseLattice",
            "RequestCentring",
            "ObtainPriorInformation",
            "PrepareForCentring",
        ):
            # Requests:
            self._await_result = []
            self.update_state(self.STATES.BUSY)
            if self.workflow_queue is None:
                # Could be None if we have ended the workflow
                return self._response_to_server(
                    GphlMessages.BeamlineAbort(), correlation_id
                )
            else:
                self.workflow_queue.put_nowait(
                    (message_type, payload, correlation_id, self._await_result)
                )
                while not self._await_result:
                    time.sleep(0.1)
                result, correlation_id = self._await_result.pop(0)
                if self.get_state() == self.STATES.BUSY:
                    self.update_state(self.STATES.READY)
                self._await_result = None

                if result is StopIteration:
                    result = GphlMessages.BeamlineAbort()
                    self.workflow_queue.put_nowait(
                        (
                            "WorkflowAborted",
                            GphlMessages.WorkflowAborted(),
                            correlation_id,
                            None,
                        )
                    )
                    self.workflow_ended()
                else:
                    logging.getLogger("HWR").debug(
                        "GΦL - response=%s jobId=%s messageId=%s"
                        % (result.__class__.__name__, enactment_id, correlation_id)
                    )
                return self._response_to_server(result, correlation_id)

        elif message_type in ("WorkflowAborted", "WorkflowCompleted", "WorkflowFailed"):
            if self.workflow_queue is not None:
                # Could happen if we have ended the workflow
                self.workflow_queue.put_nowait(
                    (message_type, payload, correlation_id, None)
                )
                self.workflow_ended()
            logging.getLogger("HWR").debug("Aborting - return None")
            return None

        else:
            logging.getLogger("HWR").error(
                "GΦL Unknown message type: %s - aborting", message_type
            )
            return self._response_to_server(
                GphlMessages.BeamlineAbort(), correlation_id
            )

    # Conversion to Python

    def _decode_py4j_message(self, py4j_message):
        """Extract messageType and convert py4J object to python object"""

        # Determine message type
        message_type = py4j_message.getPayloadClass().getSimpleName()

        xx0 = py4j_message.getEnactmentId()
        enactment_id = xx0 and xx0.toString()

        xx0 = py4j_message.getCorrelationId()
        correlation_id = xx0 and xx0.toString()
        if message_type != "String":
            logging.getLogger("HWR").debug(
                "GΦL incoming: message=%s, jobId=%s,  messageId=%s"
                % (message_type, enactment_id, correlation_id)
            )

        if message_type == "String":
            payload = py4j_message.getPayload()

        else:
            if message_type.endswith("Impl"):
                message_type = message_type[:-4]
            converterName = "_%s_to_python" % message_type

            try:
                # determine converter function
                converter = getattr(self, converterName)
            except AttributeError:
                logging.getLogger("HWR").error(
                    "GΦL Message type %s not recognised (no %s function)"
                    % (message_type, converterName)
                )
                payload = None
            else:
                try:
                    # Convert to Python objects
                    payload = converter(py4j_message.getPayload())
                except NotImplementedError:
                    logging.getLogger("HWR").error(
                        "Processing of GΦL message %s not implemented", message_type
                    )
                    payload = None
        #
        return GphlMessages.ParsedMessage(
            message_type, payload, enactment_id, correlation_id
        )

    def _RequestConfiguration_to_python(self, py4jRequestConfiguration):
        return GphlMessages.RequestConfiguration()

    def _ObtainPriorInformation_to_python(self, py4jObtainPriorInformation):
        return GphlMessages.ObtainPriorInformation()

    def _PrepareForCentring_to_python(self, py4jPrepareForCentring):
        return GphlMessages.PrepareForCentring()

    def _GeometricStrategy_to_python(self, py4jGeometricStrategy):
        uuidString = py4jGeometricStrategy.getId().toString()
        sweeps = frozenset(
            self._Sweep_to_python(x) for x in py4jGeometricStrategy.getSweeps()
        )
        beamSetting = py4jGeometricStrategy.getDefaultBeamSetting()
        if beamSetting:
            beamSetting = self._BeamSetting_to_python(beamSetting)
        else:
            beamSetting = None
        detectorSetting = py4jGeometricStrategy.getDefaultDetectorSetting()
        if detectorSetting:
            detectorSetting = self._DetectorSetting_to_python(detectorSetting)
        else:
            detectorSetting = None
        return GphlMessages.GeometricStrategy(
            # isInterleaved=py4jGeometricStrategy.isInterleaved(),
            isUserModifiable=py4jGeometricStrategy.isUserModifiable(),
            allowedWidths=py4jGeometricStrategy.getAllowedWidths(),
            sweepOffset=py4jGeometricStrategy.getSweepOffset(),
            sweepRepeat=py4jGeometricStrategy.getSweepRepeat(),
            defaultWidthIdx=py4jGeometricStrategy.getDefaultWidthIdx(),
            defaultBeamSetting=beamSetting,
            defaultDetectorSetting=detectorSetting,
            sweeps=sweeps,
            id_=uuid.UUID(uuidString),
        )

    def _SubprocessStarted_to_python(self, py4jSubprocessStarted):
        return GphlMessages.SubprocessStarted(name=py4jSubprocessStarted.getName())

    def _SubprocessStopped_to_python(self, py4jSubprocessStopped):
        return GphlMessages.SubprocessStopped()

    def _ChooseLattice_to_python(self, py4jChooseLattice):
        # NB the functions return different types, so toString is needed in only once
        indexingFormat = py4jChooseLattice.getIndexingFormat().toString()
        indexingHeader = py4jChooseLattice.getIndexingHeader()
        inputCell = py4jChooseLattice.getUserProvidedCell()
        userProvidedCell = self._UnitCell_to_python(inputCell) if inputCell else None
        return GphlMessages.ChooseLattice(
            indexingSolutions=tuple(
                self._IndexingSolution_to_python(sol)
                for sol in py4jChooseLattice.getIndexingSolutions()
            ),
            indexingFormat=indexingFormat,
            indexingHeader=indexingHeader,
            priorCrystalClasses=tuple(
                ccl.toString() for ccl in py4jChooseLattice.getPriorCrystalClasses()
            ),
            priorSpaceGroup=py4jChooseLattice.getPriorSpaceGroup(),
            priorSpaceGroupString=py4jChooseLattice.getPriorSpaceGroupString(),
            userProvidedCell=userProvidedCell,
        )

    def _CollectionProposal_to_python(self, py4jCollectionProposal):
        uuidString = py4jCollectionProposal.getId().toString()
        strategy = self._GeometricStrategy_to_python(
            py4jCollectionProposal.getStrategy()
        )
        text_type = conversion.text_type
        id2Sweep = dict((text_type(x.id_), x) for x in strategy.sweeps)
        scans = []
        for py4jScan in py4jCollectionProposal.getScans():
            sweep = id2Sweep[py4jScan.getSweep().getId().toString()]
            scans.append(self._Scan_to_python(py4jScan, sweep))
        return GphlMessages.CollectionProposal(
            relativeImageDir=py4jCollectionProposal.getRelativeImageDir(),
            strategy=strategy,
            scans=scans,
            id_=uuid.UUID(uuidString),
        )

    def __WorkflowDone_to_python(self, py4jWorkflowDone, cls):
        Issue = GphlMessages.Issue
        issues = []
        for py4jIssue in py4jWorkflowDone.getIssues():
            component = py4jIssue.getComponent()
            message = py4jIssue.getMessage()
            code = py4jIssue.getCode()
            issues.append(Issue(component=component, message=message, code=code))
        #
        return cls(issues=issues)

    def _WorkflowCompleted_to_python(self, py4jWorkflowCompleted):
        return self.__WorkflowDone_to_python(
            py4jWorkflowCompleted, GphlMessages.WorkflowCompleted
        )

    def _WorkflowAborted_to_python(self, py4jWorkflowAborted):
        return self.__WorkflowDone_to_python(
            py4jWorkflowAborted, GphlMessages.WorkflowAborted
        )

    def _WorkflowFailed_to_python(self, py4jWorkflowFailed):
        return self.__WorkflowDone_to_python(
            py4jWorkflowFailed, GphlMessages.WorkflowFailed
        )

    def _RequestCentring_to_python(self, py4jRequestCentring):
        goniostatRotation = self._GoniostatRotation_to_python(
            py4jRequestCentring.getGoniostatRotation()
        )
        return GphlMessages.RequestCentring(
            currentSettingNo=py4jRequestCentring.getCurrentSettingNo(),
            totalRotations=py4jRequestCentring.getTotalRotations(),
            goniostatRotation=goniostatRotation,
        )

    def _GoniostatRotation_to_python(self, py4jGoniostatRotation, isSweepSetting=False):
        if py4jGoniostatRotation is None:
            return None

        uuidString = py4jGoniostatRotation.getId().toString()
        axisSettings = py4jGoniostatRotation.getAxisSettings()
        if isSweepSetting:
            scanAxis = py4jGoniostatRotation.getScanAxis()
            result = GphlMessages.GoniostatSweepSetting(
                id_=uuid.UUID(uuidString), scanAxis=scanAxis, **axisSettings
            )
        else:
            result = GphlMessages.GoniostatRotation(
                id_=uuid.UUID(uuidString), **axisSettings
            )

        py4jGoniostatTranslation = py4jGoniostatRotation.getTranslation()
        if py4jGoniostatTranslation:
            translationAxisSettings = py4jGoniostatTranslation.getAxisSettings()
            translationUuidString = py4jGoniostatTranslation.getId().toString()
            # Next line creates Translation and links it to Rotation
            GphlMessages.GoniostatTranslation(
                id_=uuid.UUID(translationUuidString),
                rotation=result,
                **translationAxisSettings
            )
        return result

    def _BeamstopSetting_to_python(self, py4jBeamstopSetting):
        if py4jBeamstopSetting is None:
            return None
        uuidString = py4jBeamstopSetting.getId().toString()
        axisSettings = py4jBeamstopSetting.getAxisSettings()
        #
        return GphlMessages.BeamstopSetting(id_=uuid.UUID(uuidString), **axisSettings)

    def _DetectorSetting_to_python(self, py4jDetectorSetting):
        if py4jDetectorSetting is None:
            return None
        uuidString = py4jDetectorSetting.getId().toString()
        axisSettings = py4jDetectorSetting.getAxisSettings()
        #
        return GphlMessages.DetectorSetting(id_=uuid.UUID(uuidString), **axisSettings)

    def _BeamSetting_to_python(self, py4jBeamSetting):
        if py4jBeamSetting is None:
            return None
        uuidString = py4jBeamSetting.getId().toString()
        #
        return GphlMessages.BeamSetting(
            id_=uuid.UUID(uuidString), wavelength=py4jBeamSetting.getWavelength()
        )

    def _GoniostatSweepSetting_to_python(self, py4jGoniostatSweepSetting):
        return self._GoniostatRotation_to_python(
            py4jGoniostatSweepSetting, isSweepSetting=True
        )

    def _UnitCell_to_python(self, py4jUnitCell):

        cell_params = tuple(py4jUnitCell.getLengths()) + tuple(py4jUnitCell.getAngles())
        return GphlMessages.UnitCell(*cell_params)

    def _IndexingSolution_to_python(self, py4jIndexingSolution):

        return GphlMessages.IndexingSolution(
            bravaisLattice=py4jIndexingSolution.getBravaisLattice(),
            cell=self._UnitCell_to_python(py4jIndexingSolution.getCell()),
            isConsistent=py4jIndexingSolution.isConsistent(),
            latticeCharacter=py4jIndexingSolution.getLatticeCharacter(),
            qualityOfFit=py4jIndexingSolution.getQualityOfFit(),
        )

    def _Sweep_to_python(self, py4jSweep):

        # NB scans are not set - where scans are present in a message,
        # the link is set from the Scan side.

        uuidString = py4jSweep.getId().toString()
        return GphlMessages.Sweep(
            goniostatSweepSetting=self._GoniostatSweepSetting_to_python(
                py4jSweep.getGoniostatSweepSetting()
            ),
            detectorSetting=self._DetectorSetting_to_python(
                py4jSweep.getDetectorSetting()
            ),
            beamSetting=self._BeamSetting_to_python(py4jSweep.getBeamSetting()),
            start=py4jSweep.getStart(),
            width=py4jSweep.getWidth(),
            beamstopSetting=self._BeamstopSetting_to_python(
                py4jSweep.getBeamstopSetting()
            ),
            sweepGroup=py4jSweep.getSweepGroup(),
            id_=uuid.UUID(uuidString),
        )

    def _ScanExposure_to_python(self, py4jScanExposure):
        uuidString = py4jScanExposure.getId().toString()
        return GphlMessages.ScanExposure(
            time=py4jScanExposure.getTime(),
            transmission=py4jScanExposure.getTransmission(),
            id_=uuid.UUID(uuidString),
        )

    def _ScanWidth_to_python(self, py4jScanWidth):
        uuidString = py4jScanWidth.getId().toString()
        return GphlMessages.ScanWidth(
            imageWidth=py4jScanWidth.getImageWidth(),
            numImages=py4jScanWidth.getNumImages(),
            id_=uuid.UUID(uuidString),
        )

    def _Scan_to_python(self, py4jScan, sweep):
        uuidString = py4jScan.getId().toString()
        return GphlMessages.Scan(
            width=self._ScanWidth_to_python(py4jScan.getWidth()),
            exposure=self._ScanExposure_to_python(py4jScan.getExposure()),
            imageStartNum=py4jScan.getImageStartNum(),
            start=py4jScan.getStart(),
            sweep=sweep,
            filenameParams=py4jScan.getFilenameParams(),
            id_=uuid.UUID(uuidString),
        )

    # Conversion to Java

    def _payload_to_java(self, payload):
        """Convert Python payload object to java"""

        payloadType = payload.__class__.__name__

        if payloadType == "ConfigurationData":
            return self._ConfigurationData_to_java(payload)

        if payloadType == "BeamlineAbort":
            return self._BeamlineAbort_to_java(payload)

        if payloadType == "ReadyForCentring":
            return self._ReadyForCentring_to_java(payload)

        if payloadType == "SampleCentred":
            return self._SampleCentred_to_java(payload)

        if payloadType == "CollectionDone":
            # self.test_lattice_selection()
            return self._CollectionDone_to_java(payload)

        if payloadType == "SelectedLattice":
            return self._SelectedLattice_to_java(payload)

        if payloadType == "CentringDone":
            return self._CentringDone_to_java(payload)

        if payloadType == "PriorInformation":
            return self._PriorInformation_to_java(payload)

        raise ValueError(
            "Payload %s not supported for conversion to java" % payloadType
        )

    def _response_to_server(self, payload, correlation_id):
        """Create py4j message from py4j wrapper and current ids"""

        if self._enactment_id is None:
            enactment_id = None
        else:
            enactment_id = self._gateway.jvm.java.util.UUID.fromString(
                self._enactment_id
            )

        if correlation_id is not None:
            correlation_id = self._gateway.jvm.java.util.UUID.fromString(correlation_id)

        py4j_payload = self._payload_to_java(payload)

        try:
            response = self._gateway.jvm.co.gphl.sdcp.py4j.Py4jMessage(
                py4j_payload, enactment_id, correlation_id
            )
        except:
            self.abort_workflow(
                message="Error sending reply (%s) to server"
                % py4j_payload.getClass().getSimpleName()
            )
            return None
        else:
            return response

    def _CentringDone_to_java(self, centringDone):
        jvm = self._gateway.jvm
        return jvm.astra.messagebus.messages.information.CentringDoneImpl(
            jvm.co.gphl.beamline.v2_unstable.instrumentation.CentringStatus.valueOf(
                centringDone.status
            ),
            self.to_java_time(centringDone.timestamp),
            self._GoniostatTranslation_to_java(centringDone.goniostatTranslation),
        )

    def _ConfigurationData_to_java(self, configurationData):
        jvm = self._gateway.jvm
        return jvm.astra.messagebus.messages.information.ConfigurationDataImpl(
            self._gateway.jvm.java.io.File(configurationData.location)
        )

    def _ReadyForCentring_to_java(self, readyForCentring):
        return (
            self._gateway.jvm.astra.messagebus.messages.control.ReadyForCentringImpl()
        )

    def _PriorInformation_to_java(self, priorInformation):
        jvm = self._gateway.jvm
        buildr = jvm.astra.messagebus.messages.information.PriorInformationImpl.Builder(
            jvm.java.util.UUID.fromString(
                conversion.text_type(priorInformation.sampleId)
            )
        )
        xx0 = priorInformation.sampleName
        if xx0:
            buildr = buildr.sampleName(xx0)
        xx0 = priorInformation.rootDirectory
        if xx0:
            buildr = buildr.rootDirectory(xx0)
        buildr = buildr.userProvidedInfo(
            self._UserProvidedInfo_to_java(priorInformation.userProvidedInfo)
        )
        #
        return buildr.build()

    def _SampleCentred_to_java(self, sampleCentred):

        cls = self._gateway.jvm.astra.messagebus.messages.information.SampleCentredImpl

        # if sampleCentred.interleaveOrder:
        result = cls(
            float(sampleCentred.imageWidth),
            int(sampleCentred.wedgeWidth),
            float(sampleCentred.exposure),
            float(sampleCentred.transmission),
            list(sampleCentred.interleaveOrder),
            list(self._PhasingWavelength_to_java(x) for x in sampleCentred.wavelengths),
            self._BcsDetectorSetting_to_java(sampleCentred.detectorSetting),
            sampleCentred.repetition_count,
        )

        beamstopSetting = sampleCentred.beamstopSetting
        if beamstopSetting is not None:
            result.setBeamstopSetting(self._BeamstopSetting_to_java(beamstopSetting))

        translationSettings = sampleCentred.goniostatTranslations
        if translationSettings:
            result.setGoniostatTranslations(
                list(self._GoniostatTranslation_to_java(x) for x in translationSettings)
            )
        #
        return result

    def _CollectionDone_to_java(self, collectionDone):
        jvm = self._gateway.jvm
        proposalId = jvm.java.util.UUID.fromString(
            conversion.text_type(collectionDone.proposalId)
        )
        return jvm.astra.messagebus.messages.information.CollectionDoneImpl(
            proposalId, collectionDone.imageRoot, collectionDone.status
        )

    def _SelectedLattice_to_java(self, selectedLattice):
        jvm = self._gateway.jvm
        crystal_classes = selectedLattice.userCrystalClasses
        if crystal_classes:
            userCrystalClasses = set(
                jvm.co.gphl.beamline.v2_unstable.domain_types.CrystalClass.fromStringList(
                    self.toJStringArray(crystal_classes)
                )
            )
        else:
            userCrystalClasses = None
        result = jvm.astra.messagebus.messages.information.SelectedLatticeImpl(
            self._IndexingSolution_to_java(selectedLattice.solution),
            self._BcsDetectorSetting_to_java(selectedLattice.strategyDetectorSetting),
            self._PhasingWavelength_to_java(selectedLattice.strategyWavelength),
            selectedLattice.userSpaceGroup,
            userCrystalClasses,
            selectedLattice.strategyControl,
        )
        #
        return result

    def _IndexingSolution_to_java(self, indexingSolution):
        jvm = self._gateway.jvm
        cell = indexingSolution.cell
        cell = cell and self._UnitCell_to_java(cell)
        result = jvm.astra.messagebus.messages.information.IndexingSolutionImpl(
            indexingSolution.bravaisLattice,
            indexingSolution.latticeCharacter,
            indexingSolution.isConsistent,
            indexingSolution.qualityOfFit,
            cell,
        )
        #
        return result

    def _BeamlineAbort_to_java(self, beamlineAbort):
        return (
            self._gateway.jvm.astra.messagebus.messages.instructions.BeamlineAbortImpl()
        )

    def _UserProvidedInfo_to_java(self, userProvidedInfo):
        jvm = self._gateway.jvm

        if userProvidedInfo is None:
            return None

        builder = (
            jvm.astra.messagebus.messages.information.UserProvidedInfoImpl.Builder()
        )

        for scatterer in userProvidedInfo.scatterers:
            builder = builder.addScatterer(self._AnomalousScatterer_to_java(scatterer))
        crystal_classes = userProvidedInfo.crystalClasses
        if crystal_classes:
            ccset = set(
                jvm.co.gphl.beamline.v2_unstable.domain_types.CrystalClass.fromStringList(
                    self.toJStringArray(crystal_classes)
                )
            )
            builder = builder.crystalClasses(ccset)
        xx0 = userProvidedInfo.spaceGroup
        if xx0:
            builder = builder.spaceGroup(xx0)
        xx0 = userProvidedInfo.spaceGroupString
        if xx0:
            builder = builder.spaceGroupString(xx0)
        xx0 = userProvidedInfo.cell
        if xx0 is not None:
            builder = builder.cell(self._UnitCell_to_java(xx0))
        if userProvidedInfo.expectedResolution:
            builder = builder.expectedResolution(
                float(userProvidedInfo.expectedResolution)
            )
        xx0 = userProvidedInfo.isAnisotropic
        if xx0 is not None:
            builder = builder.anisotropic(xx0)
        #
        return builder.build()

    def _AnomalousScatterer_to_java(self, anomalousScatterer):
        jvm = self._gateway.jvm

        if anomalousScatterer is None:
            return None

        element = jvm.co.gphl.beamline.v2_unstable.domain_types.ChemicalElement.valueOf(
            anomalousScatterer.element
        )
        edge = jvm.co.gphl.beamline.v2_unstable.domain_types.AbsorptionEdge.valueOf(
            anomalousScatterer.edge
        )
        return jvm.astra.messagebus.messages.domain_types.AnomalousScattererImpl(
            element, edge
        )

    def _UnitCell_to_java(self, unitCell):

        if unitCell is None:
            return None

        lengths = [float(x) for x in unitCell.lengths]
        angles = [float(x) for x in unitCell.angles]
        return self._gateway.jvm.astra.messagebus.messages.domain_types.UnitCellImpl(
            lengths[0], lengths[1], lengths[2], angles[0], angles[1], angles[2]
        )

    def _PhasingWavelength_to_java(self, phasingWavelength):
        jvm = self._gateway.jvm

        if phasingWavelength is None:
            return None

        javaUuid = self._gateway.jvm.java.util.UUID.fromString(
            conversion.text_type(phasingWavelength.id_)
        )
        return jvm.astra.messagebus.messages.information.PhasingWavelengthImpl(
            javaUuid, float(phasingWavelength.wavelength), phasingWavelength.role
        )

    def _BcsDetectorSetting_to_java(self, bcsDetectorSetting):
        jvm = self._gateway.jvm

        if bcsDetectorSetting is None:
            return None

        orgxy = bcsDetectorSetting.orgxy
        # Need (temporarily?) because there is a primitive array, not a list,
        # on the other side
        orgxy_array = self._gateway.new_array(jvm.double, 2)
        orgxy_array[0] = orgxy[0]
        orgxy_array[1] = orgxy[1]
        axisSettings = dict(
            ((x, float(y)) for x, y in bcsDetectorSetting.axisSettings.items())
        )
        javaUuid = jvm.java.util.UUID.fromString(
            conversion.text_type(bcsDetectorSetting.id_)
        )
        return jvm.astra.messagebus.messages.instrumentation.BcsDetectorSettingImpl(
            float(bcsDetectorSetting.resolution), orgxy_array, axisSettings, javaUuid
        )

    def _GoniostatTranslation_to_java(self, goniostatTranslation):
        jvm = self._gateway.jvm

        if goniostatTranslation is None:
            return None

        gts = goniostatTranslation
        javaUuid = jvm.java.util.UUID.fromString(conversion.text_type(gts.id_))
        javaRotationId = jvm.java.util.UUID.fromString(
            conversion.text_type(gts.requestedRotationId)
        )
        axisSettings = dict(((x, float(y)) for x, y in gts.axisSettings.items()))
        newRotation = gts.newRotation
        if newRotation:
            if isinstance(newRotation, GphlMessages.GoniostatSweepSetting):
                javaNewRotation = self._GoniostatSweepSetting_to_java(newRotation)
            else:
                javaNewRotation = self._GoniostatRotation_to_java(newRotation)

            return (
                jvm.astra.messagebus.messages.instrumentation.GoniostatTranslationImpl(
                    axisSettings, javaUuid, javaRotationId, javaNewRotation
                )
            )
        else:
            return (
                jvm.astra.messagebus.messages.instrumentation.GoniostatTranslationImpl(
                    axisSettings, javaUuid, javaRotationId
                )
            )

    def _GoniostatRotation_to_java(self, goniostatRotation):
        jvm = self._gateway.jvm

        if goniostatRotation is None:
            return None

        grs = goniostatRotation
        javaUuid = jvm.java.util.UUID.fromString(conversion.text_type(grs.id_))
        axisSettings = dict(((x, float(y)) for x, y in grs.axisSettings.items()))
        # Long problematic, but now fixed (on both sides)
        return jvm.astra.messagebus.messages.instrumentation.GoniostatRotationImpl(
            axisSettings, javaUuid
        )

    def _GoniostatSweepSetting_to_java(self, goniostatSweepSetting):
        """Not currently in use, as you cannot replace SweepSettings,
        but may come back in if something changes"""
        jvm = self._gateway.jvm

        if goniostatSweepSetting is None:
            return None

        gss = goniostatSweepSetting
        javaUuid = jvm.java.util.UUID.fromString(conversion.text_type(gss.id_))
        axisSettings = dict(((x, float(y)) for x, y in gss.axisSettings.items()))
        return jvm.astra.messagebus.messages.instrumentation.GoniostatSweepSettingImpl(
            axisSettings, javaUuid, goniostatSweepSetting.scanAxis
        )

    def _BeamstopSetting_to_java(self, beamStopSetting):
        jvm = self._gateway.jvm

        if beamStopSetting is None:
            return None

        javaUuid = jvm.java.util.UUID.fromString(
            conversion.text_type(beamStopSetting.id_)
        )
        axisSettings = dict(
            ((x, float(y)) for x, y in beamStopSetting.axisSettings.items())
        )
        return jvm.astra.messagebus.messages.instrumentation.BeamstopSettingImpl(
            axisSettings, javaUuid
        )

    def toJStringArray(self, arr):
        """Modified from
        https://stackoverflow.com/questions/61230680/pyspark-py4j-create-java-string-array
        """
        jarr = self._gateway.new_array(self._gateway.jvm.java.lang.String, len(arr))
        for ind, val in enumerate(arr):
            jarr[ind] = val
        return jarr

    class Java:
        implements = ["co.gphl.py4j.PythonListener"]
