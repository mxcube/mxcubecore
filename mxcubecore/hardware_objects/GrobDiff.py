from mxcubecore.hardware_objects import MiniDiff


class GrobDiff(MiniDiff.MiniDiff):
    def init(self):
        MiniDiff.MiniDiff.init(self)

        self.phiy_direction = -1

    def oscillate(self, range, exp_time, npasses=1):
        self.get_deviceby_role("phi").oscillation(range, exp_time, npasses)
