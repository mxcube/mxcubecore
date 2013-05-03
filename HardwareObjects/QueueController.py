import logging
import gevent
import queue_entry

from HardwareRepository.BaseHardwareObjects import HardwareObject
from queue_entry import QueueEntryContainer

class QueueController(HardwareObject, QueueEntryContainer):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        QueueEntryContainer.__init__(self)
        self._root_task = None
        self._paused_event = gevent.event.Event()
        self._paused_event.set()
        self._current_queue_entry = None


    def enqueue(self, queue_entry):
        QueueEntryContainer.enqueue(self, queue_entry)
        

    def execute(self):
        self._root_task = gevent.spawn(self.__execute_task)


    def __execute_entry(self, entry):
        self.set_current_entry(entry)

        if not entry.is_enabled():
            return

        logging.getLogger('queue_exec').info('Calling execute on: ' \
                                             + str(entry))
        logging.getLogger('queue_exec').info('Using model: ' + \
                                             str(entry.get_data_model()))

        if self.is_paused():
            logging.getLogger('user_level_log').info('Queue paused, waiting ...')
            entry.get_view().setText(1, 'Queue paused, waiting')

        self.wait_for_pause_event()
        
        # Procedure to be done before main implmentation
        # of task.
        entry.pre_execute()

        try:
            #self.__queue_controller.current_executing_tasks.\
            #    append(gevent.spawn(self.execute))
            #self.__queue_controller.current_executing_tasks[-1].join()
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
                # Same as above, definetly not good state, but call post_execute
                # in anyways, there might be code that cleans up things
                # done in _pre_execute, _excute or in any thing done in
                # the excute of the children already executed.
                entry.post_execute()
                raise
            
        entry.post_execute()

            
    def __execute_task(self):
        for queue_entry in self._queue_entry_list:
            try:
                self.__execute_entry(queue_entry)
            except Exception as ex:
                try:
                    self.stop()
                except gevent.GreenletExit:
                    pass

                logging.getLogger('user_level_log').error('Error executing queue: ' + ex.message)
                raise ex
        
        self.emit('queue_execution_finished', (None,))
        

    def stop(self):
        self.get_current_entry().stop()
        # Reset the pause event, incase we were waiting.
        self.set_pause(False)
        self.emit('queue_stopped', (None,))
        self._root_task.kill(block = True)


    def set_pause(self, state):
        self.emit('queue_paused', (state,))
        if state:
            self._paused_event.clear()
        else:
            self._paused_event.set()


    def is_paused(self):
        return not self._paused_event.is_set()


    def pause(self, state):
        self.set_pause(state)
        self._paused_event.wait()


    def wait_for_pause_event(self):
        self._paused_event.wait()


    def set_current_entry(self, entry):
        self._current_queue_entry = entry


    def get_current_entry(self):
        return self._current_queue_entry


    def clear(self):
        self._queue_entry_list = []


    def __str__(self):
        s = '['
        
        for entry in self._queue_entry_list:
            s += str(entry)

        return s + ']'
        
