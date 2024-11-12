import sys
import types

# LNLS
try:
    from types import InstanceType
except ImportError:
    InstanceType = object
import collections
import logging

import gevent


class cleanup:
    def __init__(self, *args, **keys):
        self.cleanup_funcs = args
        self.keys = keys

    def __enter__(self):
        pass

    def __exit__(self, *args):
        if self.cleanup_funcs:
            for cleanup_func in self.cleanup_funcs:
                if not isinstance(cleanup_func, collections.abc.Callable):
                    continue
                try:
                    cleanup_func(**self.keys)
                except Exception:
                    logging.exception(
                        "Exception while calling cleanup callback %s", cleanup_func
                    )
                    continue


class error_cleanup:
    def __init__(self, *args, **keys):
        self.error_funcs = args
        self.keys = keys

    def __enter__(self):
        pass

    def __exit__(self, *args):
        if args[0] is not None and self.error_funcs:
            logging.debug("Doing error cleanup")
            for error_func in self.error_funcs:
                if not isinstance(error_func, collections.abc.Callable):
                    continue
                try:
                    error_func(**self.keys)
                except Exception:
                    logging.exception(
                        "Exception while calling error cleanup callback %s", error_func
                    )
                    continue


class TaskException:
    def __init__(self, exception, error_string, tb):
        self.exception = exception
        self.error_string = error_string
        self.tb = tb


class wrap_errors(object):
    def __init__(self, func):
        """Make a new function from `func', such that it catches all exceptions
        and return it as a TaskException object
        """
        self.func = func

    def __call__(self, *args, **kwargs):
        func = self.func
        try:
            return func(*args, **kwargs)
        except Exception:
            sys.excepthook(*sys.exc_info())
            return TaskException(*sys.exc_info())

    def __str__(self):
        return str(self.func)

    def __repr__(self):
        return repr(self.func)

    def __getattr__(self, item):
        return getattr(self.func, item)


def task(func):
    def start_task(*args, **kwargs):
        if args and isinstance(args[0], InstanceType):
            logging.debug("Starting %s%s", func.__name__, args[1:])
        else:
            logging.debug("Starting %s%s", func.__name__, args)

        try:
            wait = kwargs["wait"]
        except KeyError:
            wait = True
        else:
            del kwargs["wait"]
        try:
            timeout = kwargs["timeout"]
        except KeyError:
            timeout = None
        else:
            del kwargs["timeout"]

        try:
            t = gevent.spawn(wrap_errors(func), *args, **kwargs)

            if wait:
                ret = t.get(timeout=timeout)
                if isinstance(ret, TaskException):
                    sys.excepthook(ret.exception, ret.error_string, ret.tb)
                    raise ret.exception(ret.error_string)
                else:
                    return ret
            else:
                t._get = t.get

                def special_get(self, *args, **kwargs):
                    ret = self._get(*args, **kwargs)
                    if isinstance(ret, TaskException):
                        sys.excepthook(ret.exception, ret.error_string, ret.tb)
                        raise ret.exception(ret.error_string)
                    else:
                        return ret

                setattr(t, "get", types.MethodType(special_get, t))

                return t
        except Exception:
            t.kill()
            raise

    return start_task
