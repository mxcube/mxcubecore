import logging

from dispatcher import saferef
import gevent
import gevent.monkey
from gevent import _threading

from gevent.event import Event
import numpy


try:
    import Queue as queue
except ImportError:
    import queue


log = logging.getLogger("HWR")

POLLERS = {}

gevent_version = list(map(int, gevent.__version__.split('.')))


class _NotInitializedValue:
    pass


NotInitializedValue = _NotInitializedValue()


class PollingException:
    def __init__(self, e, poller_id):
        self.original_exception = e
        self.poller_id = poller_id


def get_poller(poller_id):
    return POLLERS.get(poller_id)


def poll(
    polled_call,
    polled_call_args=(),
    polling_period=1000,
    value_changed_callback=None,
    error_callback=None,
    compare=True,
    start_delay=0,
    start_value=NotInitializedValue,
):
    # logging.info(">>>> %s", POLLERS)
    for poller in POLLERS.values():
        poller_polled_call = poller.polled_call_ref()
        # logging.info(">>>>> poller.poll_cmd=%s, poll_cmd=%s, poller.args=%s, args=%s", poller_polled_call, polled_call, poller.args, polled_call_args)
        if poller_polled_call == polled_call and poller.args == polled_call_args:
            poller.set_polling_period(min(polling_period, poller.get_polling_period()))
            return poller

    # logging.info(">>>>> CREATING NEW POLLER for cmd %r, args=%s, polling time=%d", polled_call, polled_call_args, polling_period)
    poller = _Poller(
        polled_call,
        polled_call_args,
        polling_period,
        value_changed_callback,
        error_callback,
        compare,
    )
    poller.old_res = start_value
    POLLERS[poller.get_id()] = poller
    poller.start_delayed(start_delay)
    return poller


class _Poller:
    def __init__(
        self,
        polled_call,
        polled_call_args=(),
        polling_period=1000,
        value_changed_callback=None,
        error_callback=None,
        compare=True,
    ):
        self.polled_call = polled_call
        self.polled_call_ref = saferef.safe_ref(polled_call)
        self.args = polled_call_args
        self.polling_period = polling_period
        self.value_changed_callback_ref = saferef.safe_ref(value_changed_callback)
        self.error_callback_ref = saferef.safe_ref(error_callback)
        self.compare = compare
        self.old_res = NotInitializedValue
        self.queue = queue.Queue()
        self.delay = 0
        self.stop_event = Event()

        if gevent_version < [1, 3, 0]:
            self.async_watcher = getattr(gevent.get_hub().loop, "async")()
        else:
            self.async_watcher = gevent.get_hub().loop.async_()

    def start_delayed(self, delay):
        self.delay = delay
        _threading.start_new_thread(self.run, ())

    def stop(self):
        self.stop_event.set()
        del POLLERS[self.get_id()]

    def is_stopped(self):
        return self.stop_event.is_set()

    def get_id(self):
        return id(self)

    def get_polling_period(self):
        return self.polling_period

    def set_polling_period(self, polling_period):
        self.polling_period = polling_period

    def restart(self, delay=0):
        self.stop()

        polled_call = self.polled_call_ref()
        value_changed_cb = self.value_changed_callback_ref()
        error_cb = self.error_callback_ref()
        if polled_call is not None:
            return poll(
                polled_call,
                self.args,
                self.polling_period,
                value_changed_cb,
                error_cb,
                self.compare,
                delay,
                start_value=self.old_res,
            )

    def new_event(self):
        while True:
            try:
                res = self.queue.get_nowait()
            except queue.Empty:
                break

            if isinstance(res, PollingException):
                cb = self.error_callback_ref()
                if cb is not None:
                    gevent.spawn(cb, res.original_exception, res.poller_id)
            else:
                cb = self.value_changed_callback_ref()
                if cb is not None:
                    gevent.spawn(cb, res)

    def run(self):
        sleep = gevent.monkey._get_original("time", ["sleep"])[0]

        self.async_watcher.start(self.new_event)

        err_callback_args = None
        error_cb = None
        first_run = True

        while not self.stop_event.is_set():
            if first_run and self.delay:
                sleep(self.delay / 1000.0)
            first_run = False

            if self.stop_event.is_set():
                break

            polled_call = self.polled_call_ref()
            if polled_call is None:
                break

            try:
                res = polled_call(*self.args)
            except Exception as e:
                if self.stop_event.is_set():
                    break
                error_cb = self.error_callback_ref()
                if error_cb is not None:
                    self.queue.put(PollingException(e, self.get_id()))
                break

            del polled_call

            if self.stop_event.is_set():
                break

            if isinstance(res, numpy.ndarray):  # for arrays
                comparison = res == self.old_res
                if isinstance(comparison, bool):
                    is_equal = comparison
                else:
                    is_equal = all(comparison)
            else:
                is_equal = res == self.old_res

            if self.compare and is_equal:
                # do nothing: previous value is the same as "new" value
                pass
            else:
                new_value = True
                if self.compare:
                    new_value = not is_equal

                if new_value:
                    self.old_res = res
                    self.queue.put(res)
            sleep(self.polling_period / 1000.0)

        if error_cb is not None:
            self.async_watcher.send()
