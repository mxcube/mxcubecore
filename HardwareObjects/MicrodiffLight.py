from AbstractMotor import AbstractMotor


class MicrodiffLight(AbstractMotor):
    def __init__(self, name):
        AbstractMotor.__init__(self, name)

    def init(self):
        try:
            self.set_limits(eval(self.getProperty("limits")))
        except:
            self.set_limits((0, 2))

        self.chan_value = self.getChannelObject("chanLightValue")
        self.chan_value.connectSignal("update", self.value_changed)
        self.chan_light_is_on = self.getChannelObject("chanLightIsOn")

        self.set_state(self.motor_states.READY)
        self.value_changed(self.chan_value.getValue())

    def connectNotify(self, signal):
        if self.chan_value.isConnected():
            if signal == "positionChanged":
                self.emit("positionChanged", (self.get_position(),))
            elif signal == "limitsChanged":
                self.limits_changed()

    def limits_changed(self):
        self.emit("limitsChanged", (self.get_limits(),))

    def value_changed(self, position, private={}):
        self.set_position(position)
        self.emit("positionChanged", (self.get_position(),))

    def move(self, position, wait=False, timeout=None):
        self.chan_value.setValue(position)

    def stop(self):
        pass

    def light_is_out(self):
        return self.chan_light_is_on.getValue()

    def move_in(self):
        self.chan_light_is_on.setValue(False)

    def move_out(self):
        self.chan_light_is_on.setValue(True)
