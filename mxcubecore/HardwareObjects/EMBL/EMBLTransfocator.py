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

"""EMBLTransfocator"""

import logging

import gevent

from mxcubecore.BaseHardwareObjects import HardwareObject

__credits__ = ["EMBL Hamburg"]
__category__ = "General"


class EMBLTransfocator(HardwareObject):
    """Controls Transfocator"""

    def __init__(self, name):
        """Inherited from HardwareObject"""

        HardwareObject.__init__(self, name)

        self.focal_length = None
        self.lens_count = None

        self.modes = None
        self.current_mode = None
        self.energy_value = None
        self.energy_state = None
        self.current_focusing_mode = None
        self.crl_value = None
        self.chan_crl_value = None
        self.cmd_set_crl_value = None
        self.cmd_set_trans_value = None

    def init(self):
        """Inits all variables"""

        # self.chan_crl_value = self.get_channel_object("chanCrlValue")
        # if self.chan_crl_value:
        #    self.chan_crl_value.connect_signal("update", self.crl_value_changed)
        # self.cmd_set_crl_value = self.get_command_object("cmdSetLenses")

        self.current_mode = "Manual"

    def convert_value(self, value):
        """Converts int to list of bits"""
        if isinstance(value, (list, tuple)):
            lens_combination = 0
            for index in range(self.lens_count):
                lens_combination = lens_combination + value[index] * pow(2, index)
        else:
            lens_combination = [0, 0, 0, 0, 0, 0]
            for index in range(self.lens_count):
                lens_combination[index] = (value & pow(2, index)) / pow(2, index)
        return lens_combination

    def get_modes(self):
        """Returns list with available CRL modes"""
        return ["Manual"]

    def get_mode(self):
        """Returns current crl mode"""
        return self.current_mode

    def set_mode(self, mode):
        """Sets crl mode

        :param mode: crl mode
        :type mode: str
        :return: None
        """
        return

    def crl_value_changed(self, value):
        """Emit signal when crl combination changed"""
        self.crl_value = value
        self.emit("crlValueChanged", self.crl_value)

    def set_crl_value(self, value, timeout=None):
        """Sets CRL lens combination. If integer passed then
           converts value to the bit list
        """
        if not isinstance(value, (list, tuple)):
            value = self.convert_value(value)

        if value is not None:
            self.cmd_set_crl_value(value)
            logging.getLogger("GUI").info(
                "Setting CRL image plane "
                + "distance to %.2f" % self.get_image_plane_distance(value)
            )

            if timeout:
                gevent.sleep(1)
                with gevent.Timeout(timeout, Exception("Timeout waiting for CRL")):
                    while value != self.crl_value:
                        gevent.sleep(0.1)

    def get_crl_value(self):
        """Return crl combination"""
        return self.crl_value

    def re_emit_values(self):
        """Reemits signals"""
        self.emit("crlModeChanged", self.current_mode)
        self.emit("crlValueChanged", self.crl_value)

    def move_up(self):
        """Moves lense combination one value up"""
        return

    def move_down(self):
        """Moves lense combination one value down"""
        return
