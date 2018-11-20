import abc


class AbstractDetector(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        """
        Descript. : 
        """

        # self.distance = None
        self.temperature = None
        self.humidity = None
        self.exposure_time_limits = [None, None]
        self.actual_frame_rate = None

        self.pixel_min = None
        self.pixel_max = None
        self.default_distance = None
        self.distance_limits = [None, None]
        self.distance_limits_static = [None, None]
        self.binding_mode = None
        self.roi_mode = None
        self.roi_modes_list = []
        self.status = None

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

    def get_roi_mode(self):
        """Returns current ROI mode"""
        return self.roi_mode

    def set_roi_mode(self, roi_mode):
        pass

    def get_roi_mode_name(self):
        return self.roi_modes_list[self.roi_mode]

    def get_roi_modes(self):
        """Returns a list with available ROI modes"""
        return self.roi_modes_list

    def get_exposure_time_limits(self):
        """Returns exposure time limits as list with two floats"""
        return self.exposure_time_limits

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

    def set_distance(self, value, timeout=None):
        """
        Descript. : 
        """
        return

    def get_detector_mode(self):
        return self.binding_mode

    def set_detector_mode(self, value):
        """
        Descript. : 
        """
        self.binding_mode = value

    def prepare_acquisition(
        self,
        take_dark,
        start,
        osc_range,
        exptime,
        npass,
        number_of_images,
        comment,
        energy,
        still,
    ):
        """
        Descript. :
        """
        return

    def last_image_saved(self):
        """
        Descript. :
        """
        return

    def set_detector_filenames(
        self, frame_number, start, filename, jpeg_full_path, jpeg_thumbnail_full_path
    ):
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
