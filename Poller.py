import logging
from . import saferef
import threading
import Queue
import time
import gevent

POLLERS = {}

def get_poller(poller_id):
    return POLLERS.get(poller_id)
        

def poll(polled_call, polled_call_args=(), polling_period=1, value_changed_callback=None, error_callback=None, compare=True):
     #logging.info(">>>> %s", POLLERS)
     for _, poller in POLLERS.iteritems():
         poller_polled_call = poller.polled_call_ref()
         #logging.info(">>>>> poller.poll_cmd=%s, poll_cmd=%s, poller.args=%s, args=%s", poller_polled_call, polled_call, poller.args, polled_call_args)
         if poller_polled_call == polled_call and poller.args == polled_call_args:
             poller.set_polling_period(min(polling_period, poller.get_polling_period()))
             return poller
            
     #logging.info(">>>>> CREATING NEW POLLER for cmd %r, args=%s, polling time=%d", polled_call, polled_call_args, polling_period)
     poller = _Poller(polled_call, polled_call_args, polling_period, value_changed_callback, error_callback, compare)
     POLLERS[poller.get_id()] = poller
     poller.start()
     return poller
     

class _Poller(threading.Thread):
    def __init__(self, polled_call, polled_call_args=(), polling_period=1, value_changed_callback=None, error_callback=None, compare=True):
        threading.Thread.__init__(self)

        self.daemon = True #would like to get rid of that
        self.polled_call_ref = saferef.safe_ref(polled_call)
        self.args = polled_call_args
        self.polling_period = polling_period
        self.value_changed_callback_ref = saferef.safe_ref(value_changed_callback)
        self.error_callback_ref = saferef.safe_ref(error_callback)
        self.compare = compare
        self.old_res = None
        self.queue = Queue.Queue()
        self.first = True
        self.delay = 0
        self.stop_event = threading.Event()
        self.async_watcher = gevent.get_hub().loop.async()

    def start_delayed(self, delay):
        self.delay = delay
        self.start()

    def stop(self):
        self.stop_event.set()

    def get_id(self):
        return id(self)

    def get_polling_period(self):
        return self.polling_period

    def set_polling_period(self, polling_period):
        #logging.info(">>>>> CHANGIG POLLING PERIOD TO %d", polling_period)
        self.polling_period = polling_period

    def restart(self, polled_call, delay=0):
        self.stop_event.set()
        self.join()
        self.async_watcher = gevent.get_hub().loop.async()
        self.queue = Queue.Queue()
        self.polled_call_ref = saferef.safe_ref(polled_call)
        self.stop_event = threading.Event()
        self.start_delayed(delay)

    def new_event(self):
        res = self.queue.get()
        cb = self.value_changed_callback_ref()
        if cb is not None:
            # TODO: add to a queue to make sure events are processed in right order
            # in all situations
            gevent.spawn(cb, res)

    def run(self):
        self.async_watcher.start(self.new_event)
        
        while not self.stop_event.is_set():
            if self.first and self.delay:
                time.sleep(self.delay / 1000.0)
                
            polled_call = self.polled_call_ref()
            #logging.info("POLLED CALL=%s", polled_call)
            if polled_call is None:
                break

            try:
                res = polled_call(*self.args)
            except Exception, e:
                cb = self.error_callback_ref()
                if cb is not None:
                    try:
                        cb(e, self.get_id())
                    except:
                        pass
                break
            
            del polled_call
            
            if self.first:
                self.first = False
                self.old_res = res
                self.queue.put(res)
                self.async_watcher.send()
            else:
                if self.compare and res == self.old_res:
                    # do nothing: previous value is the same as "new" value
                    pass
                else:
                    self.old_res = res
                    self.queue.put(res)
                    self.async_watcher.send()

            if self.stop_event.is_set():
                break
                       
            time.sleep(self.polling_period / 1000.0)
