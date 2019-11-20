from MicrodiffInOut import MicrodiffInOut

class MicrodiffLightBeamstop(MicrodiffInOut):
    def __init__(self, name):
        MicrodiffInOut.__init__(self, name)
        self.save_position = None

    def init(self):
        MicrodiffInOut.init(self)
        self.beamstop = self.getObjectByRole("beamstop")
        try:
            self.safety_position = float(self.getProperty("safety_position"))
        except TypeError:
            self.safety_position = 38

    def actuatorIn(self, wait=True, timeout=None):
        pos = self.beamstop.get_position()
        if pos < self.safety_position:
            self.save_position = pos
            self.beamstop.move(self.safety_position, wait=True)
        MicrodiffInOut.actuatorIn(self, wait=True, timeout=None)

    def actuatorOut(self, wait=True, timeout=None):
        MicrodiffInOut.actuatorOut(self, wait=True, timeout=None)
        if self.save_position:
            self.beamstop.move(self.save_position, wait=True)
