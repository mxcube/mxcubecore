"""
  Project: JLib

  Date       Author    Changes
  01.07.09   Gobbo     Created

  Copyright 2009 by European Molecular Biology Laboratory - Grenoble
"""

import logging

from StandardClient import *

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
    def onMessageReceived(self, msg):
        if msg[:4] == "EVT:":
            try:
                evtstr = msg[4:]
                tokens = evtstr.split(PARAMETER_SEPARATOR)
                self.onEvent(tokens[0], tokens[1], long(tokens[2]))
            except BaseException:
                # print "Error processing event: " + str(sys.exc_info()[1])
                pass
        else:
            StandardClient.onMessageReceived(self, msg)

    def getMethodList(self):
        cmd = CMD_METHOD_LIST
        ret = self.sendReceive(cmd)
        ret = self.__processReturn(ret)
        if ret is None:
            return None
        ret = ret.split(PARAMETER_SEPARATOR)
        if len(ret) > 1:
            if ret[-1] == "":
                ret = ret[0:-1]
        return ret

    def getPropertyList(self):
        cmd = CMD_PROPERTY_LIST
        ret = self.sendReceive(cmd)
        ret = self.__processReturn(ret)
        if ret is None:
            return None
        ret = ret.split(PARAMETER_SEPARATOR)
        if len(ret) > 1:
            if ret[-1] == "":
                ret = ret[0:-1]
        return ret

    def getServerObjectName(self):
        cmd = CMD_NAME
        ret = self.sendReceive(cmd)
        return self.__processReturn(ret)

    def execute(self, method, pars=None, timeout=-1):
        cmd = CMD_SYNC_CALL + " " + method + " "
        if pars is not None:
            for par in pars:
                if isinstance(par, list) or isinstance(par, tuple):
                    par = self.createArrayParameter(par)
                cmd += str(par) + PARAMETER_SEPARATOR
        ret = self.sendReceive(cmd, timeout)
        return self.__processReturn(ret)

    def __processReturn(self, ret):
        if ret[:4] == RET_ERR:
            logging.getLogger("user_level_log").error(
                "Diffractometer: %s" % str(ret[4:])
            )
            raise Exception(ret[4:])
        elif ret == RET_NULL:
            return None
        elif ret[:4] == RET_OK:
            return ret[4:]
        else:
            raise ProtocolError

    def executeAsync(self, method, pars=None):
        cmd = CMD_ASNC_CALL + " " + method + " "
        if pars is not None:
            for par in pars:
                cmd += str(par) + PARAMETER_SEPARATOR
        return self.send(cmd)

    def writeProperty(self, property, value, timeout=-1):
        if isinstance(value, list) or isinstance(value, tuple):
            value = self.createArrayParameter(value)
        cmd = CMD_PROPERTY_WRITE + " " + property + " " + str(value)
        ret = self.sendReceive(cmd, timeout)
        return self.__processReturn(ret)

    def readProperty(self, property, timeout=-1):
        cmd = CMD_PROPERTY_READ + " " + property
        ret = self.sendReceive(cmd, timeout)
        process_return = None
        try:
            process_return = self.__processReturn(ret)
        except BaseException:
            pass
        return process_return

    def readPropertyAsString(self, property):
        return self.readProperty(property)

    def readPropertyAsFloat(self, property):
        return float(self.readProperty(property))

    def readPropertyAsInt(self, property):
        return int(self.readProperty(property))

    def readPropertyAsBoolean(self, property):
        if self.readProperty(property) == "true":
            return True
        return False

    def readPropertyAsStringArray(self, property):
        ret = self.readProperty(property)
        return self.parseArray(ret)

    def parseArray(self, value):
        value = str(value)
        if value.startswith(ARRAY_SEPARATOR) is False:
            return None
        if value == ARRAY_SEPARATOR:
            return []
        value = value.lstrip(ARRAY_SEPARATOR).rstrip(ARRAY_SEPARATOR)
        return value.split(ARRAY_SEPARATOR)

    def createArrayParameter(self, value):
        ret = "" + ARRAY_SEPARATOR
        if value is not None:
            if isinstance(value, list) or isinstance(value, tuple):
                for item in value:
                    ret = ret + str(item)
                    ret = ret + ARRAY_SEPARATOR
            else:
                ret = ret + str(value)
        return ret

    def onEvent(self, name, value, timestamp):
        pass
