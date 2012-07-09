import types
import logging
import gevent
from gevent.util import wrap_errors

class cleanup:
  def __init__(self,cleanup_func,**keys) :
    self.cleanup_func = cleanup_func
    self.keys = keys
    
  def __enter__(self):
    pass

  def __exit__(self,*args):
    if self.cleanup_func is not None:
      logging.debug("Doing cleanup")
      self.cleanup_func(**self.keys)


class error_cleanup:
  def __init__(self,*args,**keys) :
    self.error_funcs = args
    self.keys = keys

  def __enter__(self):
    pass

  def __exit__(self,*args):
    if args[0] is not None and self.error_funcs:
      logging.debug("Doing error cleanup")
      for error_func in self.error_funcs:
        try:
          error_func(**self.keys)
        except:
          logging.exception("Exception while calling cleanup on error callback %s", error_func)
          continue


def task(func):
    def start_task(*args, **kwargs):
        if args and type(args[0]) == types.InstanceType:
          logging.debug("Starting %s%s", func.__name__, args[1:])
        else:
          logging.debug("Starting %s%s", func.__name__, args)

        exception_callback = kwargs.get("exception_callback")
        wait = kwargs.get("wait", True)

        try:
            t = gevent.spawn(wrap_errors(Exception, func), *args)
               
            if kwargs.get("wait", True):
                ret = t.get(timeout = kwargs.get("timeout"))
                if isinstance(ret, Exception):
                  raise ret
                else:
                  return ret
            else:           
                t._get = t.get
                def special_get(self, *args, **kwargs):
                  ret = self._get(*args, **kwargs)
                  if isinstance(ret, Exception):
                    raise ret
                  else:
                    return ret
                setattr(t, "get", types.MethodType(special_get, t)) 
                
                return t
        except:
            t.kill()
            raise
          
    return start_task
