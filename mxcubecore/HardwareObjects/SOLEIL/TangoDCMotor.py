from mxcubecore import HardwareRepository as HWR

import logging
import gevent

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.Command.Tango import TangoCommand

from PyTango import DeviceProxy

from PyQt4.QtGui import QApplication

import numpy
from mxcubecore.HardwareObjects.abstract.AbstractMotor import MotorStates


class TangoDCMotor(HardwareObject):

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

        threshold = self.get_property("threshold")
        self.threshold = (
            0.0018  # default value. change it with property threshold in xml
        )

        self.old_value = 0.0
        self.tangoname = self.get_property("tangoname")
        self.motor_name = self.get_property("motor_name")
        self.ho = DeviceProxy(self.tangoname)

        try:
            self.dataType = self.get_property("datatype")
            if self.dataType is None:
                self.dataType = "float"
        except Exception:
            self.dataType = "float"

        if threshold is not None:
            try:
                self.threshold = float(threshold)
            except Exception:
                pass

        self.set_is_ready(True)
        try:
            self.limitsCommand = self.get_command_object("limits")
        except KeyError:
            self.limitsCommand = None
        self.positionChan = self.get_channel_object(
            "position"
        )  # utile seulement si positionchan n'est pas defini dans le code
        self.stateChan = self.get_channel_object(
            "state"
        )  # utile seulement si statechan n'est pas defini dans le code

        self.positionChan.connect_signal("update", self.positionChanged)
        self.stateChan.connect_signal("update", self.motorStateChanged)

    def positionChanged(self, value):
        self.positionValue = value
        if abs(float(value) - self.old_value) > self.threshold:
            try:
                # logging.getLogger("HWR").error("%s: TangoDCMotor new position  , %s", self.name(), value)
                self.emit("valueChanged", (value,))
                self.old_value = value
            except Exception:
                logging.getLogger("HWR").error(
                    "%s: TangoDCMotor not responding, %s", self.name(), ""
                )
                self.old_value = value

    def is_ready(self):
        return self.stateValue == "STANDBY"

    def connect_notify(self, signal):
        if signal == "hardware_object_name,stateChanged":
            self.motorStateChanged(TangoDCMotor.stateDict[self.stateValue])
        elif signal == "limitsChanged":
            self.motorLimitsChanged()
        elif signal == "valueChanged":
            self.motor_positions_changed(self.positionValue)
        self.set_is_ready(True)

    def motorState(self):
        return TangoDCMotor.stateDict[self.stateValue]

    def motorStateChanged(self, state):
        self.stateValue = str(state)
        self.set_is_ready(True)
        logging.info("motor state changed. it is %s " % self.stateValue)
        self.emit("stateChanged", (TangoDCMotor.stateDict[self.stateValue],))

    def get_state(self):
        return TangoDCMotor.stateDict[self.stateValue]

    def get_limits(self):
        try:
            logging.getLogger("HWR").info(
                "TangoDCMotor.get_limits: trying to get limits for motor_name %s "
                % (self.motor_name)
            )
            limits = self.ho.getMotorLimits(
                self.motor_name
            )  # limitsCommand() # self.ho.getMotorLimits(self.motor_name)
            logging.getLogger("HWR").info(
                "TangoDCMotor.get_limits: Getting limits for %s -- %s "
                % (self.motor_name, str(limits))
            )
            if numpy.inf in limits:
                limits = numpy.array([-10000, 10000])
        except Exception:
            # import traceback
            # logging.getLogger("HWR").info("TangoDCMotor.get_limits: Cannot get limits for %s.\nException %s " % (self.motor_name, traceback.print_exc()))
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
                limits = self.get_property("min"), self.get_property("max")
                logging.getLogger("HWR").info(
                    "TangoDCMotor.get_limits: %.4f ***** %.4f" % limits
                )
                limits = numpy.array(limits)
            except Exception:
                # logging.getLogger("HWR").info("TangoDCMotor.get_limits: Cannot get limits for %s" % self.name())
                limits = None
        return limits

    def motorLimitsChanged(self):
        self.emit("limitsChanged", (self.get_limits(),))

    def motorIsMoving(self):
        return self.stateValue == "RUNNING" or self.stateValue == "MOVING"

    def motorMoveDone(self, channelValue):
        if self.stateValue == "STANDBY":
            self.emit("moveDone", (self.tangoname, "tango"))

    def motor_positions_changed(self, absolutePosition):
        self.emit("valueChanged", (absolutePosition,))

    def syncQuestionAnswer(self, specSteps, controllerSteps):
        return (
            "0"  # This is only for spec motors. 0 means do not change anything on sync
        )

    def get_value(self):
        return self.positionChan.get_value()

    def convertValue(self, value):
        logging.info("TangoDCMotor: converting value to %s " % str(self.dataType))
        retvalue = value
        if self.dataType in ["short", "int", "long"]:
            retvalue = int(value)
        return retvalue

    def get_motor_mnemonic(self):
        return self.name()

    def _set_value(self, value):
        """Move the motor to the required position

        Arguments:
        absolutePosition -- position to move to
        """
        logging.getLogger("TangoClient").info(
            "TangoDCMotor move (%s). Trying to go to %s: type '%s'",
            self.motor_name,
            value,
            type(value),
        )
        value = float(value)
        if not isinstance(value, float) and not isinstance(value, int):
            logging.getLogger("TangoClient").error(
                "Cannot move %s: position '%s' is not a number. It is a %s",
                self.tangoname,
                value,
                type(value),
            )
        logging.info("TangoDCMotor: move. motor will go to %s " % str(value))
        logging.getLogger("HWR").info(
            "TangoDCMotor.move to absolute position: %.3f" % value
        )
        logging.getLogger("TangoClient").info(
            "TangoDCMotor move. Trying to go to %s: that is a '%s'", value, type(value),
        )
        # if abs(self.get_value() - value) > epsilon:
        #     logging.info(
        #         "TangoDCMotor: difference larger then epsilon (%s), executing the move "
        #         % str(epsilon)
        #     )
        self.positionChan.set_value(self.convertValue(value))
        # else:
        #     logging.info(
        #         "TangoDCMotor: not moving really as epsilon is large %s " % str(epsilon)
        #     )
        #     logging.info("TangoDCMotor: self.get_value() %s " % str(self.get_value()))
        #     logging.info("TangoDCMotor: value %s " % str(value))

    def stop(self):
        logging.getLogger("HWR").info("TangoDCMotor.stop")
        stopcmd = self.get_command_object("Stop")()
        if not stopcmd:
            stopcmd = TangoCommand("stopcmd", "Stop", self.tangoname)
        stopcmd()

    def isSpecConnected(self):
        logging.getLogger().debug("%s: TangoDCMotor.isSpecConnected()" % self.name())
        return (Truehardware_object_name,)


def test():
    hwr = HWR.get_hardware_repository()
    hwr.connect()

    motor = hwr.get_hardware_object("/phi")
    print(motor.get_value())


if __name__ == "__main__":
    test()
