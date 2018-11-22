from HardwareRepository.BaseHardwareObjects import Equipment
import logging


class MultiAxis(Equipment):
    def init(self):
        self.__steps = {"horizontal": [], "vertical": [], "rotation": []}
        self.__arrow_motormove = {
            "horizontal": "positive2right",
            "vertical": "positive2up",
            "rotation": "clockwise",
        }
        for object_name in self.objectsNames():
            if (
                object_name == "horizontal"
                or object_name == "vertical"
                or object_name == "rotation"
            ):
                self.__parsParam(object_name)

    def isMultiAxis(self):
        return True

    def getStepsByRole(self, role):
        return self.__steps[role]

    def getArrowMotorMoveByRole(self, role):
        return self.__arrow_motormove[role]

    def __parsParam(self, paramName):
        hparams = self[paramName]
        steps = self.__steps[paramName]
        tmpstepString = hparams.getProperty("steps")
        if tmpstepString is not None:
            tmpstepString = str(tmpstepString)
            for val in tmpstepString.split(" "):
                try:
                    steps.append(float(val))
                except BaseException:
                    pass

        defaultStep = hparams.getProperty("defaultStep")
        # defaultStep is allways first in the step list
        if defaultStep is not None:
            if defaultStep in steps:
                steps.remove(defaultStep)
            steps.insert(0, defaultStep)

        arrow_motormove = hparams.getProperty("arrow_motormove")
        if arrow_motormove is not None:
            self.__arrow_motormove[paramName] = arrow_motormove
