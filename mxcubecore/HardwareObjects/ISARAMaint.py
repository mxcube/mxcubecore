from typing import Optional
from tango import DeviceProxy, DevFailed
from mxcubecore.BaseHardwareObjects import HardwareObject

"""
The sample changer maintenance hardware object for ISARA2 robot.

Provide commands for powering on and off the robot. Populates the 'equipment' tab
with a handful of other useful command, while operating the sample changer.

This hardware object assumes that ISARA2 sample changer is exposed
via tango device server implementation as implemented here:
https://gitlab.com/MaxIV/isara/dev-maxiv-isara-ns-09

Example XML configuration for this hardware object:

  <object class="ISARAMaint">
     <tangoname>b312-e/ctl/sm-01</tangoname>
     <polling>400</polling>
  </object>

  tangoname - the sample changers tango device to use
  polling   - optional, sets the polling frequency of device attributes, in milliseconds
"""

DEFAULT_POLLING = 1000


def _reword_isara_error(err_message: str) -> str:
    """
    Reword some of the ISARA error messages to make them easier to understand for the user.
    """
    msg = err_message.lower()
    if msg == "remote mode requested":
        return "it is not in remote mode"

    if msg == "doors must be closed":
        return "hutch is not searched"

    # let's use error as-is
    return msg


def _get_isara_command_error(ex: DevFailed) -> Optional[str]:
    """
    Check if specified exception encodes an ISARA command error.

    Returns the human-readable error message from ISARA, or None
    if this is not an ISARA command error exception.
    """

    # The ISARA command errors are signaled by raising DevError exception,
    # with reason set to 'ISARACommandError' and 'desc' to the error message
    # from ISARA. The DevError will be wrapped inside DevFailed exception by
    # tango.
    #
    # Check if provided exception contains an DevError signalling ISARA command error.
    for err in ex.args:
        if err.reason == "ISARACommandError":
            return _reword_isara_error(err.desc)

    # this is not an ISARA command error exception
    return None


class ISARAMaint(HardwareObject):
    def __init__(self, name):
        super().__init__(name)

        self._commands_state = dict(
            PowerOn=False,
            PowerOff=False,
            openLid=True,
            closeLid=True,
            home=True,
            dry=True,
            soak=True,
            clearMemory=True,
            reset=True,
            back=True,
            abort=True,
        )

        self._powered = None
        self._position_name = None
        self._message = None

    def init(self):
        self.isara_dev = DeviceProxy(self.tangoname)

        polling = self._get_polling()

        self._poll_attribute("Powered", polling, self._powered_updated)
        self._poll_attribute("PositionName", polling, self._position_name_updated)
        self._poll_attribute("Message", polling, self._message_updated)

    def _get_polling(self):
        """
        get polling frequency to use for device attribute poller
        """
        try:
            # polling is specified in the XML file
            return self.polling
        except AttributeError:
            # no polling is specified in the XML, use default polling value
            return DEFAULT_POLLING

    def _poll_attribute(self, attr_name: str, polling: int, callback):
        channel = self.add_channel(
            {
                "type": "tango",
                "name": f"_chn{attr_name}",
                "tangoname": self.tangoname,
                "polling": polling,
            },
            attr_name,
        )

        channel.connect_signal("update", callback)

    def _update_state(self):
        for attr in [self._powered, self._position_name, self._message]:
            if attr is None:
                # some of the values are still unknown,
                # wait until we get all values
                return

        #
        # update 'power' commands
        #
        self._commands_state["PowerOn"] = not self._powered
        self._commands_state["PowerOff"] = self._powered

        #
        # update 'positions' commands
        #
        if not self._powered or self._position_name == "undefined":
            # when powered off or running a trajectory,
            # disable position commands
            self._commands_state["home"] = False
            self._commands_state["dry"] = False
            self._commands_state["soak"] = False
        else:
            self._commands_state["home"] = True
            self._commands_state["dry"] = True
            self._commands_state["soak"] = True

            if self._position_name in ["home", "dry", "soak"]:
                # can't move to same position
                self._commands_state[self._position_name] = False

        self._emit_global_state_changed()

    def _powered_updated(self, powered):
        self._powered = powered
        self._update_state()

    def _position_name_updated(self, position_name):
        self._position_name = position_name.lower()
        self._update_state()

    def _message_updated(self, message):
        self._message = message
        self._update_state()

    def _emit_global_state_changed(self):
        self.emit(
            "globalStateChanged",
            (self._commands_state, self._message),
        )

    def _toggle_power(self, power_on: bool):
        """
        issue powerOn or powerOff commands, catching ISARA command error exception
        """
        command = self.isara_dev.PowerOn if power_on else self.isara_dev.PowerOff

        try:
            command()
        except DevFailed as ex:
            isara_err = _get_isara_command_error(ex)

            # this is not an ISARA command error, pass on the exception
            if isara_err is None:
                raise ex

            state = "on" if power_on else "off"
            raise RuntimeError(f"Can't power {state} sample changer, {isara_err}.")

    def send_command(self, cmd_name, _args=None):
        if cmd_name == "PowerOn":
            self._toggle_power(True)
        elif cmd_name == "PowerOff":
            self._toggle_power(False)
        elif cmd_name == "openLid":
            self.isara_dev.OpenLid()
        elif cmd_name == "closeLid":
            self.isara_dev.CloseLid()
        elif cmd_name == "home":
            self.isara_dev.Home()
        elif cmd_name == "dry":
            self.isara_dev.Dry()
        elif cmd_name == "soak":
            self.isara_dev.Soak()
        elif cmd_name == "clearMemory":
            self.isara_dev.ClearMemory()
        elif cmd_name == "reset":
            self.isara_dev.Reset()
        elif cmd_name == "back":
            self.isara_dev.Back()
        elif cmd_name == "abort":
            self.isara_dev.Abort()
        else:
            raise Exception(f"ISARA MAINT: unexpected command '{cmd_name}'")

    def get_global_state(self):
        return dict(glob_state="dummy"), self._commands_state, self._message

    def get_cmd_info(self):
        return [
            [
                "Power",
                [
                    ["PowerOn", "PowerOn", "Switch Power On"],
                    ["PowerOff", "PowerOff", "Switch Power Off"],
                ],
            ],
            [
                "Lid",
                [
                    ["openLid", "Open Lid", "Open Lid"],
                    ["closeLid", "Close Lid", "Close Lid"],
                ],
            ],
            [
                "Positions",
                [
                    ["home", "Home", "Actions", "Home (trajectory)"],
                    ["dry", "Dry", "Actions", "Dry (trajectory)"],
                    ["soak", "Soak", "Actions", "Soak (trajectory)"],
                ],
            ],
            [
                "Recovery",
                [
                    [
                        "clearMemory",
                        "Clear Memory",
                        "Clear Info in Robot Memory "
                        " (includes info about sample on Diffr)",
                    ],
                    [
                        "reset",
                        "Reset Fault",
                        "Acknowledge security fault",
                    ],
                    [
                        "back",
                        "Back",
                        "Return sample back to Dewar",
                    ],
                ],
            ],
            ["Abort", [["abort", "Abort", "Abort running trajectory"]]],
        ]
