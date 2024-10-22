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

"""EMBLTableMotor"""

import atexit
import logging
import socket
import time

from mxcubecore.HardwareObjects.abstract.AbstractMotor import AbstractMotor

__credits__ = ["EMBL Hamburg"]
__license__ = "LGPLv3+"
__category__ = "Motor"


class EMBLTableMotor(AbstractMotor):
    """
    EMBLTableMotor defines socket interface to positioning table
    """

    def __init__(self, name):
        AbstractMotor.__init__(self, name)

        self.direction = None
        self.socket = None
        self.enabled = False

        atexit.register(self.close)

    def init(self):
        """
        Creates socket interface
        :return:
        """
        self.direction = self.get_property("direction")
        self.set_position(0)
        self.update_state(self.motor_states.READY)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(("10.14.90.12", 701))
        self.socket.send("enable (0,1,2,3)\r")
        self.enabled = True

    def is_ready(self):
        """
        Returns ready
        :return: always True
        """
        return True

    def connected(self):
        """
        Sets to ready
        :return: None
        """
        self.set_ready(True)

    def disconnected(self):
        """
        Sets not to ready
        :return:
        """
        self.set_ready(False)

    def stop(self):
        """
        Stops motor movement
        :return: None
        """
        self.socket.send("disable (0,1,2,3)\r")
        self.enabled = False

    def set_value_relative(self, relative_position, wait=False, timeout=None):
        """
        Moves motor by a relative step
        :param relative_position: float
        :param wait: boolean
        :param timeout: in seconds (int)
        :return: None
        """
        self.update_state(self.motor_states.MOVING)
        if not self.enabled:
            self.socket.send("enable (0,1,2,3)\r")
            time.sleep(1)
        if self.direction == "vertical":
            self.socket.send("PTP/r (1), %f\r" % relative_position)
        else:
            self.socket.send("PTP/r (3), %f\r" % relative_position)
        self.update_state(self.motor_states.READY)

    def close(self):
        """
        Closes the socket connection
        :return: None
        """
        try:
            self.socket.close()
            logging.getLogger("HWR").info("EMBLTableMotor: Socket closed")
        except Exception:
            logging.getLogger("HWR").error("EMBLTableMotor: Failed to close the socket")
