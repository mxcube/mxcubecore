import logging
import weakref
import copy

from .. import saferef
from .. import Poller
from HardwareRepository.CommandContainer import CommandObject, ChannelObject
from .. import TacoDevice_MTSafe as TacoDevice


class TacoCommand(CommandObject):
    def __init__(
        self, name, command, taconame=None, username=None, args=None, dc=False, **kwargs
    ):
        CommandObject.__init__(self, name, username, **kwargs)

        self.command = command
        self.deviceName = taconame
        self.dataCollector = dc
        self.pollers = {}
        self.__valueChangedCallbackRef = None
        self.__timeoutCallbackRef = None

        if args is None:
            self.arglist = ()
        else:
            # not very nice...
            args = str(args)
            if not args.endswith(","):
                args += ","
            self.arglist = eval("(" + args + ")")

        self.connectDevice()

    def connectDevice(self):
        try:
            self.device = TacoDevice.TacoDevice(self.deviceName, dc=self.dataCollector)
        except Exception:
            logging.getLogger("HWR").exception(
                "Problem with Taco ; could not open Device %s", self.deviceName
            )
            self.device = None

    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))

        if len(args) > 0 and len(self.arglist) > 0:
            logging.getLogger("HWR").error(
                "%s: cannot execute command with arguments when 'args' is defined from XML",
                str(self.name()),
            )
            self.emit("commandFailed", (-1, str(self.name())))
            return
        elif len(args) == 0 and len(self.arglist) > 0:
            args = self.arglist

        if self.device is not None and self.device.imported:
            try:
                ret = eval("self.device.%s(*%s)" % (self.command, args))
            except Exception:
                logging.getLogger("HWR").error(
                    "%s: an error occured when calling Taco command %s",
                    str(self.name()),
                    self.command,
                )
            else:
                self.emit("commandReplyArrived", (ret, str(self.name())))
                return ret

        self.emit("commandFailed", (-1, str(self.name())))

    def _valueChanged(self, value):
        self.valueChanged(self.deviceName, value)

    def valueChanged(self, deviceName, value):
        try:
            callback = self.__valueChangedCallbackRef()
        except Exception:
            pass
        else:
            if callback is not None:
                callback(deviceName, value)

    def onPollingError(self, exception, poller_id):
        self.connectDevice()
        poller = Poller.get_poller(poller_id)
        if poller is not None:
            try:
                poller.restart(1000)
            except Exception:
                pass

    def poll(
        self,
        pollingTime=500,
        argumentsList=(),
        valueChangedCallback=None,
        timeoutCallback=None,
        direct=True,
        compare=True,
    ):
        self.__valueChangedCallbackRef = saferef.safe_ref(valueChangedCallback)

        poll_cmd = getattr(self.device, self.command)

        Poller.poll(
            poll_cmd,
            copy.deepcopy(argumentsList),
            pollingTime,
            self._valueChanged,
            self.onPollingError,
            compare,
        )

    def stopPolling(self):
        pass

    def abort(self):
        pass

    def isConnected(self):
        return self.device is not None and self.device.imported


class TacoChannel(ChannelObject):
    """Emulation of a 'Taco channel' = a Taco command + polling"""

    def __init__(
        self,
        name,
        command,
        taconame=None,
        username=None,
        polling=None,
        args=None,
        **kwargs
    ):
        ChannelObject.__init__(self, name, username, **kwargs)

        self.command = TacoCommand(
            name + "_internalCmd", command, taconame, username, args, False, **kwargs
        )

        try:
            self.polling = int(polling)
        except Exception:
            self.polling = None
        else:
            self.command.poll(self.polling, self.command.arglist, self.valueChanged)

    def valueChanged(self, deviceName, value):
        self.emit("update", value)

    def getValue(self):
        return self.command()

    def isConnected(self):
        return self.command.isConnected()
