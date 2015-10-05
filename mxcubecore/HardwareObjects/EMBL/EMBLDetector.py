"""
[Name] : EMBLDetector(Equipment)

[Description] : Describes generic detector 

[Channels] :
self.chan_temperature : temperature in C (float)
self.chan_humidity : humidity in % (float)
self.chan_status : status (string)
self.chan_collect_mode : collection mode "0", "C18", "C2" (string)
self.chan_frame_rate : frame rate (float)

[Commands] :

[Emited signals] :

[Properties] : 
self.default_distance
self.collect_name
self.shutter_name
self.temp_treshold
self.hum_treshold

[Hardware Objects]      
-------------------------------------------------------------------------------
| name                       | signals             | functions
|------------------------------------------------------------------------------
| self.distance_motor_hwobj  |                     | getPosition()
-------------------------------------------------------------------------------
"""

import logging 
from AbstractDetector import AbstractDetector
from HardwareRepository.BaseHardwareObjects import HardwareObject


class EMBLDetector(AbstractDetector, HardwareObject):
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

        self.temperature = 0
        self.humidity = 0
        self.tolerance = 0.1
        self.collect_mode = 0
        self.collect_name = None
        self.shutter_name = None
        self.temp_treshold = None
        self.hum_treshold = None   
        self.exp_time_limits = None

        self.chan_temperature = None
        self.chan_humidity = None
        self.chan_status = None
        self.chan_collect_mode = None
        self.chan_frame_rate = None

    def init(self):
        """
        Descript. :
        """
        self.distance_motor_hwobj = self.getObjectByRole("distance_motor")

        self.chan_temperature = self.getChannelObject('chanTemperature')
        if self.chan_temperature is not None: 
            self.chan_temperature.connectSignal('update', \
                 self.temperature_changed)
        else:
            logging.getLogger().error("Detector: Temperature channel not defined")
        
        self.chan_humidity = self.getChannelObject('chanHumidity')
        if self.chan_humidity is not None:
            self.chan_humidity.connectSignal('update', self.humidity_changed)
        else:
            logging.getLogger().error("Detector: Humidity channel not defined")
        
        self.chan_status = self.getChannelObject('chanStatus')
        if self.chan_status is not None:
            self.chan_status.connectSignal('update', self.status_changed)
        else:
            logging.getLogger().error("Detector: Status channel not defined")
    
        self.chan_collect_mode = self.getChannelObject('chanCollectMode')
        if self.chan_collect_mode is not None:
            self.chan_collect_mode.connectSignal('update', \
                 self.collect_mode_changed)
        else:
            logging.getLogger().error("Detector: Collect mode channel not defined")

        self.chan_frame_rate = self.getChannelObject('chanFrameRate')
        if self.chan_frame_rate is not None:
            self.chan_frame_rate.connectSignal('update', \
                 self.frame_rate_changed)
        else:
            logging.getLogger().error("Detector: Frame rate channel not defined")

        self.chan_beam_xy = self.getChannelObject('chanBeamXY')

        self.collect_name = self.getProperty("collectName")
        self.shutter_name = self.getProperty("shutterName")
        self.tolerance = self.getProperty("tolerance")
        self.temp_treshold = self.getProperty("tempThreshold") 
        self.hum_treshold = self.getProperty("humidityThreshold")
 
        self.pixel_min = self.getProperty("px_min")
        self.pixel_max = self.getProperty("px_max")
        
        self.collect_mode_dict = eval(self.getProperty("collectModes"))

    def get_distance(self):
        """
        Descript. : 
        """
        if self.distance_motor_hwobj is not None:
            return self.distance_motor_hwobj.getPosition()
        else:
            return self.default_distance

    def get_distance_limits(self):
        """
        Descript. : 
        """
        if self.distance_motor_hwobj is not None:
            return self.distance_motor_hwobj.getLimits()
        else:
            return self.default_distance_limits

    def has_shutterless(self):
        """
        Descript. :
        """
        return self.getProperty("hasShutterless")

    def get_collect_name(self):
        """
        Descript. :
        """
        return self.collect_name

    def get_shutter_name(self):
        """
        Desccript. :
        """
        return self.shutter_name
        
    def temperature_changed(self, value):
        """
        Descript. :
        """
        if abs(self.temperature - value) > self.tolerance:
            self.temperature = value
            self.emit('temperatureChanged', (value, value < self.temp_treshold))
            self.status_changed('dummy')

    def humidity_changed(self, value):
        """
        Descript. :
        """
        if abs(self.humidity - value) > self.tolerance:
            self.humidity = value
            self.emit('humidityChanged', (value,  value < self.hum_treshold))
            self.status_changed('dummy')
	
    def status_changed(self, status):
        """
        Descript. :
        """
        status = "uninitialized"
        if self.chan_status is not None:
            status = self.chan_status.getValue()
        status_message = ""
        if self.temperature > self.temp_treshold:
            logging.getLogger().warning("Detector: Temperature %0.2f is greater than allowed %0.2f" % \
                    (self.temperature, self.temp_treshold))
            status_message = "Detector temperature has exceeded threshold.\n"
        if self.humidity > self.hum_treshold:
            logging.getLogger().warning("Detector: Humidity %0.2f is greater than allowed %0.2f" % \
                     (self.humidity, self.hum_treshold))
            status_message = status_message + "Detector humidity has exceeded threshold.\n"
        if status == "calibrating":
            status_message = status_message + "Energy change in progress.\n"
            status_message = status_message + "Please wait...\n"
        elif status != "ready":
            status_message = status_message + "Detector is not ready.\n"
            status_message = status_message + "Cannot start a collection at the moment."
        self.emit('statusChanged', (status, status_message, ))

    def collect_mode_changed(self, mode):
        """
        Descript. :
        """
        self.collect_mode = self.collect_mode_dict[mode]          
        self.emit('detectorModeChanged', (self.collect_mode, ))

    def frame_rate_changed(self, frame_rate):
        """
        Descript. :
        """
        if frame_rate is not None:
            self.exp_time_limits = (1 / float(frame_rate), 6000)
        self.emit('expTimeLimitsChanged', (self.exp_time_limits, )) 

    def set_collect_mode(self, mode):
        """
        Descript. :
        """
        mode = self.collect_mode_dict.keys()[self.collect_mode_dict.values().index(mode)]
        self.chan_collect_mode.setValue(mode)  

    def get_collect_mode(self):
        """
        Descript. :
        """
        return self.collect_mode

    def get_collect_mode_list(self):
        """
        Descript. :
        """
        return self.collect_mode_dict.keys()	

    def get_exposure_time_limits(self):
        """
        Descript. :
        """
        return self.exp_time_limits

    def get_beam_centre(self):
        """
        Descrip. :
        """
        beam_x = 0
        beam_y = 0
        if self.chan_beam_xy is not None:
            value = self.chan_beam_xy.getValue()
            beam_x = value[0]
            beam_y = value[1]
        return beam_x, beam_y

    def update_values(self):
        """
        Descript. :
        """
        self.emit('detectorModeChanged', (self.collect_mode, )) 
        temp = self.chan_temperature.getValue()
        self.emit('temperatureChanged', (temp, temp < self.temp_treshold))
        hum = self.chan_humidity.getValue()
        self.emit('humidityChanged', (hum,  hum < self.hum_treshold))
        self.status_changed("") 
