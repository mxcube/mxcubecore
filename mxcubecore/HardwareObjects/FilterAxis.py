# $Id: FilterAxis.py,v 1.1 2004/08/10 12:27:36 guijarro Exp $
from HardwareRepository.BaseHardwareObjects import Device
from HardwareRepository import HardwareRepository as HWR


class FilterAxis(Device):
    def __init__(self, name):
        Device.__init__(self, name)

    def getAxisMotor(self):
        hwmot = None
        motorname = self.getProperty("motor")

        if motorname:
            hwmot = HWR.getHardwareRepository().getHardwareObject(
                motorname
            )

        return hwmot

    def getAxisLabels(self):
        filterno = 0
        filters = []

        for filter in self["filter"]:
            filterno += 1
            filters.append([filter.username, filter.offset])

        return filters
