import gevent

from mxcubecore.HardwareObjects.abstract.AbstractProcedure import (
    AbstractProcedure,
)

from mxcubecore.model import procedure_model as datamodel


class ProcedureMockup(AbstractProcedure):
    _ARGS_CLASS = (datamodel.MockDataModel,)

    def __init__(self, name):
        super(ProcedureMockup, self).__init__(name)

    def _execute(self, data_model):
        print("Procedure will sleep for %d" % data_model.exposure_time)
        gevent.sleep(data_model.exposure_time)
