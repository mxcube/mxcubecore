# -*- coding: utf-8 -*-

import jsonpickle
import inspect
import logging
from mxcubecore.hardware_objects import queue_model_objects
from mxcubecore.hardware_objects import queue_model_enumerables

xmlrpc_prefix = ""


def queue_set_serialisation(self, backend):
    if backend.lower() == "json":
        return True
    else:
        raise ValueError("Unknown backend type '%s'" % backend)


def queue_get_serialisation(self):
    return "json"


def queue_get_available_serialisations(self):
    """
    Returns a tuple of the available serialisation methods for
    native queue objects
    """
    return ("json",)


def queue_add_node(server_hwobj, task_node, set_on=True):
    """
    Adds the TaskNode objects contained in the json seralized
    list of TaskNodes passed in <task_node>.

    The TaskNodes are marked as activated in the queue if <set_on>
    is True and to inactivated if False.

    :param task_node: TaskNode object to add to queue
    :type parent: TaskNode

    :param set_on: Mark TaskNode as activated if True and as inactivated
                   if false.
    :type set_on: bool

    :returns: True on success otherwise False
    :rtype: bool
    """

    try:
        task = jsonpickle.decode(task_node)
    except Exception as ex:
        logging.getLogger("HWR").exception(str(ex))
        raise

    server_hwobj._add_to_queue(task, set_on)
    return True


def queue_add_child(server_hwobj, parent_id, child):
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
        task = jsonpickle.decode(child)
    except Exception as ex:
        logging.getLogger("HWR").exception(str(ex))
        raise

    node_id = server_hwobj._model_add_child(parent_id, task)
    return node_id


def queue_get_node(server_hwobj, node_id):
    """
    :returns the TaskNode object with the node id <node_id>
    :rtype: TaskNode
    """
    node = server_hwobj._model_get_node(node_id)
    return jsonpickle.encode(node)


def queue_update_result(server_hwobj, node_id, html_report):
    result = False
    node = server_hwobj._model_get_node(node_id)

    if isinstance(node, queue_model_objects.DataCollection):
        node.html_report = str(html_report)
        result = True

    return result


def queue_get_model_code(server_hwobj):
    """
    returns a list of tuples of (name of queue model module, source code of queue model).

    The client can compile and use the queue model as follows:

        for (module_name, module_code) in server.native_get_queue_model_code():
            queue_model_objects = imp.new_module(module_name)
            exec module_code in queue_model_objects.__dict__
            sys.modules[module_name] = queue_model_objects

    The module containing the required queue model objects is the last one in
    the list, so after the loop exits queue_model_objects is set to the module
    that is needed by the client.

    Modules other than the last one are modules imported by the
    queue model that are not available for direct import by the XML-RPC client
    """

    # Recipe from
    # http://code.activestate.com/recipes/82234-importing-a-dynamically-generated-module/

    # At the moment, queue_model_objects does not import anything except
    # standard Python modules, so we only need to send over the code for the
    # queue model itself

    return [
        (queue_model_enumerables.__name__, inspect.getsource(queue_model_enumerables)),
        (queue_model_objects.__name__, inspect.getsource(queue_model_objects)),
    ]
