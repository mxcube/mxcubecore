from HardwareRepository import HardwareRepository

HWR = None

def test_hwr_qt(hwr_qt):
    global HWR
    HWR = HardwareRepository.getHardwareRepository(hwr_qt)
    HWR.connect()

def test_energy():
    energy_hwobj = HWR.getHardwareObject("energy-mockup")

    assert not energy_hwobj is None, "Energy hardware objects is None (not initialized)"
    current_energy = energy_hwobj.get_current_energy()
    current_wavelength = energy_hwobj.get_current_wavelength()
    energy_limits = energy_hwobj.get_energy_limits()
    wavelength_limits = energy_hwobj.get_wavelength_limits()

    assert isinstance(current_energy, float), "Energy value has to be float"
    assert isinstance(current_wavelength, float), "Energy value has to be float"
    assert isinstance(energy_limits, (list, tuple)), "Energy limits has to be defined as tuple or list" 
    assert isinstance(wavelength_limits, (list, tuple)), "Energy limits has to be defined as tuple or list"
    assert not None in energy_limits, "One or several energy limits is None"
    assert not None in wavelength_limits, "One or several wavelength limits is None"
    assert energy_limits[0] < energy_limits[1], "First value of energy limits has to be the low limit"
    assert hasattr(energy_hwobj, "can_move_energy")
    assert hasattr(energy_hwobj, "move_energy")
    assert hasattr(energy_hwobj, "move_wavelength")

def test_transmission():
    pass

def test_resolution():
    pass

def test_detector():
    pass

def test_diffractometer():
    pass

def test_beam_info():
    pass

def test_queue():
    pass
