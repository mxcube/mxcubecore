"""
XMLRPC-Server that makes it possbile to access core features of MXCuBE like
the queue from external applications. The Server is implemented as a
hardware object and is configured with an XML-file. See the example
configuration XML below.

<object class="XMLRPCServer" role="XMLRPCServer">
  <port>
    8000
  </port>
</object>
"""

import logging
import sys
import inspect
import pkgutil
import types
import gevent
import socket


from HardwareRepository.BaseHardwareObjects import HardwareObject
from SimpleXMLRPCServer import SimpleXMLRPCServer


__author__ = "Marcus Oskarsson, Matias Guijarro"
__copyright__ = "Copyright 2012, ESRF"
__credits__ = ["MxCuBE colaboration"]

__version__ = ""
__maintainer__ = "Marcus Oskarsson"
__email__ = "marcus.oscarsson@esrf.fr"
__status__ = "Draft"


class XMLRPCServer(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.queue_model_hwobj = None
        self.queue_hwobj = None
        self.beamline_setup_hwobj = None
        self.wokflow_in_progress = True
        self.xmlrpc_prefixes = set()


    def init(self):
        """
        Method inherited from HardwareObject, called by framework-2. 
        """        
        
        # Listen on all interfaces if <all_interfaces>True</all_interfaces>
        # otherwise only on the interface corresponding to socket.gethostname()
        if hasattr(self, "all_interfaces") and self.all_interfaces:
            host = ''
        else:
            host = socket.gethostname()
        
        # The value of the member self.port is set in the xml configuration
        # file. The initialization is done by the baseclass HardwareObject.
        self._server = SimpleXMLRPCServer((host, int(self.port)),
                                          logRequests = False)
        
        self._server.register_introspection_functions()
        self._server.register_function(self.start_queue)
        self._server.register_function(self.log_message)
        self._server.register_function(self.is_queue_executing)
        self._server.register_function(self.queue_execute_entry_with_id)
        self._server.register_function(self.shape_history_get_grid)
        self._server.register_function(self.beamline_setup_read)

        # Register functions from modules specified in <apis> element
        if self.hasObject("apis"):
            apis = next(self.getObjects("apis"))
            for api in apis.getObjects("api"):
                recurse = api.getProperty("recurse")
                if recurse is None:
                    recurse = True
                    
                self._register_module_functions(api.module, recurse=recurse)

        self.queue_hwobj = self.getObjectByRole("queue")
        self.beamline_setup_hwobj = self.getObjectByRole("beamline_setup")
        self.shape_history_hwobj =  self.beamline_setup_hwobj.shape_hisotry_hwobj
        self.queue_model_hwobj =  self.beamline_setup_hwobj.queue_model_hwobj
        self.xmlrpc_server_task = gevent.spawn(self._server.serve_forever)


    def _add_to_queue(self, task, set_on = True):
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
            self.emit('add_to_queue', (task, None, set_on))
            
        except Exception as ex:
            logging.getLogger('HWR').exception(str(ex))
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
            self.emit('start_queue')
        except Exception as ex:
            logging.getLogger('HWR').exception(str(ex))
            raise
        else:
            return True


    def log_message(self, message, level = 'info'):
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
        
        if level == 'info':
            logging.getLogger('user_level_log').info(message)
        elif level == 'warning':
            logging.getLogger('user_level_log').warning(message)
        elif level == 'error':
            logging.getLogger('user_level_log').error(message)
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
            node_id = self.queue_model_hwobj.add_child_at_id(parent_id, child)
        except Exception as ex:
            logging.getLogger('HWR').exception(str(ex))
            raise
        else:
            return node_id


    def _model_get_node(self, node_id):
        """
        :returns the TaskNode object with the node id <node_id>
        :rtype: TaskNode
        """
        try:
            node = self.queue_model_hwobj.get_node(node_id)
        except Exception as ex:
            logging.getLogger('HWR').exception(str(ex))
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
            model = self.queue_model_hwobj.get_node(node_id)
            entry = self.queue_hwobj.get_entry_with_model(model)

            if entry:
                self.queue_hwobj.execute_entry(entry)
                
        except Exception as ex:
            logging.getLogger('HWR').exception(str(ex))
            raise
        else:
            return True


    def is_queue_executing(self):
        """
        :returns: True if the queue is executing otherwise False
        :rtype: bool
        """
        try:
            return self.queue_hwobj.is_executing() 
        except Exception as ex:
            logging.getLogger('HWR').exception(str(ex))
            raise
        

    def queue_status(self):
        pass
    

    def shape_history_get_grid(self):
        """
        :returns: The currently selected grid
        :rtype: dict

        Format of the returned dictionary:

        {'dx_mm': float,
         'dy_mm': float,
         'steps_x': int,
         'steps_y': int,
         'x1': float,
         'y1': float,
         'angle': float}
         
        """
        return self.shape_history_hwobj.get_grid()


    def beamline_setup_read(self, path):
        try:
            return self.beamline_setup_hwobj.read_value(path)
        except Exception as ex:
            logging.getLogger('HWR').exception(str(ex))
            raise


    def workflow_set_in_progress(self, state):
        if state:
            self.wokflow_in_progress = True
        else:
            self.wokflow_in_progress = False

        
    def _register_module_functions(self, module_name, recurse=True, prefix=""):
    
        log = logging.getLogger("HWR")
        
        log.info('Registering functions in module %s with XML-RPC server' %
                            module_name)
        
        if not sys.modules.has_key(module_name):
            __import__(module_name)
        module = sys.modules[module_name]

        if not hasattr(module, 'xmlrpc_prefix'):
            log.error( ('Module %s  has no attribute "xmlrpc_prefix": cannot ' + 
            'register its functions. Skipping') % module_name)
        else:
            prefix += module.xmlrpc_prefix
            if len(prefix) > 0 and prefix[-1] != '_':
                prefix += '_'

            if prefix in self.xmlrpc_prefixes:
                msg = "Prefix %s already used: cannot register for module %s" % \
                (prefix, module_name)
                log.eror(msg)
                raise Exception(msg)
            self.xmlrpc_prefixes.add(prefix)
                
            for f in inspect.getmembers(module, inspect.isfunction):
                if f[0][0] != '_':
                    xmlrpc_name = prefix + f[0]
                    log.info('Registering function %s.%s as XML-RPC function %s' %
                        (module_name, f[1].__name__, xmlrpc_name) )
        
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
                    self._register_module_functions( module_name + '.' + sub_module[1],
                        recurse=False, prefix=prefix)
                except StopIteration:
                    pass

