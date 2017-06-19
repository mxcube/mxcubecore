import abc 


class AbstractDetector(object):    
    __metaclass__ = abc.ABCMeta

    def __init__(self): 
        """
        Descript. : 
        """ 
        self.pixel_min = None
        self.pixel_max = None
        self.default_distance = None
        self.distance_limits = [None, None]
        self.distance_limits_static = [None, None]
        self.binding_mode = None
        self.roi_mode = None
 
        self.roi_modes_list = []

        self.distance_motor_hwobj = None

        

    @abc.abstractmethod
    def get_distance(self):
        """
        Descript. : 
        """
        return

    @abc.abstractmethod
    def get_distance_limits(self):
        """
        Descript. : 
        """
        return 

    @abc.abstractmethod
    def has_shutterless(self):
        """
        Descript. : 
        """
        return

    def get_roi_modes(self):
        """
        Descript. : 
        """
        return self.roi_modes_list

    def get_pixel_min(self):
        """
        Descript. : Returns minimal pixel size
        """
        return self.pixel_min

    def get_pixel_max(self):
        """
        Descript. : Returns maximal pixel size
        """
        return self.pixel_max

    def set_distance(self, value):
        """
        Descript. : 
        """
        return

    def set_detector_mode(self, value):
        """
        Descript. : 
        """
        return

    def prepare_acquisition(self, take_dark, start, osc_range, exptime, npass, number_of_images, comment, energy, still):
        """
        Descript. :
        """
        return

    def last_image_saved(self):
        """
        Descript. :
        """
        return

    def set_detector_filenames(self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path):
        """
        Descript. :
        """
        return

    def start_acquisition(self):
        """
        Descript. :
        """
        return

    def stop_acquisition(self):
        """
        Descript. :
        """
        return

    def write_image(self):
        """
        Descript. :
        """
        return

    def stop(self):
        """
        Descript. :
        """
        return

    def reset_detector(self):
        """
        Descript. :
        """
        return

    def wait_detector(self, until_state):
        """
        Descript. :
        """
        return

    def wait_ready(self):
        """
        Descript. :
        """
        return
