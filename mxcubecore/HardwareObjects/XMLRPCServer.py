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
        
    
