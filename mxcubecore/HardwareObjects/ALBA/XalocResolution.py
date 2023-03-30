from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.Resolution import Resolution
import logging
import math

from mxcubecore.HardwareObjects.abstract.AbstractMotor import (
    MotorStates,
)

class XalocResolution(Resolution):
    
    unit = "A"
    
    #def __init__(self, *args, **kwargs):
    def __init__(self, name):
        #Resolution.__init__(self, name="XalocResolution")
        super(XalocResolution, self).__init__(name)
        self.logger = logging.getLogger("HWR.XalocResolution")

        #self._chnBeamX = None
        #self._chnBeamY = None
        self.resedge = None

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        #super(XalocResolution, self).init()

        self._hwr_detector = (
            self.get_object_by_role("detector") or HWR.beamline.detector
        )
        self.resedge = self.get_channel_object("resedge_value")

        self.connect(self.resedge, "valueChanged", self.set_value)
        if HWR.beamline.energy is not None:
            HWR.beamline.energy.connect("energyChanged", self.update_energy)
        self.connect(self._hwr_detector.distance, "stateChanged", self.update_state)
        self.connect(self._hwr_detector.distance, "valueChanged", self.update_distance)

        
    def is_ready(self):
        return self._hwr_detector.distance.get_state() == MotorStates.READY

        
    #def get_beam_centre(self, dtox=None):
        #return self._chnBeamX.get_value(), self._chnBeamY.get_value()

    #def get_value_at_corner(self):
        #if self.rescorner is not None:
            #return self.rescorner.get_value()

    def get_limits(self):
        """Return resolution low and high limits.
        Returns:
            (tuple): two floats tuple (low limit, high limit).
        """
        _low, _high = self._hwr_detector.distance.get_limits()

        self._limits = (
            self.distance_to_resolution(_low),
            self.distance_to_resolution(_high),
        )
        return self._limits

    def update_energy(self, energy_pos, wavelength_pos):
        """Update the resolution when energy changed.
        Args:
            value(float): Energy [keV]
        """
        logging.getLogger("HWR").debug(
            "Energy changed, updating resolution and limits"
        )

        self._nominal_value = self.resedge.force_get_value()
        self.value = self._nominal_value
        self.get_limits()
        self.emit("valueChanged", (self._nominal_value,))

    def update_state(self, state):
        pass 
        
    def update_distance(self, value=None):
        """Update the resolution when distance changed.
        Args:
            value (float): Detector distance [mm].
        """
        self._nominal_value = self.resedge.force_get_value()
        self.emit("valueChanged", (self._nominal_value,))

    def get_value(self):
        """Read the value.
        Returns:
            (float): value.
        """
        self._nominal_value = self.resedge.force_get_value()

        return self._nominal_value

    def set_value(self, value, timeout = None):
        distance = self.resolution_to_distance(value)
        msg = "Move resolution to {} ({} mm)".format(value, distance)
        logging.getLogger().info(msg)
        self._hwr_detector.distance.set_value(distance)
