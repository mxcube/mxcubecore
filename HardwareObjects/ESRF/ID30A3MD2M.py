from mx3core.HardwareObjects import MiniDiff


class ID30A3MD2M(MiniDiff.MiniDiff):
    def __init__(self, name):
        MiniDiff.MiniDiff.__init__(self, name)
        MiniDiff.qmo.CentredPosition.set_diffractometer_motor_names(
            "phi", "focus", "phiz", "phiy", "zoom", "sampx", "sampy"
        )

    def init(self):
        self.controller = self.get_object_by_role("controller")
        MiniDiff.MiniDiff.init(self)

    def oscil(self, *args, **kwargs):
        self.controller.oscil(*args, **kwargs)

    def helical_oscil(self, *args, **kwargs):
        self.controller.helical_oscil(*args, **kwargs)
