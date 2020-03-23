# encoding: utf-8
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

"""Zoom as Expoorter motor"""

from HardwareRepository.HardwareObjects.ExporterMotor import ExporterMotor


class MicrodiffZoom(ExporterMotor):
    """MicrodiffZoom class"""

    def __init__(self, name):
        ExporterMotor.__init__(self, name)
        self.predefined_positions = {}
        self._exporter = None
        self._limits = None
        self.position_channel = None
        self.motor_state = None

    def init(self):
        """Initialize the zoom"""
        ExporterMotor.init(self)
        _exporter_address = self.getProperty("exporter_address")
        self.position_channel = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": _exporter_address,
                "name": "zoom_position",
            },
            "CoaxialCameraZoomValue",
        )
        if self.position_channel:
            self.get_value()
            self.position_channel.connectSignal("update", self.update_value)

        self.motor_state = self.add_channel(
            {
                "type": "exporter",
                "exporter_address": _exporter_address,
                "name": "zoom_state",
            },
            "State",
        )

        if self.motor_state:
            self.motor_state.connectSignal("update", self._update_state)

        _low, _high = self.get_limits()
        for _idx in range(_low, _high + 1):
            self.predefined_positions["Zoom %s" % _idx] = _idx

    def get_limits(self):
        """Returns zoom low and high limits.
        Returns:
            (tuple): two int tuple (low limit, high limit).
        """
        try:
            _low, _high = self._exporter.execute("getZoomRange")
            # inf is a problematic value
            if _low == float("-inf"):
                _low = 0

            if _high == float("inf"):
                _high = 10

            self._limits = (_low, _high)
        except ValueError:
            self._limits = (1, 10)
        return self._limits
