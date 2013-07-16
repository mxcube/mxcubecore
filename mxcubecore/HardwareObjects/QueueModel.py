import queue_entry
import queue_model_objects_v1 as queue_model_objects

from HardwareRepository.BaseHardwareObjects import HardwareObject
from queue_entry import QueueEntryContainer

__author__ = "Marcus Oskarsson"
__copyright__ = "Copyright 2012, ESRF"
__credits__ = ["My great coleagues", "The MxCuBE colaboration"]

__version__ = "0.1"
__maintainer__ = "Marcus Oskarsson"
__email__ = "marcus.oscarsson@esrf.fr"
__status__ = "Beta"


class QueueModel(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        
        ispyb_model = queue_model_objects.RootNode()
        ispyb_model._node_id = 0
        free_pin_model = queue_model_objects.RootNode()
        free_pin_model._node_id = 0
        
        self._models = {'ispyb': ispyb_model,
                        'free-pin': free_pin_model}

        self._selected_model = ispyb_model


    # Framework-2 method, inherited from HardwareObject and called
    # by the framework after the object has been initialized.
    def init(self):
        """
        Framework-2 method, inherited from HardwareObject and called
        by the framework after the object has been initialized.

        You should normaly not need to call this method.
        
        """
        self.queue_controller_hwobj = self.getObjectByRole("queue_controller")


    def select_model(self, name):
        """
        Selects the model with the name <name>

        :param name: The name of the model to select.
        :type name: str

        :returns: None
        :rtype: NoneType
        """
        self._selected_model = self._models[name]
        self.queue_controller_hwobj.clear()
        self._re_emit(self._selected_model)


    def get_model_root(self):
        """
        :returns: The selected model root.
        :rtype: TaskNode
        """
        return self._selected_model


    def clear_model(self, name):
        """
        Clears the model with name <name>

        :param name: The name of the model to clear.
        :type name: str

        :returns: None
        :rtype: NoneType    
        """
        self._models[name] = queue_model_objects.RootNode()
        self.queue_controller_hwobj.clear()


    def register_model(self, name, root_node):
        """
        Register a new model with name <name> and root node <root_node>.

        :param name: The name of the 'new' model.
        :type name: str

        :param root_node: The root of the model.
        :type root_node: RootNode

        :returns: None
        :rtype: NoneType        
        """
        if name in self._models:
            raise KeyError('The key %s is already registered' % name)
        else:
            self._models[name]     


    def _re_emit(self, parent_node):
        """
        Re-emits the 'child_added' for all the nodes in the model.
        """
        for child_node in parent_node.get_children():
            self.emit('child_added', (parent_node, child_node))
            self._re_emit(child_node)
            

    def add_child(self, parent, child):
        """
        Adds the child node <child>. Raises the exception TypeError 
        if child is not of type TaskNode.

        Moves the child (reparents it) if it already has a parent. 

        :param child: TaskNode to add
        :type child: TaskNode

        :returns: None
        :rtype: None
        """
        if isinstance(child, queue_model_objects.TaskNode):
            self._selected_model._total_node_count += 1
            child._parent = parent
            child._node_id = self._selected_model._total_node_count
            parent._children.append(child)
            child._set_name(child._name)
            self.emit('child_added', (parent, child))
        else:
            raise TypeError("Expected type TaskNode, got %s " % str(type(child)))


    def add_child_at_id(self, _id, child):
        """
        Adds a child <child> at the node with the node id <_id>

        :param _id: The id of the parent node.
        :type _id: int

        :param child: The child node to add.
        :type child: TaskNode

        :returns: The id of the child.
        :rtype: int
        
        """
        parent = self.get_node(_id)
        self.add_child(parent, child)
        return child._node_id


    def get_node(self, _id, parent = None):
        """
        Retrieves the node with the node id <_id>

        :param _id: The id of the node to retrieve.
        :type _id: int

        :param parent: parent node to search in.
        :type parent: TaskNode

        :returns: The node with the id <_id>
        :rtype: TaskNode
        """
        if parent is None:
            parent = self._selected_model 
        
        for node in parent._children:
            if node._node_id is _id:
                return node
            else:
                result = self.get_node(_id, node)
                
                if result:
                    return result
                

    def del_child(self, parent, child):
        """
        Removes <child>

        :param child: Child to remove.
        :type child: TaskNode

        :returns: None
        :rtype: None
        """
        if child in parent._children:     
            parent._children.remove(child)
            self.emit('child_removed', (parent, child))
            

    def _detach_child(self, parent, child):
        """
        Detaches the child <child>
        
        :param child: Child to detach.
        :type child: TaskNode

        :returns: None
        :rtype: None
        """
        child = parent._children.pop(child)
        return child


    def set_parent(self, parent, child):
        """
        Sets the parent of the child <child> to <parent>

        :param parent: The parent.
        :type parent: TaskNode Object

        :param child: The child
        :type child: TaskNode Object
        """
        if child._parent:
            self._detach_child(parent, child)
            child.set_parent(parent)
        else:
            child._parent = parent


    def view_created(self, view_item, task_model):
        """
        Method that should be called by the routne that adds
        the view <view_item> for the model <task_model>

        :param view_item: The view item that was added.
        :type view_item: ViewItem

        :param task_model: The associated task model.
        :type task_model: TaskModel
        
        :returns: None
        :rtype: None
        """
        view_item._data_model = task_model
        cls = queue_entry.MODEL_QUEUE_ENTRY_MAPPINGS[task_model.__class__]
        qe = cls(view_item, task_model)
        view_item.setOn(task_model.is_enabled())

        if isinstance(task_model, queue_model_objects.Sample):
            self.queue_controller_hwobj.enqueue(qe)
        else:
            view_item.parent().get_queue_entry().enqueue(qe)


    def get_run_number(self, new_path_template, exclude_task = None):
        all_path_templates = self.get_path_templates()
        conflicting_path_templates = [0]

        for pt in all_path_templates:
            if pt[1] is not new_path_template:
               if pt[1] == new_path_template:
                   conflicting_path_templates.append(pt[1].run_number)

        return max(conflicting_path_templates) + 1


    def get_path_templates(self):
        return self._get_path_templates_rec(self.get_model_root())
    

    def _get_path_templates_rec(self, parent_node):
        path_template_list = []
        
        for child_node in parent_node.get_children():
            path_template = child_node.get_path_template()

            if path_template:
                path_template_list.append((child_node, path_template))

            child_path_template_list = self._get_path_templates_rec(child_node)

            if child_path_template_list:
                path_template_list.extend(child_path_template_list)

        return path_template_list


    
    
