""" NICOS test setup file

Have this setup loaded/working in NICOS server before running the pytests.
"""

description = "NICOS sim devices/PVs"

group = "optional"

devices = dict(
    virtual_motor_1=device(
        "nicos.devices.generic.VirtualMotor",
        description="Virtual motor 1",
        fmtstr="%.2f",
        unit="mm",
        speed=1.0,
        abslimits=(-100, 100),
    ),
    virtual_motor_2=device(
        "nicos.devices.generic.VirtualMotor",
        description="Virtual motor 2",
        fmtstr="%.2f",
        unit="mm",
        speed=1.0,
        abslimits=(-100, 100),
    ),
    virtual_motor_3=device(
        "nicos.devices.generic.VirtualMotor",
        description="Virtual motor 3",
        fmtstr="%.2f",
        unit="mm",
        speed=1.0,
        abslimits=(-100, 100),
    ),
    ioc_actuator_1=device(
        "nicos.devices.epics.pva.EpicsAnalogMoveable",
        readpv="IOC:m1.RBV",
        writepv="IOC:m1.VAL",
        targetpv="IOC:m1.VAL",
    ),
)
