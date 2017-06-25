"""
 Abstract base classes for beamline components
"""

import abc

class AbstractShutter(object, metaclass=abc.ABCMeta):
    """
    Abstract base class for Shutter objects. The shutter has eight states 
    which are defined as::

     0 -- 'unknown',
     3 -- 'closed',
     4 -- 'opened',
     9 -- 'moving',
     17 -- 'automatic',
     23 -- 'fault',
     46 -- 'disabled',
     -1 -- 'error'

    """

    
    @abc.abstractmethod
    def __init__(self, name):
        """
        :parame name: The name of the hardware object.
        :type name: str
        """
        return


    @abc.abstractmethod
    def value_changed(self, device_name, value):
        """
        Signals "listening" objects that the value of the device has changed.

        :param device_name: The name of the device that the value coresponds to
        :type device_name: str

        :param value: The new value
        :type value: object
        """
        return


    @abc.abstractmethod
    def get_state(self):
        """
 
        :returns: The current state, one of the following strings:

        'unknown',
        'closed',
        'opened',
        'moving',
        'automatic',
        'fault',
        'disabled',
        'error'

        :rtype: str

        """
        return

 
    @abc.abstractmethod
    def is_ok(self):
        """ Checks if the shutter is in one of its predefined states """
        return


    @abc.abstractmethod
    def open(self):
        return

    
    @abc.abstractmethod
    def close(self):
        return


class AbstractAttenuators(object, metaclass=abc.ABCMeta):
    """
    Abstract Attenuators class.
    """

    
    @abc.abstractmethod
    def __init__(self, name):
        return


    @abc.abstractmethod
    def get_state(self):
        """
        :returns: The current state.
        :rtype: int
        """
        return


    @abc.abstractmethod
    def get_factor(self):
        """
        :returns: The attenuation factor
        :rtype: object
        """
        return


    @abc.abstractmethod
    def connect(self):
        return


    @abc.abstractmethod
    def disconnect(self):
       return


    @abc.abstractmethod
    def state_changed(self, value):
        """
        :param value: The new state
        :type value: int
        """
        return


    @abc.abstractmethod
    def factor_changed(self, value):
        """
        :param value: The new factor
        :type value: float
        """
        return


class AbstractFrontend(object, metaclass=abc.ABCMeta):
    """
    Abstract base class for Frontend (shutter) Objects. 
    The shutter has eight states which are defined as::

     0 -- 'unknown',
     3 -- 'closed',
     4 -- 'opened',
     9 -- 'moving',
     17 -- 'automatic',
     23 -- 'fault',
     46 -- 'disabled',
     -1 -- 'error'

    """


    @abc.abstractmethod
    def __init__(self, name):
        return


    @abc.abstractmethod
    def get_name(self):
        """
        :returns: The device name.
        :rtype: str
        """
        return


    @abc.abstractmethod
    def value_changed(self, device_name, value):
        """
        Signals "listening" objects that the value of the device has changed.
        Emits the signal 'shutterStateChanged'.

        :param device_name: The name of the device that the value coresponds to
        :type device_name: str

        :param value: The new value
        :type value: object
        """
        return


    @abc.abstractmethod
    def get_state(self):
        """
        :returns: The current state.

        'unknown',
        'closed',
        'opened',
        'moving',
        'automatic',
        'fault',
        'disabled',
        'error'
        
        :rtype: str
        """
        return


    @abc.abstractmethod
    def get_automatic_method_time_left(self):
        """
        :return: Automatic mode time left
        :rtype: object
        """
        return


    @abc.abstractmethod
    def open(self):
        return


    @abc.abstractmethod
    def close(self):
        return


class AbstractHutchTrigger(object, metaclass=abc.ABCMeta):
    """
    Abstract base class for hutch triggers.
    """


    @abc.abstractmethod
    def __init__(self, name):
        return


    @abc.abstractmethod
    def is_connected(self):
        """
        :returns: Connection status
        :rtype: boolean
        """
        return


    @abc.abstractmethod
    def connect(self):
        """
        Connects the device.
        Emits the signal 'connect'
        """
        return


    @abc.abstractmethod
    def disconnect(self):
        """
        Disconnects the device.
        Emits the signal 'disconnnected'
        """
        return


    @abc.abstractmethod
    def started(self):
        """
        Emits the signal 'macroStarted'
        """
        return


    @abc.abstractmethod
    def done(self):
        """
        Emits the signal 'macroDone'
        """
        return


    @abc.abstractmethod
    def failed(self):
        """
        Emits the signal 'macroFailed'
        """
        return


    @abc.abstractmethod
    def abort(self):
        return


    @abc.abstractmethod
    def msg_changed(self, msg):
        """
        Emits the signal 'msgChanged' with the argument msg

        :param msg: The new message.
        :type msg: str
        """
        return


    @abc.abstractmethod
    def status_changed(self, status):
        """
        Emits the signal 'statusChanged' with the argument status

        :param status: The new status
        :type status: object
        """
        return


    @abc.abstractmethod
    def value_changed(self, device_name, value):
        return


class AbstractInOut(object, metaclass=abc.ABCMeta):
    """
    Abstract base class for InOut objects. Can be any ojects that have the two
    states 'in' and 'out'.
    """


    @abc.abstractmethod
    def __init__(self, name):
        return

    @abc.abstractmethod
    def connect_notify(self, signal):
        return

    @abc.abstractmethod
    def value_changed(self, value):
        return

    @abc.abstractmethod
    def get_state(self):
        return

    @abc.abstractmethod
    def in_(self):
        return

    @abc.abstractmethod
    def out(self):
        return

    

"""
 Abstract base classes for instruments
"""

class AbstractAdscTemperature(object, metaclass=abc.ABCMeta):
    """
    """


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


class AbstractCamera(object, metaclass=abc.ABCMeta):
    """
    """

    
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


class AbstractCryo(object, metaclass=abc.ABCMeta):
    """
    """


    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        return
    

    @abc.abstractmethod
    def value_changed(self, device_name, values):
        return


    @abc.abstractmethod
    def set_n2_level(self, new_level):
        return
    

class AbstractCyberStar(object, metaclass=abc.ABCMeta):
    """
    """

    
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


class AbstractLakeshore(object, metaclass=abc.ABCMeta):
    """
    """

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


class AbstractXCamera(object, metaclass=abc.ABCMeta):
    """
    """


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
