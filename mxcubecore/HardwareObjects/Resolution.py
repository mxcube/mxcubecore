# -*- coding: utf-8 -*-
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.
"""Resolution concrete implementation.
Example xml file:
<object class="Resolution">
  <username>Resolution</username>
  <actuator_name>resolution</actuator_name>
  <tolerance>1e-4</tolerance>
  <!-- optional -->
  <object href="/pilatus" role="detector"/>
</object>

"""

from HardwareRepository.HardwareObjects.abstract.AbstracResolution import (
    AbstractResolution,
)

__copyright__ = """ Copyright © 2010-2020 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class Resolution(AbstractResolution):
    """Resolution as motor"""

    unit = "Å"

    def __init__(self, name):
        super(Resolution, self).__init__(name)

    def init(self):
        """Initialisation"""
        super(Resolution, self).init()
