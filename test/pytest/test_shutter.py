from HardwareRepository.HardwareObjects.abstract import AbstractNState


def test_shutter_init(beamline):
    assert (
        beamline.safety_shutter is not None
    ), "Shutter hardware objects is None (not initialized)"

    # The methods are defined with abc.abstractmethod which will raise
    # an exception if the method is not defined. So there is no need to test for
    # the presence of each method
    assert beamline.safety_shutter.get_state == AbstractNState.STATES.UNKNOWN


def test_shutter_open_close(beamline):
    beamline.safety_shutter.open()
    assert beamline.safety_shutter.is_open() is True

    assert beamline.safety_shutter.get_state == AbstractNState.STATES.READY

    beamline.safety_shutter.close()
    assert beamline.safety_shutter.is_closed() is True

"""
def test_shutter_is_valid(beamline):
    beamline.safety_shutter.close()
    assert beamline.safety_shutter.is_valid()

    try:
        beamline.safety_shutter.current_state = None
    except Exception:
        assert True

    beamline.safety_shutter.open()
    assert beamline.safety_shutter.is_valid()
"""
