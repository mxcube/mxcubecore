import gevent
from HardwareRepository.BaseHardwareObjects import Equipment
from HardwareRepository import HardwareRepository as HWR


class BIOMAXTransmission(Equipment):
    def init(self):
        self.ready_event = gevent.event.Event()
        self.moving = None
        self.limits = [0, 100]
        self.threhold = 5

        if HWR.beamline.transmission is not None:
            HWR.beamline.transmission.connect(
                "positionChanged", self.transmissionPositionChanged
            )

    def isReady(self):
        return True

    def get_value(self):
        return "%.3f" % HWR.beamline.transmission.getPosition()

    def getAttFactor(self):
        return "%.3f" % HWR.beamline.transmission.getPosition()

    def getAttState(self):
        return 1

    def getLimits(self):
        return (0, 100)

    def setpoint_reached(self, setpoint):
        curr_pos = float(self.get_value())
        return abs(curr_pos - setpoint) < 5

    def set_value(self, value, timeout=30):
        if value < self.limits[0] or value > self.limits[1]:
            raise Exception("Transmssion out of limits.")
        HWR.beamline.transmission.move(value)
        with gevent.Timeout(timeout, Exception("Timeout waiting for device ready")):
            while not self.setpoint_reached(value):
                gevent.sleep(0.1)

        self._update()

    def _update(self):
        self.emit("attStateChanged", self.getAttState())

    def transmissionPositionChanged(self, *args):
        pos = self.get_value()
        self.emit("valueChanged", (pos,))

    def stop(self):
        HWR.beamline.transmission.stop()
