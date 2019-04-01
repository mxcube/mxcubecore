def test_energy_atributes(energy_list):
    for energy in energy_list:
        assert not energy is None, "Energy hardware objects is None (not initialized)"
        current_energy = energy.get_current_energy()
        current_wavelength = energy.get_current_wavelength()
        energy_limits = energy.get_energy_limits()
        wavelength_limits = energy.get_wavelength_limits()

        assert isinstance(current_energy, float), "Energy value has to be float"
        assert isinstance(current_wavelength, float), "Energy value has to be float"
        assert isinstance(energy_limits, (list, tuple)), "Energy limits has to be defined as tuple or list" 
        assert isinstance(wavelength_limits, (list, tuple)), "Energy limits has to be defined as tuple or list"
        assert not None in energy_limits, "One or several energy limits is None"
        assert not None in wavelength_limits, "One or several wavelength limits is None"
        assert energy_limits[0] < energy_limits[1], "First value of energy limits has to be the low limit"
        assert hasattr(energy, "can_move_energy")
        assert hasattr(energy, "move_energy")
        assert hasattr(energy, "move_wavelength")

def test_energy_methods(energy_list):
    for energy in energy_list:
        target = 12.7
        energy.move_energy(target)
        assert energy.get_current_energy() == target
