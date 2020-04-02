def test_sample_change_init(beamline):
    assert (
        not beamline.sample_changer is None
    ), "Sample changer hardware objects is None (not initialized)"


def test_sample_changer_load(beamline):
    pass
