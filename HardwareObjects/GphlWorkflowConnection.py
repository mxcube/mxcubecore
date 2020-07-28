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
import socket
import subprocess
import uuid
import signal
import time

import gevent.monkey
import gevent.event
from py4j import clientserver

from HardwareRepository import ConvertUtils
from HardwareRepository.HardwareObjects import GphlMessages

# NB MUST be imported via full path to match imports elsewhere:
from HardwareRepository.HardwareObjects.queue_model_enumerables import States
from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository import HardwareRepository as HWR

try:
    # Needed for 3.6(?) onwards
    from importlib import reload
except ImportError:
    # Works for earlier versions, including Python 2.6
    from imp import reload

try:
    # This file already does the alternative imports plus some tweaking
    # TODO It ought to be moved out as an accessible Util file, but meanwhile
    # Here we take care of the case where it is missing.
    from HardwareRepository.dispatcher import dispatcher
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


class GphlWorkflowConnection(HardwareObject, object):
    """
    This HO acts as a gateway to the Global Phasing workflow engine.
    """

    # object states
    valid_states = [
        States.OFF,  # Not connected to remote server
        States.ON,  # Connected, inactive, awaiting start (or disconnect)
        States.RUNNING,  # Server is active and will produce next message
        States.OPEN,  # Server is waiting for a message from the beamline
    ]

    def __init__(self, name):
        super(GphlWorkflowConnection, self).__init__(name)

        # Py4J gateway to external workflow program
        self._gateway = None

        # ID for current workflow calculation
        self._enactment_id = None

        # Name of workflow being executed.
        self._workflow_name = None

        # Queue for communicating with MXCuBE HardwareObject
        self.workflow_queue = None
        self._await_result = None
        self._running_process = None
        self.collect_emulator_process = None

        self._state = States.OFF

        # py4j connection parameters
        self._connection_parameters = {}

        # Paths to executables and software locations
        self.software_paths = {}
        # Properties for GPhL invocation
        self.java_properties = {}

    def _init(self):
        super(GphlWorkflowConnection, self)._init()

    def init(self):
        super(GphlWorkflowConnection, self).init()
        if self.hasObject("connection_parameters"):
            self._connection_parameters.update(
                self["connection_parameters"].get_properties()
            )
        if self.hasObject("ssh_options"):
            # We are running through ssh - so we need python_address
            # If not, we stick to default, which is localhost (127.0.0.1)
            self._connection_parameters["python_address"] = socket.gethostname()

        locations = next(self.get_objects("directory_locations")).get_properties()
        paths = self.software_paths
        props = self.java_properties
        dd0 = next(self.get_objects("software_paths")).get_properties()
        for tag, val in dd0.items():
            val2 = val.format(**locations)
            if not os.path.isabs(val2):
                val2 = HWR.getHardwareRepository().find_in_repository(val)
                if val2 is None:
                    raise ValueError("File path %s not recognised" % val)
            paths[tag] = val2
        dd0 = next(self.get_objects("software_properties")).get_properties()
        for tag, val in dd0.items():
            val2 = val.format(**locations)
            if not os.path.isabs(val2):
                val2 = HWR.getHardwareRepository().find_in_repository(val)
                if val2 is None:
                    raise ValueError("File path %s not recognised" % val)
            paths[tag] = props[tag] = val2
        #
        pp0 = props["co.gphl.wf.bin"] = paths["GPHL_INSTALLATION"]
        paths["BDG_home"] = paths.get("co.gphl.wf.bdg_licence_dir") or pp0

    def get_state(self):
        """Returns a member of the General.States enumeration"""
        return self._state

    def set_state(self, value):
        if value in self.valid_states:
            self._state = value
            dispatcher.send("stateChanged", self, self._state)
        else:
            raise RuntimeError(
                "GphlWorkflowConnection set to invalid state: %s" % value
            )

    def get_workflow_name(self):
        """Name of currently executing workflow"""
        return self._workflow_name

    def to_java_time(self, time_in):
        """Convert time in seconds since the epoch (python time) to Java time value"""
        return self._gateway.jvm.java.lang.Long(int(time_in * 1000))

    def get_executable(self, name):
        """Get location of executable binary for program called 'name'"""
        tag = "co.gphl.wf.%s.bin" % name
        result = self.software_paths.get(tag)
        if not result:
            result = os.path.join(self.software_paths["GPHL_INSTALLATION"], name)
        #
        return result

    def open_connection(self):

        params = self._connection_parameters

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
            "GPhL Open connection: %s ",
            (", ".join("%s:%s" % tt0 for tt0 in sorted(params.items()))),
        )

        # set sockets and threading to standard before running py4j
        # NBNB this can cause ERRORS if socket or thread have been
        # patched with non-default parameters
        # It is the best we can do, though
        #
        # These should use is_module_patched,
        # but that is not available in gevent 1.0
        socket_patched = "socket" in gevent.monkey.saved
        reload(socket)
        try:
            self._gateway = clientserver.ClientServer(
                java_parameters=clientserver.JavaParameters(**java_parameters),
                python_parameters=clientserver.PythonParameters(**python_parameters),
                python_server_entry_point=self,
            )
        finally:
            # patch back to starting state
            if socket_patched:
                gevent.monkey.patch_socket()

    def start_workflow(self, workflow_queue, workflow_model_obj):

        # NBNB All command line option values are put in quotes (repr) when
        # the workflow is invoked remotely through ssh.

        self.workflow_queue = workflow_queue

        if self.get_state() != States.OFF:
            # NB, for now workflow is started as the connection is made,
            # so we are never in state 'ON'/STANDBY
            raise RuntimeError("Workflow is already running, cannot be started")

        self._workflow_name = workflow_model_obj.get_type()
        params = workflow_model_obj.get_workflow_parameters()

        in_shell = self.hasObject("ssh_options")
        if in_shell:
            dd0 = self["ssh_options"].get_properties().copy()
            #
            host = dd0.pop("Host")
            command_list = ["ssh"]
            if "ConfigFile" in dd0:
                command_list.extend(("-F", dd0.pop("ConfigFile")))
            for tag, val in sorted(dd0.items()):
                command_list.extend(("-o", "%s=%s" % (tag, val)))
                # command_list.extend(('-o', tag, val))
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

        for tag, val in sorted(params.get("invocation_properties", {}).items()):
            command_list.extend(
                ConvertUtils.java_property(tag, val, quote_value=in_shell)
            )

        # We must get hold of the options here, as we need wdir for a property
        workflow_options = dict(params.get("options", {}))
        calibration_name = workflow_options.get("calibration")
        if calibration_name:
            # Expand calibration base name - to simplify identification.
            workflow_options["calibration"] = "%s_%s" % (
                calibration_name,
                workflow_model_obj.get_name(),
            )
        elif not workflow_options.get("strategy"):
            workflow_options[
                "strategy"
            ] = workflow_model_obj.get_characterisation_strategy()
        path_template = workflow_model_obj.get_path_template()
        if "prefix" in workflow_options:
            workflow_options["prefix"] = path_template.base_prefix
        workflow_options["wdir"] = os.path.join(
            path_template.process_directory, self.get_property("gphl_subdir")
        )
        # Hardcoded - location for log output
        command_list.extend(
            ConvertUtils.java_property(
                "co.gphl.wf.wdir", workflow_options["wdir"], quote_value=in_shell
            )
        )

        ll0 = ConvertUtils.command_option(
            "cp", self.software_paths["gphl_java_classpath"], quote_value=in_shell
        )
        command_list.extend(ll0)

        command_list.append(params["application"])

        for keyword, value in params.get("properties", {}).items():
            command_list.extend(
                ConvertUtils.java_property(keyword, value, quote_value=in_shell)
            )
        for keyword, value in self.java_properties.items():
            command_list.extend(
                ConvertUtils.java_property(keyword, value, quote_value=in_shell)
            )

        for keyword, value in workflow_options.items():
            command_list.extend(
                ConvertUtils.command_option(keyword, value, quote_value=in_shell)
            )
        #
        wdir = workflow_options.get("wdir")
        # NB this creates the appdir as well (wdir is within appdir)
        if not os.path.isdir(wdir):
            try:
                os.makedirs(wdir)
            except BaseException:
                # No need to raise error - program will fail downstream
                logging.getLogger("HWR").error(
                    "Could not create GPhL working directory: %s", wdir
                )

        for ss0 in command_list:
            ss0 = ss0.split("=")[-1]
            if ss0.startswith("/") and "*" not in ss0 and not os.path.exists(ss0):
                logging.getLogger("HWR").warning("File does not exist : %s" % ss0)

        logging.getLogger("HWR").info("GPhL execute :\n%s", " ".join(command_list))

        # Get environmental variables
        envs = os.environ.copy()

        # # Trick to allow unauthorised account (e.g. ESRF: opid30) to run GPhL programs
        # # Any value is OK, just setting it is enough.
        # envs["AutoPROCWorkFlowUser"] = "1"

        # Hack to pass alternative installation dir for processing
        val = self.software_paths.get("gphl_wf_processing_installation")
        if val:
            envs["GPHL_PROC_INSTALLATION"] = val

        # These env variables are needed in some cases for wrapper scripts
        # Specifically for the stratcal wrapper.
        envs["GPHL_INSTALLATION"] = self.software_paths["GPHL_INSTALLATION"]
        envs["BDG_home"] = self.software_paths["BDG_home"]
        logging.getLogger("HWR").info(
            "Executing GPhL workflow, in environment %s", envs
        )
        try:
            self._running_process = subprocess.Popen(command_list, env=envs)
        except BaseException:
            logging.getLogger().error("Error in spawning workflow application")
            raise

        logging.getLogger("py4j.clientserver").setLevel(logging.WARNING)
        self.set_state(States.RUNNING)

        logging.getLogger("HWR").debug(
            "GPhL workflow pid, returncode : %s, %s"
            % (self._running_process.pid, self._running_process.returncode)
        )

    def workflow_ended(self):
        if self.get_state() == States.OFF:
            # No workflow to abort
            return

        logging.getLogger("HWR").debug("GPhL workflow ended")
        self.set_state(States.OFF)
        if self._await_result is not None:
            # We are awaiting an answer - give an abort
            self._await_result.append((GphlMessages.BeamlineAbort(), None))
            time.sleep(0.2)
        elif self._running_process is not None:
            self._running_process = None
            # NBNB TODO how do we close down the workflow if there is no answer pending?

        self._enactment_id = None
        self._workflow_name = None
        self.workflow_queue = None
        self._await_result = None

        # xx0 = self._running_process
        # self._running_process = None
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
            except BaseException:
                logging.getLogger("HWR").info(
                    "Exception while terminating external workflow process %s", xx0
                )
                logging.getLogger("HWR").info("Error was:", exc_info=True)

    def close_connection(self):

        logging.getLogger("HWR").debug("GPhL Close connection ")
        xx0 = self._gateway
        self._gateway = None
        if xx0 is not None:
            try:
                # Exceptions 'can easily happen' (py4j docs)
                # We could catch them here rather than have them caught and echoed
                # downstream, but it seems to keep the program open (??)
                # xx0.shutdown(raise_exception=True)
                xx0.shutdown()
            except BaseException:
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
                "GPhL Empty or unparsable information message. Ignored"
            )

        else:
            if not enactment_id:
                logging.getLogger("HWR").warning(
                    "GPhL information message lacks enactment ID:"
                )
            elif self._enactment_id != enactment_id:
                logging.getLogger("HWR").warning(
                    "Workflow enactment I(D %s != info message enactment ID %s."
                    % (self._enactment_id, enactment_id)
                )
            if self.workflow_queue is not None:
                # Could happen if we have ended the workflow
                self.workflow_queue.put_nowait(
                    (message_type, payload, correlation_id, None)
                )

        logging.getLogger("HWR").debug("Text info message - return None")
        #
        return None

    def processMessage(self, py4j_message):
        """Receive and process message from workflow server
        Return goes to server

        NB Callled freom external java) workflow"""

        xx0 = self._decode_py4j_message(py4j_message)
        message_type = xx0.message_type
        payload = xx0.payload
        correlation_id = xx0.correlation_id
        enactment_id = xx0.enactment_id

        if not enactment_id:
            logging.getLogger("HWR").error(
                "GPhL message lacks enactment ID - sending 'Abort' to external workflow"
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
                "GPhL message lacks payload - sending 'Abort' to external workflow"
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
            self.set_state(States.OPEN)
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
                self._await_result = None
                if self.get_state() == States.OPEN:
                    self.set_state(States.RUNNING)

                logging.getLogger("HWR").debug(
                    "GPhL - response=%s jobId=%s messageId=%s"
                    % (result.__class__.__name__, enactment_id, correlation_id)
                )
                return self._response_to_server(result, correlation_id)

        elif message_type in ("WorkflowAborted", "WorkflowCompleted", "WorkflowFailed"):
            if self.workflow_queue is not None:
                # Could happen if we have ended the workflow
                self.workflow_queue.put_nowait(
                    (message_type, payload, correlation_id, None)
                )
                self.workflow_queue.put_nowait(StopIteration)
            logging.getLogger("HWR").debug("Aborting - return None")
            return None

        else:
            logging.getLogger("HWR").error(
                "GPhL Unknown message type: %s - aborting", message_type
            )
            return self._response_to_server(
                GphlMessages.BeamlineAbort(), correlation_id
            )

    # def _extractResponse(self, responses, message_type):
    #     result = abort_message = None
    #
    #     validResponses = [tt0 for tt0 in responses if tt0[1] is not None]
    #     if not validResponses:
    #         abort_message = "No valid response to %s request" % message_type
    #     elif len(validResponses) == 1:
    #         result = validResponses[0][1]
    #     else:
    #         abort_message = "Too many responses to %s request" % message_type
    #     #
    #     return result, abort_message

    # Conversion to Python

    def _decode_py4j_message(self, py4j_message):
        """Extract messageType and convert py4J object to python object"""

        # Determine message type
        message_type = py4j_message.getPayloadClass().getSimpleName()

        xx0 = py4j_message.getEnactmentId()
        enactment_id = xx0 and xx0.toString()

        xx0 = py4j_message.getCorrelationId()
        correlation_id = xx0 and xx0.toString()
        logging.getLogger("HWR").debug(
            "GPhL incoming: message=%s, jobId=%s,  messageId=%s"
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
                    "GPhL Message type %s not recognised (no %s function)"
                    % (message_type, converterName)
                )
                payload = None
            else:
                try:
                    # Convert to Python objects
                    payload = converter(py4j_message.getPayload())
                except NotImplementedError:
                    logging.getLogger("HWR").error(
                        "Processing of GPhL message %s not implemented", message_type
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
            isInterleaved=py4jGeometricStrategy.isInterleaved(),
            isUserModifiable=py4jGeometricStrategy.isUserModifiable(),
            allowedWidths=py4jGeometricStrategy.getAllowedWidths(),
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
        lattice_format = py4jChooseLattice.getFormat().toString()
        solutions = py4jChooseLattice.getSolutions()
        lattices = py4jChooseLattice.getLattices()
        return GphlMessages.ChooseLattice(
            lattice_format=lattice_format, solutions=solutions, lattices=lattices
        )

    def _CollectionProposal_to_python(self, py4jCollectionProposal):
        uuidString = py4jCollectionProposal.getId().toString()
        strategy = self._GeometricStrategy_to_python(
            py4jCollectionProposal.getStrategy()
        )
        text_type = ConvertUtils.text_type
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

        elif payloadType == "BeamlineAbort":
            return self._BeamlineAbort_to_java(payload)

        elif payloadType == "ReadyForCentring":
            return self._ReadyForCentring_to_java(payload)

        elif payloadType == "SampleCentred":
            return self._SampleCentred_to_java(payload)

        elif payloadType == "CollectionDone":
            # self.test_lattice_selection()
            return self._CollectionDone_to_java(payload)

        elif payloadType == "SelectedLattice":
            return self._SelectedLattice_to_java(payload)

        elif payloadType == "CentringDone":
            return self._CentringDone_to_java(payload)

        elif payloadType == "PriorInformation":
            return self._PriorInformation_to_java(payload)

        else:
            raise ValueError(
                "Payload %s not supported for conversion to java" % payloadType
            )

    def test_lattice_selection(self):
        """Dummy test of lattice selection UI"""

        # |NB @~@~for test only
        test_payload = GphlMessages.ChooseLattice(
            lattice_format="IDXREF",
            crystalSystem="m",
            lattices=["tP", "aP"],
            solutions="""
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

 For protein crystals the possible space group numbers corresponding  to""",
        )
        if self.workflow_queue is not None:
            # Could happen if we have ended the workflow
            self.workflow_queue.put_nowait(
                ("ChooseLattice", test_payload, "9999999", None)
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
        except BaseException:
            self.abort_workflow(
                message="Error sending reply (%s) to server"
                % py4j_payload.getClass().getSimpleName()
            )
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
                ConvertUtils.text_type(priorInformation.sampleId)
            )
        )
        xx0 = priorInformation.sampleName
        if xx0:
            buildr = buildr.sampleName(xx0)
        xx0 = priorInformation.rootDirectory
        if xx0:
            buildr = buildr.rootDirectory(xx0)
        # images not implemented yet - awaiting uses
        # indexingResults not implemented yet - awaiting uses
        buildr = buildr.userProvidedInfo(
            self._UserProvidedInfo_to_java(priorInformation.userProvidedInfo)
        )
        #
        return buildr.build()

    def _SampleCentred_to_java(self, sampleCentred):

        cls = self._gateway.jvm.astra.messagebus.messages.information.SampleCentredImpl

        if sampleCentred.interleaveOrder:
            result = cls(
                float(sampleCentred.imageWidth),
                sampleCentred.wedgeWidth,
                float(sampleCentred.exposure),
                float(sampleCentred.transmission),
                list(sampleCentred.interleaveOrder),
                list(
                    self._PhasingWavelength_to_java(x)
                    for x in sampleCentred.wavelengths
                ),
                self._BcsDetectorSetting_to_java(sampleCentred.detectorSetting),
            )
        else:
            result = cls(
                float(sampleCentred.imageWidth),
                float(sampleCentred.exposure),
                float(sampleCentred.transmission),
                list(
                    self._PhasingWavelength_to_java(x)
                    for x in sampleCentred.wavelengths
                ),
                self._BcsDetectorSetting_to_java(sampleCentred.detectorSetting),
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
            ConvertUtils.text_type(collectionDone.proposalId)
        )
        return jvm.astra.messagebus.messages.information.CollectionDoneImpl(
            proposalId, collectionDone.imageRoot, collectionDone.status
        )

    def _SelectedLattice_to_java(self, selectedLattice):
        jvm = self._gateway.jvm
        frmt = jvm.co.gphl.beamline.v2_unstable.domain_types.IndexingFormat.valueOf(
            selectedLattice.lattice_format
        )
        return jvm.astra.messagebus.messages.information.SelectedLatticeImpl(
            frmt, selectedLattice.solution
        )

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
        if userProvidedInfo.lattice:
            builder = builder.lattice(
                jvm.co.gphl.beamline.v2_unstable.domain_types.CrystalSystem.valueOf(
                    userProvidedInfo.lattice
                )
            )
        # NB The Java point groups are anenumeration: 'PG1', 'PG422' etc.
        xx0 = userProvidedInfo.pointGroup
        if xx0:
            builder = builder.pointGroup(
                jvm.co.gphl.beamline.v2_unstable.domain_types.PointGroup.valueOf(
                    "PG%s" % xx0
                )
            )
        xx0 = userProvidedInfo.spaceGroup
        if xx0:
            builder = builder.spaceGroup(xx0)
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
            ConvertUtils.text_type(phasingWavelength.id_)
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
            ConvertUtils.text_type(bcsDetectorSetting.id_)
        )
        return jvm.astra.messagebus.messages.instrumentation.BcsDetectorSettingImpl(
            float(bcsDetectorSetting.resolution), orgxy_array, axisSettings, javaUuid
        )

    def _GoniostatTranslation_to_java(self, goniostatTranslation):
        jvm = self._gateway.jvm

        if goniostatTranslation is None:
            return None

        gts = goniostatTranslation
        javaUuid = jvm.java.util.UUID.fromString(ConvertUtils.text_type(gts.id_))
        javaRotationId = jvm.java.util.UUID.fromString(
            ConvertUtils.text_type(gts.requestedRotationId)
        )
        axisSettings = dict(((x, float(y)) for x, y in gts.axisSettings.items()))
        newRotation = gts.newRotation
        if newRotation:
            javaNewRotation = self._GoniostatRotation_to_java(newRotation)
            return jvm.astra.messagebus.messages.instrumentation.GoniostatTranslationImpl(
                axisSettings, javaUuid, javaRotationId, javaNewRotation
            )
        else:
            return jvm.astra.messagebus.messages.instrumentation.GoniostatTranslationImpl(
                axisSettings, javaUuid, javaRotationId
            )

    def _GoniostatRotation_to_java(self, goniostatRotation):
        jvm = self._gateway.jvm

        if goniostatRotation is None:
            return None

        grs = goniostatRotation
        javaUuid = jvm.java.util.UUID.fromString(ConvertUtils.text_type(grs.id_))
        axisSettings = dict(((x, float(y)) for x, y in grs.axisSettings.items()))
        # NBNB The final None is necessary because there is no non-deprecated
        # constructor that takes two UUIDs. Eventually the deprecated
        # constructor will disappear and we can remove the None
        return jvm.astra.messagebus.messages.instrumentation.GoniostatRotationImpl(
            axisSettings, javaUuid, None
        )

    def _BeamstopSetting_to_java(self, beamStopSetting):
        jvm = self._gateway.jvm

        if beamStopSetting is None:
            return None

        javaUuid = jvm.java.util.UUID.fromString(
            ConvertUtils.text_type(beamStopSetting.id_)
        )
        axisSettings = dict(
            ((x, float(y)) for x, y in beamStopSetting.axisSettings.items())
        )
        return jvm.astra.messagebus.messages.instrumentation.BeamstopSettingImpl(
            axisSettings, javaUuid
        )

    class Java(object):
        implements = ["co.gphl.py4j.PythonListener"]
