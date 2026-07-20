"""
QueueManager, handles the execution of the MxCuBE queue. It is implemented
as a hardware object and is configured by an XML file. See the example of the
XML configuration for more details.

The Queue manager acts as both the controller of execution and as the root/
container of the queue, note the inheritance from QueueEntryContainer. See the
documentation for the queue_entry module for more information.
"""

import logging

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore import queue_entry
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.model import queue_model_objects
from mxcubecore.model.queue_model_enumerables import CENTRING_METHOD
from mxcubecore.queue_entry import base_queue_entry
from mxcubecore.queue_entry.base_queue_entry import QUEUE_ENTRY_STATUS

QueueEntryContainer = base_queue_entry.QueueEntryContainer


class QueueManager(HardwareObject, QueueEntryContainer):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        QueueEntryContainer.__init__(self)
        self.centring_method = CENTRING_METHOD.NONE
        self._root_task = None
        self._paused_event = gevent.event.Event()
        self._paused_event.set()
        self._current_queue_entry = None
        self._current_queue_entries = []
        self._running = False
        self._disable_collect = False
        self._is_stopped = False

    def init(self):
        site_entry_path = self.get_property("site_entry_path")
        if site_entry_path:
            queue_entry.import_queue_entries(site_entry_path.split(","))
        else:
            queue_entry.import_queue_entries()

    def __getstate__(self):
        d = dict(self.__dict__)
        d["_root_task"] = None
        d["_paused_event"] = None
        return d

    def __setstate__(self, d):
        self.__dict__.update(d)
        self._paused_event = gevent.event.Event()

    @property
    def current_queue_entries(self):
        return self._current_queue_entries

    def enqueue(self, queue_entry):
        """
        Method inherited from QueueEntryContainer, enqueues the QueueEntry
        object <queue_entry>.

        :param queue_entry: QueueEntry to add
        :type queue_entry: QueueEntry

        :returns: None
        :rtype: NoneType
        """

        queue_entry.set_queue_controller(self)
        super(QueueManager, self).enqueue(queue_entry)

    def execute(self, entry=None):
        """
        Starts execution of the queue.

        Runs the entire queue or a single entry (entry is set) as one "run" of
        the queue and  manages the various states such as "running", "paused"
        and "stopped".

        :param entry: Optional, queue_entry to run
        :type entry: QueueEntry
        :raises: RuntimeError, if the queue is already running when called
        """
        if self._running:
            raise RuntimeError("Can't call execute on a queue that is already running")

        if not self.is_disabled():
            # If no entry is passed run all entries in the queue
            # otherwise, run only the entry given
            self.emit("statusMessage", ("status", "Queue running", "running"))
            self._is_stopped = False
            self._running = True

            if not entry:
                self._current_queue_entries = []
                self._set_in_queue_flag()
                self._root_task = gevent.spawn(self.__execute_task)
            else:
                task = gevent.spawn(self.__execute_entry, entry)
                task.link((lambda _t: self._queue_end()))

    def _set_in_queue_flag(self):
        """
        Methods iterates over all queue entries and sets in_queue flag for
        DataCollectionQueue entries
        """
        self.entry_list = []

        def get_data_collection_list(entry):
            for child in entry._queue_entry_list:
                if (
                    (
                        isinstance(child, queue_entry.DataCollectionQueueEntry)
                        or isinstance(
                            child, queue_entry.CharacterisationGroupQueueEntry
                        )
                    )
                    and not child.get_data_model().is_executed()
                    and child.is_enabled()
                ):
                    self.entry_list.append(child)
                get_data_collection_list(child)

        for qe in self._queue_entry_list:
            get_data_collection_list(qe)

        if len(self.entry_list) > 1:
            for index, entry in enumerate(self.entry_list[:-1]):
                entry.in_queue = index + 1

        # msg = "Starting to execute queue with %d elements: " % len(self.entry_list)
        # for entry in self.entry_list:
        #    msg += str(entry) + " (in_queue=%s) " % entry.in_queue
        # logging.getLogger('queue_exec').info(msg)

    def is_executing(self, node_id=None):
        """
        :returns: True if the queue is executing otherwise False
        :rtype: bool
        """
        status = self._running

        if node_id:
            if self._current_queue_entries:
                for qe in self._current_queue_entries:
                    if qe.get_data_model()._node_id == node_id:
                        status = True
                        break
                    else:
                        status = False
            else:
                status = False

        return status

    def __execute_task(self):
        self._running = True
        # self.emit('centringAllowed', (False, ))
        try:
            for qe in self._queue_entry_list:
                try:
                    self.__execute_entry(qe)
                except (base_queue_entry.QueueAbortedException, Exception) as ex:
                    try:
                        qe.handle_exception(ex)
                        self.stop()
                    except gevent.GreenletExit:
                        self.log.exception("")

                    if isinstance(ex, base_queue_entry.QueueAbortedException):
                        logging.getLogger("user_level_log").warning(
                            "Queue execution was aborted, " + str(ex)
                        )
                    else:
                        logging.getLogger("user_level_log").error(
                            "Queue execution failed with: " + str(ex)
                        )

                    raise ex
        finally:
            self._running = False
            self.emit("queue_execution_finished", (None,))

    def __execute_entry(self, entry):
        if not entry.is_enabled() or self._is_stopped:
            return

        self.emit("queue_entry_execute_started", (entry,))
        self.set_current_entry(entry)
        self._current_queue_entries.append(entry)

        logging.getLogger("queue_exec").info("Executing: " + str(entry))

        if self.is_paused():
            logging.getLogger("user_level_log").info("Queue paused, waiting ...")
            entry.get_view().setText(1, "Queue paused, waiting")

        self.wait_for_pause_event()

        try:
            # Procedure to be done before main implementation
            # of task.
            entry.status = QUEUE_ENTRY_STATUS.RUNNING
            entry.pre_execute()
            entry.execute()

            for child in entry._queue_entry_list:
                self.__execute_entry(child)
            # This part should not be here
            # But somehow exception from collect_failed is not caught here
            if entry.is_failed():
                entry.status = QUEUE_ENTRY_STATUS.FAILED
                self.emit("queue_entry_execute_finished", (entry, "Failed"))
                self.emit(
                    "statusMessage", ("status", "Queue execution failed", "error")
                )
            else:
                entry.status = QUEUE_ENTRY_STATUS.SUCCESS
                self.emit("queue_entry_execute_finished", (entry, "Successful"))
                self.emit("statusMessage", ("status", "", "ready"))
        except base_queue_entry.QueueSkipEntryException as ex:
            self.log.warning(
                "encountered Exception (continuing):\n%s" % ex.stack_trace or ex.message
            )
            # Queue entry, failed, skip.
            entry.status = QUEUE_ENTRY_STATUS.SKIPPED
            self.emit("queue_entry_execute_finished", (entry, "Skipped"))
        except base_queue_entry.QueueAbortedException as ex:
            # Queue entry was aborted in a controlled, way.
            # or in the exception case:
            # Definitely not good state, but call post_execute
            # anyway, there might be code that cleans up things
            # done in _pre_execute or before the exception in _execute.
            self.log.warning(
                "encountered Exception (continuing):\n%s" % ex.stack_trace or ex.message
            )
            entry.status = QUEUE_ENTRY_STATUS.FAILED
            self.emit("queue_entry_execute_finished", (entry, "Aborted"))
            entry.post_execute()
            entry.handle_exception(ex)
            raise ex
        except base_queue_entry.QueueExecutionException as ex:
            self.log.warning(
                "encountered Exception (continuing):\n%s" % ex.stack_trace or ex.message
            )
            entry.status = QUEUE_ENTRY_STATUS.FAILED
            self.emit("queue_entry_execute_finished", (entry, "Failed"))
            self.emit("statusMessage", ("status", "Queue execution failed", "error"))
        except:
            self.log.exception("")
            raise
        else:
            entry.post_execute()
        finally:
            # self.emit('queue_entry_execute_finished', (entry, ))
            self.set_current_entry(None)
            self._current_queue_entries.pop(self._current_queue_entries.index(entry))

    def stop(self):
        """
        Stops the queue execution.

        :returns: None
        :rtype: NoneType
        """
        if self._queue_entry_list:
            for qe in self._current_queue_entries:
                try:
                    qe.status = QUEUE_ENTRY_STATUS.FAILED
                    self.emit("queue_entry_execute_finished", (qe, "Aborted"))
                    qe.stop()
                    qe.post_execute()
                except base_queue_entry.QueueAbortedException:
                    self.log.exception("")
                except Exception:
                    self.log.exception("")

        if self._root_task:
            self._root_task.kill(block=False)

        self._queue_end()

    def _queue_end(self):
        # Reset the pause event, in case we were waiting.
        self.set_pause(False)
        self._is_stopped = True
        self._running = False
        self.emit("statusMessage", ("status", "", "Queue stopped"))
        self.emit("queue_stopped", (None,))

    def set_pause(self, state):
        """
        Sets the queue in paused state <state>. Emits the signal queue_paused
        with the current state as parameter.

        :param state: Paused if True running if False
        :type state: bool

        :returns: None
        :rtype: NoneType
        """
        self.emit("queue_paused", (state,))
        self.emit("statusMessage", ("status", "Queue paused", "action_req"))
        # self.emit('centringAllowed', (True, ))
        if state:
            self._paused_event.clear()
        else:
            self._paused_event.set()

    def is_paused(self):
        """
        Returns the pause state, see the method set_pause().

        :returns: None
        :rtype: NoneType
        """
        return not self._paused_event.is_set()

    def pause(self, state):
        """
        Sets the queue in paused state <state> (and waits), paused if True
        running if False.

        :param state: Paused if True running if False
        :type state: bool

        :returns: None
        :rtype: NoneType
        """
        self.set_pause(state)
        self._paused_event.wait()

    def wait_for_pause_event(self):
        """
        Wait for the queue to be set to running set_pause(False) or continue if
        it already was running.

        :returns: None
        :rtype: NoneType
        """
        self._paused_event.wait()

    def disable(self, state):
        """
        Sets the disable state to <state>, disables the possibility
        to call execute if True enables if False.

        :param state: The disabled state, True, False.
        :type state: bool

        :returns: None
        :rtype: NoneType

        """
        self._disable_collect = state

    def is_disabled(self):
        """
        :returns: True if the queue is disabled, (calling execute
                  will do nothing).
        :rtype: bool
        """
        return self._disable_collect

    def set_current_entry(self, entry):
        """
        Sets the currently executing QueueEntry to <entry>.

        :param entry: The entry.
        :type entry: QeueuEntry

        :returns: None
        :rtype: NoneType
        """
        self._current_queue_entry = entry

    def get_current_entry(self):
        """
        Gets the currently executing QueueEntry.

        :returns: The currently executing QueueEntry:
        :rtype: QueueEntry
        """
        return self._current_queue_entry

    def get_entry_with_model(self, model, root_queue_entry=None):
        """
        Find the entry with the data model model.

        :param model: The model to look for.
        :type model: TaskNode

        :returns: The QueueEntry with the model <model>
        :rtype: QueueEntry
        """
        if not root_queue_entry:
            root_queue_entry = self

        for queue_entry in root_queue_entry._queue_entry_list:
            if queue_entry.get_data_model() is model:
                return queue_entry
            else:
                result = self.get_entry_with_model(model, queue_entry)

                if result:
                    return result

    def get_entry(self, node_id):
        """
        Retrieve the model and the queue entry for the model node with id
        <node_id>.

        :param int node_id: Node id of node to retrieve
        :returns: The tuple (model, entry)
        :rtype: Tuple
        """
        if node_id is None:
            dummy_variable = "Cannot retrieve entry without a node id"
            raise ValueError(dummy_variable)

        model = HWR.beamline.queue_model.get_node(int(node_id))
        entry = self.get_entry_with_model(model)
        return model, entry

    def get_entry_status(self, node_id):
        """
        Get the current execution status for the queue entry associated
        with the model node <node_id>.

        :param int node_id: Node id of the model node, or None.
        :returns: (enabled, is_executed, is_running, status), where status
                  is one of the QUEUE_ENTRY_STATUS values.
        :rtype: Tuple
        """
        if node_id is None:
            return True, False, False, None

        model, entry = self.get_entry(node_id)

        enabled = model.is_enabled()
        curr_entry = self.get_current_entry()
        running = self.is_executing() and (
            curr_entry == entry or curr_entry == entry._parent_container
        )

        return enabled, model.is_executed(), running, entry.status

    def enable_entry(self, id_or_qentry, flag):
        """
        Helper function that sets the enabled flag for one or more entries
        and their models.

        Accepts a single item, or a list of items, where each item is
        either a model node id or a QueueEntry object.

        :param object id_or_qentry: Node id, QueueEntry object, or a list
                                     of either.
        :param bool flag: True for enabled False for disabled
        """
        items = id_or_qentry if isinstance(id_or_qentry, list) else [id_or_qentry]

        for item in items:
            if isinstance(item, base_queue_entry.BaseQueueEntry):
                entry, model = item, item.get_data_model()
            else:
                model, entry = self.get_entry(item)

            entry.set_enabled(flag)
            model.set_enabled(flag)

    def _delete_entry(self, entry):
        """Helper function that deletes an entry and its model from the queue."""
        parent_entry = entry.get_container()
        parent_entry.dequeue(entry)
        model = entry.get_data_model()
        HWR.beamline.queue_model.del_child(model.get_parent(), model)
        logging.getLogger("HWR").info(
            "[DELETE QUEUE] FROM:\n%s " % model.get_parent().get_name()
        )

    def delete_entry_at(self, item_pos_list):
        """
        Deletes the queue entries at the given (sample_id, task_index)
        positions.

        :param list item_pos_list: List of [sample_id, task_index] pairs.
                                    task_index may be None/"undefined" to
                                    refer to the sample entry itself.
        """
        for sid, tindex in item_pos_list:
            if tindex in ("undefined", None):
                model = HWR.beamline.queue_model.get_sample_by_loc_str(sid)
            else:
                model = HWR.beamline.queue_model.get_node_at_task_index(
                    sid, int(tindex)
                )

            entry = self.get_entry_with_model(model)

            if tindex not in ("undefined", None) and not isinstance(
                entry, queue_entry.TaskGroupQueueEntry
            ):
                # Get the TaskGroup of the item, there is currently only one
                # task per TaskGroup so we have to remove the entire
                # TaskGroup with its task.
                entry = entry.get_container()

            self._delete_entry(entry)

    def swap_task_entry(self, sid, ti1, ti2):
        """
        Swap order of two queue entries in the queue, with the same sample
        <sid> as parent.

        :param str sid: Sample id
        :param int ti1: Position of task1 (old position)
        :param int ti2: Position of task2 (new position)
        """
        sample_model = HWR.beamline.queue_model.get_sample_by_loc_str(sid)
        sentry = self.get_entry_with_model(sample_model)

        # Swap the order in the queue model
        ti2_temp_model = sample_model.get_children()[ti2]
        sample_model._children[ti2] = sample_model._children[ti1]
        sample_model._children[ti1] = ti2_temp_model

        # Swap queue entry order
        ti2_temp_entry = sentry._queue_entry_list[ti2]
        sentry._queue_entry_list[ti2] = sentry._queue_entry_list[ti1]
        sentry._queue_entry_list[ti1] = ti2_temp_entry

    def enable_sample_entries(self, sample_id_list, flag):
        """
        Sets the enabled flag for the entries of the samples in
        <sample_id_list>.

        :param list sample_id_list: List of sample location strings.
        :param bool flag: True for enabled, False for disabled.
        """
        node_ids = [
            HWR.beamline.queue_model.get_sample_by_loc_str(sample_id)._node_id
            for sample_id in sample_id_list
        ]
        self.enable_entry(node_ids, flag)

    def set_auto_add_diff_plan_for_characterisations(self, autoadd):
        """
        Propagates the auto add diffraction plan flag to the queue entries
        of all Characterisation nodes currently in the queue.

        :param bool autoadd: True autoadd, False wait for user
        """
        for node in HWR.beamline.queue_model.get_nodes():
            if isinstance(node, queue_model_objects.Characterisation):
                entry = self.get_entry_with_model(node)

                if entry is not None:
                    entry.auto_add_diff_plan = autoadd

    def last_queue_node(self):
        """
        Gets the node index information for the node currently being
        executed.

        :returns: dict as returned by QueueModel.node_index, plus "node".
        :rtype: dict
        """
        node = self._current_queue_entries[-1].get_data_model()

        # Reference collections (created for a Characterisation) are
        # orphans in the flattened task list - the node of interest there is
        # the Characterisation itself, not the reference collection.

        if "ref" in node.get_name():
            parent = node.get_parent()
            node = parent._children[0]

        res = HWR.beamline.queue_model.node_index(node)
        res["node"] = node

        return res

    def execute_entry(self, entry, use_async=False):
        """
        Executes the queue entry once the queue has been started <entry>.

        :param entry: The entry to execute.
        :type entry: QueueEntry

        :raises: RuntimeError if the queue is not already running when called
        :returns: None
        :rtype: NoneType
        """
        if not self._running:
            raise RuntimeError(
                "Queue has to be running to execute an entry with execute_entry"
            )

        if use_async:
            gevent.spawn(self.__execute_entry, entry)
        else:
            self.__execute_entry(entry)

    def clear(self):
        """
        Clears the queue (removes all entries).

        :returns: None
        :rtype: NoneType
        """
        self._queue_entry_list = []

    def show_workflow_tab(self):
        self.emit("show_workflow_tab")

    def __str__(self):
        s = "["

        for entry in self._queue_entry_list:
            s += str(entry)

        return s + "]"
