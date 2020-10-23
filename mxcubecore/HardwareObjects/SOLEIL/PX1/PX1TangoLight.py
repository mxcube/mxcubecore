import logging
import time
import gevent

from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.Command.Tango import DeviceProxy


class PX1TangoLight(Device):
    def __init__(self, name):
        Device.__init__(self, name)
        self.currentState = "unknown"

    def init(self):
        # self.tangoname = self.
        self.attrchan = self.get_channel_object("attributeName")
        self.attrchan.connectSignal("update", self.valueChanged)

        self.attrchan.connectSignal("connected", self._setReady)
        self.attrchan.connectSignal("disconnected", self._setReady)
        self.set_in = self.get_command_object("set_in")
        self.set_in.connectSignal("connected", self._setReady)
        self.set_in.connectSignal("disconnected", self._setReady)
        self.set_out = self.get_command_object("set_out")

        self.px1env_hwo = self.getObjectByRole("px1environment")
        self.light_hwo = self.getObjectByRole("intensity")
        self.zoom_hwo = self.getObjectByRole("zoom")

        self.connect(self.zoom_hwo, "predefinedPositionChanged", self.zoom_changed)

        self._setReady()
        try:
            self.inversed = self.getProperty("inversed")
        except Exception:
            self.inversed = False

        if self.inversed:
            self.states = ["in", "out"]
        else:
            self.states = ["out", "in"]

    def _setReady(self):
        self.setIsReady(self.attrchan.isConnected())

    def connectNotify(self, signal):
        if self.is_ready():
            self.valueChanged(self.attrchan.getValue())

    def valueChanged(self, value):
        self.currentState = value

        if value:
            self.currentState = self.states[1]
        else:
            self.currentState = self.states[0]

        self.emit("wagoStateChanged", (self.currentState,))

    def getWagoState(self):
        return self.currentState

    def wagoIn(self):
        self.setIn()

    def wagoOut(self):
        self.setOut()

    def setIn(self):
        if not self.px1env_hwo.isPhaseVisuSample():
            self.px1env_hwo.gotoSampleViewPhase()
            start_phase = time.time()
            while not self.px1env_hwo.isPhaseVisuSample():
                time.sleep(0.1)
                if time.time() - start_phase > 20:
                    break

        self.adjustLightLevel()

    def setOut(self):
        self._setReady()
        if self.is_ready():
            if self.inversed:
                self.set_in()
            else:
                self.light_hwo.set_value(0)
                self.set_out()

    def zoom_changed(self, position_name, value):
        if self.currentState == "in":
            logging.getLogger("HWR").debug(
                "Zoom changed. and light is in. setting light level"
            )
            self.adjustLightLevel()

    def adjustLightLevel(self):
        if self.zoom_hwo is None or self.light_hwo is None:
            return

        props = self.zoom_hwo.getCurrentPositionProperties()

        try:
            if "lightLevel" in props.keys():
                light_level = float(props["lightLevel"])
                light_current = self.light_hwo.get_value()
                if light_current != light_level:
                    logging.getLogger("HWR").debug(
                        "Setting light level to %s" % light_level
                    )
                    self.light_hwo.set_value(light_level)
        except Exception:
            logging.getLogger("HWR").debug("Cannot set light level")
