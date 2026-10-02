# encoding: utf-8
#
# This file is part of MXCuBE.
#
# MXCuBE is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MXCuBE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with MXCuBE.  If not, see <https://www.gnu.org/licenses/>.
"""Client of a murko server (https://github.com/MartinSavko/murko), loop detection."""

import pickle
import socket

from mxcubecore.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © by MXCuBE Collaboration """
__license__ = "LGPLv3+"


class MurkoUnavailable(RuntimeError):
    """Murko cannot be reached, the queue should not go on without it."""

    abort_queue = True


class Murko(HardwareObject):
    """Configuration properties: host, port and timeout (s)."""

    def init(self):
        super().init()
        self.host = self.get_property("host", "localhost")
        self.port = int(self.get_property("port", 8901))
        self.timeout = self.get_property("timeout", 30)

    def is_available(self) -> bool:
        try:
            socket.create_connection((self.host, self.port), timeout=2).close()
        except OSError:
            return False
        return True

    def predict(self, image) -> dict | None:
        """Find the loop in image.

        Returns:
            None when nothing is seen, otherwise "click" (x, y) and
            "box" (x1, y1, x2, y2), in fractions of the image size.
        """
        import zmq.green as zmq  # optional dependency

        request = {
            "to_predict": image,
            "description": [
                "foreground",
                "crystal",
                "loop_inside",
                "loop",
                ["crystal", "loop"],
                ["crystal", "loop", "stem"],
            ],
            "save": False,
            "prefix": "predicted",
        }
        context = zmq.Context()
        sock = context.socket(zmq.REQ)
        sock.setsockopt(zmq.LINGER, 0)

        try:
            sock.connect(f"tcp://{self.host}:{self.port}")
            sock.send(pickle.dumps(request))

            if not sock.poll(self.timeout * 1000):
                msg = f"murko ({self.host}:{self.port}) did not answer"
                raise MurkoUnavailable(msg)

            # The murko protocol is pickle both ways
            description = pickle.loads(sock.recv())["descriptions"][0]  # noqa: S301
        finally:
            sock.close()
            context.term()

        if description["present"] != 1:
            return None

        _present, row, col, height, width = description["aoi_bbox"]
        click_row, click_col = description["most_likely_click"]

        return {
            "click": (click_col, click_row),
            "box": (
                col - width / 2,
                row - height / 2,
                col + width / 2,
                row + height / 2,
            ),
        }
