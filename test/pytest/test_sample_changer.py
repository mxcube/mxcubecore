
def test_sample_changer_load(beamline):
    beamline.sample_changer.load((1, 1))
    assert(beamline.sample_changer.is_mounted_sample((1, 1)))

def test_sample_has_loaded_sample(beamline):
    beamline.sample_changer.load((1, 1))
    assert(beamline.sample_changer.has_loaded_sample())
    beamline.sample_changer.unload()
    assert(not beamline.sample_changer.has_loaded_sample())

def test_sample_changer_unload(beamline):
    assert(beamline.sample_changer.unload() is not None)
    assert (
       not beamline.sample_changer.has_loaded_sample() is None
    ), "Sample changer  has_loaded_sample() must be  None (not initialized)"


def test_sample_changer_select(beamline):
    pass

def test_sample_changer_abort(beamline):
    assert(beamline.sample_changer.task_proc is not None)
    beamline.sample_changer.abort()
    assert(beamline.sample_changer.task_proc is None)


def test_sample_changer_get_state(beamline):
   state = beamline.sample_changer.get_state()
   assert(not beamline.sample_changer. get_state() is None)
   assert(not beamline.sample_changer.SampleChangerState.STATE_DESC.get(state, "Unknown"))

def test_sample_changer_get_status(beamline):
    assert(beamline.sample_changer.get_status() is not None)

def test_sample_changer_get_loaded_sample(beamline):
    loaded_samples = len(beamline.sample_changer.get_sample_list())
    assert (
        loaded_samples >= 0
    ), "Sample changer len(get_loaded_sample) must be >= 0 but is None (not initialized)"
    assert(beamline.sample_changer.get_loaded_sample())