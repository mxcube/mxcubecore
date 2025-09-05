from mxcubecore.HardwareObjects.MAXIV.beamline import Beamline


def _setup_beamline_obj(config: dict):
    beamline = Beamline("dummy")
    beamline._config = Beamline.HOConfig(**config)  # noqa: SLF001

    return beamline


def test_emulate_default():
    """Test the `emulate()` method when no
    `emulate` config have been specified.
    """
    beamline = _setup_beamline_obj({})

    assert not beamline.emulate("feature1")
    assert not beamline.emulate("feature2")


def test_emulate_enabled():
    """Test the `emulate()` method when
    some feature have been configured to be emulated.
    """

    beamline = _setup_beamline_obj(
        {
            "emulate": {
                "feature1": True,
                "feature2": False,
            },
        }
    )

    assert beamline.emulate("feature1")
    assert not beamline.emulate("feature2")
    # this feature is not included into the config,
    # it must default to false
    assert not beamline.emulate("feature3")
