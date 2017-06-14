"""
Detector hwobj maintains information about detector.
"""
from HardwareRepository.BaseHardwareObjects import Equipment
import logging 

class DetectorMockup(Equipment):    
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
        Equipment.__init__(self, name)

        self.temperature = 23
        self.humidity = 50
        self.tolerance = 0.1
        self.detector_mode = 0
        self.detector_modes_dict = None
        self.detector_collect_name = None
        self.detector_shutter_name = None
        self.temp_treshold = None
        self.hum_treshold = None   
        self.exp_time_limits = None

        self.distance_motor_hwobj = None

        self.chan_temperature = None
        self.chan_humidity = None
        self.chan_status = None
        self.chan_detector_mode = None
        self.chan_frame_rate = None

    def init(self):
        """
        Descript. :
        """
        self.detector_collect_name = self.getProperty("collectName")
        self.detector_shutter_name = self.getProperty("shutterName")
        self.tolerance = self.getProperty("tolerance")
        self.temp_treshold = self.getProperty("tempThreshold") 
        self.hum_treshold = self.getProperty("humidityThreshold")

        try:
           self.detector_modes_dict = eval(self.getProperty("detectorModes"))
        except:
           pass

    def get_collect_name(self):
        """
        Descript. :
        """
        return self.detector_collect_name

    def get_shutter_name(self):
        """
        Desccript. :
        """
        return self.detector_shutter_name
        
    def get_distance(self):
        """
        Descript. : 
        """
        if self.distance_motor_hwobj:
            return self.distance_motor_hwobj.getPosition()

    def set_detector_mode(self, mode):
        """
        Descript. :
        """
        return

    def get_detector_mode(self):
        """
        Descript. :
        """
        return self.detector_mode

    def default_mode(self):
        return 1

    def get_detector_modes_list(self):
        """
        Descript. :
        """
        if self.detector_modes_dict is not None:
            return self.detector_modes_dict.keys()	
        else:
            return [] 

    def has_shutterless(self):
        """
        Description. :
        """
        return self.getProperty("hasShutterless")

    def get_exposure_time_limits(self):
        """
        Description. :
        """
        return self.exp_time_limits
