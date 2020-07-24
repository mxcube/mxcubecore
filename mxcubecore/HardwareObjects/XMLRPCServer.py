"""
XMLRPC-Server that makes it possbile to access core features of MXCuBE like
the queue from external applications. The Server is implemented as a
hardware object and is configured with an XML-file. See the example
configuration XML for more information.
"""

import logging
import sys
import inspect
import pkgutil
import types
import gevent
import socket
import time
import json
import atexit
import traceback


from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository import HardwareRepository as HWR

if sys.version_info > (3, 0):
    from xmlrpc.server import SimpleXMLRPCRequestHandler
    from xmlrpc.server import SimpleXMLRPCServer
else:
    from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
    from SimpleXMLRPCServer import SimpleXMLRPCServer


__author__ = "Marcus Oskarsson, Matias Guijarro"
__copyright__ = "Copyright 2012, ESRF"
__credits__ = ["MxCuBE collaboration"]

__version__ = ""
__maintainer__ = "Marcus Oskarsson"
__email__ = "marcus.oscarsson@esrf.fr"
__status__ = "Draft"


class SecureXMLRpcRequestHandler(SimpleXMLRPCRequestHandler):
    """
    Secure XML-RPC request handler class.

    It it very similar to SimpleXMLRPCRequestHandler but it checks for a
    "Token" entry in the header. If this token doesn't correspond to a
    reference token the server sends a "401" (Unauthorized) reply.
    """

    __referenceToken = None

    @staticmethod
    def setReferenceToken(token):
        SecureXMLRpcRequestHandler.__referenceToken = token

    def setup(self):
        self.connection = self.request
        self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
        self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)

    def do_POST(self):
        """
        Handles the HTTPS POST request.

        It was copied out from SimpleXMLRPCServer.py and modified to check for "Token" in the headers.
        """
        # Check that the path is legal
        if not self.is_rpc_path_valid():
            self.report_404()
            return

        referenceToken = SecureXMLRpcRequestHandler.__referenceToken
        if (
            referenceToken is not None
            and "Token" in self.headers
            and referenceToken == self.headers["Token"]
        ):
            try:
                # Get arguments by reading body of request.
                # We read this in chunks to avoid straining
                # socket.read(); around the 10 or 15Mb mark, some platforms
                # begin to have problems (bug #792570).
                max_chunk_size = 10 * 1024 * 1024
                size_remaining = int(self.headers["content-length"])
                L = []
                while size_remaining:
                    chunk_size = min(size_remaining, max_chunk_size)
                    chunk = self.rfile.read(chunk_size)
                    if not chunk:
                        break
                    L.append(chunk)
                    size_remaining -= len(L[-1])
                data = "".join(L)
                # In previous versions of SimpleXMLRPCServer, _dispatch
                # could be overridden in this class, instead of in
                # SimpleXMLRPCDispatcher. To maintain backwards compatibility,
                # check to see if a subclass implements _dispatch and dispatch
                # using that method if present.
                response = self.server._marshaled_dispatch(
                    data, getattr(self, "_dispatch", None)
                )
            except Exception as e:  # This should only happen if the module is buggy
                # internal error, report as HTTP server error
                self.send_response(500)

                # Send information about the exception if requested
                if (
                    hasattr(self.server, "_send_traceback_header")
                    and self.server._send_traceback_header
                ):
                    self.send_header("X-exception", str(e))
                    self.send_header("X-traceback", traceback.format_exc())

                self.end_headers()
            else:
                # got a valid XML RPC response
                self.send_response(200)
                self.send_header("Content-type", "text/xml")
                self.send_header("Content-length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

                # shut down the connection
                self.wfile.flush()
                self.connection.shutdown(1)
        else:
            # Unrecognized token - access unauthorized
            self.send_response(401)
            self.end_headers()


class XMLRPCServer(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self.host = None
        self.port = None
        self.all_interfaces = None
        self.enforceUseOfToken = None

        self.wokflow_in_progress = True
        self.xmlrpc_prefixes = set()
        self.current_entry_task = None
        self.host = None
        self.doEnforceUseOfToken = False

        atexit.register(self.close)

    def init(self):
        """
        Method inherited from HardwareObject, called by framework-2.
        """

        self.all_interfaces = self.get_property("all_interfaces", False)
        # Listen on all interfaces if <all_interfaces>True</all_interfaces>
        # otherwise only on the interface corresponding to socket.gethostname()
        if self.all_interfaces:
            host = ""
        else:
            host = socket.gethostname()

        self.host = host
        self.port = self.get_property("port")

        self.doEnforceUseOfToken = self.get_property("enforceUseOfToken", False)

        try:
            self.open()
        except BaseException:
            logging.getLogger("HWR").debug("Can't start XML-RPC server")

    def close(self):
        try:
            self.xmlrpc_server_task.kill()
            self._server.server_close()
            del self._server
        except AttributeError:
            pass
        logging.getLogger("HWR").info("XML-RPC server closed")

    def open(self):
        # The value of the member self.port is set in the xml configuration
        # file. The initialization is done by the baseclass HardwareObject.
        if hasattr(self, "_server"):
            return
        self.xmlrpc_prefixes = set()

        if self.doEnforceUseOfToken:
            self._server = SimpleXMLRPCServer(
                (self.host, int(self.port)),
                requestHandler=SecureXMLRpcRequestHandler,
                logRequests=False,
                allow_none=True,
            )
        else:
            self._server = SimpleXMLRPCServer(
                (self.host, int(self.port)), logRequests=False, allow_none=True
            )

        msg = "XML-RPC server listening on: %s:%s" % (self.host, self.port)
        logging.getLogger("HWR").info(msg)

        self._server.register_introspection_functions()
        self._server.register_function(self.start_queue)
        self._server.register_function(self.log_message)
        self._server.register_function(self.is_queue_executing)
        self._server.register_function(self.queue_execute_entry_with_id)
        self._server.register_function(self.queue_set_workflow_lims_id)
        self._server.register_function(self.shape_history_get_grid)
        self._server.register_function(self.shape_history_set_grid_data)
        self._server.register_function(self.beamline_setup_read)
        self._server.register_function(self.get_diffractometer_positions)
        self._server.register_function(self.move_diffractometer)
        self._server.register_function(self.save_snapshot)
        self._server.register_function(self.cryo_temperature)
        self._server.register_function(self.flux)
        self._server.register_function(self.set_aperture)
        self._server.register_function(self.get_aperture)
        self._server.register_function(self.get_aperture_list)
        self._server.register_function(self.get_cp)
        self._server.register_function(self.save_current_pos)
        self._server.register_function(self.anneal)
        self._server.register_function(self.open_dialog)
        self._server.register_function(self.workflow_end)
        self._server.register_function(self.dozor_batch_processed)
        self._server.register_function(self.dozor_status_changed)
        self._server.register_function(self.processing_status_changed)
        self.image_num = 0
        self._server.register_function(self.get_image_num, "get_image_num")
        self._server.register_function(self.set_zoom_level)
        self._server.register_function(self.get_zoom_level)
        self._server.register_function(self.get_available_zoom_levels)
        self._server.register_function(self.set_front_light_level)
        self._server.register_function(self.get_front_light_level)
        self._server.register_function(self.set_back_light_level)
        self._server.register_function(self.get_back_light_level)
        self._server.register_function(self.centre_beam)

        # Register functions from modules specified in <apis> element
        if self.hasObject("apis"):
            apis = next(self.get_objects("apis"))
            for api in apis.get_objects("api"):
                recurse = api.get_property("recurse")
                if recurse is None:
                    recurse = True

                self._register_module_functions(
                    api.get_property("module"), recurse=recurse
                )

        self.xmlrpc_server_task = gevent.spawn(self._server.serve_forever)
        self.beamcmds_hwobj = self.get_object_by_role("beamcmds")

    def anneal(self, time):
        cryoshutter_hwobj = self.get_object_by_role("cryoshutter")
        try:
            cryoshutter_hwobj.get_command_object("anneal")(time)
        except Exception as ex:
            logging.getLogger("HWR").exception(str(ex))
            raise
        else:
            return True

    def _add_to_queue(self, task, set_on=True):
        """
        Adds the TaskNode objects contained in the
        list of TaskNodes passed in <task>.

        The TaskNodes are marked as activated in the queue if <set_on>
        is True and to inactivated if False.

        :param task: TaskNode object to add to queue
        :type parent: TaskNode

        :param set_on: Mark TaskNode as activated if True and as inactivated
                       if false.
        :type set_on: bool

        :returns: True on success otherwise False
        :rtype: bool
        """

        # The exception is re raised so that it will
        # be sent to the client.
        try:
            self.emit("add_to_queue", (task, None, set_on))

        except Exception as ex:
            logging.getLogger("HWR").exception(str(ex))
            raise
        else:
            return True

    def start_queue(self):
        """
        Starts the queue execution.

        :returns: True on success otherwise False
        :rtype: bool
        """
        try:
            self.emit("start_queue")
        except Exception as ex:
            logging.getLogger("HWR").exception(str(ex))
            raise
        else:
            return True

    def log_message(self, message, level="info"):
        """
        Logs a message in the user_level_log of MxCuBE,
        normally displayed at the bottom of the MxCuBE
        window.

        :param message: The message to log
        :type parent: str

        :param message: The log level, one of the strings:
                        'info'. 'warning', 'error'
        :type parent: str

        :returns: True on success otherwise False
        :rtype: bool
        """
        status = True

        if level == "info":
            logging.getLogger("user_level_log").info(message)
        elif level == "warning":
            logging.getLogger("user_level_log").warning(message)
        elif level == "error":
            logging.getLogger("user_level_log").error(message)
        else:
            status = False

        return status

    def _model_add_child(self, parent_id, child):
        """
        Adds the model node task to parent_id.

        :param parent_id: The id of the parent.
        :type parent_id: int

        :param child: The TaskNode object to add.
        :type child: TaskNode

        :returns: The id of the added TaskNode object.
        :rtype: int
        """
        try:
            node_id = HWR.beamline.queue_model.add_child_at_id(parent_id, child)
        except Exception as ex:
            logging.getLogger("HWR").exception(str(ex))
            raise
        else:
            return node_id

    def _model_get_node(self, node_id):
        """
        :returns the TaskNode object with the node id <node_id>
        :rtype: TaskNode
        """
        try:
            node = HWR.beamline.queue_model.get_node(node_id)
        except Exception as ex:
            logging.getLogger("HWR").exception(str(ex))
            raise
        else:
            return node

    def queue_execute_entry_with_id(self, node_id):
        """
        Execute the entry that has the model with node id <node_id>.

        :param node_id: The node id of the model to find.
        :type node_id: int
        """
        try:
            model = HWR.beamline.queue_model.get_node(node_id)
            entry = HWR.beamline.queue_manager.get_entry_with_model(model)

            if entry:
                self.current_entry_task = HWR.beamline.queue_manager.execute_entry(
                    entry
                )

        except Exception as ex:
            logging.getLogger("HWR").exception(str(ex))
            raise
        else:
            return True

    def queue_set_workflow_lims_id(self, node_id, lims_id):
        """
        Set lims id of workflow node with id <node_id>

        :param node_id: The node id of the workflow node
        :type node_id: int
        :param lims_id: The lims id
        :type lims_id: int
        """
        try:
            model = HWR.beamline.queue_model.get_node(node_id)
            model.lims_id = lims_id
        except Exception as ex:
            logging.getLogger("HWR").exception(str(ex))
            raise
        else:
            return True

    def is_queue_executing(self, node_id=None):
        """
        :returns: True if the queue is executing otherwise False
        :rtype: bool
        """
        try:
            return HWR.beamline.queue_manager.is_executing(node_id)
        except Exception as ex:
            logging.getLogger("HWR").exception(str(ex))
            raise

    def queue_status(self):
        pass

    def shape_history_get_grid(self):
        """
        :returns: The currently selected grid
        :rtype: dict

        Format of the returned dictionary:

        {'id': id,
         'dx_mm': float,
         'dy_mm': float,
         'steps_x': int,
         'steps_y': int,
         'x1': float,
         'y1': float,
         'angle': float}

        """
        grid_dict = HWR.beamline.sample_view.get_grid()
        # self.shape_history_set_grid_data(grid_dict['id'], {})

        return grid_dict

    def shape_history_set_grid_data(self, key, result_data):
        int_based_result = {}
        for result in result_data.items():
            int_based_result[int(result[0])] = result[1]

        HWR.beamline.sample_view.set_grid_data(key, int_based_result)
        return True

    def get_cp(self):
        """
        :returns: a json encoded list with all centred positions
        """
        cplist = []
        points = HWR.beamline.sample_view.get_points()

        for point in points:
            cp = point.get_centred_positions()[0].as_dict()
            cplist.append(cp)

        json_cplist = json.dumps(cplist)

        return json_cplist

    def beamline_setup_read(self, path):
        raise NotImplementedError(
            "There is no longer a BeamlineSetup object. Please refactor code"
        )
        # try:
        #     return self.beamline_setup_hwobj.read_value(path)
        # except Exception as ex:
        #     logging.getLogger("HWR").exception(str(ex))
        #     raise

    def workflow_set_in_progress(self, state):
        if state:
            self.wokflow_in_progress = True
        else:
            self.wokflow_in_progress = False

    def get_diffractometer_positions(self):
        return HWR.beamline.diffractometer.get_positions()

    def move_diffractometer(self, roles_positions_dict):
        HWR.beamline.diffractometer.move_motors(roles_positions_dict)
        return True

    def save_snapshot(self, imgpath, showScale=False):
        res = True

        try:
            if showScale:
                HWR.beamline.diffractometer.save_snapshot(imgpath)
            else:
                HWR.beamline.diffractometer.get_object_by_role("camera").takeSnapshot(
                    imgpath
                )
        except Exception as ex:
            logging.getLogger("HWR").exception("Could not take snapshot %s " % str(ex))
            res = False

        return res

    def save_current_pos(self):
        """
        Saves the current position as a centered position.
        """
        HWR.beamline.diffractometer.saveCurrentPos()
        return True

    def cryo_temperature(self):
        return HWR.beamline.collect.get_cryo_temperature()

    def flux(self):
        flux = HWR.beamline.flux.get_value()
        if flux is None:
            flux = 0
        return float(flux)

    def set_aperture(self, pos_name, timeout=20):
        HWR.beamline.beam.aperture.move_to_position(pos_name)
        t0 = time.time()
        while HWR.beamline.beam.aperture.get_state() == "MOVING":
            time.sleep(0.1)
            if time.time() - t0 > timeout:
                raise RuntimeError("Timeout waiting for aperture to move")
        return True

    def get_aperture(self):
        return HWR.beamline.beam.aperture.get_current_position_name()

    def get_aperture_list(self):
        return HWR.beamline.beam.aperture.get_predefined_positions_list()

    def open_dialog(self, dict_dialog):
        """
        Opens the workflow dialog in mxCuBE.
        This call blocks util the dialog is ended by the user.
        """
        return_map = {}
        workflow_hwobj = HWR.beamline.workflow
        if workflow_hwobj is not None:
            return_map = workflow_hwobj.open_dialog(dict_dialog)
        self.emit("open_dialog", dict_dialog)
        return return_map

    def workflow_end(self):
        """
        Notify the workflow HO that the workflow has finished.
        """
        workflow_hwobj = HWR.beamline.workflow
        if workflow_hwobj is not None:
            workflow_hwobj.workflow_end()

    def dozor_batch_processed(self, dozor_batch_dict):
        HWR.beamline.online_processing.batch_processed(dozor_batch_dict)

    def dozor_status_changed(self, status):
        HWR.beamline.online_processing.set_processing_status(status)

    def processing_status_changed(self, collection_id, method, status, msg=""):
        for queue_entry in HWR.beamline.queue_model.get_all_dc_queue_entries():
            data_model = queue_entry.get_data_model()
            if data_model.id == collection_id:
                prefix = data_model.acquisitions[0].path_template.get_image_file_name()
                prefix = prefix.replace("%05d", "#####")

                if status in ("started", "success"):
                    logging.getLogger("user_level_log").info(
                        "EDNA %s: processing of data collection %s %s %s"
                        % (method, prefix, status, msg)
                    )
                elif status == "failed":
                    logging.getLogger("user_level_log").error(
                        "EDNA %s: processing of data collection %s %s %s"
                        % (method, prefix, status, msg)
                    )

                queue_entry.add_processing_msg(
                    str(time.strftime("%Y-%m-%d %H:%M:%S")), method, status, msg
                )

    def image_taken(self, image_num):
        self.image_num = image_num

    def get_image_num(self):
        return self.image_num

    def set_zoom_level(self, zoom_level):
        """
        Sets the zoom to a pre-defined level.
        """
        HWR.beamline.diffractometer.zoomMotor.moveToPosition(zoom_level)

    def get_zoom_level(self):
        """
        Returns the zoom level.
        """
        return HWR.beamline.diffractometer.zoomMotor.get_current_position_name()

    def get_available_zoom_levels(self):
        """
        Returns the avaliable pre-defined zoom levels.
        """
        return HWR.beamline.diffractometer.zoomMotor.getPredefinedPositionsList()

    def set_front_light_level(self, level):
        """
        Sets the level of the front light
        """
        HWR.beamline.diffractometer.setFrontLightLevel(level)

    def get_front_light_level(self):
        """
        Gets the level of the front light
        """
        return HWR.beamline.diffractometer.getFrontLightLevel()

    def set_back_light_level(self, level):
        """
        Sets the level of the back light
        """
        HWR.beamline.diffractometer.setBackLightLevel(level)

    def get_back_light_level(self):
        """
        Gets the level of the back light
        """
        return HWR.beamline.diffractometer.getBackLightLevel()

    def centre_beam(self):
        """
        Centers the beam using the beamcmds hardware object.
        """
        self.beamcmds_hwobj.centrebeam()
        while (
            self.beamcmds_hwobj.centrebeam._cmd_execution
            and not self.beamcmds_hwobj.centrebeam._cmd_execution.ready()
        ):
            time.sleep(1)

    def _register_module_functions(self, module_name, recurse=True, prefix=""):
        log = logging.getLogger("HWR")
        # log.info("Registering functions in module %s with XML-RPC server" % module_name)

        if module_name not in sys.modules:
            __import__(module_name)
        module = sys.modules[module_name]

        if not hasattr(module, "xmlrpc_prefix"):
            log.error(
                (
                    'Module %s  has no attribute "xmlrpc_prefix": cannot '
                    + "register its functions. Skipping"
                )
                % module_name
            )
        else:
            prefix += module.xmlrpc_prefix
            if len(prefix) > 0 and prefix[-1] != "_":
                prefix += "_"

            if prefix in self.xmlrpc_prefixes:
                msg = "Prefix %s already used: cannot register for module %s" % (
                    prefix,
                    module_name,
                )
                log.error(msg)
                raise Exception(msg)
            self.xmlrpc_prefixes.add(prefix)

            for f in inspect.getmembers(module, inspect.isfunction):
                if f[0][0] != "_":
                    xmlrpc_name = prefix + f[0]
                    # log.info(
                    #    "Registering function %s.%s as XML-RPC function %s"
                    #    % (module_name, f[1].__name__, xmlrpc_name)
                    # )

                    # Bind method to this XMLRPCServer instance but don't set attribute
                    # This is sufficient to register it as an xmlrpc function.
                    bound_method = types.MethodType(f[1], self, self.__class__)
                    self._server.register_function(bound_method, xmlrpc_name)

            # TODO: Still need to test with deeply-nested modules, in particular that
            # modules and packages are both handled correctly in complex cases.
            if recurse and hasattr(module, "__path__"):
                sub_modules = pkgutil.walk_packages(module.__path__)
                try:
                    sub_module = next(sub_modules)
                    self._register_module_functions(
                        module_name + "." + sub_module[1], recurse=False, prefix=prefix
                    )
                except StopIteration:
                    pass

    def setToken(self, token):
        SecureXMLRpcRequestHandler.setReferenceToken(token)
