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

""" ProtocolError and StandardClient implementation"""
import sys
import socket
import gevent
import gevent.lock

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


class TimeoutError(Exception):
    """Protype"""


class ProtocolError(Exception):
    """Protype"""


class SocketError(Exception):
    """Protype"""


if sys.version_info > (3, 0):
    STX = 2  # b'\x02'
    ETX = 3  # b'\x03'

    def empty_buffer():
        """Empty buffer"""
        return b""

    _bytes = bytes

    encode = str.encode

else:
    STX = chr(2)
    ETX = chr(3)

    def empty_buffer():
        """Empty buffer"""
        return ""

    _bytes = str

    encode = str

MAX_SIZE_STREAM_MSG = 500000


class PROTOCOL:
    """Protocol"""

    DATAGRAM = 1
    STREAM = 2


class StandardClient:
    """Standard JLib client"""

    def __init__(self, server_ip, server_port, protocol, timeout, retries):
        self.server_ip = server_ip
        self.server_port = server_port
        self.timeout = timeout
        self.default_timeout = timeout
        self.retries = retries
        self.protocol = protocol
        self.error = None
        self.received_msg = None
        self.receiving_greenlet = None
        self.msg_received_event = gevent.event.Event()
        self._lock = gevent.lock.Semaphore()
        self.__msg_index__ = -1
        self.__sock = None
        self.__constant_local_port = True
        self._is_connected = False

    def __create_socket(self):
        """Create socket"""
        if self.protocol == PROTOCOL.DATAGRAM:
            self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.__sock.settimeout(self.timeout)
        else:
            self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __close_socket(self):
        """Close socket"""
        try:
            self.__sock.close()
        except BaseException:
            pass
        self._is_connected = False
        self.__sock = None
        self.received_msg = None

    def connect(self):
        """Socket connect"""
        if self.protocol == PROTOCOL.DATAGRAM:
            return
        if self.__sock is None:
            self.__create_socket()
        self.__sock.connect((self.server_ip, self.server_port))
        self._is_connected = True
        self.error = None
        self.received_msg = None
        self.receiving_greenlet = gevent.spawn(self.recv_thread)

    def is_connected(self):
        """Check if connected
        Returns:
            (bool): True if connected
        """
        if self.protocol == PROTOCOL.DATAGRAM:
            return False
        if self.__sock is None:
            return False
        return self._is_connected

    def disconnect(self):
        """Disconnect"""
        if self.is_connected():
            self.receiving_greenlet.kill()
        self.__close_socket()

    def __send_receive_datagram_single(self, cmd):
        """Send and receive single datagram.
        Args:
            cmd(str): Command
        Returns:
            (str): return message
        Raises:
            SocketError, TimeoutError
        """
        try:
            if self.__constant_local_port is False or self.__sock is None:
                self.__create_socket()
            msg_number = "%04d " % self.__msg_index__
            msg = msg_number + cmd
            try:
                self.__sock.sendto(encode(msg), (self.server_ip, self.server_port))
            except:
                raise SocketError("Socket error:" + str(sys.exc_info()[1]))
            received = False
            while received is False:
                try:
                    ret = self.__sock.recv(4096).decode()
                except socket.timeout:
                    raise TimeoutError("Timeout error:" + str(sys.exc_info()[1]))
                except BaseException:
                    raise SocketError("Socket error:" + str(sys.exc_info()[1]))
                if ret[0:5] == msg_number:
                    received = True
            ret = ret[5:]
        except SocketError:
            self.__close_socket()
            raise
        except BaseException:
            if self.__constant_local_port is False:
                self.__close_socket()
            raise
        if self.__constant_local_port is False:
            self.__close_socket()
        return ret

    def __send_receive_datagram(self, cmd):
        """Send/receive datagram.
        Args:
            (str): command
        Returns:
            (str): datagram
        Raises:
            TimeoutError, ProtocolError
        """
        self.__msg_index__ = self.__msg_index__ + 1
        if self.__msg_index__ >= 10000:
            self.__msg_index__ = 1
        for i in range(0, self.retries):
            try:
                ret = self.__send_receive_datagram_single(encode(cmd))
                return ret
            except TimeoutError:
                if i >= self.retries - 1:
                    raise
            except ProtocolError:
                if i >= self.retries - 1:
                    raise
            except SocketError:
                if i >= self.retries - 1:
                    raise
            except BaseException:
                raise

    def set_timeout(self, timeout):
        """Set the socket timeout.
        Args:
            timeout(float): Timeout value
        """
        self.timeout = timeout
        if self.protocol == PROTOCOL.DATAGRAM:
            if self.__sock is not None:
                self.__sock.settimeout(self.timeout)

    def restore_timeout(self):
        """Restore the default timeout"""
        self.set_timeout(self.default_timeout)

    def dispose(self):
        """Disconnect or close socket"""
        if self.protocol == PROTOCOL.DATAGRAM:
            if self.__constant_local_port:
                self.__close_socket()
            else:
                pass
        else:
            self.disconnect()

    def on_message_received(self, msg):
        """Actions
        Args:
            msg(str): Message
        """
        self.received_msg = msg
        self.msg_received_event.set()

    def recv_thread(self):
        """Receive thread"""
        try:
            self.on_connected()
        except BaseException:
            pass
        buffer = empty_buffer()
        mReceivedSTX = False
        while True:
            ret = self.__sock.recv(4096)
            if not ret:
                # connection reset by peer
                self.error = "Disconnected"
                self.__close_socket()
                break
            for b in ret:
                if b == STX:
                    buffer = empty_buffer()
                    mReceivedSTX = True
                elif b == ETX:
                    if mReceivedSTX:
                        try:
                            # Unicode decoding exception catching,
                            # consider errors='ignore'
                            buffer_utf8 = buffer.decode()
                        except UnicodeDecodeError as e:
                            # Syntax not allowed in Python 2
                            # raise ProtocolError from e
                            raise ProtocolError(
                                "UnicodeDecodeError: %s" % sys.exc_info()
                            )
                        self.on_message_received(buffer_utf8)
                        mReceivedSTX = False
                        buffer = empty_buffer()
                else:
                    if mReceivedSTX:
                        buffer += _bytes([b])

            if len(buffer) > MAX_SIZE_STREAM_MSG:
                mReceivedSTX = False
                buffer = empty_buffer()
        try:
            self.on_disconnected()
        except BaseException:
            pass

    def __send_stream(self, cmd):
        """Send a command.
        Args:
            cmd(str): command
        """
        if not self.is_connected():
            self.connect()
        try:
            pack = _bytes([STX]) + encode(cmd) + _bytes([ETX])
            self.__sock.send(pack)
        except SocketError:
            self.disconnect()

    def __send_receive_stream(self, cmd):
        """Send/receive event.
        Args:
            cmd(str): command
        Returns:
            (str): reply form the socket
        """
        self.error = None
        self.received_msg = None
        self.msg_received_event.clear()  # = gevent.event.Event()
        if not self.is_connected():
            self.connect()
        self.__send_stream(cmd)

        with gevent.Timeout(self.timeout, TimeoutError):
            while self.received_msg is None:
                if self.error is not None:
                    raise SocketError("Socket error:" + str(self.error))
                self.msg_received_event.wait()
            return self.received_msg

    def send_receive(self, cmd, timeout=-1):
        """Send/receive command, locking the socket.
        Args:
            cmd(str): command
        Returns:
            (str): reply form the socket
        """
        self._lock.acquire()
        try:
            if (timeout is None) or (timeout >= 0):
                self.set_timeout(timeout)
            if self.protocol == PROTOCOL.DATAGRAM:
                return self.__send_receive_datagram(cmd)
            return self.__send_receive_stream(cmd)
        finally:
            try:
                if (timeout is None) or (timeout >= 0):
                    self.restore_timeout()
            finally:
                self._lock.release()

    def send(self, cmd):
        """Send command.
        Args:
            cmd(str): command
        Returns:
            (str): reply form the socket
        Raises:
            ProtocolError
        """
        if self.protocol == PROTOCOL.DATAGRAM:
            raise ProtocolError(
                "Protocol error: send command not support in datagram clients"
            )
        return self.__send_stream(cmd)

    def on_connected(self):
        """On connect"""

    def on_disconnected(self):
        """On disconnect"""
