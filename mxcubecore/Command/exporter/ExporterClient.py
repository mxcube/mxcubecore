# -*- coding: utf-8 -*-
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
#  You should have received a copy of the GNU General Lesser Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

"""Exporter Client implementation"""

import logging

from .StandardClient import (
    ProtocolError,
    StandardClient,
)

__copyright__ = """ Copyright © 2019 by the MXCuBE collaboration """
__license__ = "LGPLv3+"

CMD_SYNC_CALL = "EXEC"
CMD_ASNC_CALL = "ASNC"
CMD_METHOD_LIST = "LIST"
CMD_PROPERTY_READ = "READ"
CMD_PROPERTY_WRITE = "WRTE"
CMD_PROPERTY_LIST = "PLST"
CMD_NAME = "NAME"
RET_ERR = "ERR:"
RET_OK = "RET:"
RET_NULL = "NULL"
EVENT = "EVT:"

PARAMETER_SEPARATOR = "\t"
ARRAY_SEPARATOR = ""  # 0x001F


class ExporterClient(StandardClient):
    """ExporterClient class"""

    def on_message_received(self, msg):
        """Act if the message is an event, pass to StandardClient otherwise.
        Args:
            msg(str): The message.
        """
        if msg[:4] == EVENT:
            try:
                tokens = msg[4:].split(PARAMETER_SEPARATOR)
                self.on_event(tokens[0], tokens[1], int(tokens[2]))
            except Exception:
                pass
        else:
            StandardClient.on_message_received(self, msg)

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

    def execute(self, method, pars=None, timeout=-1):
        """Execute a command synchronous.
        Args:
            method(str): Method name
            pars(str): parameters
            timeout(float): Timeout [s]
        """

        # runScript returns results in a different way than any other
        # comand, fix on MD side ?
        if method == "runScript" and pars is not None:
            pars = pars[0].split(",")

        cmd = "{} {} ".format(CMD_SYNC_CALL, method)

        if pars is not None:
            if isinstance(pars, (list, tuple)):
                for par in pars:
                    if isinstance(par, (list, tuple)):
                        par = self.create_array_parameter(par)
                    cmd += str(par) + PARAMETER_SEPARATOR
            else:
                cmd += str(pars)

        ret = self.send_receive(cmd, timeout)
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
        if ret[:4] == RET_ERR:
            msg = f"{self.get_server_object_name()} : {str(ret[4:])}"
            logging.getLogger("HWR").error(msg)
            raise Exception(ret[4:])
        if ret == RET_NULL:
            return None
        if ret[:4] == RET_OK:
            return ret[4:]
        raise ProtocolError

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
