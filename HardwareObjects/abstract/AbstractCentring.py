#
#  Project: MXCuBE
#  https://github.com/mxcube.
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.
"""
Example xml file

<object class = "CentringProcedures">
  <username>Centring Procedures</username>
  <object role="diffractometer" href="/diffractometer"/>
  <object role="centring" href="/centring_math"/>
  <object role="beam_info" href="/beam_info"/>
  <centring_motors>
    omega
    horizontal_alignment
    vertical_alignment
    horizontal_centring
    vertical_centring
    zoom
    focus
    kappa
    kappa_phi
  </centring_motors>
  <grid_directions>
    <holderlength>-1</holderlength>
    <horizontal_centring>-1</horizontal_centring>
  </grid_directions>
</object>
"""
from __future__ import print_function
import math
import numpy
import gevent
import logging
import enum

from HardwareRepository.BaseHardwareObjects import HardwareObject


@enum.unique
class CentringMethod(enum.Enum):
    MANUAL_3CLICKS = "Manual 3-click"
    AUTOMATIC = "Automatic centring"
    MOVE_TO_BEAM = "Move to beam"


class AbstractCentring(HardwareObject):
    def __init__(self, name):
        HardwareObject.__init__(self, name)
        self.centring_motors = None
        self.directions = {}

    
    def init(self):
        self.diffr_hwobj = self.getObjectByRole("diffractometer")
        self.centring_hwobj = self.getObjectByRole("centring_math")
        self.beaminfo_hwobj = self.self.getObjectByRole("beam_info")

        # which are the centring motors (by roles)
        try:
            self.centring_motors = self.getProperty("centring_motors").split()
        except IndexError:
            pass

        for role in self.centring_motors:
            self.directions[role] = 1

        # get the grid directions, if any
        try:
            directions = self["grid_directions"].getProperties()
            for role, value in directions.items():
                self.directions[role] = value
        except IndexError:
            pass

    def motor_positions_to_screen(self, centred_positions_dict):
        """ Retirns x, y coordinates of the centred point, calculated
            from positions of the centring motors
        Args:
            centred_positions_dict (dict): role:position dictionary
        Returns:
            (tuple): x, y [pixels]
        """
        # update the zoom calibration and get pixeld/mm
        self.update_zoom_calibration()
        pixels_mm_x, pixels_mm_y = self.diffr_hwobj.get_pixels_per_mm()
        if None in (pixels_mm_x, pixels_mm_y):
            return 0, 0

        # read the motor positions
        motors_pos_dict = dict(self.diffr_hwobj.get_motor_positions())

        omega_angle = math.radians(motors_pos_list["omega"] * self.directions["omega"])
        sampx = self.direction["horizontal_centring"] * (
            centred_positions_dict["horizontal_centring"] -
            motors_pos_dict["horizontal_centring"]
        )
        sampy = self.direction["vertical_centring"] * (
            centred_positions_dict["vertical_centring"] -
            motors_pos_dict["vertical_centring"]
        )
        phiy = self.direction["horizontal_alignment"] * (
            centred_positions_dict["horizontal_alignment"] -
            motors_pos_dict["horizontal_alignment"]
        )
        phiz = self.direction["vertical_alignment"] * (
            centred_positions_dict["vertical_alignment"] -
            motors_pos_dict["vertical_alignment"]
        )

        rot_matrix = numpy.matrix(
            [
                math.cos(omega_angle),
                -math.sin(omega_angle),
                math.sin(omega_angle),
                math.cos(omega_angle),
            ]
        )
        rot_matrix.shape = (2, 2)
        inv_rot_matrix = numpy.array(rot_matrix.I)
        dx, dy = (
            numpy.dot(numpy.array([sampx, sampy]), inv_rot_matrix) * pixels_mm_x
        )
        beam_x, beam_y = self.beaminfo_hwobj.get_beam_position()
        x = (phiy * pixels_mm_x) + beam_x
        y = dy + (phiz * pixels_mm_y) + beam_y

        return x, y

    def automatic_centring(self, motors_list):
        """ Do automatic centring, using the motors, defined in the motors_list
        Args:
            motors_list (list): lis of motor roles
        Returns:
            (dict): motor_role:position dictionary
        """
    def start_centring(self, method, sample_info=None, wait=False):
        """ Start centring """

    def cancel_centring(self):
        """ Cancel centring """

    def manual_centring(self, motors_list, nb_positions=3, rotation_angle=90):
        """ Do manual centring, using the motors, defined in the motors_list
        Args:
            motors_list (list): lis of motor roles
            nb_rotations (int): Number of different positions, needed to
                                calculate the centre position.
            rotation_angle (float): Angle to rotate between each position [deg]
        Returns:
            (dict): motor_role:position dictionary
        """
        omega = self.diffr_hwobj.centring_motors["omega"]
        self.centring_hwobj.initCentringProcedure()
        for click in range(nb_clicks):
            # get pixeld/mm on every image as the zoom may change
            pixels_mm_x, pixels_mm_y = self.diffr_hwobj.get_pixels_per_mm()
            beam_x, beam_y = self.beaminfo_hwobj.get_beam_position()
            self.user_clicked_event = gevent.event.AsyncResult()
            x, y = self.user_clicked_event.get()
            self.centring_hwobj.appendCentringDataPoint(
                {"X": (x - beam_x) / pixels_mm_x,
                 "Y": (y - beam_y) / pixels_mm_y,
                }
            )

            if self.diffr_hwobj.in_plate_mode():
                dynamic_limits = omega.get_dynamic_limits()
                if click == 0:
                    omega.move(dynamic_limits[0], wait=True)
                elif click == 1:
                    omega.move(dynamic_limits[1], wait=True)
            else:
                if click < 2:
                    omega.move_relative(90, wait=True)
        self.omega_reference_add_constraint()
        return self.centring_hwobj.centeredPosition(return_by_name=False)

        def move_to_beam(self, coord_x, coord_y, wait=False):
        """ Move the diffractometer to coordinates
        Args:
            coord_x (int): X coordinate [pixels]
            coord_y (int): Y coordinate [pixels]
            waith (bool): wait (True) or not (False) until the end of the movement
        """
        self.start_centring(
            CentringMethod.MOVE_TO_BEAM, coordinates=[coord_x, coord_y],
            wait=wait
        )
