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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import logging
import traceback
from collections import namedtuple

status_list = ["SUCCESS", "WARNING", "FAILED", "SKIPPED", "RUNNING", "NOT_EXECUTED"]
QueueEntryStatusType = namedtuple("QueueEntryStatusType", status_list)
QUEUE_ENTRY_STATUS = QueueEntryStatusType(0, 1, 2, 3, 4, 5)


__credits__ = ["MXCuBE collaboration"]
__license__ = "LGPLv3+"
__category__ = "General"


class QueueExecutionException(Exception):
    def __init__(self, message, origin):
        Exception.__init__(self, message, origin)
        self.message = message
        self.origin = origin
        self.stack_trace = traceback.format_exc()


class QueueAbortedException(QueueExecutionException):
    def __init__(self, message, origin):
        QueueExecutionException.__init__(self, message, origin)
        self.origin = origin
        self.message = message
        self.stack_trace = traceback.format_exc()


class QueueSkippEntryException(QueueExecutionException):
    def __init__(self, message, origin):
        QueueExecutionException.__init__(self, message, origin)
        self.origin = origin
        self.message = message
        self.stack_trace = traceback.format_exc()


class QueueEntryContainer(object):
    """
    A QueueEntryContainer has a list of queue entries, classes
    inheriting BaseQueueEntry, and a Queue object. The Queue object
    controls/handles the execution of the queue entries.
    """

    def __init__(self):
        object.__init__(self)
        self._queue_entry_list = []
        self._queue_controller = None
        self._parent_container = None

    def get_queue_entry_list(self):
        return self._queue_entry_list

    def enqueue(self, queue_entry, queue_controller=None):
        # A queue entry container has a QueueController object
        # which controls the execution of the tasks in the
        # container. The container is set to be its own controller
        # if none is given.
        if queue_controller:
            queue_entry.set_queue_controller(queue_controller)
        else:
            queue_entry.set_queue_controller(self)

        queue_entry.set_container(self)
        self._queue_entry_list.append(queue_entry)

    def dequeue(self, queue_entry):
        """
        Dequeues the QueueEntry <queue_entry> and returns the
        dequeued entry.

        Throws ValueError if the queue_entry is not in the queue.

        :param queue_entry: The queue entry to dequeue/remove.
        :type queue_entry: QueueEntry

        :returns: The dequeued entry.
        :rtype: QueueEntry
        """
        result = None
        index = None
        queue_entry.set_queue_controller(None)
        queue_entry.set_container(None)

        try:
            index = self._queue_entry_list.index(queue_entry)
        except ValueError:
            raise

        if index is not None:
            result = self._queue_entry_list.pop(index)

        log = logging.getLogger("queue_exec")
        msg = "dequeue called with: " + str(queue_entry)
        log.info(msg)

        return result

    def swap(self, queue_entry_a, queue_entry_b):
        """
        Swaps places between the two queue entries <queue_entry_a> and
        <queue_entry_b>.

        Throws a ValueError if one of the entries does not exist in the
        queue.

        :param queue_entry: Queue entry to swap
        :type queue_entry: QueueEntry

        :param queue_entry: Queue entry to swap
        :type queue_entry: QueueEntry
        """
        index_a = None
        index_b = None

        try:
            index_a = self._queue_entry_list.index(queue_entry_a)
        except ValueError:
            raise

        try:
            index_b = self._queue_entry_list.index(queue_entry_b)
        except ValueError:
            raise

        if (index_a is not None) and (index_b is not None):
            temp = self._queue_entry_list[index_a]
            self._queue_entry_list[index_a] = self._queue_entry_list[index_b]
            self._queue_entry_list[index_b] = temp

        log = logging.getLogger("queue_exec")
        msg = "swap called with: " + str(queue_entry_a) + ", " + str(queue_entry_b)
        log.info(msg)

        msg = "Queue is :" + str(self.get_queue_controller())
        log.info(msg)

    def set_queue_controller(self, queue_controller):
        """
        Sets the queue controller, the object that controls execution
        of this QueueEntryContainer.

        :param queue_controller: The queue controller object.
        :type queue_controller: QueueController
        """
        self._queue_controller = queue_controller

    def get_queue_controller(self):
        """
        :returns: The queue controller
        :type queue_controller: QueueController
        """
        return self._queue_controller

    def set_container(self, queue_entry_container):
        """
        Sets the parent queue entry to <queue_entry_container>

        :param queue_entry_container:
        :type queue_entry_container: QueueEntryContainer
        """
        self._parent_container = queue_entry_container

    def get_container(self):
        """
        :returns: The parent QueueEntryContainer.
        :rtype: QueueEntryContainer
        """
        return self._parent_container


