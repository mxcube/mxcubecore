"""
QueueManager, handles the execution of the MxCuBE queue. It is implemented
as a hardware object and is configured by an XML file. See the example of the
XML configuration for more details.

The Queue manager acts as both the controller of execution and as the root/
container of the queue, note the inheritance from QueueEntryContainer. See the
documentation for the queue_entry module for more information.
"""
import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
import gevent
import gevent.event
import queue_entry

from HardwareRepository.BaseHardwareObjects import HardwareObject
from queue_entry import QueueEntryContainer

"""
logger = logging.getLogger('queue_exec')
try:
    formatter = \
              logging.Formatter('%(asctime)s |%(levelname)-7s| %(message)s')
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
      if isinstance(handler, TimedRotatingFileHandler):
         filename = handler.baseFilename
         hdlr = logging.FileHandler(os.path.join(os.path.dirname(filename), 'queue_exec.log'))
         break
    else:
        hdlr = logging.StreamHandler(sys.stdout)
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
except:
    pass

logger.setLevel(logging.INFO)
logger = logging.getLogger('queue_exec').\
         info("Module load, probably application start")
"""


class QueueManager(HardwareObject, QueueEntryContainer):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        QueueEntryContainer.__init__(self)
        self._root_task = None
        self._paused_event = gevent.event.Event()
        self._paused_event.set()
        self._current_queue_entry = None
        self._current_queue_entries = []
        self._running = False
        self._disable_collect = False
        self._is_stopped = False

    def __getstate__(self):
        d = dict(self.__dict__)
        d['_root_task'] = None
        d['_paused_event'] = None  
        return d      

    def __setstate__(self, d):
        self.__dict__.update(d)
        self._paused_event = gevent.event.Event()

    def enqueue(self, queue_entry):
        """
        Method inherited from QueueEntryContainer, enqueues the QueueEntry
        object <queue_entry>.

        :param queue_entry: QueueEntry to add
        :type queue_entry: QueueEntry

        :returns: None
        :rtype: NoneType
        """
        QueueEntryContainer.enqueue(self, queue_entry)

    def execute(self):
        """
        Starts execution of the queue.
        """
        if not self.is_disabled():
            self._is_stopped = False
            self._set_in_queue_flag()
            self._root_task = gevent.spawn(self.__execute_task)

    def _set_in_queue_flag(self):
        """
        Methods iterates over all queue entries and sets in_queue flag for
        DataCollectionQueue entries
        """
        self.entry_list = []
        def get_data_collection_list(entry):
            for child in entry._queue_entry_list:
                if ((isinstance(child, queue_entry.DataCollectionQueueEntry) or
                     isinstance(child, queue_entry.CharacterisationGroupQueueEntry)) and
                     not child.get_data_model().is_executed() and child.is_enabled()):
                    self.entry_list.append(child)
                get_data_collection_list(child)

        for qe in self._queue_entry_list:
            get_data_collection_list(qe)

        if len(self.entry_list) > 1:
            for entry in self.entry_list[:-1]:
                entry.in_queue = True

        #msg = "Starting to execute queue with %d elements: " % len(self.entry_list)
        #for entry in self.entry_list:
        #    msg += str(entry) + " (in_queue=%s) " % entry.in_queue
        #logging.getLogger('queue_exec').info(msg)

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
        #self.emit('centringAllowed', (False, ))
        try:
          for qe in self._queue_entry_list:
            try:
                self.__execute_entry(qe)
            except (queue_entry.QueueAbortedException, Exception) as ex:
                try:
                    qe.handle_exception(ex)
                    self.stop()
                except gevent.GreenletExit:
                    pass

                if isinstance(ex, queue_entry.QueueAbortedException):
                    logging.getLogger('user_level_log').\
                        warning('Queue execution was aborted, ' + str(ex))
                else:
                    logging.getLogger('user_level_log').\
                        error('Queue execution failed with: ' + str(ex))

                raise ex
        finally:
          self._running = False
          self.emit('queue_execution_finished', (None,))
          #self.emit('centringAllowed', (True, ))

    def __execute_entry(self, entry):
        if not entry.is_enabled() or self._is_stopped:
            return
        
        status = "Successful"
        #self.emit('centringAllowed', (False, ))
        self.emit('queue_entry_execute_started', (entry, ))
        self.set_current_entry(entry)
        self._current_queue_entries.append(entry)

        logging.getLogger('queue_exec').info('Calling execute on: ' + str(entry))
        logging.getLogger('queue_exec').info('Using model: ' + str(entry.get_data_model()))

        if self.is_paused():
            logging.getLogger('user_level_log').info('Queue paused, waiting ...')
            entry.get_view().setText(1, 'Queue paused, waiting')

        self.wait_for_pause_event()

        failed = False
        try:
            # Procedure to be done before main implmentation
            # of task.
            entry.pre_execute()
            entry.execute()

            for child in entry._queue_entry_list:
                self.__execute_entry(child)
            self.emit('queue_entry_execute_finished', (entry, "Successful"))
        except queue_entry.QueueSkippEntryException:
            # Queue entry, failed, skipp.
            self.emit('queue_entry_execute_finished', (entry, "Skipped"))
            pass
        except (queue_entry.QueueExecutionException, Exception) as ex:
            self.emit('queue_entry_execute_finished', (entry, "Failed"))
            pass
        except (queue_entry.QueueAbortedException, Exception) as ex:
            # Queue entry was aborted in a controlled, way.
            # or in the exception case:
            # Definetly not good state, but call post_execute
            # in anyways, there might be code that cleans up things
            # done in _pre_execute or before the exception in _execute.
            self.emit('queue_entry_execute_finished', (entry, "Aborted"))
            entry.post_execute()
            entry.handle_exception(ex)
            raise ex
        else:
            entry.post_execute()
        finally:
            self.emit('queue_execute_entry_finished', (entry, ))
            self.set_current_entry(None)
            self._current_queue_entries.remove(entry)

    def stop(self):
        """
        Stops the queue execution.

        :returns: None
        :rtype: NoneType
        """
        if self._queue_entry_list:
            for qe in self._current_queue_entries:
                try:
                    self.emit('queue_entry_execute_finished', (qe, "Aborted"))
                    qe.stop()
                    qe.post_execute()
                except queue_entry.QueueAbortedException:
                    pass
                except:
                    pass

        self._root_task.kill(block = False)

        # Reset the pause event, incase we were waiting.
        self.set_pause(False)
        self.emit('queue_stopped', (None,))
        #self.emit('centringAllowed', (True, )) 
        self._is_stopped = True

    def set_pause(self, state):
        """
        Sets the queue in paused state <state>. Emits the signal queue_paused
        with the current state as parameter.

        :param state: Paused if True running if False
        :type state: bool

        :returns: None
        :rtype: NoneType
        """
        self.emit('queue_paused', (state,))
        #self.emit('centringAllowed', (True, ))
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

    def get_entry_with_model(self, model, root_queue_entry = None):
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

    def execute_entry(self, entry):
        """
        Executes the queue entry <entry>.

        :param entry: The entry to execute.
        :type entry: QueueEntry

        :returns: None
        :rtype: NoneType
        """
        self.__execute_entry(entry)

    def clear(self):
        """
        Clears the queue (removes all entries).

        :returns: None
        :rtype: NoneType
        """
        self._queue_entry_list = []

    def show_workflow_tab(self):
        self.emit('show_workflow_tab')

    def show_workflow_tab(self):
        self.emit('show_workflow_tab')

    def __str__(self):
        s = '['

        for entry in self._queue_entry_list:
            s += str(entry)

        return s + ']'
