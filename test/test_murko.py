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
"""The murko client, against a fake zmq module standing for the server."""

import pickle
import sys
import types

import pytest

from mxcubecore.HardwareObjects.Murko import MurkoUnavailable


class FakeSocket:
    def __init__(self, server):
        self.server = server

    def setsockopt(self, *args):
        pass

    def connect(self, address):
        self.server.address = address

    def send(self, data):
        self.server.request = pickle.loads(data)  # noqa: S301

    def poll(self, timeout):
        self.server.poll_timeout = timeout
        return self.server.reply is not None

    def recv(self):
        return pickle.dumps(self.server.reply)

    def close(self):
        self.server.closed = True


@pytest.fixture
def server(monkeypatch):
    """A murko server: set its reply, None when it does not answer."""
    server = types.SimpleNamespace(reply=None, closed=False)
    zmq = types.ModuleType("zmq.green")
    zmq.REQ, zmq.LINGER = 3, 17
    zmq.Context = lambda: types.SimpleNamespace(
        socket=lambda kind: FakeSocket(server), term=lambda: None
    )
    package = types.ModuleType("zmq")
    package.green = zmq
    monkeypatch.setitem(sys.modules, "zmq", package)
    monkeypatch.setitem(sys.modules, "zmq.green", zmq)
    return server


@pytest.fixture
def murko(beamline):
    return beamline.get_object_by_role("murko")


def _reply(present=1):
    # aoi_bbox: present, centre row, centre column, height, width
    return {
        "descriptions": [
            {
                "present": present,
                "aoi_bbox": (1, 0.5, 0.4, 0.2, 0.3),
                "most_likely_click": (0.45, 0.35),
            }
        ]
    }


def test_configuration(murko):
    assert (murko.config.host, murko.config.port) == ("localhost", 8901)
    assert murko.config.timeout == 30


def test_loop_found(murko, server):
    server.reply = _reply()

    prediction = murko.predict("image")

    assert server.address == "tcp://localhost:8901"
    assert server.request["to_predict"] == "image"
    assert server.poll_timeout == 30000
    assert prediction["click"] == (0.35, 0.45)
    assert prediction["box"] == pytest.approx((0.25, 0.4, 0.55, 0.6))
    assert server.closed


def test_no_loop(murko, server):
    server.reply = _reply(present=0)

    assert murko.predict("image") is None


def test_no_answer_aborts(murko, server):
    with pytest.raises(MurkoUnavailable):
        murko.predict("image")

    assert MurkoUnavailable.abort_queue
    assert server.closed


def test_not_available(murko, monkeypatch):
    def refuse(*args, **kwargs):
        raise ConnectionRefusedError

    monkeypatch.setattr("socket.create_connection", refuse)

    assert not murko.is_available()
