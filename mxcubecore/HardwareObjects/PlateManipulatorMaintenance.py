"""
Plate Manipulator maintenance.
"""

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject


class PlateManipulatorMaintenance(HardwareObject):
    __TYPE__ = "PlateManipulatorMaintenance"

    """
    Actual implementation of the Plate Manipulator MAINTENANCE,
    COMMANDS ONLY
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._scan_limits = ""
        self._sc = None

    def init(self):
        self._sc = HWR.beamline.sample_changer

    def set_plate_barcode(self, args):
        """Plate barcode is set in config, but can be update here"""
        ret = self._sc.change_plate_barcode(args)
        if ret:
            self._update_global_state()

    def _update_global_state(self):
        state_dict, cmd_state, message = self.get_global_state()
        self.emit("globalStateChanged", (state_dict, cmd_state, message))

    def get_global_state(self):
        """Return the gloobal state."""
        state = self._sc._read_state()
        state_dict = {
            "running": state.upper() == "RUNNING",
            "scan_limits": self._scan_limits,
            "state": state,
            "plate_info": self._sc.get_plate_info(),
        }

        cmd_state = {
            "abort": True,
        }

        return state_dict, cmd_state, ""

    def get_cmd_info(self):
        """return information about existing commands for this object
        the information is organized as a list
        with each element contains
        [ cmd_name,  display_name, category ]
        [cmd_id, cmd_display_name, nb_args, cmd_category, description ]
        """

        cmd_list = [
            [
                "Actions",
                [
                    ["abort", "Abort", "Actions", None],
                ],
            ],
        ]

        return cmd_list

    def send_command(self, cmdname, args=None):
        """Send command to the sample changer.
        Args:
            cmdname: The command name
            args: Arguments, if any
        """
        if cmdname in ["getOmegaMotorDynamicScanLimits"]:
            self._scan_limits = self._sc.diffr.scan_limits()
            self._update_global_state()
        if cmdname in ["moveToCrystalPosition"]:
            self._sc.move_to_crystal_position(args)
        if cmdname == "abort":
            self._sc._do_abort()
        if cmdname == "setPlateBarcode":
            self.set_plate_barcode(args)
        # if cmdname == "change_mode":
        #     self._sc._do_change_mode(args)
        return True
