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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

from mx3core.hardware_objects.abstract.AbstractTransmission import (
    AbstractTransmission,
)
from mx3core.hardware_objects.mockup.ActuatorMockup import ActuatorMockup


__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class TransmissionMockup(ActuatorMockup, AbstractTransmission):
    """Transmission value as a percentage """

    # All necessary functionality is present in superclasses
    pass
