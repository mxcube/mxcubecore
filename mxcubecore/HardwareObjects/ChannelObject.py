from HardwareRepository.BaseHardwareObjects import Device
import logging


class ChannelObject(Device):
    def __init__(self, name):
        Device.__init__(self, name)

    def init(self):

        try:
            self.object_channel = self.getChannelObject("channel")
            self.object_channel.connectSignal("update", self.valueChanged)

            self.status_channel = self.getChannelObject("state")
            if self.status_channel is not None:
                self.status_channel.connectSignal("update", self.stateChanged)
        except KeyError:
            logging.getLogger().warning("%s: cannot connect to channel", self.name())
        except Exception, e:
            import traceback

            logging.getLogger("HWR").error(
                "error creating channel value : %s ", traceback.format_exc()
            )

    def getValue(self):
        self.current_value = self.object_channel.getValue()
        return self.current_value

    def valueChanged(self, value):
        self.current_value = value
        self.emit("valueChanged", value)

    def stateChanged(self, value):
        self.emit("stateChanged", value)


def test_hwo(hwo):
    print hwo.getValue()
