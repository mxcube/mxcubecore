import logging
from AbstractDetector import AbstractDetector
from HardwareRepository.BaseHardwareObjects import HardwareObject

class DetectorMockup(AbstractDetector, HardwareObject): 
    """
    Descript. : Detector class. Contains all information about detector
                the states are 'OK', and 'BAD'
                the status is busy, exposing, ready, etc.
                the physical property is RH for pilatus, P for rayonix
    """
    def __init__(self, name): 
        """
        Descript. :
        """ 
        AbstractDetector.__init__(self)
        HardwareObject.__init__(self, name)
 
        self.distance = None
        self.exposure_time_limits = [0.04, 60000]

    def init(self):
        """
        Descript. :
        """
        self.distance = 500

    def get_distance(self):
        return self.distance

    def get_distance_limits(self):
        return [100, 1000] 

    def has_shutterless(self):
        """Returns always True
        """
        return True

    def get_beam_centre(self):
        return 0, 0

    def get_exposure_time_limits(self):
        return self.exposure_time_limits
