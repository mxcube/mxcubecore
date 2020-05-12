from HardwareRepository.BaseHardwareObjects import HardwareObject
from bliss.config import static

class BlissVolpi(HardwareObject):
    
    def __init__(self, name):
        #AbstractMotor.__init__(self, name)
        Device.__init__(self, name)
        
    def init(self):
        self.username = self.volpi_name

        cfg = static.get_config()
        self.volpi = cfg.get(self.volpi_name)
        self.connect(self.volpi, "intensity", self.intensity_changed)
    
    def connectNotify(self, signal):
        if signal == "intensityChanged":
            self.emit("intensityChanged", (self.get_value(),))

    def set_value(self, intensity):
        """set volpi to new value."""
        self.volpi.intensity = intensity

    def get_value(self):
        """get volpi intensity value."""
        return self.volpi.intensity
    
    def re_emit_values(self):
        self.emit("intensityChanged", (self.get_value(),))

    def intensity_changed(self, new_intensity):
        self.emit("intensityChanged", (new_intensity,))
