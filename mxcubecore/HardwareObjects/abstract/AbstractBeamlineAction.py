from mxcubecore.BaseHardwareObjects import HardwareObject

__copyright__ = """ Copyright © 2022 by the MXCuBE collaboration """
__license__ = "LGPLv3+"


def export(func):
    func._is_action = True

    return func


class AbstractBeamlineAction(HardwareObject):
    def __init__(self, name):
        super().__init__(name)

    def show_dialog(self, model) -> None:
        self.emit("show_dialog", (model, ))


