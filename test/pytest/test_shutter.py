from HardwareRepository.HardwareObjects.abstract.AbstractNState import AbstractShutter


def test_shutter_init(shutter_list):
    for shutter in shutter_list:
        assert shutter is not None, "Shutter hardware objects is None (not initialized)"

        # The methods are defined with abc.abstractmethod which will raise
        # an exception if the method is not defined. So there is no need to test for
        # the presence of each method


def test_shutter_open_close(shutter_list):
    for shutter in shutter_list:
        shutter.close()

        assert shutter.state() == AbstractShutter.STATE.CLOSED.name

        shutter.open()

        assert shutter.state() == AbstractShutter.STATE.OPEN.name


def test_shutter_is_valid(shutter_list):
    for shutter in shutter_list:
        shutter.close()

        assert shutter.is_valid()

        try:
            shutter.current_state = None
        except Exception:
            assert True

        shutter.open()

        assert shutter.is_valid()
