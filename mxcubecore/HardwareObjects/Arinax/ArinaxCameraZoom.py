import gevent
import math
from enum import Enum
# import ast
import logging
# import PyTango
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState
from mxcubecore.HardwareObjects.abstract.AbstractNState import BaseValueEnum
from mxcubecore import HardwareRepository as HWR

""" XML Configuration example
<device class="Arinax.ArinaxCameraZoom">
  <username>bzoom</username>
  <tangoname>tango://tango_name</tangoname>
  <channel type="tango" name="zoom_idx">video_zoom_idx</channel>
  <channel type="tango" name="video_scale">video_scale</channel>
  <channel type="tango" name="num_zoom_levels">num_zoom_levels</channel>
  <channel type="tango" name="zoom_state">State</channel>
</device>"""

__credits__ = ["Arinax"]

class ArinaxCameraZoom(AbstractNState):

    def __init__(self, name):
        AbstractNState.__init__(self, name)

    def _init(self):
        AbstractNState.init(self)

        # logging.getLogger("HWR").info("initializing camera object")
        self.tangoname = self.get_property("tangoname")
        # self.device = PyTango.DeviceProxy(self.tangoname)
        self.zoom_idx_chan = self.get_channel_object("zoom_idx")
        self.zoom_idx_chan.connect_signal("update", self.update_value)
        # self.zoom_idx_chan.connectSignal("update", self.update_state)
        self.um_per_pixel = self.get_channel_object("video_scale")
        self.um_per_pixel.connect_signal("update", self.update_value)
        self.zoom_levels = self.get_channel_object("num_zoom_levels")
        limits = (1, self.zoom_levels.get_value())
        self.set_limits(limits)
        self.state = self.get_channel_object("zoom_state")

        self.initialise_values()

        self.update_limits(limits)
        self.update_value(self.get_value())
        self.update_state(self.get_state())


    def get_zoom(self):
        return self.zoom_idx_chan.get_value()

    def get_state(self):
        return self.STATES.READY

    def get_value(self):
        return self.value_to_enum(self.get_zoom())

    def get_pixels_per_mm(self):
        pixels_per_mm = 1000/self.um_per_pixel.get_value()
        return (pixels_per_mm, pixels_per_mm)

    def _set_zoom(self, value):
        self.zoom_idx_chan.set_value(value)

    def _set_value(self, value):
        gevent.spawn(self._set_zoom, value.value)
        self.update_value(value.value)
        self.update_state(self.STATES.READY)
        self.emit("stateChanged", (self.STATES.READY,))
        camera_device = HWR.beamline.diffractometer.get_object_by_role("camera")
        if camera_device is not None:
            camera_device._zoom_changed()


    def set_limits(self, limits):
        self._nominal_limits = limits
        # self.emit("limitsChanged", (self._nominal_limits,))

    def update_limits(self, limits=None):
        """Check if the limits have changed. Emits signal limitsChanged.
        Args:
            limits (tuple): two elements tuple (low limit, high limit).
        """
        if not limits:
            limits = self.get_limits()

        if self._nominal_limits != limits:
            # All values are not NaN
            if not any(isinstance(lim, float) and math.isnan(lim) for lim in limits):
                self._nominal_limits = limits
                self.emit("limitsChanged", (limits,))

    def _initialise_values(self):
        """Initialise the ValueEnum """
        low, high = self.get_limits()

        values = {"LEVEL%s" % str(v): v for v in range(low, high + 1)}
        self.VALUES = Enum(
            "ValueEnum",
            dict(values, **{item.name: item.value for item in BaseValueEnum}),
        )
