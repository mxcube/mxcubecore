import logging
import time

import epics

from mxcubecore.HardwareObjects.abstract.AbstractDetector import AbstractDetector


class LNLSPilatusDet(AbstractDetector):

    DET_THRESHOLD = 'det_threshols_energy'
    # DET_STATUS = 'det_status_message'
    DET_WAVELENGTH = 'det_wavelength'
    DET_DETDIST = 'det_detdist'
    DET_BEAM_X = 'det_beam_x'
    DET_BEAM_Y = 'det_beam_y'
    USER_BEAM_X = 'user_beam_x'
    USER_BEAM_Y = 'user_beam_y'
    DET_TRANSMISSION = 'det_transmission'
    DET_START_ANGLE = 'det_start_angle'
    DET_ANGLE_INCR = 'det_angle_incr'

    def __init__(self, name):
        """
        Descript. :
        """
        AbstractDetector.__init__(self, name)

    def init(self):
        """
        Descript. :
        """
        AbstractDetector.init(self)

        # self.distance = 500
        self._temperature = 25
        self._humidity = 60
        self.actual_frame_rate = 50
        self._roi_modes_list = ("0", "C2", "C16")
        self._roi_mode = 0
        self._exposure_time_limits = [0.04, 60000]
        self.status = "ready"
        self.pv_status = epics.PV(self.getProperty("channel_status"))
        self.threshold = -1  # Starts with invalid value. To be set.
        self.wavelength = -1
        self.det_distance = -1
        self.beam_x = -1
        self.beam_y = -1
        self.default_beam_x = float(self.getProperty("default_beam_x"))
        self.default_beam_y = float(self.getProperty("default_beam_y"))

        self._distance_motor_hwobj = self.get_object_by_role("detector_distance")
        self.threshold = self.get_threshold_energy()

    def set_roi_mode(self, roi_mode):
        self._roi_mode = roi_mode
        self.emit("detectorModeChanged", (self._roi_mode,))

    def has_shutterless(self):
        """Returns always True
        """
        return True

    def get_beam_position(self, distance=None, wavelength=None):
        """Get approx detector centre """
        xval, yval = super(LNLSPilatusDet, self).get_beam_position(distance=distance)
        if None in (xval, yval):
            # default to Pilatus values
            xval = self.getProperty("width", 2463) / 2.0 + 0.4
            yval = self.getProperty("height", 2527) / 2.0 + 0.4
        return xval, yval

    def update_values(self):
        self.emit("detectorModeChanged", (self._roi_mode,))
        self.emit("temperatureChanged", (self._temperature, True))
        self.emit("humidityChanged", (self._humidity, True))
        self.emit("expTimeLimitsChanged", (self._exposure_time_limits,))
        self.emit("frameRateChanged", self.actual_frame_rate)
        self.emit("statusChanged", (self.status, "Ready"))

    def prepare_acquisition(self, *args, **kwargs):
        """
        Prepares detector for acquisition
        """
        return

    def last_image_saved(self):
        """
        Returns:
            str: path to last image
        """
        return

    def start_acquisition(self):
        """
        Starts acquisition
        """
        return

    def stop_acquisition(self):
        """
        Stops acquisition
        """
        return

    def get_threshold_energy(self):
        """
        Returns:
            float: threshold energy
        """
        value = float(self.get_channel_value(self.DET_THRESHOLD))
        return value

    def set_threshold_energy(self, energy):
        """
        Set threshold energy and returns whether it was successful or not.
        """
        try:
            float(energy)
        except Exception as e:
            logging.getLogger("HWR").error(
                    "Error while setting Pilatus threshold. Value must be float."
            )
            return False

        target_threshold = energy / 2
        if abs(self.get_threshold_energy() - target_threshold) < 0.0001:
            return True

        logging.getLogger("HWR").info("Setting Pilatus threshold...")
        for i in range(3):
            logging.getLogger("user_level_log").info(
                "Setting Pilatus threshold..."
            )

        self.set_channel_value(self.DET_THRESHOLD, target_threshold)

        # wait for threshold setting to be done
        time.sleep(2)
        # Using epics because we need 'as_string' option
        status = self.pv_status.get(as_string=True)
        logging.getLogger("HWR").info('Pilatus status: %s' % status)

        while status == "Setting threshold":
            logging.getLogger("HWR").info(
                'Pilatus status: %s (this may take a minute)...' % status
            )
            time.sleep(3)
            status = self.pv_status.get(as_string=True)

        self.threshold = self.get_threshold_energy()
        logging.getLogger("HWR").info(
            'Pilatus: current threshold is %s (target is %s)' %
            (self.threshold, target_threshold)
        )
        if (status == "Camserver returned OK"
        and self.threshold == target_threshold):
            logging.getLogger("HWR").info('Pilatus status: %s' % status)
            logging.getLogger("HWR").info(
                "Pilatus threshold successfully set."
            )
            return True

        logging.getLogger("HWR").error('Pilatus status: %s' % status)
        logging.getLogger("HWR").error(
            "Error while setting Pilatus threshold. Please, check the detector."
        )
        return False

    def get_wavelength(self):
        """
        Returns:
            float: wavelength
        """
        value = float(self.get_channel_value(self.DET_WAVELENGTH))
        return value

    def set_wavelength(self, wavelength):
        """
        Set wavelength and returns whether it was successful or not.
        """
        try:
            float(wavelength)
        except Exception as e:
            logging.getLogger("HWR").error(
                    "Error while setting Pilatus wavelength. Value must be float."
            )
            return False

        #if abs(self.wavelength - wavelength) < 0.0001:
        #    logging.getLogger("HWR").info(
        #        "Pilatus wavelength still okay."
        #    )
        #    return True
        
        # As the set of Pilatus wavelength, det dist and beam xy is fast,
        # there is no need to compare the target value with the current one.
        logging.getLogger("HWR").info("Setting Pilatus wavelength...")
        self.set_channel_value(self.DET_WAVELENGTH, wavelength)
        time.sleep(0.6)
        
        print('WAVELENGHT WAS SET: ' + str(wavelength))
        self.wavelength = self.get_wavelength()
        print('WAVELENGHT GOT: ' + str(self.wavelength))

        if abs(self.wavelength - wavelength) < 0.0001:
            logging.getLogger("HWR").info(
                "Pilatus wavelength successfully set."
            )
            return True

        logging.getLogger("HWR").error(
            "Error while setting Pilatus wavelength. Please, check the detector."
        )
        return False

    def get_detector_distance(self):
        """
        Returns:
            float: detector distance
        """
        value = float(self.get_channel_value(self.DET_DETDIST))
        return value

    def set_detector_distance(self, det_distance):
        """
        Set detector distance and returns whether it was successful or not.
        """
        try:
            float(det_distance)
        except Exception as e:
            logging.getLogger("HWR").error(
                    "Error while setting Pilatus det distance. Value must be float."
            )
            return False

        #if abs(self.det_distance - det_distance) < 0.001:
        #    logging.getLogger("HWR").info(
        #        "Pilatus det distance still okay."
        #    )
        #    return True

        logging.getLogger("HWR").info("Setting Pilatus det distance...")
        self.set_channel_value(self.DET_DETDIST, det_distance)
        time.sleep(0.3)

        self.det_distance = self.get_detector_distance()

        if abs(self.det_distance - det_distance) < 0.001:
            logging.getLogger("HWR").info(
                "Pilatus det distance successfully set."
            )
            return True

        logging.getLogger("HWR").error(
            "Error while setting Pilatus det distance. Please, check the detector."
        )
        return False

    def get_user_beam_x(self):
        """
        Returns:
            float: user beam x
        """
        value = float(self.get_channel_value(self.USER_BEAM_X))
        return value

    def get_beam_x(self):
        """
        Returns:
            float: detector beam x
        """
        value = float(self.get_channel_value(self.DET_BEAM_X))
        return value

    def set_beam_x(self, from_user=False, beam_x=None):
        """
        Set detector beam_x and returns whether it was successful or not.

        Beam X value can come from different sources. The priority (from 
        high to low) is:
        * from_user
        * beam_x argument
        * default_beam_x (value set on xml file)
        """
        if from_user:
            logging.getLogger("HWR").info(
                "Getting beam X from user..."
            )
            beam_x = self.get_user_beam_x()

        if beam_x is None:
            if from_user:
                logging.getLogger("HWR").error(
                    "Could not get user beam X. Setting default value (from xml)."
                )
            beam_x = self.default_beam_x

        #if abs(self.beam_x - beam_x) == 0:
        #    logging.getLogger("HWR").info(
        #        "Pilatus beam X still okay."
        #    )
        #    return True

        logging.getLogger("HWR").info("Setting Pilatus beam X to {}...".format(beam_x))
        self.set_channel_value(self.DET_BEAM_X, beam_x)
        time.sleep(1)

        self.beam_x = self.get_beam_x()

        if float(self.beam_x) == float(beam_x):
            logging.getLogger("HWR").info(
                "Pilatus det beam X successfully set."
            )
            return True

        logging.getLogger("HWR").error(
            "Error while setting Pilatus beam X. Please, check the detector."
        )
        return False

    def get_user_beam_y(self):
        """
        Returns:
            float: user beam y
        """
        value = float(self.get_channel_value(self.USER_BEAM_Y))
        return value

    def get_beam_y(self):
        """
        Returns:
            float: detector beam y
        """
        value = float(self.get_channel_value(self.DET_BEAM_Y))
        return value

    def set_beam_y(self, from_user=False, beam_y=None):
        """
        Set detector beam_y and returns whether it was successful or not.

        Beam Y value can come from different sources. The priority (from 
        high to low) is:
        * from_user
        * beam_y argument
        * default_beam_y (value set on xml file)
        """
        if from_user:
            logging.getLogger("HWR").info(
                "Getting beam Y from user..."
            )
            beam_y = self.get_user_beam_y()

        if beam_y is None:
            if from_user:
                logging.getLogger("HWR").error(
                    "Could not get user beam Y. Setting default value (from xml)."
                )
            beam_y = self.default_beam_y

        #if abs(self.beam_y - beam_y) == 0:
        #    logging.getLogger("HWR").info(
        #        "Pilatus beam X still okay."
        #    )
        #    return True

        logging.getLogger("HWR").info("Setting Pilatus beam Y to {}...".format(beam_y))
        self.set_channel_value(self.DET_BEAM_Y, beam_y)
        time.sleep(1)

        self.beam_y = self.get_beam_y()

        if float(self.beam_y) == float(beam_y):
            logging.getLogger("HWR").info(
                "Pilatus det beam Y successfully set."
            )
            return True

        logging.getLogger("HWR").error(
            "Error while setting Pilatus beam Y. Please, check the detector."
        )
        return False
    
    def get_transmission(self):
        """
        Returns:
            float: detector filter transmission value
        """
        value = float(self.get_channel_value(self.DET_TRANSMISSION))
        return value

    def set_transmission(self, transmission):
        """
        Set filter transmission and returns whether it was successful or not.
        """
        try:
            float(transmission)
        except Exception as e:
            logging.getLogger("HWR").error(
                    "Error while setting Pilatus transmission. Value must be float."
            )
            return False

        logging.getLogger("HWR").info("Setting Pilatus transmission to {}...".format(transmission))
        self.set_channel_value(self.DET_TRANSMISSION, transmission)
        time.sleep(0.3)

        self.transmission = self.get_transmission()

        if abs(self.transmission - transmission) < 0.0001:
            logging.getLogger("HWR").info(
                "Pilatus transmission successfully set."
            )
            return True

        logging.getLogger("HWR").error(
            "Error while setting Pilatus transmission. Please, check the detector."
        )
        return False
    
    def get_start_angle(self):
        """
        Returns:
            float: detector start angle value
        """
        value = float(self.get_channel_value(self.DET_START_ANGLE))
        return value

    def set_start_angle(self, start_angle):
        """
        Set start angle and returns whether it was successful or not.
        """
        try:
            float(start_angle)
        except Exception as e:
            logging.getLogger("HWR").error(
                    "Error while setting Pilatus start angle. Value must be float."
            )
            return False

        logging.getLogger("HWR").info("Setting Pilatus start angle to {}...".format(start_angle))
        self.set_channel_value(self.DET_START_ANGLE, start_angle)
        time.sleep(3)

        self.start_angle = self.get_start_angle()

        if abs(self.start_angle - start_angle) < 0.0001:
            logging.getLogger("HWR").info(
                "Pilatus start angle successfully set."
            )
            return True

        logging.getLogger("HWR").error(
            "Error while setting Pilatus start angle. Please, check the detector."
        )
        return False
    
    def get_angle_incr(self):
        """
        Returns:
            float: detector angle increment value
        """
        value = float(self.get_channel_value(self.DET_ANGLE_INCR))
        return value

    def set_angle_incr(self, angle_incr):
        """
        Set angle increment and returns whether it was successful or not.
        """
        try:
            float(angle_incr)
        except Exception as e:
            logging.getLogger("HWR").error(
                    "Error while setting Pilatus angle increment. Value must be float."
            )
            return False

        logging.getLogger("HWR").info("Setting Pilatus angle increment to {}...".format(angle_incr))
        self.set_channel_value(self.DET_ANGLE_INCR, angle_incr)
        time.sleep(3)

        self.angle_incr = self.get_angle_incr()

        if abs(self.angle_incr - angle_incr) < 0.0001:
            logging.getLogger("HWR").info(
                "Pilatus angle increment successfully set."
            )
            return True

        logging.getLogger("HWR").error(
            "Error while setting Pilatus angle increment. Please, check the detector."
        )
        return False
