def test_sample_changer_load(beamline):
    beamline.sample_changer.load((1, 1))
    assert(beamline.sample_changer.is_mounted_sample((1, 1)))

def test_sample_has_loaded_sample(beamline):
    beamline.sample_changer.load((1, 1))
    assert(beamline.sample_changer.has_loaded_sample())
    beamline.sample_changer.unload()
    assert(not beamline.sample_changer.has_loaded_sample())

def test_sample_changer_unload(beamline):
    beamline.sample_changer.load((1, 1))
    assert(beamline.sample_changer.has_loaded_sample())
    # import pdb; pdb.set_trace()
    assert(beamline.sample_changer.unload() is not None)
    assert (
        not beamline.sample_changer.has_loaded_sample()
    ), "Sample changer  has_loaded_sample() must be  None (not initialized)"


def test_sample_changer_select(beamline):
    beamline.sample_changer.load((1, 1), wait=False)
    sample = beamline.sample_changer._resolve_component((1, 1))
    assert(beamline.sample_changer.select(sample) is not None)

def test_sample_changer_abort(beamline):
    beamline.sample_changer.load((1, 1), wait=False)
    # assert(beamline.sample_changer.get_state() != 1) # SampleChangerState.BUSY
    beamline.sample_changer.abort()
    beamline.sample_changer.wait_ready()
    # assert(beamline.sample_changer.get_state() == 1) # SampleChangerState.READY


def test_sample_changer_get_state(beamline):
    beamline.sample_changer.load((1, 1), wait=False)
    # assert(beamline.sample_changer. get_state() == 3) # SampleChangerState.BUSY
    beamline.sample_changer.wait_ready()
    assert(beamline.sample_changer.get_state() == 1) # SampleChangerState.READY


def test_sample_changer_get_status(beamline):
    assert(beamline.sample_changer.get_status() is not None)

def test_sample_changer_get_loaded_sample(beamline):
    beamline.sample_changer.load((1, 1))
    loaded_samples = len(beamline.sample_changer.get_sample_list())
    assert (
        loaded_samples >= 0
    ), "Sample changer len(get_loaded_sample) must be >= 0 but is None"
    assert(beamline.sample_changer.get_loaded_sample() is not None)