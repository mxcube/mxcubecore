from Bliss import Bliss


class ID30Controller(Bliss):
    def __init__(self, *args):
        Bliss.__init__(self, *args)

    def init(self, *args):
        Bliss.init(self)

    def set_diagfile(self, diagfile):
        self.minidiff.diagfile = diagfile

    def __getattr__(self, attr):
        if attr.startswith("__") or attr == "minidiff":
            raise AttributeError(attr)
        return getattr(self.minidiff, attr)
