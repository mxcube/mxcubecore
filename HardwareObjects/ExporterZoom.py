from HardwareRepository.HardwareObjects.ExporterMotor import ExporterMotor
import math


class ExporterZoom(ExporterMotor):
    def __init__(self, name):
        ExporterMotor.__init__(self, name)

    def init(self):
        self.actuator_name = "Zoom"
        self.motor_pos_attr_suffix = "Position"
        self._last_position_name = None

        self.chan_predefined_position = self.add_channel(
            {"type": "exporter", "name": "predefined_position"},
            "CoaxialCameraZoomValue",
        )

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
        self.sort_predefined_positions_list()
        self.set_limits((0, 10))
        self.update_state(self.motor_states.READY)

        ExporterMotor.init(self)

    def sort_predefined_positions_list(self):
        self.predefined_positions_names_list = self.predefined_positions.keys()
        self.predefined_positions_names_list.sort(
            lambda x, y: int(
                round(self.predefined_positions[x] - self.predefined_positions[y])
            )
        )

    def connect_notify(self, signal):
        if signal == "predefinedPositionChanged":
            position_name = self.get_current_position_name()

            try:
                pos = self.predefined_positions[position_name]
            except KeyError:
                self.emit(signal, ("", None))
            else:
                self.emit(signal, (position_name, pos))
        else:
            return ExporterMotor.connect_notify.im_func(self, signal)

    def get_predefined_positions_list(self):
        return self.predefined_positions_names_list

    def position_changed(self, position, private={}):
        ExporterMotor.position_changed.im_func(self, position, private)

        position_name = self.get_current_position_name(position)
        if self._last_position_name != position_name:
            self._last_position_name = position_name
            self.emit(
                "predefinedPositionChanged",
                (position_name, position_name and position or None),
            )

    def get_current_position_name(self, position=None):
        position = self.chan_predefined_position.get_value()

        for position_name in self.predefined_positions:
            if math.fabs(self.predefined_positions[position_name] - position) <= 1e-3:
                return position_name
        return ""

    def move_to_position(self, position_name):
        self.chan_predefined_position.set_value(self.predefined_positions[position_name])

    def zoom_in(self):
        position_name = self.get_current_position_name()
        position_index = self.predefined_positions_names_list.index(position_name)
        if position_index < len(self.predefined_positions_names_list) - 1:
            self.move_to_position(
                self.predefined_positions_names_list[position_index + 1]
            )

    def zoom_out(self):
        position_name = self.get_current_position_name()
        position_index = self.predefined_positions_names_list.index(position_name)
        if position_index > 0:
            self.move_to_position(
                self.predefined_positions_names_list[position_index - 1]
            )
