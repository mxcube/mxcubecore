"""
XMLRPC-Server that makes it possbile to access core features of MXCuBE like
the queue from external applications. The Server is implemented as a
hardware object and is configured with an XML-file. See the example
configuration XML for more information.
"""

import logging
import sys
import os
import shutil
import inspect
import pkgutil
import types
import socket
import time
import xml
import json
import atexit
import jsonpickle

from functools import reduce
import gevent

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.SecureXMLRpcRequestHandler import (
    SecureXMLRpcRequestHandler,
)

if sys.version_info > (3, 0):
    from xmlrpc.server import SimpleXMLRPCServer
else:
    from SimpleXMLRPCServer import SimpleXMLRPCServer


__author__ = "Marcus Oskarsson, Matias Guijarro"
__copyright__ = "Copyright 2012, ESRF"
__credits__ = ["MxCuBE collaboration"]

__version__ = ""
__maintainer__ = "Marcus Oskarsson"
__email__ = "marcus.oscarsson@esrf.fr"
__status__ = "Draft"


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
        self.use_token = None

        atexit.register(self.close)
        self.gphl_workflow_status = None

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

        self.use_token = self.get_property("use_token", False)

        try:
            self.open()
        except Exception:
            logging.getLogger("HWR").debug("Can't start XML-RPC server")

    def close(self):
        try:
            self.xmlrpc_server_task.kill()
            self._server.server_close()
            del self._server
        except AttributeError:
            pass

    def open(self):
        # The value of the member self.port is set in the xml configuration
        # file. The initialization is done by the baseclass HardwareObject.
        if hasattr(self, "_server"):
            return
        self.xmlrpc_prefixes = set()

        if self.use_token:
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

        self.connect(
            HWR.beamline.gphl_workflow,
            "gphl_workflow_finished",
            self._async_job_completed,
        )

        self._server.register_introspection_functions()
        self._server.register_function(self.start_queue)
        self._server.register_function(self.log_message)
        self._server.register_function(self.is_queue_executing)
        self._server.register_function(self.queue_execute_entry_with_id)
        self._server.register_function(self.queue_set_workflow_lims_id)
        self._server.register_function(self.shape_history_get_grid)
        self._server.register_function(self.shape_history_set_grid_data)
        self._server.register_function(self.beamline_setup_read)
        self._server.register_function(self.get_default_path_template)
        self._server.register_function(self.get_default_acquisition_parameters)

        self._server.register_function(self.get_diffractometer_positions)
        self._server.register_function(self.get_resolution_limits)
        self._server.register_function(self.move_diffractometer)
        self._server.register_function(self.save_snapshot)
        self._server.register_function(self.save_multiple_snapshots)
        self._server.register_function(self.save_twelve_snapshots_script)
        self._server.register_function(self.cryo_temperature)
        self._server.register_function(self.flux)
        self._server.register_function(self.check_for_beam)
        self._server.register_function(self.set_beam_size)
        self._server.register_function(self.get_beam_size)
        self._server.register_function(self.get_available_beam_size)
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
        self._server.register_function(self.addXrayCentring)
        self._server.register_function(self.addGphlWorkflow)
        self._server.register_function(self.get_gphl_workflow_status)
        self._server.register_function(self.clearISPyBClientGroupId)
        self._server.register_function(self.setCharacterisationResult)

        # Register functions from modules specified in <apis> element
        if self.has_object("apis"):
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
            cryoshutter_hwobj.getCommandObject("anneal")(time)
        except Exception as ex:
            logging.getLogger("HWR").exception(str(ex))
            raise
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
        return node

    def queue_execute_entry_with_id(self, node_id, use_async=False):
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
                    entry, use_async=use_async
                )

        except Exception as ex:
            logging.getLogger("HWR").exception(str(ex))
            raise
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

    def shape_history_get_grid(self, sid):
        """
        :param sid: Shape id
        :returns: Grid with id <sid>
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
        grid_dict = HWR.beamline.sample_view.get_shape(sid).as_dict()

        return grid_dict

    def shape_history_set_grid_data(self, key, result_data, data_file_path=None):
        if isinstance(result_data, list):
            result = {}

            for result in result_data.items():
                # int_based_result is not defined
                int_based_result[int(result[0])] = result[1]
        else:
            result = result_data

        HWR.beamline.sample_view.set_grid_data(key, result, data_file_path)
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

    def _getattr_from_path(self, obj, attr, delim="/"):
        """Recurses through an attribute chain to get the attribute."""
        return reduce(getattr, attr.split(delim), obj)

    def beamline_setup_read(self, path):
        value = None

        if path.strip("/").endswith("default-acquisition-parameters"):
            value = jsonpickle.encode(self.get_default_acquisition_parameters())
        elif path.strip("/").endswith("default-path-template"):
            value = jsonpickle.encode(self.get_default_path_template())
        else:
            try:
                path = path[1:] if path[0] == "/" else path
                ho = self._getattr_from_path(HWR, path)
                value = ho.get_value()
            except:
                logging.getLogger("HWR").exception("Could no get %s " % str(path))

        return value

    def get_default_path_template(self):
        return HWR.beamline.get_default_path_template()

    def get_default_acquisition_parameters(self):
        return HWR.beamline.get_default_acquisition_parameters()

    def workflow_set_in_progress(self, state):
        if state:
            self.wokflow_in_progress = True
        else:
            self.wokflow_in_progress = False

    def get_resolution_limits(self):
        return HWR.beamline.resolution.get_limits()

    def get_diffractometer_positions(self):
        return HWR.beamline.diffractometer.get_positions()

    def move_diffractometer(self, roles_positions_dict):
        HWR.beamline.diffractometer.move_motors(roles_positions_dict)
        return True

    def save_twelve_snapshots_script(self, path):
        HWR.beamline.diffractometer.run_script("Take12Snapshots")
        # Wait a couple of seconds for the files to appear

        time.sleep(2)
        HWR.beamline.diffractometer.wait_ready(300)
        tmp_path = HWR.beamline.diffractometer.get_property(
            "custom_snapshot_script_dir", "/tmp"
        )

        file_list = os.listdir(tmp_path)

        for filename in file_list:
            shutil.copy(tmp_path + filename, path)

    def save_multiple_snapshots(self, path_list, show_scale=False):
        logging.getLogger("HWR").info("Taking snapshot %s " % str(path_list))

        try:
            for angle, path in path_list:
                HWR.beamline.diffractometer.phiMotor.set_value(angle)
                # give some time to get the snapshot
                time.sleep(1)
                HWR.beamline.diffractometer.wait_ready()
                self.save_snapshot(path, show_scale, handle_light=False)
        except Exception as ex:
            logging.getLogger("HWR").exception("Could not take snapshot %s " % str(ex))

    def save_snapshot(self, imgpath, showScale=False, handle_light=True):
        res = True
        logging.getLogger("HWR").info("Taking snapshot %s " % str(imgpath))

        try:
            if showScale:
                HWR.beamline.diffractometer.save_snapshot(imgpath)
            else:
                HWR.beamline.sample_view.save_snapshot(imgpath, overlay=False, bw=False)
        except Exception as ex:
            logging.getLogger("HWR").exception("Could not take snapshot %s " % str(ex))
            res = False
        finally:
            pass

        return res

    def save_current_pos(self):
        """
        Saves the current position as a centered position.
        """
        HWR.beamline.diffractometer.save_current_position()
        return True

    def cryo_temperature(self):
        return HWR.beamline.diffractometer.cryostream.get_value()

    def flux(self):
        flux = HWR.beamline.flux.get_value()
        if flux is None:
            flux = 0
        return float(flux)

    def check_for_beam(self):
        return HWR.beamline.flux.is_beam()

    def set_beam_size(self, size):
        """Set the beam size.
        Args:
            size (list): Width, heigth or
                 (str): Size label.
        """
        HWR.beamline.beam.set_value(size)
        return True

    def get_beam_size(self):
        """Get the beam size [um], its shape and label.
        Returns:
            (tuple):  (width, heigth, shape, label), with types
                      (float, float, str, str)
        """
        return HWR.beamline.beam.get_value_xml()

    def get_available_beam_size(self):
        """Get the available predefined beam sizes.
        Returns:
            (dict): Dictionary wiith list of avaiable beam size labels
                    and the corresponding size (width,height) tuples.
                    {"label": [str, str, ...], "size": [(w,h), (w,h), ...]}
        """
        return HWR.beamline.beam.get_defined_beam_size()

    def set_aperture(self, pos_name):
        HWR.beamline.beam.set_value(pos_name)
        return True

    def get_aperture(self):
        return HWR.beamline.beam.get_value()[-1]

    def get_aperture_list(self):
        return HWR.beamline.beam.get_available_size()["values"]

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

    def set_zoom_level(self, pos):
        """
        Sets the zoom to a pre-defined level.
        """
        zoom = HWR.beamline.diffractometer.zoomMotor
        zoom.set_value(zoom.value_to_enum(pos))

    def get_zoom_level(self):
        """
        Returns the zoom level.
        """
        zoom = HWR.beamline.diffractometer.zoomMotor
        pos = zoom.get_value().value
        return pos

    def get_available_zoom_levels(self):
        """
        Returns the avaliable pre-defined zoom levels.
        """
        _value_enum = HWR.beamline.diffractometer.zoomMotor.VALUES.items()
        _names = [name for name, value in _value_enum.items()]

        return _names

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
        logging.getLogger("HWR").info("Setting backlight level to %s" % level)
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
                    bound_method = types.MethodType(f[1], self)
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

    def clearISPyBClientGroupId(self):
        HWR.beamline.lims.group_id = None

    def setCharacterisationResult(self, characterisationResult):
        HWR.beamline.characterisation.characterisationResult = (
            xml.sax.saxutils.unescape(characterisationResult)
        )

    def addXrayCentring(self, parent_node_id, **centring_parameters):
        """Add Xray centring to queue."""
        from mxcubecore.model import queue_model_objects as qmo

        xc_model = qmo.XrayCentring2(**centring_parameters)
        child_id = HWR.beamline.queue_model.add_child_at_id(parent_node_id, xc_model)
        return child_id

    def addGphlWorkflow(self, parent_node_id, task_dict, workflow_id):
        """Add GPhL workflow to queue."""
        self.workflow_id = workflow_id
        from mxcubecore.model import queue_model_objects as qmo

        gphl_model = qmo.GphlWorkflow()
        parent_model = HWR.beamline.queue_model.get_node(int(parent_node_id))
        sample_model = parent_model.get_sample_node()
        gphl_model.init_from_task_data(sample_model, task_dict)
        child_id = HWR.beamline.queue_model.add_child_at_id(parent_node_id, gphl_model)
        self.gphl_workflow_status = "RUNNING"
        return child_id

    def _async_job_completed(self, job_status):
        self.gphl_workflow_status = job_status

    def get_gphl_workflow_status(self):
        return self.gphl_workflow_status
