from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.ExpMotor import ExpMotor


class MicrodiffFocusMotor(ExpMotor):
    def __init__(self, name):
        ExpMotor.__init__(self, name)

    def init(self):

        if HWR.beamline.diffractometer.in_plate_mode():
            self.actuator_name = self.get_property("centring_focus")
        else:
            self.actuator_name = self.get_property("alignment_focus")
        ExpMotor.init(self)
