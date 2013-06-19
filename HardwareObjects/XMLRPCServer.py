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
import gevent
import queue_entry
import socket
import jsonpickle
import queue_model_objects_v1


from HardwareRepository.BaseHardwareObjects import HardwareObject
from queue_entry import QueueEntryContainer
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

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
        self.queue_controller_hwobj = None


    def init(self):
        """
        Method inherited from HardwareObject, called by framework-2. 
        """        
        # The value of the member self.port is set in the xml configuration
        # file. The initialization is done by the baseclass HardwareObject.
        self._server = SimpleXMLRPCServer((socket.gethostname(), int(self.port)),
                                          logRequests = False)
        
        self._server.register_introspection_functions()
        self._server.register_function(self.add_to_queue)
        self._server.register_function(self.start_queue)
        self._server.register_function(self.log_message)
        self._server.register_function(self.model_add_child)
        self._server.register_function(self.model_get_node)
        self._server.register_function(self.is_queue_executing)
        self._server.register_function(self.queue_execute_entry_with_id)

        self.queue_model_hwobj = self.getObjectByRole("queue_model")
        self.queue_controller_hwobj = self.getObjectByRole("queue_controller")
        self.xmlrpc_server_task = gevent.spawn(self._server.serve_forever)


    def add_to_queue(self, json_task_node, set_on = True):
        """
        Adds the TaskNode objects contained in the json seralized
        list of TaskNodes passed in <json_task_node>.
        
        The TaskNodes are marked as activated in the queue if <set_on>
        is True and to inactivated if False.

        :param json_task_node: TaskNode object to add to queue
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
            task = jsonpickle.decode(json_task_node)
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


    def model_add_child(self, parent_id, child):
        """
        Adds the model node <child> to parent_id.

        :param parent_id: The id of the parent.
        :type parent_id: int

        :param child: The TaskNode object to add.
        :type child: TaskNode

        :returns: The id of the added TaskNode object.
        :rtype: int
        """
        
        task = jsonpickle.decode(child)

        try:
            node_id = self.queue_model_hwobj.add_child_at_id(parent_id, task)
        except Exception as ex:
            logging.getLogger('HWR').exception(str(ex))
            raise
        else:
            return node_id


    def model_get_node(self, node_id):
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
            return jsonpickle.encode(node)


    def queue_execute_entry_with_id(self, node_id):
        """
        Execute the entry that has the model with node id <node_id>.

        :param node_id: The node id of the model to find.
        :type node_id: int
        """
        import pdb
        pdb.set_trace()

        try:
            model = self.queue_model_hwobj.get_node(node_id)
            entry = self.queue_controller_hwobj.get_entry_with_model(model)

            if entry:
                self.queue_controller_hwobj.execute_entry(entry)
                
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
            return self.queue_controller_hwobj.is_executing() 
        except Exception as ex:
            logging.getLogger('HWR').exception(str(ex))
            raise
        
        
        

    
