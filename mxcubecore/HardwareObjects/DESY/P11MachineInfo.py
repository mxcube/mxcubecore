import logging
import gevent
from mxcubecore.HardwareObjects.abstract.AbstractMachineInfo import AbstractMachineInfo
from mxcubecore.HardwareObjects.TangoMachineInfo import TangoMachineInfo


class P11MachineInfo(TangoMachineInfo):
    """MachineInfo for the P11 Beamline, using Tango channels for accelerator data."""

    def init(self):
        """
        Initializes the P11 machine info object.

        This method sets up the Tango channels for 'current', 'message',
        'lifetime', and 'energy', ensuring that all attributes have valid
        Tango channels, and connects signals to update values.

        Raises:
            AttributeError: If any of the Tango channels are not properly set up.
        """
        super().init()

        # Set the Tango channel names to match the device
        self._mach_info_keys = ["current", "message", "lifetime", "energy"]

        # Check if all defined attributes have a valid channel
        self._check_attributes()

        # Connect signals to update attributes when the current changes
        if hasattr(self, "current"):
            self.current.connect_signal("update", self._update_value)

        # Setting initial machine state to READY
        self.update_state(self.STATES.READY)

    def _check_attributes(self, attr_list=None):
        """
        Ensures that all attributes in the configuration have valid Tango channels.

        Args:
            attr_list (list, optional): List of attribute keys to check. Defaults to None.

        Raises:
            AttributeError: If any attribute does not have a valid Tango channel.
        """
        attr_list = attr_list or self._mach_info_keys

        for attr_key in attr_list:
            try:
                if not hasattr(self.get_channel_object(attr_key), "get_value"):
                    attr_list.remove(attr_key)
            except AttributeError:
                attr_list.remove(attr_key)
        self._mach_info_keys = attr_list

    def _update_value(self, value):
        """
        Updates all machine attributes whenever a Tango signal is received.

        Args:
            value (any): The value received from the Tango signal.
        """
        self.update_value()

    def get_current(self) -> float:
        """
        Reads the current from the Tango channel.

        Returns:
            float: The current in milliamps (mA). Returns 0.0 in case of an error.
        """
        try:
            return self.current.get_value()
        except Exception as err:
            logging.getLogger("HWR").exception(f"Error reading current: {err}")
            return 0.0

    def get_message(self) -> str:
        """
        Reads the machine message from the Tango channel.

        Returns:
            str: A string containing the machine message.
                 Returns 'Message unavailable' in case of an error.
        """
        try:
            return self.message.get_value()
        except Exception as err:
            logging.getLogger("HWR").exception(f"Error reading message: {err}")
            return "Message unavailable"

    def get_lifetime(self) -> float:
        """
        Reads the beam lifetime from the Tango channel.

        Returns:
            float: The beam lifetime in hours. Returns 0.0 in case of an error.
        """
        try:
            return self.lifetime.get_value()
        except Exception as err:
            logging.getLogger("HWR").exception(f"Error reading lifetime: {err}")
            return 0.0

    def get_maschine_energy(self) -> float:
        """
        Reads the machine energy from the Tango channel.

        Returns:
            float: The machine energy in GeV. Returns 0.0 in case of an error.
        """
        try:
            return self.energy.get_value()
        except Exception as err:
            logging.getLogger("HWR").exception(f"Error reading energy: {err}")
            return 0.0
