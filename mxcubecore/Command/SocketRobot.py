from mxcubecore.CommandContainer import CommandObject, ChannelObject
import logging
import gevent
from gevent.queue import Queue
from mxcubecore.CommandContainer import CommandObject, ChannelObject
import socket
import gevent.lock
import gevent.event
import sys
# from exporter.StandardClient import StandardClient, ProtocolError,SocketError     #不能家，会报错

class SocketError(Exception):
    """"""


CLIENTS = {}

class PROTOCOL:
    """Protocol"""

    DATAGRAM = 1
    STREAM = 2

encode = str.encode

_bytes = bytes


ETX = 0     # b'\x00'

MAX_SIZE_STREAM_MSG = 500000
RET_NULL = "NULL"

PARAMETER_SEPARATOR = " "

#等待机械手回消息的timeout(与 和机械手创建socket连接时没有连上超时断开的timeout不一样)
Timeout_recv = 180

def empty_buffer():
    """Empty buffer"""
    return b""


class StandardClientRobot:
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
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('set the timeout for socket connection',self.timeout)
        self.__sock.settimeout(self.timeout)
    def __close_socket(self):
        """Close socket"""
        try:
            self.__sock.close()
        except Exception:
            pass
        self._is_connected = False
        self.__sock = None
        self.received_msg = None

    def connect(self):
        """Socket connect"""
        if self.protocol == PROTOCOL.DATAGRAM:
            return
        print("self.__sock:",self.__sock)
        if self.__sock is None:
            self.__create_socket()
            print("socket object after creating the socket：",self.__sock)
        print("self.__sock.connect function start to run")
        #添加
        try:
            self.__sock.connect((self.server_ip, self.server_port))
        except socket.timeout: #如果没插网线，是不会有这个timeout报错的，会立刻直接报错 Error: [Errno 101] Network is unreachable，因此也不会返回False
            print("connection timeout")
            return False
        else:
            print("self.__sock.connect function completed")
            #重新设置等待机械手回信息的timeout
            self.__sock.settimeout(Timeout_recv)
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
            except Exception:
                raise SocketError("Socket error:" + str(sys.exc_info()[1]))
            received = False
            while received is False:
                try:
                    ret = self.__sock.recv(4096).decode()
                except socket.timeout:
                    raise TimeoutError("Timeout error:" + str(sys.exc_info()[1]))
                except Exception:
                    raise SocketError("Socket error:" + str(sys.exc_info()[1]))
                if ret[0:5] == msg_number:
                    received = True
            ret = ret[5:]
        except SocketError:
            self.__close_socket()
            raise
        except Exception:
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
            except Exception:
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
        except Exception:
            pass
        buffer = empty_buffer()
        mReceivedSTX = True
        while True:
            logging.getLogger("HWR").info("robot: start to wait the return message from camerman")
            ret = self.__sock.recv(512)
            if not ret:
                # connection reset by peer
                self.error = "Disconnected"
                self.__close_socket()
                break
            for b in ret:

                if b == ETX:
                    if mReceivedSTX:
                        try:
                            # Unicode decoding exception catching,
                            # consider errors='ignore'
                            buffer_utf8 = buffer.decode()
                        except UnicodeDecodeError as e:
                            # Syntax not allowed in Python 2
                            # raise ProtocolError from e
                            raise ProtocolError(
                                "UnicodeDecodeError: %s" % (sys.exc_info(),)
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
        except Exception:
            pass
    def __send_stream(self, cmd):
        """Send a command.
        Args:
            cmd(str): command
        """
        print(' into __send_stream function')
        if not self.is_connected():
            self.connect()
        try:
            print("get into try")
            print(cmd)
            pack = encode(cmd) + _bytes([ETX])
            print(pack)
            self.__sock.send(pack)
        except SocketError:
            self.disconnect()
##################################################改过##########################################


    def __send_receive_stream(self, cmd):
        """Send/receive event.
        Args:
            cmd(str): command
        Returns:
            (str): reply form the socket
        """
        print("step into __send_receive_stream function")
        self.error = None
        self.received_msg = None
        self.msg_received_event.clear()  # = gevent.event.Event()
        if not self.is_connected():
            print("start the socket connection")
            self.connect()
            # 尝试连接之后还是没有连接成功，返回
            if not self.is_connected():
                return False

        print("already is_connected")
        self.__send_stream(cmd)
        with gevent.Timeout(100, TimeoutError):
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



class SocketRobotClient(StandardClientRobot):
    """SocketRobotClient class"""
    def on_message_received(self, msg):
        """Act if the message is an event, pass to StandardClient otherwise.
        Args:
            msg(str): The message.
        """

        logging.getLogger("HWR").info("robot: have received the return message from camerman")
        StandardClientRobot.on_message_received(self, msg)

    def get_method_list(self):
        """Get the list of the methods
        Returns:
            (list): List of strings (the methods)
        """
        cmd = CMD_METHOD_LIST
        ret = self.send_receive(cmd)
        ret = self.__process_return(ret)
        if ret is None:
            return None
        ret = ret.split(PARAMETER_SEPARATOR)
        if len(ret) > 1:
            if ret[-1] == "":
                ret = ret[0:-1]
        return ret

    def get_property_list(self):
        """Get the list of the properties.
        Returns:
            (list): List of strings (the properties)
        """
        cmd = CMD_PROPERTY_LIST
        ret = self.send_receive(cmd)
        ret = self.__process_return(ret)
        if ret is None:
            return None
        ret = ret.split(PARAMETER_SEPARATOR)
        if len(ret) > 1:
            if ret[-1] == "":
                ret = ret[0:-1]
        return ret

    def get_server_object_name(self):
        """Get the server object name
        Returns:
            (str): The name.
        """
        cmd = CMD_NAME
        ret = self.send_receive(cmd)
        return self.__process_return(ret)


    def execute(self, method, pars=None, timeout=-1,**kwargs):
        """Execute a command synchronous.
        Args:
            method(str): Method name
            pars(str): parameters
            timeout(float): Timeout [s]
        """
        # print("进入二重execute函数")
        cmd = "{} ".format(method)    # CMD_SYNC_CALL = "EXEC"

        if kwargs is not None:
            if cmd == "Mount " or cmd =="Dismount ":
                args1 = 'Dewar=1'
                args2 = 'Magazine='+str(kwargs['magazine'])
                args3 = 'Position='+str(kwargs['position'])
                args = [args1,args2,args3]
                for i in range(3):
                    cmd += args[i] + PARAMETER_SEPARATOR
            elif cmd== "Exchange ":
                args1 = 'OldDewar=1'
                args2 = 'OldMagazine='+str(kwargs['oldMagazine'])
                args3 = 'OldPosition='+str(kwargs['oldPosition'])
                args4 = 'NewDewar=1'
                args5 = 'NewMagazine='+str(kwargs['newMagazine'])
                args6 = 'NewPosition='+str(kwargs['newPosition'])
                args = [args1,args2,args3,args4,args5,args6]
                for i in range(6):
                    cmd += args[i] + PARAMETER_SEPARATOR
            elif cmd =="Abort ":
                self._lock.release()
                print("command: abort，run self._lock.release()")
        print("the default timeout of current command:",timeout)
        ret = self.send_receive(cmd, timeout)
        print("the return of execute function:",ret,type(ret))
        # ret == False means the socket failed to connect
        print("the return value of send_receice function: (False means connection failed)",ret)
        if ret==False:
            return False
        return self.__process_return(ret)

    def __process_return(self, ret):
        """Analyse the return message.
        Args:
            ret(str): Returned message
        Returns:
            (str): The stripped message or None
        Raises:
            ProtocolError
        """

        ret_list = ret.split(' ')
        index_ErrorCode = ret_list.index('ErrorCode')
        ErrorCode = ret_list[index_ErrorCode+2]
        print("Error:")
        print(ErrorCode,type(ErrorCode),ErrorCode!='0')
        if ErrorCode != '0':
            msg = "Robot: {}".format(str(ErrorCode))
            logging.getLogger("HWR").error(msg)
            self.disconnect()
            raise Exception(ErrorCode)
        elif ret == RET_NULL:
            return None
        else:
            return ret_list




    def execute_async(self, method, pars=None):
        """Execute command asynchronous.
        Args:
            method(str): Method name
            pars(str): parameters
        """
        cmd = "{} {} ".format(CMD_ASNC_CALL, method)
        if pars is not None:
            for par in pars:
                cmd += str(par) + PARAMETER_SEPARATOR
        return self.send(cmd)

    def write_property(self, prop, value, timeout=-1):
        """Write property synchronous.
        Args:
            prop(str): property name
            value: sample, list or tuple
        """
        if isinstance(value, (list, tuple)):
            value = self.create_array_parameter(value)
        cmd = "{} {} {}".format(CMD_PROPERTY_WRITE, prop, str(value))
        ret = self.send_receive(cmd, timeout)
        return self.__process_return(ret)

    def read_property(self, prop, timeout=-1):
        """Read a property
        Args:
            prop(str): property name
        Returns:
            (str): reply from the process.
        """
        cmd = "{} {}".format(CMD_PROPERTY_READ, prop)
        ret = self.send_receive(cmd, timeout)
        process_return = None
        try:
            process_return = self.__process_return(ret)
        except Exception:
            pass
        return process_return

    def read_property_as_string_array(self, prop):
        """Read a propery and convert the return value to list of strings.
        Args:
            prop(str): property name
        Returns:
            (list): List of strings
        """
        ret = self.read_property(prop)
        return self.parse_array(ret)

    def parse_array(self, value):
        """Parse to list
        Args:
            value(str): input string
        Returns:
            (list): List of strings
        """
        value = str(value)
        if value.startswith(ARRAY_SEPARATOR) is False:
            return None
        if value == ARRAY_SEPARATOR:
            return []
        value = value.lstrip(ARRAY_SEPARATOR).rstrip(ARRAY_SEPARATOR)
        return value.split(ARRAY_SEPARATOR)

    def create_array_parameter(self, value):
        """Create a string to send.
        Args:
            value: simple, tuple ot list
        Returns:
            (str): formated string
        """
        ret = ARRAY_SEPARATOR
        if value is not None:
            if isinstance(value, (list, tuple)):
                for item in value:
                    ret += str(item) + ARRAY_SEPARATOR
            else:
                ret += str(value)
        return ret

    def on_event(self, name, value, timestamp):
        """Action"""







class SocketRobot(SocketRobotClient, object):
    """Exporter class"""

    STATE_EVENT = "State"
    STATUS_EVENT = "Status"
    VALUE_EVENT = "Value"
    POSITION_EVENT = "Position"
    MOTOR_STATES_EVENT = "MotorStates"

    STATE_READY = "Ready"
    STATE_INITIALIZING = "Initializing"
    STATE_STARTING = "Starting"
    STATE_RUNNING = "Running"
    STATE_MOVING = "Moving"
    STATE_CLOSING = "Closing"
    STATE_REMOTE = "Remote"
    STATE_STOPPED = "Stopped"
    STATE_COMMUNICATION_ERROR = "Communication Error"
    STATE_INVALID = "Invalid"
    STATE_OFFLINE = "Offline"
    STATE_ALARM = "Alarm"
    STATE_FAULT = "Fault"
    STATE_UNKNOWN = "Unknown"

    def __init__(self, address, port, timeout=10, retries=1):
        super(SocketRobot, self).__init__(address, port, PROTOCOL.STREAM, timeout, retries)

        self.started = False
        self.callbacks = {}
        self.events_queue = Queue()
        self.events_processing_task = None
    def start(self):
        """Start"""

    def stop(self):
        """Stop"""
        self.disconnect()
    def execute(self, *args, **kwargs):
        """Execute"""
        # print("进入execute函数")
        ret = SocketRobotClient.execute(self, *args, **kwargs)
        self.disconnect()
        return ret

    def get_state(self):
        """Read the state"""
        return self.execute("getState")

    def read_property(self, *args, **kwargs):
        """Read a property"""
        ret = ExporterClient.ExporterClient.read_property(self, *args, **kwargs)
        return self._to_python_value(ret)

    def reconnect(self):
        """Reconnect"""
        return

    def on_disconnected(self):
        """Actions on disconnect"""

    def register(self, name, cb):
        """Register to a callback"""
        if callable(cb):
            self.callbacks.setdefault(name, []).append(cb)
        if not self.events_processing_task:
            self.events_processing_task = gevent.spawn(self.process_events_from_queue)

    def _to_python_value(self, value):
        """Convert exporter value to python one
        Args:
            value (str): String from the exporter
        """
        if value is None:
            return value

        if "\x1f" in value:
            value = self.parse_array(value)
            try:
                value = list(map(int, value))
            except (TypeError, ValueError):
                try:
                    value = list(map(float, value))
                except (TypeError, ValueError):
                    pass
        else:
            if value == "false":
                value = False
            elif value == "true":
                value = True
            else:
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    try:
                        value = float(value)
                    except (TypeError, ValueError):
                        pass
        return value

    def on_event(self, name, value, timestamp):
        """Put the event in the queue
        Args:
            name: Name
            value: Value
            timestamp: Timestamp
        """
        self.events_queue.put((name, value))

    def process_events_from_queue(self):
        """Process events from the queue"""
        while True:
            try:
                name, value = self.events_queue.get()
            except Exception:
                return

            for cb in self.callbacks.get(name, []):
                try:
                    cb(self._to_python_value(value))
                except Exception:
                    msg = "Exception while executing callback {} for event {}".format(
                        cb, name
                    )
                    logging.exception(msg)
                    continue















def start_socket(address, port, timeout=10, retries=1):
    """Start the exporter"""
    # 这里的timeout好像没有用？
    global CLIENTS
    if (address, port) not in CLIENTS:
        client = SocketRobot(address, port, timeout)
        # print("初始化时的client:",client,timeout,address)
        CLIENTS[(address, port)] = client
        client.start()
        return client
    return CLIENTS[(address, port)]



class SocketRobotCommand(CommandObject):
    def __init__(
        self, name, command, username=None, address=None, port=None, timeout=5, **kwargs
    ):
        CommandObject.__init__(self, name, username, **kwargs)
        self.command = command
        self.__socket = start_socket(address, port, timeout)
        msg = "Attaching SocketRobot command: {} {}".format(address, name)
        logging.getLogger("HWR").debug(msg)


    def __call__(self, *args, **kwargs):
        self.emit("commandBeginWaitReply", (str(self.name()),))
        print("get in __call__ function")
        try:
            ret = self.__socket.execute(self.command, args, kwargs.get("timeout", -1),**kwargs)  #.get(),如果timeout没有设置，输出默认值-1
            
        except Exception:
            self.emit("commandFailed", (-1, self.name()))
            raise
        else:
            self.emit("commandReplyArrived", (ret, str(self.name())))
            print("the ret value returned from __call__():",ret)
            return ret

    def abort(self):
        """Abort"""

    def get_state(self):
        """FRead the state
        Returns:
            (str): State
        """
        return self.__exporter.get_state()

    def is_connected(self):
        """Check if connected.
        Returns:
            (bool): True if connected
        """
        return self.__exporter.is_connected()
