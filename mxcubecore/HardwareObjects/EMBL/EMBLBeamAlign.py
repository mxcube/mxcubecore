#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""
EMBLBeamAlign
"""

import logging
from HardwareRepository.BaseHardwareObjects import HardwareObject


__author__ = "Ivars Karpics"
__credits__ = ["MXCuBE colaboration"]

__version__ = "2.2."
__maintainer__ = "Ivars Karpics"
__email__ = "ivars.karpics[at]embl-hamburg.de"
__status__ = "Draft"


class EMBLBeamAlign(HardwareObject):
    """
    Descript. :
    """

    def __init__(self, name):
        """
        Descript. :
        """
        HardwareObject.__init__(self, name)   

        self.horizontal_motor_hwobj = None
        self.vertical_motor_hwobj = None
        self.graphics_manager_hwobj = None

        self.scale_hor = None
        self.scale_ver = None
           
    def init(self):
        """
        Descript. :
        """
        self.scale_hor = self.getProperty("scale_hor") 
        self.scale_ver = self.getProperty("scale_ver")

        self.horizontal_motor_hwobj = self.getObjectByRole("horizontal_motor")
        self.vertical_motor_hwobj = self.getObjectByRole("vertical_motor")
        self.graphics_manager_hwobj = self.getObjectByRole("graphics_manager")

    def align_beam(self):
        beam_pos_displacement = self.graphics_manager_hwobj.get_beam_displacement()         
        if None in beam_pos_displacement:
            logging.getLogger("user_level_log").error("Unable to " + \
                "detect beam shape. Beam align will not be done") 
        else:
            delta_hor = beam_pos_displacement[0] * scale_hor
            delta_ver = beam_pos_displacement[1] * scale_ver   
            logging.getLogger("user_level_log").debug("BeamAlign: Applying " + \
                 "%.2f mm horizontal and %.2f mm vertical correction" % \
                 (delta_hor, delta_ver)) 
            #self.vertical_motor_hwobj.moveRelative(delta_ver)
            #self.horizontal_motor_hwobj.moveRelative(delta_hor)
