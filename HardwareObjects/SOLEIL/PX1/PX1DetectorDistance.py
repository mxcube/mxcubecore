import time
import logging
import gevent

from HardwareRepository.BaseHardwareObjects import Device


class PX1DetectorDistance(Device):

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

    def init(self):
        self.current_position = 0.0
        self.state_value = "UNKNOWN"
        self.threshold = (
            0.0018
        )  # default value. change it with property threshold in xml

        self.old_value = 0.0
        self.tangoname = self.getProperty("tangoname")

        threshold = self.getProperty("threshold")
        if threshold is not None:
            try:
                self.threshold = float(threshold)
            except:
                pass

        self.setIsReady(True)

        self.position_chan = self.getChannelObject("position")
        self.state_chan = self.getChannelObject("state")
        self.stop_command = self.getCommandObject("stop")

        self.distance_min_chan = self.getChannelObject("minimum_distance")

        self.light_state_chan = self.getChannelObject("light_state")
        self.light_extract_cmd = self.getCommandObject("extract_light")

        self.position_chan.connectSignal("update", self.motor_position_changed)
        self.state_chan.connectSignal("update", self.motor_state_changed)
        self.distance_min_chan.connectSignal("update", self.distance_min_changed)

    def isReady(self):
        return self.state_value == "STANDBY"

    def connectNotify(self, signal):
        if signal == "hardwareObjectName,stateChanged":
            self.motor_state_changed()
        elif signal == "position_changed":
            self.motor_position_changed()
        elif signal == "limitsChanged":
            self.distance_min_changed()
        self.setIsReady(True)

    def motor_state_changed(self, state=None):
        state_code = self.getState(state)

        if self.state_value not in ["RUNNING", "MOVING"]:
            position = self.position_chan.getValue()
            self.motor_position_changed(position)

        self.setIsReady(True)
        self.emit("stateChanged", (state_code,))

    def motor_position_changed(self, position=None):
        if position is None:
            position = self.getPosition()

        self.current_position = position

        if abs(position - self.old_value) > self.threshold:
            try:
                self.emit("positionChanged", (position,))
                self.old_value = position
            except:
                self.old_value = position

    def distance_min_changed(self, value=None):
        self.emit("limitsChanged", (self.getLimits(),))

    def getState(self, state=None):
        if state is None:
            state = str(self.state_chan.getValue())
        else:
            state = str(state)

        self.state_value = state

        return self.stateDict[state]

    def getPosition(self):
        return self.position_chan.getValue()

    def getDialPosition(self):
        return self.getPosition()

    def getLimits(self):
        try:
            info = self.position_chan.getInfo()
            max = float(info.max_value)
            min = float(self.distance_min_chan.getValue())
            return [min, max]
        except:
            return [-1, 1]

    def is_moving(self):
        self.getState()
        return self.state_value in ["RUNNING", "MOVING"]

    def move(self, position):
        if not self.check_light(position):
            return (False, "Error while trying to extract the light arm!")

        self.position_chan.setValue(position)

    def syncMove(self, position):
        if not self.check_light(position):
            return (False, "Error while trying to extract the light arm!")

        self.position_chan.setValue(position)

        while self.is_moving():
            gevent.sleep(0.03)

    def moveRelative(self, position):
        target_position = self.getPosition() + position
        if not self.check_light(target_position):
            return (False, "Error while trying to extract the light arm!")

        self.position_chan.setValue(target_position)

        while self.is_moving():
            gevent.sleep(0.03)

    def syncMoveRelative(self, position):
        target_position = self.getPosition() + position
        if not self.check_light(target_position):
            return (False, "Error while trying to extract the light arm!")

        self.position_chan.setValue(target_position)

        while self.is_moving():
            gevent.sleep(0.03)

    def getMotorMnemonic(self):
        return self.name()

    def check_light(self, position):
        # ligth is not controlled anymore. it is left in place but the
        # px1environment sets the distanceMin value used here as a lower limit
        # to avoid collision

        limits = self.getLimits()
        if None in limits:
            return False
        if position < limits[0]:
            return False

        return True

        if self.light_is_extracted():
            return True
        else:
            self.light_extract_cmd()
            cmd_start = time.time()
            while not self.light_is_extracted():
                if time.time() - cmd_start > 3:
                    return False
                gevent.sleep(0.3)
            else:
                return True

    def light_is_inserted(self):
        return self.read_light_state() == "INSERT"

    def light_is_extracted(self):
        return self.read_light_state() == "EXTRACT"

    def read_light_state(self):
        return str(self.light_state_chan.getValue())

    def stop(self):
        self.stop_command()


def test_hwo(hwo):
    print hwo.getPosition()
    print hwo.getLimits()
