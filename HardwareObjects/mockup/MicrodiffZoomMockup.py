import ast
import gevent

from HardwareRepository.HardwareObjects.abstract.AbstractNState import AbstractNState
from HardwareRepository.BaseHardwareObjects import Device, HardwareObjectState

class MicrodiffZoomMockup(AbstractNState):
    """MicrodiffZoomMockup class"""
    def __init__(self, name):
        AbstractNState.__init__(self, name)

    def init(self):
        """Initialize the zoom"""
        AbstractNState.init(self)

        try:
            values = ast.literal_eval(self.getProperty("values")).values()
        except AttributeError:
            limits = (0, 10)
        else:
            limits = (min(values), max(values))

        self.update_limits(limits)
        #self.update_value([**self.VALUES.__members__.values()][0])
        self.update_state(self.STATES.READY)

    def _set_zoom(self, value):
        """
        Simulated motor movement
        """
        self.update_state(self.STATES.BUSY)
        gevent.sleep(0.2)
        self.update_value(value)
        self.update_state(self.STATES.READY)

    def update_limits(self, limits=None):
        """Overrriden from AbstractNState"""
        if limits is None:
            limits = self.get_limits()

        self._nominal_limits = limits
        self.emit("limitsChanged", (limits,))

    def _set_value(self, value):
        "Overrriden from AbstractActuator"
        gevent.spawn(self._set_zoom, value)

    def get_value(self):
        "Overrriden from AbstractActuator"
        return self._nominal_value
