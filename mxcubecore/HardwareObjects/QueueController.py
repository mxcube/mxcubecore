"""
QueueController, handles the execution of the MxCuBE queue. It is implemented
as a hardware object and is configured by an XML file. See the example of the
XML configuration below for more details.

<object class = "QueueController" role = "QueueController">
  <object href="/sc" role="sample_changer"/>    
  <object href="/minidiff" role="diffractometer"/>
  <object href="/energyscan" role="energy"/>
  <object href="/mxlocal" role="beamline_configuration"/>
  <object href="/data-analysis" role="data_analysis"/>
  <object href="/mxcollect" role="collect"/>
</object>

The QueueController acts as both the controller of execution and as the root/
container of the queue, note the inheritance from QueueEntryContainer. See the
documentation for the queue_entry module for more information.
"""

import logging
import gevent
import queue_entry


from HardwareRepository.BaseHardwareObjects import HardwareObject
from queue_entry import QueueEntryContainer

__author__ = "Marcus Oskarsson"
__copyright__ = "Copyright 2012, ESRF"
__credits__ = ["My great coleagues", "The MxCuBE colaboration"]

__version__ = "0.1"
__maintainer__ = "Marcus Oskarsson"
__email__ = "marcus.oscarsson@esrf.fr"
__status__ = "Beta"


logger = logging.getLogger('queue_exec')
try:
    formatter = \
              logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr = logging.FileHandler('/users/blissadm/log/queue_exec.log')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
except:
    pass

logger.setLevel(logging.INFO)
logger = logging.getLogger('queue_exec').\
         info("Module load, probably application start")


class QueueController(HardwareObject, QueueEntryContainer):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        QueueEntryContainer.__init__(self)
        self._root_task = None
        self._paused_event = gevent.event.Event()
        self._paused_event.set()
        self._current_queue_entry = None


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
        self._root_task = gevent.spawn(self.__execute_task)


    def __execute_task(self):
        for queue_entry in self._queue_entry_list:
            try:
                self.__execute_entry(queue_entry)
            except Exception as ex:
                try:
                    self.stop()
                except gevent.GreenletExit:
                    pass

                logging.getLogger('user_level_log').error('Error executing ' +\
                                                          'queue' + ex.message)
                raise ex
        
        self.emit('queue_execution_finished', (None,))
 

    def __execute_entry(self, entry):
        self.set_current_entry(entry)

        if not entry.is_enabled():
            return

        logging.getLogger('queue_exec').info('Calling execute on: ' \
                                             + str(entry))
        logging.getLogger('queue_exec').info('Using model: ' + \
                                             str(entry.get_data_model()))

        if self.is_paused():
            logging.getLogger('user_level_log').info('Queue paused,' +\
                                                     'waiting ...')
            entry.get_view().setText(1, 'Queue paused, waiting')

        self.wait_for_pause_event()
        
        # Procedure to be done before main implmentation
        # of task.
        entry.pre_execute()

        try:
            entry.execute()
        except:
            # This is definetly not good state, but call post_execute
            # in anyways, there might be code that cleans up things
            # done in _pre_execute or before the exception in _execute.
            entry.post_execute()
            raise

        
        # Call execute on the children of this node
        for child in entry._queue_entry_list:
            try:
                self.__execute_entry(child)
            except:
                # Same as above, definetly not good state, but call
                # post_execut in anyways, there might be code that cleans up
                # things done in _pre_execute, _excute or in any thing done in
                # the excute of the children already executed.
                entry.post_execute()
                raise
            
        entry.post_execute()
        

    def stop(self):
        """
        Stops the queue execution.

        :returns: None
        :rtype: NoneType
        """
        self.get_current_entry().stop()
        # Reset the pause event, incase we were waiting.
        self.set_pause(False)
        self.emit('queue_stopped', (None,))
        self._root_task.kill(block = True)


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


    def clear(self):
        """
        Clears the queue (removes all entries).

        :returns: None
        :rtype: NoneType
        """
        self._queue_entry_list = []


    def __str__(self):
        s = '['
        
        for entry in self._queue_entry_list:
            s += str(entry)

        return s + ']'
        
