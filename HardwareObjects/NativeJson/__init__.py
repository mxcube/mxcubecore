# -*- coding: utf-8 -*-

import jsonpickle
import inspect
import logging
import queue_model_objects_v1 as queue_model_objects

xmlrpc_prefix = "native_json"

def add_to_queue(server_hwobj, json_task_node, set_on=True):
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

    try:
        task = jsonpickle.decode(json_task_node)
    except Exception as ex:
        logging.getLogger('HWR').exception(str(ex))
        raise

    server_hwobj._add_to_queue(task, set_on)
    return True

def add_child(server_hwobj, parent_id, json_child):

    """
    Adds the model node task to parent_id.

    :param parent_id: The id of the parent.
    :type parent_id: int

    :param json_child: The TaskNode object to add.
    :type child: TaskNode

    :returns: The id of the added TaskNode object.
    :rtype: int
    """

    try:
        task = jsonpickle.decode(json_child)
    except Exception as ex:
        logging.getLogger('HWR').exception(str(ex))
        raise

    node_id = server_hwobj._model_add_child(parent_id, task)
    return node_id
    
    
def get_node(server_hwobj, node_id):
    """
    :returns the TaskNode object with the node id <node_id>
    :rtype: TaskNode
    """

    node = server_hwobj._model_get_node(node_id)
    return jsonpickle.encode(node)

def get_queue_model_code(server_hwobj):
    """
    returns a list of tuples of (name of queue model module, source code of queue model).

    The client can compile and use the queue model as follows:

        for (module_name, module_code) in server.native_json_get_queue_model_code():
            queue_model_objects = imp.new_module(module_name)
            exec module_code in queue_model_objects.__dict__
            sys.modules[module_name] = queue_model_objects

    The module containing the required queue model objects is the last one in
    the list, so after the loop exits queue_model_objects is set to the module
    that is needed by the client.

    Modules other than the last one are modules imported by the
    queue model that are not available for direct import by the XML-RPC client
    """

    # Recipe from http://code.activestate.com/recipes/82234-importing-a-dynamically-generated-module/

    # At the moment, queue_model_objects_v1 does not import anything except
    # standard Python modules, so we only need to send over the code for the
    # queue model itself

    return [ (queue_model_objects.__name__,
        inspect.getsource(queue_model_objects) ) ]

