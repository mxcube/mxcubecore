import logging
import gevent
import queue_entry
import socket
import jsonpickle
import queue_model


from HardwareRepository.BaseHardwareObjects import HardwareObject
from queue_entry import QueueEntryContainer
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

        
class XMLRPCServer(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)


    def init(self):
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
        try:
            self.emit('start_queue')
        except Exception as ex:
            logging.getLogger('HWR').exception(str(ex))
            raise
        else:
            return True


    def log_message(self, message, level = 'info'):
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
        
    
