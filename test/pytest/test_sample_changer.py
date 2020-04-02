def test_sample_change_init(beamline):
    assert (
        not beamline.sample_changer is None
    ), "Sample changer hardware objects is None (not initialized)"


def test_sample_changer_load(beamline):
    pass

def test_sample_change_unload(beamline):
    pass

def test_sample_change_select(beamline):
    pass

def test_sample_change_abort(beamline):
    pass

def test_sample_change_get_state(beamline):
    pass

def test_sample_change_get_status(beamline):
    pass

def test_sample_change_has_loaded_sample(beamline):
    pass

def test_sample_change_get_loaded_sample(beamline):
    pass