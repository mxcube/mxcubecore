import time
import gevent

from mx3core.BaseHardwareObjects import Device
from mx3core.hardware_objects.abstract.AbstractMotor import AbstractMotor


class PX1DetectorDistance(Device, AbstractMotor):

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
            0.0018  # default value. change it with property threshold in xml
        )

        self.old_value = 0.0
        self.tangoname = self.get_property("tangoname")

        threshold = self.get_property("threshold")
        if threshold is not None:
            try:
                self.threshold = float(threshold)
            except Exception:
                pass

        self.set_is_ready(True)

        self.position_chan = self.get_channel_object("position")
        self.state_chan = self.get_channel_object("state")
        self.stop_command = self.get_command_object("stop")

        self.distance_min_chan = self.get_channel_object("minimum_distance")

        self.light_state_chan = self.get_channel_object("light_state")
        self.light_extract_cmd = self.get_command_object("extract_light")

        self.position_chan.connect_signal("update", self.motor_position_changed)
        self.state_chan.connect_signal("update", self.motor_state_changed)
        self.distance_min_chan.connect_signal("update", self.distance_min_changed)

    def is_ready(self):
        return self.state_value == "STANDBY"

    def connect_notify(self, signal):
        if signal == "hardware_object_name,stateChanged":
            self.motor_state_changed()
        elif signal == "position_changed":
            self.motor_position_changed()
        elif signal == "limitsChanged":
            self.distance_min_changed()
        self.set_is_ready(True)

    def motor_state_changed(self, state=None):
        state_code = self.get_state(state)

        if self.state_value not in ["RUNNING", "MOVING"]:
            position = self.position_chan.get_value()
            self.motor_position_changed(position)

        self.set_is_ready(True)
        self.emit("stateChanged", (state_code,))

    def motor_position_changed(self, position=None):
        if position is None:
            position = self.get_value()

        self.current_position = position

        if abs(position - self.old_value) > self.threshold:
            try:
                self.emit("valueChanged", (position,))
                self.old_value = position
            except Exception:
                self.old_value = position

    def distance_min_changed(self, value=None):
        self.emit("limitsChanged", (self.get_limits(),))

    def get_state(self, state=None):
        if state is None:
            state = str(self.state_chan.get_value())
        else:
            state = str(state)

        self.state_value = state

        return self.stateDict[state]

    def get_value(self):
        return self.position_chan.get_value()

    def get_limits(self):
        try:
            info = self.position_chan.getInfo()
            max = float(info.max_value)
            min = float(self.distance_min_chan.get_value())
            return [min, max]
        except Exception:
            return [-1, 1]

    def is_moving(self):
        self.get_state()
        return self.state_value in ["RUNNING", "MOVING"]

    def _set_value(self, value):
        if not self.check_light(value):
            return (False, "Error while trying to extract the light arm!")

        self.position_chan.set_value(value)

    def get_motor_mnemonic(self):
        return self.name()

    def check_light(self, position):
        # ligth is not controlled anymore. it is left in place but the
        # px1environment sets the distanceMin value used here as a lower limit
        # to avoid collision

        limits = self.get_limits()
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
        return str(self.light_state_chan.get_value())

    def stop(self):
        self.stop_command()


def test_hwo(hwo):
    print(hwo.get_value())
    print(hwo.get_limits())
