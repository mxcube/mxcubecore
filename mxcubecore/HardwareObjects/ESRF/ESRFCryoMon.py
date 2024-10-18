import time

import gevent
from PyTango.gevent import DeviceProxy

from mxcubecore.BaseHardwareObjects import HardwareObject

CRYO_STATUS = ["OFF", "SATURATED", "READY", "WARNING", "FROZEN", "UNKNOWN"]


class ESRFCryoMon(HardwareObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.n2level = None
        self.temp = None
        self.temp_error = None
        self.cryo_status = None
        self.dry_status = None
        self.sdry_status = None

    def init(self):
        self.tg_device = None
        self.set_is_ready(True)
        self._monitoring_greenlet = gevent.spawn(self._monitor)

    def _monitor(self):
        self.tg_device = None
        while True:
            if self.tg_device is None:
                self.tg_device = DeviceProxy(self.get_property("tangoname"))
            try:
                temp = self.tg_device.Gas_temp
            except Exception:
                self.tg_device = None
            else:
                # if n2level != self.n2level:
                #  self.n2level = n2level
                #  self.emit("levelChanged", (n2level, ))
                if temp != self.temp:
                    self.temp = temp
                    self.emit("temperatureChanged", (temp, 0))
                # if cryo_status != self.cryo_status:
                #  self.cryo_status = cryo_status
                #  self.emit("cryoStatusChanged", (CRYO_STATUS[cryo_status], ))
                # if dry_status != self.dry_status:
                #  self.dry_status = dry_status
                #  if dry_status != 9999:
                #      self.emit("dryStatusChanged", (CRYO_STATUS[dry_status], ))
                # if sdry_status != self.sdry_status:
                #  self.sdry_status = sdry_status
                #  if sdry_status != 9999:
                #      self.emit("sdryStatusChanged", (CRYO_STATUS[sdry_status], ))
            time.sleep(3)

    def setN2Level(self, newLevel):
        raise NotImplementedError

    def getTemperature(self):
        return self.tg_device.Gas_temp
