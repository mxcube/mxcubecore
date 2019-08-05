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
    __object_role_categories = OrderedDict()

    def __init__(self, name):
        """

        Args:
            name (str) : Object name, generally saet to teh role name of the object
        """
        super(EMBLBeamline, self).__init__(name)

    @property
    def role_to_category(self):
        """Mapping from role to category

        Returns:
            OrderedDict[text_str, text_str]
        """
        # Copy roles from superclass and add those form this class
        result = super(EMBLBeamline, self).role_to_category
        result.update(self.__object_role_categories)
        return result


    # Additional properties

    @property
    def beam_definer(self):
        """Beam-definer Hardware object

        Returns:
            Optional[AbstractMotor]:
        """
        return self._objects.get("beam_definer")
    __object_role_categories["beam_definer"] = "hardware"

    @property
    def ppu_control(self):
        """PPU control Hardware object

        Returns:
            Optional[HardwareObject]:
        """
        return self._objects.get("ppu_control")
    __object_role_categories["ppu_control"] = "hardware"
