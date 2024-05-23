def test_sample_change_init(beamline):
    assert (
        beamline.config.sample_changer is not None
    ), "Sample changer hardware objects is None (not initialized)"


def test_sample_changer_load(beamline):
    beamline.config.sample_changer.load((1, 1))
    assert beamline.config.sample_changer.is_mounted_sample((1, 1))


def test_sample_has_loaded_sample(beamline):
    beamline.config.sample_changer.load((1, 1))
    assert beamline.config.sample_changer.has_loaded_sample()
    beamline.config.sample_changer.unload()
    assert not beamline.config.sample_changer.has_loaded_sample()


def test_sample_changer_unload(beamline):
    pass


def test_sample_changer_select(beamline):
    pass


def test_sample_changer_abort(beamline):
    pass


def test_sample_changer_get_state(beamline):
    pass


def test_sample_changer_get_status(beamline):
    pass


def test_sample_changer_get_loaded_sample(beamline):
    pass
