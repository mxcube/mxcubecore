from HardwareRepository.BaseHardwareObjects import HardwareObject
from bliss.config import static

class BlissTurret(HardwareObject):
    
    def __init__(self, name):
        Device.__init__(self, name)
        
    def init(self):
        self.username = self.turret_name

        cfg = static.get_config()
        self.turret = cfg.get(self.turret_name)
        self.connect(self.turret, "position", self.position_changed)
        self.connect(self.turret, "mode", self.mode_changed)
    
    def connectNotify(self, signal):
        if signal == "positionChanged":
            self.emit("positionChanged", (self.get_value(),))
        elif signal == "modeChanged":
            self.emit("modeChanged", (self.get_mode(),))
    
    def position_changed(self, new_position):
        # print self.name(), absolutePosition
        self.emit("positionChanged", (new_position,))

    def mode_changed(self, new_mode):
        self.emit("modeChanged", (new_mode,))

    def set_mode(self,mode):
        self.turret.mode = mode
    
    def get_mode(self):
        return self.turret.mode

    def get_value(self):
        return self.turret.position
    
    def set_value(self, position):
        self.turret.position = position
    
    def get_turret_mnemonic(self):
        return self.turret_name

    def re_emit_values(self):
        self.emit("positionChanged", (self.get_value(),))
        self.emit("modeChanged", (self.get_mode(),))


