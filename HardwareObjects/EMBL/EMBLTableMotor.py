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
#  You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import time
import socket
import atexit
import logging
from abstract.AbstractMotor import AbstractMotor

__credits__ = ["EMBL Hamburg"]
__category__ = "Motor"


class EMBLTableMotor(AbstractMotor):
    def __init__(self, name):
        AbstractMotor.__init__(self, name)

        self.direction = None
        self.socket = None
        self.enabled = False

        atexit.register(self.close)

    def init(self):
        self.direction = self.getProperty("direction")
        self.set_position(0)
        self.set_state(self.motor_states.READY)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(("10.14.90.12", 701))
        self.socket.send("enable (0,1,2,3)\r")
        self.enabled = True

    def is_ready(self):
        return True

    def connected(self):
        self.set_ready(True)

    def disconnected(self):
        self.set_ready(True)

    def stop(self):
        self.socket.send("disable (0,1,2,3)\r")
        self.enabled = False

    def move(self, target, wait=None, timeout=None):
        pass

    def move_relative(self, relative_position, wait=False, timeout=None):
        self.set_state(self.motor_states.MOVING)
        if not self.enabled:
            self.socket.send("enable (0,1,2,3)\r")
            time.sleep(1)
        if self.direction == "vertical":
            self.socket.send("PTP/r (1), %f\r" % relative_position)
        else:
            self.socket.send("PTP/r (3), %f\r" % relative_position)
        self.set_state(self.motor_states.READY)

    def close(self):
        try:
            self.socket.close()
            logging.getLogger().info("EMBLTableMotor: Socket closed")
        except BaseException:
            logging.getLogger().error("EMBLTableMotor: Failed to close the socket")
