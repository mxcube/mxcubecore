def test_transmission_atributes(transmission_list):
    for transmission in transmission_list:
        assert not transmission is None, "Transmission hardware objects is None (not initialized)"

        transmission_value = transmission.get_transmission()
        transmission_limits = transmission.get_limits()
        transmission_state = transmission.get_state()

        assert isinstance(transmission_value, (int, float)), "Transmission value has to be int or float"
        assert isinstance(transmission_limits, (list, tuple)), "Transmission limits has to be defined as tuple or list" 
        assert not None in transmission_limits, "One or several energy limits is None"
        assert not None in transmission_limits, "One or several wavelength limits is None"
        assert transmission_limits[0] < transmission_limits[1], "First value of transmission limits has to be the low limit"

def test_transmission_methods(transmission_list):
    for transmission in transmission_list:
        target = 50.0
        transmission.set_transmission(target)
        assert transmission.get_transmission() == target