class BaseQueueEntry(QueueEntryContainer):
    """
    Base class for queue entry objects. Defines the overall
    interface and behaviour for a queue entry.
    """

    def __init__(self, view=None, data_model=None, view_set_queue_entry=True):
        QueueEntryContainer.__init__(self)
        self._data_model = None
        self._view = None
        self.set_data_model(data_model)
        self.set_view(view, view_set_queue_entry)
        self._checked_for_exec = False
        self.status = QUEUE_ENTRY_STATUS.NOT_EXECUTED
        self.type_str = ""

    def is_failed(self):
        """Returns True if failed
        """
        return self.status == QUEUE_ENTRY_STATUS.FAILED

    def enqueue(self, queue_entry, queue_controller=None):
        """
        Method inherited from QueueEntryContainer, a derived class
        should newer need to override this method.
        """
        QueueEntryContainer.enqueue(self, queue_entry, self.get_queue_controller())

    def set_data_model(self, data_model):
        """
        Sets the model node of this queue entry to <data_model>

        :param data_model: The data model node.
        :type data_model: TaskNode
        """
        self._data_model = data_model

    def get_data_model(self):
        """
        :returns: The data model of this queue entry.
        :rtype: TaskNode
        """
        return self._data_model

    def set_view(self, view, view_set_queue_entry=True):
        """
        Sets the view of this queue entry to <view>. Makes the
        correspodning bi-directional connection if view_set_queue_entry
        is set to True. Which is normaly case, it can be usefull with
        'uni-directional' connection in some rare cases.

        :param view: The view to associate with this entry
        :type view: ViewItem

        :param view_set_queue_entry: Bi- or uni-directional
                                     connection to view.
        :type view_set_queue_entry: bool
        """
        if view:
            self._view = view

            if view_set_queue_entry:
                view.set_queue_entry(self)

    def get_view(self):
        """
        :returns the view:
        :rtype: ViewItem
        """
        return self._view

    def is_enabled(self):
        """
        :returns: True if this item is enabled.
        :rtype: bool
        """
        return self._checked_for_exec

    def set_enabled(self, state):
        """
        Enables or disables this entry, controls wether this item
        should be executed (enabled) or not (disabled)

        :param state: Enabled if state is True otherwise disabled.
        :type state: bool
        """
        self._checked_for_exec = state

    def execute(self):
        """
        Execute method, should be overriden my subclasses, defines
        the main body of the procedure to be performed when the entry
        is executed.

        The default executer calls excute on all child entries after
        this method but before post_execute.
        """
        msg = "Calling execute on: " + str(self)
        logging.getLogger("queue_exec").info(msg)

    def pre_execute(self):
        """
        Procedure to be done before execute.
        """
        msg = "Calling pre_execute on: " + str(self)
        logging.getLogger("queue_exec").info(msg)
        self.get_data_model().set_running(True)

    def post_execute(self):
        """
        Procedure to be done after execute, and execute of all
        children of this entry.
        """
        msg = "Calling post_execute on: " + str(self)
        logging.getLogger("queue_exec").info(msg)
        view = self.get_view()

        view.setHighlighted(True)
        view.setOn(False)
        self.get_data_model().set_executed(True)
        self.get_data_model().set_running(False)
        self.get_data_model().set_enabled(False)
        self.set_enabled(False)
        self._set_background_color()

    def _set_background_color(self):
        view = self.get_view()

        if self.get_data_model().is_executed():
            view.set_background_color(self.status + 1)
        else:
            view.set_background_color(0)
            # view.setBackgroundColor(widget_colors.WHITE)

    def stop(self):
        """
        Stops the execution of this entry, should free
        external resources, cancel all pending processes and so on.
        """
        self.get_view().setText(1, "Stopped")
        msg = "Calling stop on: " + str(self)
        logging.getLogger("queue_exec").info(msg)

    def handle_exception(self, ex):
        view = self.get_view()

        if view and isinstance(ex, QueueExecutionException):
            if ex.origin is self:
                # view.setBackgroundColor(widget_colors.LIGHT_RED)
                view.set_background_color(3)

    def __str__(self):
        info_str = "<%s object at %s> [" % (self.__class__.__name__, hex(id(self)))

        for entry in self._queue_entry_list:
            info_str += str(entry)

        return info_str + "]"

    def get_type_str(self):
        return self.type_str
