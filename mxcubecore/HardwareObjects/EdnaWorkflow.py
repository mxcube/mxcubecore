from HardwareRepository.BaseHardwareObjects import HardwareObject

import os
import time
import gevent
import pprint
import logging
import requests
import binascii

# import threading
from HardwareRepository.HardwareObjects.SecureXMLRpcRequestHandler import SecureXMLRpcRequestHandler
from HardwareRepository import HardwareRepository as HWR

try:
    from httplib import HTTPConnection
except:
    # Python3
    from http.client import HTTPConnection


class State(object):
    """
    Class for mimic the PyTango state object
    """

    def __init__(self, parent):
        self._value = "ON"
        self._parent = parent

    def getValue(self):
        return self._value

    def setValue(self, new_value):
        self._value = new_value
        self._parent.state_changed(new_value)

    def delValue(self):
        pass

    value = property(getValue, setValue, delValue, "Property for value")


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
        self.command_failed = False
        self.bes_workflow_id = None
        self.gevent_event = None
        self.bes_host = None
        self.bes_port = None
        self.token = None

    def _init(self):
        pass

    def init(self):
        self.gevent_event = gevent.event.Event()
        self.bes_host = self.getProperty("bes_host")
        self.bes_port = int(self.getProperty("bes_port"))
        self._state.value = "ON"

    def getState(self):
        return self._state

    def setState(self, new_state):
        self._state = new_state

    def delState(self):
        pass

    state = property(getState, setState, delState, "Property for state")

    def command_failure(self):
        return self.command_failed

    def set_command_failed(self, *args):
        logging.getLogger("HWR").error("Workflow '%s' Tango command failed!" % args[1])
        self.command_failed = True

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
        if not self.gevent_event.is_set():
            self.gevent_event.set()
        self.state.value = "ON"

    def open_dialog(self, dict_dialog):
        # If necessary unblock dialog
        if not self.gevent_event.is_set():
            self.gevent_event.set()
        self.params_dict = dict()
        if "reviewData" in dict_dialog and "inputMap" in dict_dialog:
            review_data = dict_dialog["reviewData"]
            for dict_entry in dict_dialog["inputMap"]:
                if "value" in dict_entry:
                    value = dict_entry["value"]
                else:
                    value = dict_entry["defaultValue"]
                self.params_dict[dict_entry["variableName"]] = str(value)
            self.emit("parametersNeeded", (review_data,))
            self.state.value = "OPEN"
            self.gevent_event.clear()
            while not self.gevent_event.is_set():
                self.gevent_event.wait()
                time.sleep(0.1)
        return self.params_dict

    def get_values_map(self):
        return self.params_dict

    def set_values_map(self, params):
        self.params_dict = params
        self.gevent_event.set()

    def get_available_workflows(self):
        workflow_list = list()
        no_wf = len(self["workflow"])
        for wf_i in range(no_wf):
            wf = self["workflow"][wf_i]
            dict_workflow = dict()
            dict_workflow["name"] = str(wf.title)
            dict_workflow["path"] = str(wf.path)
            try:
                req = [r.strip() for r in wf.getProperty("requires").split(",")]
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
        if not self.gevent_event.is_set():
            self.gevent_event.set()
        self.command_failed = False
        if self.bes_workflow_id is not None:
            abort_URL = os.path.join("http://{0}:{1}".format(self.bes_host, 
                                                             self.bes_port),
                                     "ABORT", 
                                     self.bes_workflow_id)
            logging.getLogger("HWR").info("BES abort web service URL: %r" % abort_URL)
            response = requests.get(abort_URL)
            if response.status_code == 200:
                workflow_status=response.text
                logging.getLogger("HWR").info("BES workflow id {0}: {1}".format(self.bes_workflow_id, workflow_status))
        self.state.value = "ON"

    def generateNewToken(self):
        # See: https://wyattbaldwin.com/2014/01/09/generating-random-tokens-in-python/
        self.token = binascii.hexlify(os.urandom(5)).decode('utf-8')
        SecureXMLRpcRequestHandler.setReferenceToken(self.token)

    def getToken(self):
        return self.token

    def start(self, list_arguments):
        self.generateNewToken()
        # If necessary unblock dialog
        if not self.gevent_event.is_set():
            self.gevent_event.set()
        self.state.value = "RUNNING"

        self.dict_parameters = {}
        index = 0
        if len(list_arguments) == 0:
            self.error_stream("ERROR! No input arguments!")
            return
        elif len(list_arguments) % 2 != 0:
            self.error_stream("ERROR! Odd number of input arguments!")
            return
        while index < len(list_arguments):
            self.dict_parameters[list_arguments[index]] = list_arguments[index + 1]
            index += 2
        logging.info("Input arguments:")
        logging.info(pprint.pformat(self.dict_parameters))

        if "modelpath" in self.dict_parameters:
            modelpath = self.dict_parameters["modelpath"]
            if "." in modelpath:
                modelpath = modelpath.split(".")[0]
            self.workflow_name = os.path.basename(modelpath)
        else:
            self.error_stream("ERROR! No modelpath in input arguments!")
            return

        time0 = time.time()
        self.startBESWorkflow()
        time1 = time.time()
        logging.info("Time to start workflow: {0}".format(time1 - time0))

    def startBESWorkflow(self):
        logging.info("Starting workflow {0}".format(self.workflow_name))
        logging.info(
            "Starting a workflow on http://%s:%d/BES" % (self.bes_host, self.bes_port)
        )
        start_URL = os.path.join(
            "/BES", "bridge", "rest", "processes", self.workflow_name, "RUN"
        )
        self.dict_parameters["initiator"] = HWR.beamline.session.endstation_name
        self.dict_parameters["sessionId"] = HWR.beamline.session.session_id
        self.dict_parameters["externalRef"] = HWR.beamline.session.get_proposal()
        self.dict_parameters["token"] = self.token
        start_URL = os.path.join("http://{0}:{1}".format(self.bes_host, 
                                                         self.bes_port),
                                 "RUN", 
                                 self.workflow_name)
        logging.getLogger("HWR").info("BES start URL: %r" % start_URL)
        response = requests.post(start_URL, json=self.dict_parameters)
        if response.status_code == 200:
            self.state.value = "RUNNING"
            request_id = response.text
            logging.getLogger("HWR").info("Workflow started, request id: %r" % request_id)
            self.bes_workflow_id = request_id
        else:
            logging.getLogger("HWR").error("Workflow didn't start!")
            request_id = None
            self.state.value = "ON"
