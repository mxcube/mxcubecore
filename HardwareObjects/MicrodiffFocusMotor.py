from HardwareRepository.HardwareObjects.ExpMotor import ExpMotor
from HardwareRepository import HardwareRepository as HWR


class MicrodiffFocusMotor(ExpMotor):
    def __init__(self, name):
        ExpMotor.__init__(self, name)

    def init(self):

        if HWR.beamline.diffractometer.in_plate_mode():
            self.motor_name = self.getProperty("centring_focus")
        else:
            self.motor_name = self.getProperty("alignment_focus")
        ExpMotor.init(self)
