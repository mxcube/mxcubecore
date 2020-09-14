#! /usr/bin/env python
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
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

"""Beamline class serving as singleton container for links to top-level HardwareObjects

All HardwareObjects
"""

from __future__ import division, absolute_import
from __future__ import print_function, unicode_literals

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"
__author__ = "Rasmus H Fogh"

from collections import OrderedDict
from HardwareRepository.HardwareObjects.Beamline import Beamline


class EMBLBeamline(Beamline):
    """Beamline class serving as singleton container for links to HardwareObjects"""

    # Roles of defined objects and the category they belong to
    # NB the double underscore is deliberate - attribute must be hidden from subclasses
    __content_roles = []

    def __init__(self, name):
        """

        Args:
            name (str) : Object name, generally saet to teh role name of the object
        """
        super(EMBLBeamline, self).__init__(name)

    # NB this function must be re-implemented in nested subclasses
    @property
    def all_roles(self):
        """Tuple of all content object roles, indefinition and loading order

        Returns:
            tuple[text_str, ...]
        """
        return super(EMBLBeamline, self).all_roles + tuple(self.__content_roles)

    # Additional properties

    @property
    def beam_focusing(self):
        """Beam-definer Hardware object

        Returns:
            Optional[AbstractMotor]:
        """
        return self._objects.get("beam_focusing")

    __content_roles.append("beam_focusing")

    @property
    def ppu_control(self):
        """PPU control Hardware object

        Returns:
            Optional[HardwareObject]:
        """
        return self._objects.get("ppu_control")

    __content_roles.append("ppu_control")

    # Additional procedures

    # NB this is just an example of a beamline-specific procedure description
    @property
    def xray_centring(self):
        """ X-ray Centring Procedure

        NB EMBLXrayCentring is defined in EMBL-specific code, like EMBLBeamline

        Returns:
            Optional[EMBLXrayCentring]
        """
        return self._objects.get("xray_centring")

    __content_roles.append("xray_centring")
    # Registers this object as a procedure:
    Beamline._procedure_names.add("xray_centring")
