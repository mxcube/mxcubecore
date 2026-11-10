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
"""Client of a murko server, loop and crystal segmentation of sample images.

murko: https://github.com/MartinSavko/murko. The server answers zmq REQ
requests; the client needs pyzmq, which is only imported when it is used.

Example yaml configuration:

    class: mxcubecore.HardwareObjects.Murko.Murko
    configuration:
      host: murko-server
      port: 8901
      timeout: 30
"""

import pickle
import socket

from mxcubecore.BaseHardwareObjects import ConfiguredObject, HardwareObject

__copyright__ = """ Copyright © by MXCuBE Collaboration """
__license__ = "LGPLv3+"


class MurkoUnavailable(RuntimeError):
    """Murko cannot be reached, the queue should not go on without it."""

    abort_queue = True


class Murko(HardwareObject):
    """Asks murko where the loop is in an image."""

    class HOConfig(ConfiguredObject.HOConfig):
        host: str = "localhost"
        port: int = 8901
        # Seconds to wait for an answer
        timeout: float = 30

    def is_available(self) -> bool:
        """True when the murko server accepts connections."""
        try:
            socket.create_connection(
                (self.config.host, self.config.port), timeout=2
            ).close()
        except OSError:
            return False
        return True

    def predict(self, image) -> dict | None:
        """Find the loop in image.

        Args:
            image: the image, as an array or JPEG bytes.

        Returns:
            None when no loop is seen, otherwise "click" (x, y), the most
            likely centring point, and "box" (x1, y1, x2, y2), the loop, in
            fractions of the image size.

        Raises:
            MurkoUnavailable: when murko does not answer within the timeout.
        """
        import zmq.green as zmq

        host, port = self.config.host, self.config.port
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
            sock.connect(f"tcp://{host}:{port}")
            sock.send(pickle.dumps(request))

            if not sock.poll(self.config.timeout * 1000):
                msg = f"murko ({host}:{port}) did not answer"
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
