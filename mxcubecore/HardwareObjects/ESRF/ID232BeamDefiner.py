import ast

from enum import Enum
from gevent import Timeout, sleep

from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractNState import AbstractNState
from bliss.common import event


class ID232BeamDefiner(AbstractNState):

    def __init__(self, *args):
        super().__init__(*args)
        self.tf_cfg_by_name = {}
        self.coef_by_name = {}
        self.size_by_name = {}
        self.pos_names = []
        self.controller = None

    def init(self):
        super().init()

        self.controller = self.get_object_by_role("controller")
        event.connect(self.controller.tf, "state", self._tf_state_updated)
        event.connect(self.controller.tf2, "state", self._tf_state_updated)

        cfg = self["lenses_config"]
        if not isinstance(cfg, list):
            cfg = [cfg]

        for lens_cfg in cfg:
            name = lens_cfg.get_property("name")
            tf1 = lens_cfg.get_property("tf1").split()
            tf2 = lens_cfg.get_property("tf2").split()
            size = lens_cfg.get_property("size")
            coef = lens_cfg.get_property("coef")
            self.pos_names.append(lens_cfg.get_property("name"))
            self.tf_cfg_by_name[name] = {
                "tf1": ["IN" if x else "OUT" for x in map(int, tf1)],
                "tf2": ["IN" if x else "OUT" for x in map(int, tf2)],
            }
            self.size_by_name[name] = tuple([float(x) for x in ast.literal_eval(size)])
            self.coef_by_name[name] = float(coef)

        # check if we have values other that UKNOWN
        if len(self.VALUES) == 1:
            self._initialise_values()

    def is_ready(self):
        return self.controller is not None

    def get_state(self):
        """Get the device state.
        Returns:
            (enum 'HardwareObjectState'): Device state.
        """
        return self.STATES.READY

    def get_limits(self):
        return (1, len(self.pos_names))

    def get_value(self):
        """Get the device value
        Returns:
            (int): The position index.
        """
        try:
            return self.VALUES[self.get_current_position_name()]
        except (ValueError, KeyError):
            return self.VALUES.UNKNOWN

    def _tf_state_updated(self, new_state=None):
        name = self.get_current_position_name()
        self.emit("valueChanged", name)
        self.emit(
            "diameterIndexChanged", (name, (1e6, self.size_by_name.get(name, 1e6)))
        )

    def connect_notify(self, signal):
        return self._tf_state_updated()

    def get_predefined_positions_list(self):
        return self.pos_names

    def get_current_status(self):
        tf1_status = self.controller.tf.wago.get("stat")[::2]
        tf2_status = self.controller.tf2.wago.get("stat")[::2]
        return tf1_status, tf2_status

    def get_current_position_name(self, *args):
        try:
            tf1_state = self.controller.tf.status_read()[1].split()
            tf2_state = self.controller.tf2.status_read()[1].split()
        except:
            return "UNKNOWN"
        for name in self.pos_names:
            tf1_cfg = self.tf_cfg_by_name[name]["tf1"]
            tf2_cfg = self.tf_cfg_by_name[name]["tf2"]

            for i, tf_pos in enumerate(zip(tf1_state, tf2_state)):
                if tf_pos[0] in (tf1_cfg[i], "---") and tf_pos[1] in (
                    tf2_cfg[i],
                    "---",
                ):
                    continue
                else:
                    break
            else:
                return name

    def set_value(self, name, timeout=None):
        """Set the beam size.
        Args:
            name (str): position name
        """
        tf1_cfg = [1 if x == "IN" else 0 for x in self.tf_cfg_by_name[name]["tf1"]]
        tf2_cfg = [1 if x == "IN" else 0 for x in self.tf_cfg_by_name[name]["tf2"]]

        self.controller.tf.set(*tf1_cfg)
        self.controller.tf2.set(*tf2_cfg)
        self.wait_ready((tf1_cfg,tf2_cfg), timeout)

    def wait_ready(self, status, timeout=None):
        """Wait timeout seconds until status reached
        Args:
            timeout (float): Timeout [s]. Defaults to None.
        """
        with Timeout(timeout, RuntimeError("Execution timeout")):
            while status != self.get_current_status():
                sleep(0.5)

    def _initialise_values(self):
        """Initialise the ValueEnum from the hardware
        Raises:
            RuntimeError: No aperture diameters defined.
        """
        values = {}
        for val in self.pos_names:
            values[val] = [self.pos_names.index(val), self.size_by_name[val]]

        self.VALUES = Enum(
            "ValueEnum",
            dict(values, **{item.name: item.value for item in self.VALUES}),
        )
