from HardwareRepository import HardwareRepository

import logging
import gevent

from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository.Command.Tango import TangoCommand

from PyTango import DeviceProxy

from PyQt4.QtGui import QApplication

# from qt import qApp

import numpy
from HardwareRepository.HardwareObjects.abstract.AbstractMotor import MotorStates


class TangoDCMotor(Device):

    MOVESTARTED = 0
    NOTINITIALIZED = 0
    UNUSABLE = 0
    READY = 2
    MOVING = 4
    ONLIMIT = 1

    stateDict = {
        "UNKNOWN": 0,
        "OFF": 0,
        "ALARM": 1,
        "FAULT": 1,
        "STANDBY": 2,
        "RUNNING": 4,
        "MOVING": 4,
        "ON": 2,
    }

    def __init__(self, name):

        # State values as expected by Motor bricks

        Device.__init__(self, name)
        self.GUIstep = 0.1
        self.motor_states = MotorStates()

    def _init(self):
        self.positionValue = 0.0
        self.stateValue = "UNKNOWN"

        threshold = self.getProperty("threshold")
        self.threshold = (
            0.0018
        )  # default value. change it with property threshold in xml

        self.old_value = 0.0
        self.tangoname = self.getProperty("tangoname")
        self.motor_name = self.getProperty("motor_name")
        self.ho = DeviceProxy(self.tangoname)

        try:
            self.dataType = self.getProperty("datatype")
            if self.dataType is None:
                self.dataType = "float"
        except BaseException:
            self.dataType = "float"

        if threshold is not None:
            try:
                self.threshold = float(threshold)
            except BaseException:
                pass

        self.setIsReady(True)
        try:
            self.limitsCommand = self.getCommandObject("limits")
        except KeyError:
            self.limitsCommand = None
        self.positionChan = self.getChannelObject(
            "position"
        )  # utile seulement si positionchan n'est pas defini dans le code
        self.stateChan = self.getChannelObject(
            "state"
        )  # utile seulement si statechan n'est pas defini dans le code

        self.positionChan.connectSignal("update", self.positionChanged)
        self.stateChan.connectSignal("update", self.motorStateChanged)

    def positionChanged(self, value):
        self.positionValue = value
        if abs(float(value) - self.old_value) > self.threshold:
            try:
                # logging.getLogger("HWR").error("%s: TangoDCMotor new position  , %s", self.name(), value)
                self.emit("positionChanged", (value,))
                self.old_value = value
            except BaseException:
                logging.getLogger("HWR").error(
                    "%s: TangoDCMotor not responding, %s", self.name(), ""
                )
                self.old_value = value

    def is_ready(self):
        return self.isReady()

    def isReady(self):
        return self.stateValue == "STANDBY"

    def connectNotify(self, signal):
        if signal == "hardwareObjectName,stateChanged":
            self.motorStateChanged(TangoDCMotor.stateDict[self.stateValue])
        elif signal == "limitsChanged":
            self.motorLimitsChanged()
        elif signal == "positionChanged":
            self.motorPositionChanged(self.positionValue)
        self.setIsReady(True)

    def motorState(self):
        return TangoDCMotor.stateDict[self.stateValue]

    def motorStateChanged(self, state):
        self.stateValue = str(state)
        self.setIsReady(True)
        logging.info("motor state changed. it is %s " % self.stateValue)
        self.emit("stateChanged", (TangoDCMotor.stateDict[self.stateValue],))

    def get_state(self):
        return self.getState()

    def getState(self):
        # state = self.stateValue
        return TangoDCMotor.stateDict[self.stateValue]

    def getLimits(self):
        try:
            logging.getLogger("HWR").info(
                "TangoDCMotor.getLimits: trying to get limits for motor_name %s "
                % (self.motor_name)
            )
            limits = self.ho.getMotorLimits(
                self.motor_name
            )  # limitsCommand() # self.ho.getMotorLimits(self.motor_name)
            logging.getLogger("HWR").info(
                "TangoDCMotor.getLimits: Getting limits for %s -- %s "
                % (self.motor_name, str(limits))
            )
            if numpy.inf in limits:
                limits = numpy.array([-10000, 10000])
        except BaseException:
            # import traceback
            # logging.getLogger("HWR").info("TangoDCMotor.getLimits: Cannot get limits for %s.\nException %s " % (self.motor_name, traceback.print_exc()))
            if self.motor_name in [
                "detector_distance",
                "detector_horizontal",
                "detector_vertical",
            ]:
                info = self.positionChan.getInfo()
                limits = [float(info.min_value), float(info.max_value)]
            # if self.motor_name == 'detector_ts':
            # limits = [96, 1100]
            # elif self.motor_name == 'detector_tx':
            # limits =
            elif self.motor_name == "exposure":
                limits = [float(self.min_value), float(self.max_value)]

        if limits is None:
            try:
                limits = self.getProperty("min"), self.getProperty("max")
                logging.getLogger("HWR").info(
                    "TangoDCMotor.getLimits: %.4f ***** %.4f" % limits
                )
                limits = numpy.array(limits)
            except BaseException:
                # logging.getLogger("HWR").info("TangoDCMotor.getLimits: Cannot get limits for %s" % self.name())
                limits = None
        return limits

    def motorLimitsChanged(self):
        self.emit("limitsChanged", (self.getLimits(),))

    def motorIsMoving(self):
        return self.stateValue == "RUNNING" or self.stateValue == "MOVING"

    def motorMoveDone(self, channelValue):
        if self.stateValue == "STANDBY":
            self.emit("moveDone", (self.tangoname, "tango"))

    def motorPositionChanged(self, absolutePosition):
        self.emit("positionChanged", (absolutePosition,))

    def syncQuestionAnswer(self, specSteps, controllerSteps):
        return (
            "0"
        )  # This is only for spec motors. 0 means do not change anything on sync

    def getRealPosition(self):
        return self.positionChan.getValue()

    def get_position(self):
        return self.getRealPosition()

    def getPosition(self):
        pos = self.positionValue
        return pos

    def getDialPosition(self):
        return self.getPosition()

    def syncMove(self, position):
        prev_position = self.getPosition()
        # self.positionValue = position
        relative_position = position - prev_position
        self.syncMoveRelative(relative_position)
        gevent.sleep(0.2)  # allow MD2 to change the state
        while (
            self.stateValue == "RUNNING" or self.stateValue == "MOVING"
        ):  # or self.stateValue == SpecMotor.MOVESTARTED:
            QApplication.processEvents(100)

    def moveRelative(self, position):
        old_pos = self.positionValue
        self.positionValue = old_pos + position
        self.positionChan.setValue(self.convertValue(self.positionValue))
        logging.info(
            "TangoDCMotor: movingRelative. motor will go to %s "
            % str(self.positionValue)
        )

        while self.stateValue == "RUNNING" or self.stateValue == "MOVING":
            QApplication.processEvents(100)

    def convertValue(self, value):
        logging.info("TangoDCMotor: converting value to %s " % str(self.dataType))
        retvalue = value
        if self.dataType in ["short", "int", "long"]:
            retvalue = int(value)
        return retvalue

    def syncMoveRelative(self, position):
        old_pos = self.positionValue
        self.positionValue = old_pos + position
        logging.info(
            "TangoDCMotor: syncMoveRelative going to %s "
            % str(self.convertValue(self.positionValue))
        )
        self.positionChan.setValue(self.convertValue(self.positionValue))

        dev = DeviceProxy(self.tangoname)
        gevent.sleep(0.2)  # allow MD2 to change the state

        mystate = str(dev.State())
        logging.info(
            "TangoDCMotor: %s syncMoveRelative state is %s / %s "
            % (self.tangoname, str(self.stateValue), mystate)
        )

        while mystate == "RUNNING" or mystate == "MOVING":
            logging.info("TangoDCMotor: syncMoveRelative is moving %s" % str(mystate))
            gevent.sleep(0.1)
            mystate = str(dev.State())
            QApplication.processEvents(100)

    def getMotorMnemonic(self):
        return self.name()

    def move(self, absolutePosition, epsilon=0.0, sync=False):
        """Move the motor to the required position

        Arguments:
        absolutePosition -- position to move to
        """
        logging.getLogger("TangoClient").info(
            "TangoDCMotor move (%s). Trying to go to %s: type '%s'",
            self.motor_name,
            absolutePosition,
            type(absolutePosition),
        )
        absolutePosition = float(absolutePosition)
        if not isinstance(absolutePosition, float) and not isinstance(
            absolutePosition, int
        ):
            logging.getLogger("TangoClient").error(
                "Cannot move %s: position '%s' is not a number. It is a %s",
                self.tangoname,
                absolutePosition,
                type(absolutePosition),
            )
        logging.info("TangoDCMotor: move. motor will go to %s " % str(absolutePosition))
        logging.getLogger("HWR").info(
            "TangoDCMotor.move to absolute position: %.3f" % absolutePosition
        )
        logging.getLogger("TangoClient").info(
            "TangoDCMotor move. Trying to go to %s: that is a '%s'",
            absolutePosition,
            type(absolutePosition),
        )
        if abs(self.getPosition() - absolutePosition) > epsilon:
            logging.info(
                "TangoDCMotor: difference larger then epsilon (%s), executing the move "
                % str(epsilon)
            )
            self.positionChan.setValue(self.convertValue(absolutePosition))
        else:
            logging.info(
                "TangoDCMotor: not moving really as epsilon is large %s " % str(epsilon)
            )
            logging.info(
                "TangoDCMotor: self.getPosition() %s " % str(self.getPosition())
            )
            logging.info("TangoDCMotor: absolutePosition %s " % str(absolutePosition))

    def stop(self):
        logging.getLogger("HWR").info("TangoDCMotor.stop")
        stopcmd = self.getCommandObject("Stop")()
        if not stopcmd:
            stopcmd = TangoCommand("stopcmd", "Stop", self.tangoname)
        stopcmd()

    def isSpecConnected(self):
        logging.getLogger().debug("%s: TangoDCMotor.isSpecConnected()" % self.name())
        return (TruehardwareObjectName,)


def test():
    hwr = HardwareRepository.getHardwareRepository()
    hwr.connect()

    motor = hwr.getHardwareObject("/phi")
    print motor.getPosition()


if __name__ == "__main__":
    test()
