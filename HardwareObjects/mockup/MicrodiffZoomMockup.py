# from MD2Motor import MD2Motor
from HardwareRepository.BaseHardwareObjects import Device
import logging
import math


class MicrodiffZoomMockup(Device):

    (NOTINITIALIZED, UNUSABLE, READY, MOVESTARTED, MOVING, ONLIMIT) = (0, 1, 2, 3, 4, 5)

    def init(self):
        self.actuator_name = "Zoom"
        self._last_position_name = None
        self.predefined_position_attr = 1
        self.predefined_positions = {
            "Zoom 1": 1,
            "Zoom 2": 2,
            "Zoom 3": 3,
            "Zoom 4": 4,
            "Zoom 5": 5,
            "Zoom 6": 6,
            "Zoom 7": 7,
            "Zoom 8": 8,
            "Zoom 9": 9,
            "Zoom 10": 10,
        }
        self.sort_positions_list()

    def isReady(self):
        return True

    def sort_positions_list(self):
        self.positions_names_list = list(self.predefined_positions.keys())
        # self.positions_names_list.sort()
        #    lambda x, y: int(
        #        round(self.predefined_positions[x] - self.predefined_positions[y])
        #    )
        # )

    def connectNotify(self, signal):
        if signal == "predefinedPositionChanged":
            positionName = self.get_current_position_name()

            try:
                pos = self.predefined_positions[positionName]
            except KeyError:
                self.emit(signal, ("", None))
            else:
                self.emit(signal, (positionName, pos))
        else:
            return True  # .connectNotify.im_func(self, signal)

    def get_limits(self):
        return (1, 10)

    def get_state(self):
        return MicrodiffZoomMockup.READY

    def get_predefined_positions_list(self):
        return self.positions_names_list

    def motor_position_changed(self, absolutePosition, private={}):
        # MD2Motor.motor_position_changed.im_func(self, absolutePosition, private)
        positionName = self.get_current_position_name(absolutePosition)
        if self._last_position_name != positionName:
            self._last_position_name = positionName
            self.emit(
                "predefinedPositionChanged",
                (positionName, positionName and absolutePosition or None),
            )

    def get_current_position_name(self, pos=None):
        pos = self.predefined_position_attr

        for positionName in self.predefined_positions:
            if math.fabs(self.predefined_positions[positionName] - pos) <= 1e-3:
                return positionName
        return ""

    def move_to_position(self, positionName):
        valid = True

        try:
            self.predefined_position_attr = self.predefined_positions[positionName]
            self.motor_position_changed(self.predefined_position_attr)
            return True
        except BaseException:
            valid = False

        self.connectNotify("predefinedPositionChanged")
        return valid
