from HardwareRepository.BaseHardwareObjects import Equipment


class Filters(Equipment):
    def getAxes(self):
        axes = []

        if len(self["axis"]) == 1:
            axes.append(self["axis"].getDevices()[0])
        else:
            for axis in self["axis"]:
                axes.append(axis.getDevices()[0])

        return axes
