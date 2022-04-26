import gevent

from contextlib import contextmanager


def unpatch_module(module, name):
    """Undo gevent monkey patching of this module

    :param module:
    :param str name: the name given by gevent to this module
    """
    original_module_items = gevent.monkey.saved.pop(name, None)
    if not original_module_items:
        return
    for attr, value in original_module_items.items():
        setattr(module, attr, value)


def repatch_module(module, name):
    """Redo gevent monkey patching of this module,
    whether it is already patched or not.

    :param module:
    :param str name: the name given by gevent to this module
    """
    gevent.monkey._patch_module(name)
