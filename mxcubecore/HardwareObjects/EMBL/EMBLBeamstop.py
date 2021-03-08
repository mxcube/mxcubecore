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

from mxcubecore.BaseHardwareObjects import Device
from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


class EMBLBeamstop(Device, AbstractMotor):
    def __init__(self, name):
        Device.__init__(self, name)

        self.distance = None
        self.default_size = None
        self.default_distance = None
        self.default_direction = None

        self.chan_distance = None
        self.chan_position = None

    def init(self):
        """Reads parameters from xml and adds neccessary channels"""
        self.default_size = self.get_property("defaultBeamstopSize")
        self.default_distance = self.get_property("defaultBeamstopDistance")
        self.default_direction = self.get_property("defaultBeamstopDirection")

        if self.default_distance is None:
            self.chan_distance = self.get_channel_object("BeamstopDistance")
            if self.chan_distance is not None:
                self.chan_distance.connect_signal("update", self.distance_changed)
            self.distance_changed(self.chan_distance.get_value())
        else:
            self.distance = float(self.default_distance)

        self.chan_position = self.get_channel_object("BeamstopPosition")

    def is_ready(self):
        """Returns True if device ready
        """
        return True

    def distance_changed(self, value):
        """Updates beam stop distance value

        :param value: beamstop distance
        :type value: float
        :return: None
        """
        self.distance = value
        self.emit("beamstopDistanceChanged", value)

    def get_size(self):
        """Returns default beamstop size"""
        return self.default_size

    def set_distance(self, distance):
        """Sets beamstop distance

        :param distance: beamstop distance
        :type distance: float (mm)
        """
        if self.chan_distance is not None:
            self.chan_distance.set_value(distance)
            self.distance_changed(distance)

    def get_distance(self):
        """Returns beamstop distance in mm"""
        return self.distance

    def get_direction(self):
        """Returns beamstop direction"""
        return self.default_direction

    def get_value(self):
        """Returns beamstop position"""
        return self.chan_position.get_value()

    def set_position(self, position):
        """Sets position

        :param position: beamstop position
        :type position: str
        """
        self.chan_position.set_value(position)

    def re_emit_values(self):
        """Reemits available signals"""
        self.emit("beamstopDistanceChanged", self.distance)
