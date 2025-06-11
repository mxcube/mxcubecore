# encoding: utf-8
#
#  Project: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""
Detector API
Abstract methods:
    prepare_acquisition
    start_acquisition
    has_shutterless
Overloaded methods:
    force_emit_signals
Implemented methods:
    stop_acquisition
    get_pixel_size, get_width, get_heigth, get_metadata
    get_radius, get_outer_radius
    get_beam_position
    get_roi_mode, set_roi_mode, get_roi_mode_name, get_roi_modes
    get_exposure_time_limits
    get_threshold_energy, set_threshold_energy
    get_binning_mode, set_binning_mode
Implemented propertries:
    distance
Emited signals:
    detectorRoiModeChanged
    temperatureChanged
    humidityChanged
    expTimeLimitsChanged
    frameRateChanged
    stateChanged
    specificStateChanged
Hardware objects used: energy
"""

import abc
import ast
import math

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.model.queue_model_objects import PathTemplate

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class AbstractDetector(HardwareObject):
    """Common base class for detectors"""

    __metaclass__ = abc.ABCMeta

    def __init__(self, name):
        super().__init__(name)

        self._temperature = None
        self._humidity = None
        self._actual_frame_rate = None
        self._exposure_time_limits = (None, None)
        self._pixel_size = (None, None)
        self._binning_mode = None
        self._roi_mode = 0
        self._images_per_file = 0
        self._roi_modes_list = []

        self._threshold_energy = None
        self._distance_motor_hwobj = None
        self._width = None  # [pixel]
        self._height = None  # [pixel]
        self._metadata = {}

    def init(self):
        """Initialise some common parameters"""
        super().init()

        self._metadata = self.get_property("beam", {})

        self._images_per_file = self.get_property("images_per_file", 100)

        self._distance_motor_hwobj = self.get_object_by_role("detector_distance")

        self._roi_modes_list = ast.literal_eval(self.get_property("roiModes", "()"))

        self._pixel_size = (self.get_property("px"), self.get_property("py"))
        self._width = self.get_property("width")
        self._height = self.get_property("height")

    def force_emit_signals(self):
        """Emit all hardware object signals."""
        self.emit("detectorRoiModeChanged", (self._roi_mode,))
        self.emit("temperatureChanged", (self._temperature, True))
        self.emit("humidityChanged", (self._humidity, True))
        self.emit("expTimeLimitsChanged", (self._exposure_time_limits,))
        self.emit("frameRateChanged", (self._actual_frame_rate,))
        self.emit("stateChanged", (self._state,))
        self.emit("specificStateChanged", (self._specific_state,))

    @property
    def images_per_file(self):
        return self._images_per_file

    @property
    def distance(self):
        """Property for contained detector_distance hardware object
        Returns:
            (AbstratctMotor): Hardware object.
        """
        return self._distance_motor_hwobj

    @abc.abstractmethod
    def has_shutterless(self):
        """Check if detector is capable of shutterless acquisition.
        Returns:
            (bool): True if detector is capable, False otherwise
        """
        return

    @abc.abstractmethod
    def prepare_acquisition(self, *args, **kwargs):
        """
        Prepares detector for acquisition
        """

    def last_image_saved(self):
        """Get the path to the last saved image
        Returns:
            (str): full path.
        """
        return None

    @abc.abstractmethod
    def start_acquisition(self):
        """Start the acquisition."""

    def stop_acquisition(self):
        """Stop the acquisition."""

    def get_roi_mode(self):
        """Get the current ROI mode.
        Returns:
            (str): current ROI mode
        """
        return self._roi_mode

    def set_roi_mode(self, roi_mode):
        """Set the current ROI mode.
        Args:
            roi_mode (int): ROI mode to set.
        """
        self._roi_mode = roi_mode
        self.emit("detectorRoiModeChanged", (self._roi_mode,))

    def get_roi_mode_name(self):
        """Get the current ROI mode name.
        Returns:
            (str): name
        """
        return self._roi_modes_list[self._roi_mode]

    def get_roi_modes(self):
        """Get the available ROI modes
        Returns:
            (tuple): Tuple of strings.
        """
        return tuple(self._roi_modes_list)

    def get_exposure_time_limits(self):
        """Get the exposure time lower and upper limits.
        Returns:
            (tuple): Two floats (lower and upper limit) [s]
        """
        return self._exposure_time_limits

    def get_pixel_size(self):
        """Get the pixel size.
        Returns:
            (tuple): Two floats (x, y) [mm].
        """
        return self._pixel_size

    def get_binning_mode(self):
        """Get the current binning mode.
        Returns:
            (int): Binning mode
        """
        return self._binning_mode

    def set_binning_mode(self, value):
        """Set the current binning mode.
        Args:
            value (int): binning mode.
        """
        self._binning_mode = value

    def get_beam_position(self, distance=None, wavelength=None):  # noqa: ARG002
        """Calculate the beam position for a given distance.
        Args:
            distance (float): detector distance [mm]
            wavelength (float): X-ray wavelength [Å]
        Returns:
            tuple(float, float): Beam position x,y coordinates [pixel].
        """
        # Following is just an example of calculating beam center using
        # simple linear regression,
        # One needs to overload the method in case more complex calculation
        # is required, e.g. using other detector positioning motors and
        # wavelength

        try:
            distance = (
                distance
                if distance is not None
                else self._distance_motor_hwobj.get_value()
            )

            metadata = self.get_metadata()

            beam_position = (
                float(distance * metadata["ax"] + metadata["bx"]),
                float(distance * metadata["ay"] + metadata["by"]),
            )
        except (AttributeError, KeyError):
            beam_position = (None, None)

        return beam_position

    def get_radius(self, distance=None):
        """Get distance from the beam position to the nearest detector edge.
        Args:
            distance (float): Distance [mm]
        Returns:
            (float): Detector radius [mm]
        """
        try:
            distance = (
                distance
                if distance is not None
                else self._distance_motor_hwobj.get_value()
            )
        except AttributeError as err:
            raise RuntimeError("Cannot calculate radius, unknown distance") from err

        beam_x, beam_y = self.get_beam_position(distance)
        pixel_x, pixel_y = self.get_pixel_size()
        rrx = min(self.get_width() - beam_x, beam_x) * pixel_x
        rry = min(self.get_height() - beam_y, beam_y) * pixel_y
        radius = min(rrx, rry)

        return radius

    def get_outer_radius(self, distance=None):
        """Get distance from beam_position to the furthest point on the detector.
        Args:
            distance (float): Distance [mm]
        Returns:
            (float): Detector outer adius [mm]
        """
        try:
            distance = (
                distance
                if distance is not None
                else self._distance_motor_hwobj.get_value()
            )
        except AttributeError as err:
            raise RuntimeError(
                "Cannot calculate outer radius, distance unknown"
            ) from err

        beam_x, beam_y = self.get_beam_position(distance)
        pixel_x, pixel_y = self.get_pixel_size()
        max_delta_x = max(beam_x, self._width - beam_x) * pixel_x
        max_delta_y = max(beam_y, self._height - beam_y) * pixel_y

        return math.sqrt(max_delta_x * max_delta_x + max_delta_y * max_delta_y)

    def get_metadata(self):
        """Returns relevant metadata.
        Returns:
            (dict): metadata
        """
        self._metadata["width"] = self.get_width()
        self._metadata["height"] = self.get_height()

        return self._metadata

    def get_width(self):
        """Returns detector width.
        Returns:
            (int): detector width [px]
        """
        return self._width

    def get_height(self):
        """Returns detector height.
        Returns:
            (int): detector height [px]
        """
        return self._height

    def set_threshold_energy(self, threshold_energy):
        """
        Args:
            threshold_energy (float): Detector threshold energy [eV]
        """
        self._threshold_energy = threshold_energy

    def get_threshold_energy(self):
        """Returns detector threshold_energy
        Returns:
            (float): Detector threshold energy [eV]
        """
        return self._threshold_energy

    def get_image_file_name(self, path_template, suffix=None):
        template = "%s_%s_%%0" + str(path_template.precision) + "d.%s"
        suffix = suffix or path_template.suffix
        file_name = template % (
            path_template.get_prefix(), path_template.run_number, suffix
        )
        if path_template.compression:
            file_name = "%s.gz" % file_name

        return file_name

    def get_first_and_last_file(self, pt: PathTemplate):
        """
        Get complete path to first and last image

        Args:
          pt (PathTempalte): Path template parameter

        Returns:
        (Tuple): Tuple containing first and last image path (first, last)
        """
        start_num = pt.start_num
        end_num = pt.start_num + pt.num_files - 1

        return (pt.get_image_path() % start_num, pt.get_image_path() % end_num)
