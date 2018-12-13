from HardwareRepository import HardwareRepository
from HardwareRepository.BaseHardwareObjects import Equipment
import logging


class SampleStage(Equipment):
    def init(self):
        self.__axis = []
        for token in self:
            if token.name() == "axis":
                axis_name = token.getProperty("objectName")
                if axis_name is not None:
                    axis = HardwareRepository.getHardwareRepository().getHardwareObject(
                        axis_name
                    )
                    if axis is not None:
                        self.__axis.append(axis)

    def isSampleStage(self):
        return True

    def getAxisList(self):
        return self.__axis
