def test_detector_atributes(detector_list):
    for detector in detector_list:
        assert not detector is None, "Detector hardware objects is None (not initialized)"
        current_distance = detector.get_distance()
        distance_limits = detector.get_distance_limits()
        exp_time_limits = detector.get_exposure_time_limits()
        has_shutterless = detector.has_shutterless()

        assert isinstance(current_distance, (int, float)), "Distance value has to be int or float. Now %s, %d" % (str(current_distance))
        assert isinstance(distance_limits, (list, tuple)), "Distance limits has to be defined as a tuple or list"
        assert not None in distance_limits, "One or several distance limits is None"
        assert distance_limits[0] < distance_limits[1], "First value of distance limits has to be the low limit"

        assert hasattr(detector, "set_distance")

def test_detector_methods(detector_list):
    for detector in detector_list:
        target = 600
        detector.set_distance(target)
        assert detector.get_distance() == target
