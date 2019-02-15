from HardwareRepository import HardwareRepository

def test_hwr_qt(hwr_qt):

    hwr = HardwareRepository.getHardwareRepository(hwr_qt)
    hwr.connect()

    """
    blsetup_hwobj = hwr.getHardwareObject("beamline-setup")
    role_list = ("transmission", "diffractometer", "omega_axis", "kappa_axis",
                 "kappa_phi_axis", "sample_changer", "plate_manipulator",
                 "resolution", "energy", "flux", "beam_info",
                 "session", "lims_client", "data_analysis", "energyscan",
                 "collect", "parallel_processing", "xrf_spectrum", "detector")
    for role in role_list:
        assert hasattr(blsetup_hwobj, "%s_hwobj" % role)
    """
    energy_hwobj = hwr.getHardwareObject("energy-mockup")

    # Energy hwobj
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
