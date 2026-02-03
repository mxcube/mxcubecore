# encoding: utf-8
#
#  Project name: MXCuBE
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
"""
Control the detector cover

Example xml file:

.. code-block:: xml

  <object class="DetectorCover">
    <object href="/detcover" role="detector_cover"/>
    <object href="/handle_detcover" role="handle_detector_cover"/>
  </object>

.. code-block:: yaml

 class DetectorCover.DetectorCover
 configuration:
    username: Detector Cover
 objects:
    detector_cover: detcover.yaml
    handle_detector_cover: handle_detcover.yaml

"""

from mxcubecore.HardwareObjects.abstract.AbstractActuator import AbstractActuator

__copyright__ = """ Copyright © by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class DetectorCover(AbstractActuator):
    """Detector Cover class"""

    def __init__(self, name):
        super().__init__(name)
        self.detector_cover = None
        self.handle_detector_cover = True

    def init(self):
        """Initialise properties and objects"""
        super().init()
        self.detector_cover = self.get_object_by_role("detector_cover")
        self.handle_detector_cover = self.get_object_by_role("handle_detector_cover")

    def set_value(self, value, timeout: float | None = None):
        """Set the detector cover. Check if you need to handle it.
        Args:
            value: target value.
            timeout: optional - timeout [s].
                     If timeout = 0: return at once and do not wait,
                     if timeout is None: wait forever (default).
        """

        use = True
        if self.handle_detector_cover:
            try:
                use = self.handle_detector_cover.get_value().value
            except AttributeError:
                use = False
        if use:
            self.detector_cover.set_value(value, timeout)

    def get_value(self):
        """Get the values for the detector cover only."""
        return self.detector_cover.get_value()

    def get_value_handle(self):
        """Get the handle detector cover option."""
        if self.handle_detector_cover:
            return self.handle_detector_cover.get_value()
        return True
