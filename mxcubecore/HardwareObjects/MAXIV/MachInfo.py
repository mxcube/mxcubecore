import re
import math
import logging
import gevent
from tango import DeviceProxy
from mxcubecore.utils.units import sec_to_hour, A_to_mA
from mxcubecore.HardwareObjects.abstract.AbstractMachineInfo import AbstractMachineInfo

# how often we refresh machine info
REFRESH_PERIOD_SEC = 30
CLEANR = re.compile("<.*?>")


log = logging.getLogger("HWR")


def cleanhtml(raw_html):
    cleantext = re.sub(CLEANR, "", raw_html)
    return cleantext


def catch_errors(func):
    """
    run wrapped function, catching all exception

    If an exception as raised, log the exception and return 'unknown'
    """

    def wrapper(*a, **kw):
        try:
            return func(*a, **kw)
        except Exception:
            log.exception("error fetching machine info")
            return "unknown"

    return wrapper


class MachInfo(AbstractMachineInfo):
    """
    Machine info hardware object for MAXIV site.

    Provides to the user general information about the machine,
    such as ring status, current, operator message, etc.

    This hardware objects fetches the information from attributes
    of specified tango devices.

    Hardware object properties:
        mach_info (str): name of the machine status tango device
        current (str): name of the ring status tango device
        parameters (str): topics to export, see AbstractMachineInfo class for details
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.mach_info = None
        self.mach_curr = None

    def init(self):
        super().init()

        self.mach_info = self._get_tango_device("mach_info")
        self.mach_curr = self._get_tango_device("current")
        gevent.spawn(self._refresh_ticker)

    def _get_tango_device(self, property_name: str) -> DeviceProxy:
        dev_name = self.get_property(property_name)
        try:
            return DeviceProxy(dev_name)
        except Exception:
            log.exception(f"error connecting to machine info tango device {dev_name}")

    def _refresh_ticker(self):
        while True:
            self.update_value()
            gevent.sleep(REFRESH_PERIOD_SEC)

    @catch_errors
    def get_current(self) -> str:
        current = A_to_mA(self.mach_curr.Current)
        return f"{current:.2f} mA"

    @catch_errors
    def get_fillmode(self) -> str:
        return self.mach_info.R3Mode

    @catch_errors
    def get_message(self) -> str:
        return self.mach_info.OperatorMessage

    @catch_errors
    def get_lifetime(self) -> str:
        lifetime = self.mach_curr.Lifetime
        if math.isnan(lifetime):
            return "n/a"

        return f"{sec_to_hour(lifetime):.2f} h"

    @catch_errors
    def get_injection(self) -> str:
        return self.mach_info.R3NextInjection

    @catch_errors
    def get_status(self) -> str:
        message = cleanhtml(self.mach_info.MachineMessage)
        message = message.replace("R1", " R1").replace("Linac", " Linac")

        return message
