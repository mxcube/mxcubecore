from HardwareRepository.HardwareObjects import MicrodiffInOut
import gevent
import time


class MAXIVMicrodiffInOut(MicrodiffInOut.MicrodiffInOut):
    def __init__(self, *args):
        MicrodiffInOut.MicrodiffInOut.__init__(self, *args)

    def init(self, *args):
        MicrodiffInOut.MicrodiffInOut.init(self)
        self.keep_polling = True

        self.polling = gevent.spawn(self._polling)

    def get_actuator_state(self, read=False):
        """
        to avoid infinite loooooop
        """
        value = self.state_attr.get_value()
        self.actuatorState = self.states.get(value, "unknown")
        return self.actuatorState

    def _polling(self):
        old_state = "somewhere"

        while self.keep_polling:
            try:
                state = self.get_actuator_state()
            except Exception:
                time.sleep(1)
                continue
            if state != old_state:
                old_state = state
                self.value_changed(self.state_attr.get_value())
            time.sleep(1)
