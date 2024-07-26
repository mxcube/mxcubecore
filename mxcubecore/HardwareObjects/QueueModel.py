#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.
#
#  Please user PEP 0008 -- "Style Guide for Python Code" to format code
#  https://www.python.org/dev/peps/pep-0008/

"""
Handels interaction with the data model(s). Adding, removing and
retreiving nodes are all done via this object. It is possbile to
handle several models by using register_model and select_model.
"""

import os
import json
import logging
import jsonpickle

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore import queue_entry
from mxcubecore.model import queue_model_objects
from mxcubecore import HardwareRepository as HWR


class Serializer(object):
    @staticmethod
    def serialize(object):
        return json.dumps(object, default=lambda o: o.__dict__.values()[0])


class QueueModel(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)

        self._ispyb_model = queue_model_objects.RootNode()
        self._ispyb_model._node_id = 0
        self._free_pin_model = queue_model_objects.RootNode()
        self._free_pin_model._node_id = 0
        self._plate_model = queue_model_objects.RootNode()
        self._plate_model._node_id = 0

        self._models = {
            "ispyb": self._ispyb_model,
            "free-pin": self._free_pin_model,
            "plate": self._plate_model,
        }

        self._selected_model = self._ispyb_model

    def __getstate__(self):
        d = dict(self.__dict__)
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)

    # Framework-2 method, inherited from HardwareObject and called
    # by the framework after the object has been initialized.
    def init(self):
        """
        Framework-2 method, inherited from HardwareObject and called
        by the framework after the object has been initialized.

        You should normaly not need to call this method.
        """
        pass

    def select_model(self, name):
        """
        Selects the model with the name <name>

        :param name: The name of the model to select.
        :type name: str

        :returns: None
        :rtype: NoneType
        """
        self._selected_model = self._models[name]
        HWR.beamline.queue_manager.clear()
        self._re_emit(self._selected_model)

    def get_model_root(self):
        """
        :returns: The selected model root.
        :rtype: TaskNode
        """
        return self._selected_model

    def clear_model(self, name=None):
        """
        Clears the model with name <name>, clears all if name is None

        :param name: The name of the model to clear.
        :type name: str

        :returns: None
        :rtype: NoneType
        """
        self._models[name] = queue_model_objects.RootNode()

        if not name:
            for name in self._models.keys():
                self._models[name] = queue_model_objects.RootNode()

        HWR.beamline.queue_manager.clear()

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
            raise KeyError("The key %s is already registered" % name)
        else:
            self._models[name]

    def _re_emit(self, parent_node):
        """
        Re-emits the 'child_added' for all the nodes in the model.
        """
        for child_node in parent_node.get_children():
            self.emit("child_added", (parent_node, child_node))
            self._re_emit(child_node)

    def add_child(self, parent, child):
        """
        Adds the child node <child>. Raises the exception TypeError
        if child is not of type TaskNode.

        Moves the child (re-parents it) if it already has a parent.

        :param child: TaskNode to add
        :type child: TaskNode

        :returns: None
        :rtype: None
        """
        if True:
            # if isinstance(child, queue_model_objects.TaskNode):
            self._selected_model._total_node_count += 1
            child._parent = parent
            child._node_id = self._selected_model._total_node_count
            parent._children.append(child)
            child._set_name(child._name)
            self.emit("child_added", (parent, child))
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

    def get_node(self, _id, parent=None):
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
            if node._node_id == _id:
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
            self.emit("child_removed", (parent, child))

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
        Method that should be called by the routine that adds
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
        # view_item.setText(0, task_model.get_name())

        # if isinstance(task_model, queue_model_objects.Sample) or \
        #  isinstance(task_model, queue_model_objects.TaskGroup):
        #    view_item.setText(0, task_model.get_name())
        # else:
        view_item.setText(0, task_model.get_display_name())

        view_item.setOn(task_model.is_enabled())

        if isinstance(task_model, queue_model_objects.Sample):
            HWR.beamline.queue_manager.enqueue(qe)
        elif not isinstance(task_model, queue_model_objects.Basket):
            # else:
            view_item.parent().get_queue_entry().enqueue(qe)
        view_item.update_tool_tip()

    def get_next_run_number(self, new_path_template, exclude_current=True):
        """
        Iterates through all the path templates of the tasks
        in the model and returns the next available run number
        for the path template <new_path_template>.

        :param new_path_template: PathTempalte to match with.
        :type new_path_template: PathTemplate
        :param exclude_current: Skips it self when iterating through
                                the model, default Tree.
        :type exlcude_current: bool

        :returns: The next available run number for the given path_template.
        :rtype: int
        """
        all_path_templates = self.get_path_templates()
        conflicting_path_templates = [0]

        for pt in all_path_templates:
            if exclude_current:
                if pt[1] is not new_path_template:
                    if pt[1] == new_path_template:
                        conflicting_path_templates.append(pt[1].run_number)
            else:
                if pt[1] == new_path_template:
                    conflicting_path_templates.append(pt[1].run_number)

        return max(conflicting_path_templates) + 1

    def get_path_templates(self):
        """
        Retrievies a list of all the path templates in the model.
        """
        return self._get_path_templates_rec(self.get_model_root())

    def _get_path_templates_rec(self, parent_node):
        """
        Recursive part of get_path_templates.
        """
        path_template_list = []

        for child_node in parent_node.get_children():
            path_template = child_node.get_path_template()

            if path_template:
                path_template_list.append((child_node, path_template))

            child_path_template_list = self._get_path_templates_rec(child_node)

            if child_path_template_list:
                path_template_list.extend(child_path_template_list)

        return path_template_list

    def check_for_path_collisions(self, new_path_template):
        """
        Returns True if there is a path template (task) in the model,
        that produces the same files as this one.

        :returns: True if there is a potential path collision.
        """
        result = False
        path_template_list = self.get_path_templates()

        for pt in path_template_list:
            if pt[1] is not new_path_template:
                if new_path_template.intersection(pt[1]):
                    result = True

        return result

    def copy_node(self, node):
        """
        Copys the node <node> and returns it.

        :param node: The node to copy.
        :type node: TaskModel

        :returns: A copy of the node.
        :rtype: TaskModel
        """
        new_node = node.copy()

        if new_node.get_path_template():
            pt = new_node.get_path_template()
            new_run_number = self.get_next_run_number(pt)
            pt.run_number = new_run_number
            new_node.set_number(new_run_number)

        # We do not copy grid object, but keep a link to the original grid
        if hasattr(new_node, "grid"):
            new_node.grid = node.grid

        new_node.set_executed(False)

        return new_node

    def get_nodes(self):
        node_list = []

        def get_nodes_list(entry):
            for child in entry._children:
                node_list.append(child)
                get_nodes_list(child)

        for qe in self._selected_model._children:
            get_nodes_list(qe)

        return node_list

    def get_all_queue_entries(self):
        node_list = []

        def get_nodes_list(entry):
            for child in entry._queue_entry_list:
                node_list.append(child)
                get_nodes_list(child)

        for qe in HWR.beamline.queue_manager._queue_entry_list:
            get_nodes_list(qe)

        return node_list

    def get_all_dc_queue_entries(self):
        result = []

        for item in self.get_all_queue_entries():
            if isinstance(item, queue_entry.DataCollectionQueueEntry):
                result.append(item)

        return result

    def save_queue(self, filename=None):
        """Saves queue in the file. Current selected model is saved as a list
        of dictionaries. Information about samples and baskets is not saved
        """
        if not filename:
            filename = os.path.join(self.user_file_directory, "queue_active.dat")

        items_to_save = []

        selected_model = ""
        for key in self._models:
            if self._selected_model == self._models[key]:
                selected_model = key

        queue_entry_list = HWR.beamline.queue_manager.get_queue_entry_list()
        for item in queue_entry_list:
            # On the top level is Sample or Basket
            if isinstance(item, queue_entry.SampleQueueEntry):
                for task_item in item.get_queue_entry_list():
                    task_item_dict = {
                        "sample_location": item.get_data_model().location,
                        "task_group_entry": jsonpickle.encode(
                            task_item.get_data_model()
                        ),
                    }
                    items_to_save.append(task_item_dict)

        save_file = None
        try:
            save_file = open(filename, "w")
            save_file.write(repr((selected_model, items_to_save)))
        except Exception:
            logging.getLogger().exception(
                "Unable to save queue " + "in file %s", filename
            )
            if save_file:
                save_file.close()

    def get_queue_as_json_list(self):
        items_to_save = []

        selected_model = ""
        for key in self._models:
            if self._selected_model == self._models[key]:
                selected_model = key

        queue_entry_list = HWR.beamline.queue_manager.get_queue_entry_list()
        for item in queue_entry_list:
            # On the top level is Sample or Basket
            if isinstance(item, queue_entry.SampleQueueEntry):
                for task_item in item.get_queue_entry_list():
                    task_item_dict = {
                        "sample_location": item.get_data_model().location,
                        # "task_group_entry": Serializer.serialize(task_item.get_data_model())}
                        # "task_group_entry" : jsonpickle.encode(task_item.get_data_model())}
                        "task_group_entry": json.dumps(task_item.get_data_model()),
                    }
                    items_to_save.append(task_item_dict)

        return selected_model, items_to_save

    def load_queue_from_json_list(self, queue_list, snapshot):
        # Prepare list of samplesL
        sample_dict = {}
        for item in HWR.beamline.queue_manager.get_queue_entry_list():
            if isinstance(item, queue_entry.SampleQueueEntry):
                sample_data_model = item.get_data_model()
                sample_dict[sample_data_model.location] = sample_data_model
            elif isinstance(item, queue_entry.BasketQueueEntry):
                for sample_item in item.get_queue_entry_list():
                    sample_data_model = sample_item.get_data_model()
                    sample_dict[sample_data_model.location] = sample_data_model
        if len(queue_list) > 0:
            try:
                for task_group_item in queue_list:
                    task_group_entry = json.load(task_group_item["task_group_entry"])
                    self.add_child(
                        sample_dict[task_group_item["sample_location"]],
                        task_group_entry,
                    )
                    for child in task_group_entry.get_children():
                        child.set_snapshot(snapshot)
                logging.getLogger("HWR").info("Queue loading done")
            except Exception:
                logging.getLogger("HWR").exception("Unable to load queue")

    def load_queue_from_file(self, filename, snapshot=None):
        """Loads queue from file. The problem is snapshots that are
        not stored in the file, so we have to add new ones in
        the loading process

        :returns: model name 'free-pin', 'ispyb' or 'plate'
        """

        logging.getLogger("HWR").info("Loading queue from file %s" % filename)
        load_file = None
        try:
            # Read file and clear the model
            load_file = open(filename, "r")
            decoded_file = eval(load_file.read())
            self.select_model(decoded_file[0])

            # Prepare list of samples
            sample_dict = {}
            for item in HWR.beamline.queue_manager.get_queue_entry_list():
                if isinstance(item, queue_entry.SampleQueueEntry):
                    sample_data_model = item.get_data_model()
                    sample_dict[sample_data_model.location] = sample_data_model
                elif isinstance(item, queue_entry.BasketQueueEntry):
                    for sample_item in item.get_queue_entry_list():
                        sample_data_model = sample_item.get_data_model()
                        sample_dict[sample_data_model.location] = sample_data_model

            if len(decoded_file[1]) > 0:
                for task_group_item in decoded_file[1]:
                    task_group_entry = jsonpickle.decode(
                        task_group_item["task_group_entry"]
                    )
                    self.add_child(
                        sample_dict[task_group_item["sample_location"]],
                        task_group_entry,
                    )
                    for child in task_group_entry.get_children():
                        child.set_snapshot(snapshot)
                logging.getLogger("HWR").info("Queue loading done")
            else:
                logging.getLogger("HWR").info("No queue content available in file")
            return decoded_file[0]
        except Exception:
            logging.getLogger("HWR").exception(
                "Unable to load queue " + "from file %s", filename
            )
            if load_file:
                load_file.close()
