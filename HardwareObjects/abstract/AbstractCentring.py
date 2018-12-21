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
</object>
"""
from __future__ import print_function
import gevent
import logging
import enum
from warnings import warn

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
    
    def init(self):
        self.diffr_hwobj = self.getObjectByRole("diffractometer")
        self.centring_hwobj = self.getObjectByRole("centring_math")
        self.beaminfo_hwobj = self.self.getObjectByRole("beam_info")

        # which are the centring motors (by roles)
        try:
            self.centring_motors = self.getProperty("centring_motors").split()
        except IndexError:
            pass

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Descript. :
        """
        c = centred_positions_dict

        if self.head_type == GenericDiffractometer.HEAD_TYPE_MINIKAPPA:
            kappa = self.motor_hwobj_dict["kappa"]
            phi = self.motor_hwobj_dict["kappa_phi"]

        xy = self.centring_hwobj.centringToScreen(c)
        x = xy["X"] * self.pixels_per_mm_x + self.zoom_centre["x"]
        y = xy["Y"] * self.pixels_per_mm_y + self.zoom_centre["y"]
        return x, y

    def manual_centring(self, nb_clicks=3):
        """ Do centring based on nb_clicks
        Args:
           nb_clicks (int): number of clicks, default value is 3
        Returns:
           (dict): Motor hardware object as key, position as value
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
                {
                    "X": (x - beam_x) / pixels_mm_x,
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
