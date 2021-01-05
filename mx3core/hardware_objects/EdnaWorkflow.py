from mx3core.BaseHardwareObjects import HardwareObject

import os
import time
import gevent
import pprint
import logging
import binascii

# import threading
from mx3core.hardware_objects.SecureXMLRpcRequestHandler import SecureXMLRpcRequestHandler
from mx3core import HardwareRepository as HWR

try:
    from httplib import HTTPConnection
except Exception:
    # Python3
    from http.client import HTTPConnection


class State(object):
    """
    Class for mimic the PyTango state object
    """

    def __init__(self, parent):
        self._value = "ON"
        self._parent = parent

    def get_value(self):
        return self._value

    def set_value(self, newValue):
        self._value = newValue
        self._parent.state_changed(newValue)

    def delValue(self):
        pass

    value = property(get_value, set_value, delValue, "Property for value")


class EdnaWorkflow(HardwareObject):
    """
    This HO acts as a interface to the Passerelle EDM workflow engine.

    The previous version of this HO was a Tango client. In order to avoid
    too many changes this version of the HO is a drop-in replacement of the
    previous version, hence the "State" object which mimics the PyTango state.

    Example of a corresponding XML file (currently called "ednaparams.xml"):

    <object class = "EdnaWorkflow" role = "workflow">
    <bes_host>mxhpc2-1705</bes_host>
    <bes_port>8090</bes_port>
    <object href="/session" role="session"/>
    <workflow>
        <title>MXPressA</title>
        <path>MXPressA</path>
    </workflow>
    <workflow>
        <title>...</title>
        <path>...</path>
    </workflow>
    """

    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self._state = State(self)
        self._command_failed = False
        self._besWorkflowId = None
        self._gevent_event = None
        self._bes_host = None
        self._bes_port = None
        self._token = None

    def _init(self):
        pass

    def init(self):
        self._gevent_event = gevent.event.Event()
        self._bes_host = self.get_property("bes_host")
        self._bes_port = int(self.get_property("bes_port"))
        self.state.value = "ON"

    def getState(self):
        return self._state

    def setState(self, newState):
        self._state = newState

    def delState(self):
        pass

    state = property(getState, setState, delState, "Property for state")

    def command_failure(self):
        return self._command_failed

    def set_command_failed(self, *args):
        logging.getLogger("HWR").error("Workflow '%s' Tango command failed!" % args[1])
        self._command_failed = True

    def state_changed(self, new_value):
        new_value = str(new_value)
        logging.getLogger("HWR").debug(
            "%s: state changed to %r", str(self.name()), new_value
        )
        self.emit("stateChanged", (new_value,))

    def workflow_end(self):
        """
        The workflow has finished, sets the state to 'ON'
        """
        # If necessary unblock dialog
        if not self._gevent_event.is_set():
            self._gevent_event.set()
        self.state.value = "ON"

    def open_dialog(self, dict_dialog):
        # If necessary unblock dialog
        if not self._gevent_event.is_set():
            self._gevent_event.set()
        self.params_dict = dict()
        if "reviewData" in dict_dialog and "inputMap" in dict_dialog:
            review_data = dict_dialog["reviewData"]
            for dictEntry in dict_dialog["inputMap"]:
                if "value" in dictEntry:
                    value = dictEntry["value"]
                else:
                    value = dictEntry["defaultValue"]
                self.params_dict[dictEntry["variableName"]] = str(value)
            self.emit("parametersNeeded", (review_data,))
            self.state.value = "OPEN"
            self._gevent_event.clear()
            while not self._gevent_event.is_set():
                self._gevent_event.wait()
                time.sleep(0.1)
        return self.params_dict

    def get_values_map(self):
        return self.params_dict

    def set_values_map(self, params):
        self.params_dict = params
        self._gevent_event.set()

    def get_available_workflows(self):
        workflow_list = list()
        no_wf = len(self["workflow"])
        for wf_i in range(no_wf):
            wf = self["workflow"][wf_i]
            dict_workflow = dict()
            dict_workflow["name"] = str(wf.title)
            dict_workflow["path"] = str(wf.path)
            try:
                req = [r.strip() for r in wf.get_property("requires").split(",")]
                dict_workflow["requires"] = req
            except (AttributeError, TypeError):
                dict_workflow["requires"] = []
            dict_workflow["doc"] = ""
            workflow_list.append(dict_workflow)
        return workflow_list

    def abort(self):
        self.generateNewToken()
        logging.getLogger("HWR").info("Aborting current workflow")
        # If necessary unblock dialog
        if not self._gevent_event.is_set():
            self._gevent_event.set()
        self._command_failed = False
        if self._besWorkflowId is not None:
            abortWorkflowURL = os.path.join(
                "/BES",
                "bridge",
                "rest",
                "processes",
                self._besWorkflowId,
                "STOP?timeOut=0",
            )
            logging.info("BES web service URL: %r" % abortWorkflowURL)
            conn = HTTPConnection(self._bes_host, self._bes_port)
            conn.request("POST", abortWorkflowURL)
            response = conn.getresponse()
            if response.status == 200:
                workflowStatus = response.read()
                logging.info("BES {0}: {1}".format(self._besWorkflowId, workflowStatus))
        self.state.value = "ON"

    def generateNewToken(self):
        # See: https://wyattbaldwin.com/2014/01/09/generating-random-tokens-in-python/
        self._token = binascii.hexlify(os.urandom(5)).decode('utf-8')
        SecureXMLRpcRequestHandler.setReferenceToken(self._token)

    def getToken(self):
        return self._token

    def start(self, listArguments):
        self.generateNewToken()
        # If necessary unblock dialog
        if not self._gevent_event.is_set():
            self._gevent_event.set()
        self.state.value = "RUNNING"

        self.dictParameters = {}
        iIndex = 0
        if len(listArguments) == 0:
            self.error_stream("ERROR! No input arguments!")
            return
        elif len(listArguments) % 2 != 0:
            self.error_stream("ERROR! Odd number of input arguments!")
            return
        while iIndex < len(listArguments):
            self.dictParameters[listArguments[iIndex]] = listArguments[iIndex + 1]
            iIndex += 2
        logging.info("Input arguments:")
        logging.info(pprint.pformat(self.dictParameters))

        if "modelpath" in self.dictParameters:
            modelPath = self.dictParameters["modelpath"]
            if "." in modelPath:
                modelPath = modelPath.split(".")[0]
            self.workflowName = os.path.basename(modelPath)
        else:
            self.error_stream("ERROR! No modelpath in input arguments!")
            return

        time0 = time.time()
        self.startBESWorkflow()
        time1 = time.time()
        logging.info("Time to start workflow: {0}".format(time1 - time0))

    def startBESWorkflow(self):

        logging.info("Starting workflow {0}".format(self.workflowName))
        logging.info(
            "Starting a workflow on http://%s:%d/BES" % (self._bes_host, self._bes_port)
        )
        startWorkflowURL = os.path.join(
            "/BES", "bridge", "rest", "processes", self.workflowName, "RUN"
        )
        isFirstParameter = True
        self.dictParameters["initiator"] = HWR.beamline.session.endstation_name
        self.dictParameters["sessionId"] = HWR.beamline.session.session_id
        self.dictParameters["externalRef"] = HWR.beamline.session.get_proposal()
        self.dictParameters["token"] = self._token
        # Build the URL
        for key in self.dictParameters:
            urlParameter = "%s=%s" % (
                key,
                str(self.dictParameters[key]).replace(" ", "_"),
            )
            if isFirstParameter:
                startWorkflowURL += "?%s" % urlParameter
            else:
                startWorkflowURL += "&%s" % urlParameter
            isFirstParameter = False
        logging.info("BES web service URL: %r" % startWorkflowURL)
        conn = HTTPConnection(self._bes_host, self._bes_port)
        headers = {"Accept": "text/plain"}
        conn.request("POST", startWorkflowURL, headers=headers)
        response = conn.getresponse()
        if response.status == 200:
            self.state.value = "RUNNING"
            requestId = response.read().decode("utf-8")
            logging.info("Workflow started, request id: %r" % requestId)
            self._besWorkflowId = requestId
        else:
            logging.error("Workflow didn't start!")
            requestId = None
            self.state.value = "ON"
