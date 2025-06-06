import gevent

from mxcubecore.HardwareObjects.abstract.AbstractProcedure import ProcedureState
from mxcubecore.model import procedure_model


def test_procedure_init(beamline):
    assert beamline.procedure is not None, (
        "MockProcedure hardware objects is None (not initialized)"
    )
    # The methods are defined with abc.abstractmethod which will raise
    # an exception if the method is not defined. So there is no need to test for
    # the presence of each method


def test_procedure_start(beamline):
    data = procedure_model.MockDataModel(**{"exposure_time": 5})
    beamline.procedure.start(data)
    gevent.sleep(1)
    assert beamline.procedure.state == ProcedureState.BUSY
    beamline.procedure.wait()
    assert beamline.procedure.state == ProcedureState.READY


def test_procedure_stop(beamline):
    data = procedure_model.MockDataModel(**{"exposure_time": 5})
    beamline.procedure.start(data)
    gevent.sleep(1)
    assert beamline.procedure.state == ProcedureState.BUSY
    beamline.procedure.stop()
    assert beamline.procedure.state == ProcedureState.READY
