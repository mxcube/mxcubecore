"""
 Abstract base classes for instruments
"""

import abc

class AbstractAdscTemperature(object):
    """
    """

    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def __init__(self, name):
        return


    @abc.abstractmethod
    def value_changed(self, device_name, value):
        """
        Emits 'valueChanged' signal with the argument value.

        :param device_name: Name of the device.
        :type device_name: str
        :param value: The new value.
        :type value: object
        """
        return


class AbstractCamera(object):
    """
    """

    __metaclass__ = abc.ABCMeta

    
    @abc.abstractmethod
    def set_brightness(self, brightness):
        return

    
    @abc.abstractmethod
    def get_brightness(self):
        return

    
    @abc.abstractmethod
    def get_brightness_min_max(self):
        return


    @abc.abstractmethod
    def has_brightness(self):
        return
        

    @abc.abstractmethod
    def has_gamma(self):
        return
    

    @abc.abstractmethod
    def set_gamma(self, gamma):
        return


    @abc.abstractmethod
    def get_gamma(self):
        return

    
    @abc.abstractmethod
    def set_roi(self, start_x, end_x, start_y, end_y):
        return

    
    @abc.abstractmethod
    def get_bpm_state(self):
        return

    
    @abc.abstractmethod
    def set_bpm(self, bpm_on):
        return

    
    @abc.abstractmethod
    def get_bpm_values(self):
        return


    @abc.abstractmethod
    def set_live(self, mode):
        return

    
    @abc.abstractmethod
    def set_exposure(self, exposure):
        return


    @abc.abstractmethod
    def set_size(self, width, height):
        return


    @abc.abstractmethod
    def get_height(self):
        return


    @abc.abstractmethod
    def get_width(self):
        return


    @abc.abstractmethod
    def set_threshold(self, threshold):
        return


    @abc.abstractmethod
    def get_contrast(self):
        return

     
    @abc.abstractmethod
    def set_contrast(self, contrast):
        return


    @abc.abstractmethod
    def get_contrast_min_max(self):
        return


    @abc.abstractmethod
    def has_contrast(self):
        return

    
    @abc.abstractmethod
    def set_gain(self, gain):
        return


    @abc.abstractmethod
    def get_gain(self):
        return

    
    @abc.abstractmethod
    def get_gain_min_max(self):
        return
    

    @abc.abstractmethod
    def has_gain(self):
        return


    @abc.abstractmethod
    def value_changed(self, device_name, value):
        return


    @abc.abstractmethod
    def image_type(self):
        return


    @abc.abstractmethod
    def take_snapshot(self, *args):
        return

    
    @abc.abstractmethod
    def oprint(self, msg):
        return


class AbstractCryo(object):
    """
    """

    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        return
    

    @abc.abstractmethod
    def value_changed(self, device_name, values):
        return


    @abc.abstractmethod
    def set_n2_level(self, new_level):
        return
    

class AbstractCyberStar(object):
    """
    """
    
    __metaclass__ = abc.ABCMeta

    
    @abc.abstractmethod
    def __init__(self, name):
        """
        :param name: The name of the device.
        :type name: str
        """
        return

    
    @abc.abstractmethod
    def value_changed(self, device_name, values):
        """
        Emits a 'valueChanged' signal.

        :param device_name: The device name.
        :type device_name: str
        :param values: The new values
        :type values: object
        """

        return


class AbstractLakeshore(object):
    """
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def set_unit(self, unit):
        """
        Sets the measurement unit either (C)elsius or (K)elvin

        :param unit: The unit 'C' for celsius and 'K' for kelvin
        :type unit: str 

        """
        return


    @abc.abstractmethod
    def get_ident(self):
        """
        Retrieves the device identity.

        :returns: The identity string.
        :rtype: str

        """
        return


    @abc.abstractmethod    
    def get_channels_number(self):
        """
        Gets the number of channels available.

        :returns: Number of channels.
        :rtype: int

        """
        return
    

    @abc.abstractmethod
    def set_interval(self, new_interval):
        """
        Sets the polling intervall, the method read_channels
        is called each 'new_interval' milliseconds.
        

        :param new_interval: Time in milliseconds.
        :type new_interval: int
        """
        return


    @abc.abstractmethod    
    def connect_notify(self):
        return


    @abc.abstractmethod
    def disconnet_notify(self, signal):
        return


    @abc.abstractmethod    
    def putget(self, cmd, timeout):
        return


    @abc.abstractmethod
    def set_status(self, status):
        return


    @abc.abstractmethod
    def read_channels(self):
        return


    @abc.abstractmethod
    def reset(self):
        return


class AbstractXCamera(object):
    """
    """
    
    __metaclass__ = abc.ABCMeta


    @abc.abstractmethod
    def value_changed(self, device_name, value):
        return


    @abc.abstractmethod
    def get_width(self):
        return


    @abc.abstractmethod    
    def get_height(self):
        return


    @abc.abstractmethod
    def set_size(self):
        return


    @abc.abstractmethod
    def statistics_changed(self, stats):
        return


    @abc.abstractmethod
    def statistics_timeout(self, stats):
        return


    @abc.abstractmethod
    def get_image_data(self, read):
        return
