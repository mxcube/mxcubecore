import MiniDiff

class GrobDiff(MiniDiff.MiniDiff):
    def init(self):
        MiniDiff.MiniDiff.init(self)

        self.phiy_direction = -1

    def oscillate(self, range, exp_time, npasses=1):
        self.getDeviceByRole("phi").oscillation(range, exp_time, npasses)
