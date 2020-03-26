def test_energy_atributes(beamline):
    assert (
        not beamline.energy is None
    ), "Energy hardware objects is None (not initialized)"
    current_energy = beamline.energy.get_value()
    current_wavelength = beamline.energy.get_wavelength()
    energy_limits = beamline.energy.get_limits()
    wavelength_limits = beamline.energy.get_wavelength_limits()

    assert isinstance(current_energy, float), "Energy value has to be float"
    assert isinstance(current_wavelength, float), "Energy value has to be float"
    assert isinstance(
        energy_limits, (list, tuple)
    ), "Energy limits has to be defined as tuple or list"
    assert isinstance(
        wavelength_limits, (list, tuple)
    ), "Energy limits has to be defined as tuple or list"
    assert not None in energy_limits, "One or several energy limits is None"
    assert not None in wavelength_limits, "One or several wavelength limits is None"
    assert (
        energy_limits[0] < energy_limits[1]
    ), "First value of energy limits has to be the low limit"


def test_energy_methods(beamline):
    target = 12.7
    beamline.energy.set_value(target)
    assert beamline.energy.get_value() == target
