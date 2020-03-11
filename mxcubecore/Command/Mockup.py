import time
import logging
import Queue
import weakref

from HardwareRepository.CommandContainer import CommandObject, ChannelObject


class MockupCommand(CommandObject):
    def __init__(self, name, command_name, ListArgs=None, timeout=1000, **kwargs):
        CommandObject.__init__(self, name, username, **kwargs)

        self.command_name = command_name
        self.result = None

    def __call__(self, *args, **kwargs):
        self.result = args[0]

    def get(self):
        return self.result

    def abort(self):
        pass

    def isConnected(self):
        return True


class MockupChannel(ChannelObject):
    def __init__(self, name, username=None, timeout=1000, **kwargs):
        ChannelObject.__init__(self, name, username, **kwargs)

        self.timeout = int(timeout)
        self.value = kwargs["default_value"]

    def getValue(self, force=False):
        return self.value

    def setValue(self, new_value):
        self.value = new_value
        self.emit("update", self.value)

    def isConnected(self):
        return self.linkid > 0
