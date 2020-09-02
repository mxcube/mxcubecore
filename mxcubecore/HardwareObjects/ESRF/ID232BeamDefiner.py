import ast

from HardwareRepository.BaseHardwareObjects import HardwareObject
from HardwareRepository.HardwareObjects.abstract.AbstractNState import AbstractNState
from HardwareRepository.BaseHardwareObjects import HardwareObjectState
from bliss.common import event


class ID232BeamDefiner(AbstractNState):
    READY = HardwareObjectState.READY

    def __init__(self, *args):
        HardwareObject.__init__(self, *args)

    # def userName(self):
    #     return self.getProperty("username") or self.name()

    def init(self):
        HardwareObject.init(self)

        self.controller = self.getObjectByRole("controller")
        event.connect(self.controller.tf, "state", self._tf_state_updated)
        event.connect(self.controller.tf2, "state", self._tf_state_updated)
        self.tfCfgByName = {}
        self.coefByName = {}
        self.sizeByName = {}
        self.posNames = []

        cfg = self["lenses_config"]
        if not isinstance(cfg, list):
            cfg = [cfg]

        for lens_cfg in cfg:
            name = lens_cfg.getProperty("name")
            tf1 = lens_cfg.getProperty("tf1").split()
            tf2 = lens_cfg.getProperty("tf2").split()
            size = lens_cfg.getProperty("size")
            coef = lens_cfg.getProperty("coef")
            self.posNames.append(lens_cfg.getProperty("name"))
            self.tfCfgByName[name] = {
                "tf1": ["IN" if x else "OUT" for x in map(int, tf1)],
                "tf2": ["IN" if x else "OUT" for x in map(int, tf2)],
            }
            self.sizeByName[name] = tuple([float(x) for x in ast.literal_eval(size)])
            self.coefByName[name] = float(coef)

    def is_ready(self):
        return self.controller is not None

    def get_state(self):
        return self.READY

    def get_limits(self):
        return (1, len(self.posNames))

    def get_value(self):
        try:
            return self.posNames.index(self.get_current_position_name())
        except ValueError:
            return -1

    def _tf_state_updated(self, new_state=None):
        name = self.get_current_position_name()
        self.emit("valueChanged", name)
        self.emit("diameterIndexChanged", (name, (1e6, self.sizeByName.get(name, 1e6))))

    def connectNotify(self, signal):
        return self._tf_state_updated()

    def get_predefined_positions_list(self):
        return self.posNames

    def get_current_position_name(self, *args):
        tf1_state = self.controller.tf.status_read()[1].split()
        tf2_state = self.controller.tf2.status_read()[1].split()

        for name in self.posNames:
            tf1_cfg = self.tfCfgByName[name]["tf1"]
            tf2_cfg = self.tfCfgByName[name]["tf2"]

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

    def move_to_position(self, name):
        tf1_cfg = [1 if x == "IN" else 0 for x in self.tfCfgByName[name]["tf1"]]
        tf2_cfg = [1 if x == "IN" else 0 for x in self.tfCfgByName[name]["tf2"]]

        self.controller.tf.set(*tf1_cfg)
        self.controller.tf2.set(*tf2_cfg)

    def setNewPredefinedPosition(self, positionName, positionOffset):
        raise NotImplementedError
