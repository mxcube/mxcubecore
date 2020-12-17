from mx3core.HardwareObjects import GrobMotor


class GrobGonio(GrobMotor.GrobMotor):
    def __init__(self, name):
        GrobMotor.GrobMotor.__init__(self, name)

    def oscillation(self, *args):
        self.motor.oscillation(*args)
