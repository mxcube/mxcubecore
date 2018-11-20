"""
  Project: JLib

  Date       Author    Changes
  01.07.09   Gobbo     Created

  Copyright 2009 by European Molecular Biology Laboratory - Grenoble
"""
import gevent
import gevent.lock
import time
import socket
import sys


class TimeoutError(Exception):
    pass


class ProtocolError(Exception):
    pass


class SocketError(Exception):
    pass


STX = chr(2)
ETX = chr(3)
MAX_SIZE_STREAM_MSG = 500000


class PROTOCOL:
    DATAGRAM = 1
    STREAM = 2


class StandardClient:
    def __init__(self, server_ip, server_port, protocol, timeout, retries):
        self.server_ip = server_ip
        self.server_port = server_port
        self.timeout = timeout
        self.default_timeout = timeout
        self.retries = retries
        self.protocol = protocol
        self.error = None
        self.msg_received_event = gevent.event.Event()
        self._lock = gevent.lock.Semaphore()
        self.__msg_index__ = -1
        self.__sock__ = None
        self.__CONSTANT_LOCAL_PORT__ = True
        self._isConnected = False

    def __createSocket__(self):
        if self.protocol == PROTOCOL.DATAGRAM:
            self.__sock__ = socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM
            )  # , socket.IPPROTO_UDP)
            self.__sock__.settimeout(self.timeout)
        else:
            self.__sock__ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __closeSocket__(self):
        try:
            self.__sock__.close()
        except BaseException:
            pass
        self._isConnected = False
        self.__sock__ = None
        self.received_msg = None

    def connect(self):
        if self.protocol == PROTOCOL.DATAGRAM:
            return
        if self.__sock__ is None:
            self.__createSocket__()
        self.__sock__.connect((self.server_ip, self.server_port))
        self._isConnected = True
        self.error = None
        self.received_msg = None
        # thread.start_new_thread(self.recv_thread,())
        self.receiving_greenlet = gevent.spawn(self.recv_thread)

    def isConnected(self):
        if self.protocol == PROTOCOL.DATAGRAM:
            return False
        if self.__sock__ is None:
            return False
        return self._isConnected

    def disconnect(self):
        if self.isConnected():
            self.receiving_greenlet.kill()
        self.__closeSocket__()

    def __sendReceiveDatagramSingle__(self, cmd):
        try:
            if self.__CONSTANT_LOCAL_PORT__ is False or self.__sock__ is None:
                self.__createSocket__()
            msg_number = "%04d " % self.__msg_index__
            msg = msg_number + cmd
            try:
                self.__sock__.sendto(msg, (self.server_ip, self.server_port))
            except BaseException:
                raise SocketError("Socket error:" + str(sys.exc_info()[1]))
            received = False
            while received is False:
                try:
                    ret = self.__sock__.recv(4096)
                except socket.timeout:
                    raise TimeoutError("Timeout error:" + str(sys.exc_info()[1]))
                except BaseException:
                    raise SocketError("Socket error:" + str(sys.exc_info()[1]))
                if ret[0:5] == msg_number:
                    received = True
            ret = ret[5:]
        except SocketError:
            self.__closeSocket__()
            raise
        except BaseException:
            if self.__CONSTANT_LOCAL_PORT__ is False:
                self.__closeSocket__()
            raise
        if self.__CONSTANT_LOCAL_PORT__ is False:
            self.__closeSocket__()
        return ret

    def __sendReceiveDatagram__(self, cmd, timeout=-1):
        self.__msg_index__ = self.__msg_index__ + 1
        if self.__msg_index__ >= 10000:
            self.__msg_index__ = 1
        for i in range(0, self.retries):
            try:
                ret = self.__sendReceiveDatagramSingle__(cmd)
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

    def setTimeout(self, timeout):
        self.timeout = timeout
        if self.protocol == PROTOCOL.DATAGRAM:
            if self.__sock__ is not None:
                self.__sock__.settimeout(self.timeout)

    def restoreTimeout(self):
        self.setTimeout(self.default_timeout)

    def dispose(self):
        if self.protocol == PROTOCOL.DATAGRAM:
            if self.__CONSTANT_LOCAL_PORT__:
                self.__closeSocket__()
            else:
                pass
        else:
            self.disconnect()

    def onMessageReceived(self, msg):
        self.received_msg = msg
        self.msg_received_event.set()

    def recv_thread(self):
        try:
            self.onConnected()
        except BaseException:
            pass
        buffer = ""
        mReceivedSTX = False
        while True:
            ret = self.__sock__.recv(4096)
            if not ret:
                # connection reset by peer
                self.error = "Disconnected"
                self.__closeSocket__()
                break
            for b in ret:
                if b == STX:
                    buffer = ""
                    mReceivedSTX = True
                elif b == ETX:
                    if mReceivedSTX is True:
                        self.onMessageReceived(buffer)
                        mReceivedSTX = False
                        buffer = ""
                else:
                    if mReceivedSTX is True:
                        buffer = buffer + b

            if len(buffer) > MAX_SIZE_STREAM_MSG:
                mReceivedSTX = False
                buffer = ""
        try:
            self.onDisconnected()
        except BaseException:
            pass

    def __sendStream__(self, cmd):
        if not self.isConnected():
            self.connect()

        try:
            pack = STX + cmd + ETX
            self.__sock__.send(pack)
        except SocketError:
            self.disconnect()
            # raise SocketError,"Socket error:" + str(sys.exc_info()[1])

    def __sendReceiveStream__(self, cmd):
        self.error = None
        self.received_msg = None
        self.msg_received_event.clear()  # = gevent.event.Event()
        if not self.isConnected():
            self.connect()
        self.__sendStream__(cmd)

        with gevent.Timeout(self.timeout, TimeoutError):
            while self.received_msg is None:
                if self.error is not None:
                    raise SocketError("Socket error:" + str(self.error))
                self.msg_received_event.wait()
            return self.received_msg

    def sendReceive(self, cmd, timeout=-1):
        self._lock.acquire()
        try:
            if (timeout is None) or (timeout >= 0):
                self.setTimeout(timeout)
            if self.protocol == PROTOCOL.DATAGRAM:
                return self.__sendReceiveDatagram__(cmd)
            else:
                return self.__sendReceiveStream__(cmd)
        finally:
            try:
                if (timeout is None) or (timeout >= 0):
                    self.restoreTimeout()
            finally:
                self._lock.release()

    def send(self, cmd):
        if self.protocol == PROTOCOL.DATAGRAM:
            raise ProtocolError(
                "Protocol error: send command not support in datagram clients"
            )
        else:
            return self.__sendStream__(cmd)

    def onConnected(self):
        pass

    def onDisconnected(self):
        pass
