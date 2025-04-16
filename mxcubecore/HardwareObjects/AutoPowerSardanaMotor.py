#
# Disable 'Invalid module name' check.
#
# We can possibly make module name ruff compliant once we migrated to
# YAML config files. With YAML configs we get more flexibility with module
# names.
#
# ruff: noqa: N999
#

from mxcubecore.HardwareObjects.SardanaMotor import SardanaMotor


class AutoPowerSardanaMotor(SardanaMotor):
    """Adds auto power-on feature to a SardanaMotor.

    This hardware object powers on the underlying motor,
    before it is moved.

    It is assumed that the sardana movable have a boolean
    'PowerOn' property. Setting this property to True will
    power on the underlying motors of the movable.
    """

    def __init__(self, name):
        super().__init__(name)
        self.power_on_channel = None

    def init(self):
        super().init()

        self.power_on_channel = self.add_channel(
            {
                "type": "sardana",
                "name": f"{self.actuator_name}PowerOn",
                "taurusname": self.taurusname,
            },
            "PowerOn",
        )

    def _set_value(self, value):
        # power on the motor
        self.power_on_channel.set_value(True)
        # start the motor movement
        super()._set_value(value)
