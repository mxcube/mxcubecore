from mxcubecore.HardwareObjects.Resolution import Resolution
import logging
import math

class XalocResolution(Resolution):
    #def __init__(self, *args, **kwargs):
    def __init__(self, name):
        #Resolution.__init__(self, name="XalocResolution")
        super(XalocResolution, self).__init__(name)
        self.logger = logging.getLogger("HWR.XalocResolution")

        self._chnBeamX = None
        self._chnBeamY = None
        self.resedge = None

    def init(self):
        self.logger.debug("Initializing {0}".format(self.__class__.__name__))
        super(XalocResolution, self).init()
        self._chnBeamX = self.detector.get_channel_object('beamx')
        self._chnBeamY = self.detector.get_channel_object('beamy')
        self.rescorner = self.get_channel_object("rescorner_value")
        self.logger("self._hwr_detector %s, type is %s" % ( self._hwr_detector, type(self._hwr_detector) ) )
        
    #def get_beam_centre(self, dtox=None):
        #return self._chnBeamX.get_value(), self._chnBeamY.get_value()

    #def get_value_at_corner(self):
        #if self.rescorner is not None:
            #return self.rescorner.get_value()

    def set_value(self, value, timeout=None):
        """Set the resolution.
        Args:
            value(float): target value [Å]
            timeout(float): optional - timeout [s],
                             if timeout is None: wait forever (default).
        """
        # The precision depoends on the difference between the current
        # resolution and the target value - the smaller the difference,
        # the better the precision.
        # We move twice to get the closet possible to the requested resolution.
        super().set_value(value, timeout)
