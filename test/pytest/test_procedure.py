import gevent
from mxcubecore.HardwareObjects import datamodel
from mxcubecore.HardwareObjects.abstract.AbstractProcedure import ProcedureState


def test_procedure_init(beamline):
    assert (
        beamline.mock_procedure is not None
    ), "MockProcedure hardware objects is None (not initialized)"
    # The methods are defined with abc.abstractmethod which will raise
    # an exception if the method is not defined. So there is no need to test for
    # the presence of each method


def test_procedure_start(beamline):
    data = datamodel.MockDataModel(**{"exposure_time": 5})
    beamline.mock_procedure.start(data)
    gevent.sleep(1)
    assert beamline.mock_procedure.state == ProcedureState.BUSY
    beamline.mock_procedure.wait()
    assert beamline.mock_procedure.state == ProcedureState.READY


def test_procedure_stop(beamline):
    data = datamodel.MockDataModel(**{"exposure_time": 5})
    beamline.mock_procedure.start(data)
    gevent.sleep(1)
    assert beamline.mock_procedure.state == ProcedureState.BUSY
    beamline.mock_procedure.stop()
    assert beamline.mock_procedure.state == ProcedureState.READY
