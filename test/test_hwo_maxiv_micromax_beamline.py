from mxcubecore.HardwareObjects.MAXIV.MicroMAX.beamline import Beamline, SampleDelivery


def _setup_beamline_obj(config: dict):
    beamline = Beamline("dummy")
    beamline._config = Beamline.HOConfig(**config)  # noqa: SLF001

    return beamline


def test_sample_delivery_osc():
    """test 'OSC' sample delivery mode"""

    beamline = _setup_beamline_obj({"sample_delivery": "osc"})

    assert not beamline.is_hve_sample_delivery()
    assert not beamline.is_fixed_target_sample_delivery()
    assert beamline.sample_delivery == SampleDelivery.osc


def test_sample_delivery_hve():
    """test 'HVE' sample delivery mode"""

    beamline = _setup_beamline_obj({"sample_delivery": "hve"})

    assert beamline.is_hve_sample_delivery()
    assert not beamline.is_fixed_target_sample_delivery()
    assert beamline.sample_delivery == SampleDelivery.hve


def test_sample_delivery_fixed_target():
    """test 'Fixed-target' sample delivery mode"""

    beamline = _setup_beamline_obj({"sample_delivery": "fixed-target"})

    assert not beamline.is_hve_sample_delivery()
    assert beamline.is_fixed_target_sample_delivery()
    assert beamline.sample_delivery == SampleDelivery.fixed_target
