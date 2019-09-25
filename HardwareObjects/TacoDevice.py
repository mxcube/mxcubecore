import logging

from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.BaseHardwareObjects import Null
from HardwareRepository import TacoDevice_MTSafe
import collections


class TacoDevice(Device):
    def __init__(self, name, dc=False):
        Device.__init__(self, name)

        self.__dc = dc

    def tacoName(self):
        return self.getProperty("taconame")

    def _init(self):
        self.device = None
        self.__nb_connections = 0
        self.__polling_args = ()
        self.__polling_kwargs = {"direct": True}

        self.device = TacoDevice_MTSafe.TacoDevice(self.tacoName(), dc=self.__dc)

        if self.device is None:
            logging.getLogger("HWR").error(
                "%s: could not import Taco Device %s", str(self.name()), self.tacoName()
            )

            self.device = Null()

        if self.device.imported == 1:
            if not self.__dc:
                self.device.tcp()

    def setPollCommand(self, command, *args, **kwargs):
        cmdDict = {"type": "taco", "name": "pollCmd", "taconame": self.tacoName()}
        if self.__dc:
            cmdDict["dc"] = True
        cmdObject = self.add_command(cmdDict, command)
        self.__polling_args = args
        self.__polling_kwargs.update(kwargs)

    def connectNotify(self, signal):
        self.__nb_connections += 1

        if self.__nb_connections == 1:
            # start polling only if needed
            try:
                cmdObject = self.getCommandObject("pollCmd")
            except BaseException:
                logging.getLogger("HWR").error(
                    "%s: cannot start polling, command not set.", self.name()
                )
            else:
                cmdObject.poll(
                    self.interval,
                    self.__polling_args,
                    self.valueChanged,
                    **self.__polling_kwargs
                )

    def disconnectNotify(self, signal):
        if self.__nb_connections <= 0:
            return

        self.__nb_connections -= 1

        if self.__nb_connections == 0:
            try:
                cmdObject = self.getCommandObject("pollCmd")
            except BaseException:
                return
            else:
                cmdObject.stopPolling()

    def valueChanged(self, deviceName, value):
        self.emit("valueChanged", (value,))

    def executeCommand(self, command, *args):
        if self.device is not None:
            result = None

            if command.endswith("()"):
                command = command[:-2]

            try:
                func = getattr(self.device, command)

                if isinstance(func, collections.Callable):
                    result = func(*args)
            except BaseException:
                logging.getLogger().exception(
                    "Failed to execute command %s on device %s",
                    command,
                    self.userName(),
                )

            return result
