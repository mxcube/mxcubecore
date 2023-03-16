"""
Plate Manipulator maintenance.
"""
from mxcubecore.BaseHardwareObjects import Equipment


class PlateManipulatorMaintenance(Equipment):

    __TYPE__ = "PlateManipulatorM"

    """
        Plate Manipulator is treated like a SC
    """

    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)
    
    def init(self):
        self._sc = self.get_object_by_role("sample_changer")
        self._scan_limits = ''

    def _do_abort(self):
        """
        Abort current command

        :returns: None
        :rtype: None
        """
        return self._sc._do_abort()
    
    def _move_to_crystal_position(self, args):
        """
        moveToCrystalPosition current command

        :returns: None
        :rtype: None
        """
        return self._sc.move_to_crystal_position(args)
    

    def _do_change_mode(self, args):
        self._sc._do_change_mode(args)

    def set_plate_barcode(self, args):
        ret = self._sc.change_plate_barcode(args)
        if ret:
            self._update_global_state()

    def _get_scan_limits(self, args):
        """
        Omega Dynamic scan limit current command
        :returns: None
        :rtype: None
        """
        self._scan_limits = self._sc.get_scan_limits(args)
        self.emit("globalStateChanged", (self.get_global_state()))


    def _update_global_state(self):
        state_dict, cmd_state, message = self.get_global_state()
        self.emit("globalStateChanged", (state_dict, cmd_state, message))
    
    def get_global_state(self):
        """
        """
        state = self._sc._read_state()
        scan_limits = self._scan_limits
        # ready = self._sc._ready()
        running = state in ("RUNNING",)
        plate_info_dict =  self._sc.get_plate_info()
        state_dict = {
            "running": running,
            "scan_limits": scan_limits,
            "state": state,
            "plate_info" : plate_info_dict
        }

        cmd_state = {
            "abort": True,
        }

        message = ""

        return state_dict, cmd_state, message

    

    def get_cmd_info(self):
        """ return information about existing commands for this object
           the information is organized as a list
           with each element contains
           [ cmd_name,  display_name, category ]
        """
        """ [cmd_id, cmd_display_name, nb_args, cmd_category, description ] """

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
        if cmdname in ["getOmegaMotorDynamicScanLimits"]:
            self._get_scan_limits(args)
        if cmdname in ["moveToCrystalPosition"]:
            self._move_to_crystal_position(args)
        if cmdname == "abort":
            self._do_abort()
        if cmdname == "setPlateBarcode":
            self.set_plate_barcode(args)
        # if cmdname == "change_mode":
        #     self._do_change_mode(args)      
        return True
