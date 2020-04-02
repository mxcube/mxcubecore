
def test_motor_methods(beamline):
    assert (
        not beamline.motor is None
    ), "Motor hardware objects is None (not initialized)"

    # set/get value
    target = 100.0
    beamline.motor.set_value(target)
    assert beamline.motor.get_value() == target

    # set/get limits
    target = (-100., 100)
    beamline.motor.set_limits(target)
    asssert eamline.motor.get_limits() == target

    #set/get velocity
    target = 11.
    beamline.motor.set_velocity(target)
    asssert beamline.motor.get_velocity() == target
