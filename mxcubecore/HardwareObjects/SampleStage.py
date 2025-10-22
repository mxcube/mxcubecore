from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject


class SampleStage(HardwareObject):
    def init(self):
        self.__axis = []
        for token in self:
            if token.name() == "axis":
                axis_name = token.get_property("objectName")
                if axis_name is not None:
                    axis = HWR.get_hardware_repository().get_hardware_object(axis_name)
                    if axis is not None:
                        self.__axis.append(axis)

    def isSampleStage(self):
        return True

    def getAxisList(self):
        return self.__axis
