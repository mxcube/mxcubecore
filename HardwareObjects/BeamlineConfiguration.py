"""
BeamlineConfiguration hardware object.

Contains static information about the beamline, and methods to retreive/handle
that information.
"""

from HardwareRepository.BaseHardwareObjects import HardwareObject
from queue_entry import QueueEntryContainer

__author__ = "Marcus Oskarsson"
__copyright__ = "Copyright 2012, ESRF"
__credits__ = ["My great coleagues", "The MxCuBE colaboration"]

__version__ = "0.1"
__maintainer__ = "Marcus Oskarsson"
__email__ = "marcus.oscarsson@esrf.fr"
__status__ = "Beta"


class BeamlineConfiguration(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)


    def detector_has_shutterless(self):
        """
        :returns: True if the detector is capable of shuterless.
        :rtype: bool
        """
        shutter_less = False
        
        try:
            shutter_less = self["BCM_PARS"]['detector'].\
                           getProperty('has_shutterless')

            if shutter_less is None:
                shutter_less = False

        except:
            shutter_less = False
            
        return shutter_less


    def tunable_wavelength(self):
        """
        :returns: Returns True if the beamline has tunable wavelength.
        :rtype: bool
        """
        tw = False
        
        try:
            tw = self["BCM_PARS"].getProperty('tunable_wavelength')
            
            if tw is None:
                tw = False
                
        except:
            shutter_less = False
        
        return tw
