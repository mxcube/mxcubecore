"""
Harvester Maintenance maintenance .
"""
from mxcubecore.BaseHardwareObjects import HardwareObject


class HarvesterMaintenance(HardwareObject):

    __TYPE__ = "HarvesterMaintenance"

    """
    Actual implementation of the Harvester MAINTENANCE,
    COMMANDS ONLY
    """

    def __init__(self, *args, **kwargs):
       super().__init__(*args, **kwargs)

    def init(self):
        self._harvester = self.get_object_by_role("harvester")

    # def get_current_tool(self):
    #     return self._harvester.get_gripper()

    def _do_trash(self):
        """
        Trash sample

        :returns: None
        """
        return self._harvester.trash_sample()
    
    def _transfer_sample(self):
        """
        Transfer sample

        :returns: None
        """
        return self._harvester.transfer_sample()
    
    def _load_plate(self, args):
        """
        Load Plate

        :returns: None
        :args: str
        """
        return self._harvester.load_plate(plate_id=args)
    
    def _set_room_temperature_mode(self, args):
        """
        Set Harvester temperature mode

        :returns: None
        :args: boolean
        """
        value = True if args.lower() in ['true', 'True', '1'] else False
        return self._harvester.set_room_temperature_mode(value)

    def _do_abort(self):
        """
        Abort current command

        :returns: None
        """
        return self._harvester.abort()

    def _do_park(self):
        """
        Abort and Park (Homing) 

        :returns: None
        """
        self._harvester.do_abort()
        return self._harvester.home()


    def _update_global_state(self):
        """
        update global state
        :returns: True
        """
        state_dict, cmd_state, message = self.get_global_state()
        self.emit("globalStateChanged", (state_dict, cmd_state, message))
        return True

    def get_global_state(self):
        """
        update global state
        :returns: True
        """
        state = self._harvester.get_state()
        # ready = self._harvester._is_device_busy()
        running = state in ["RUNNING", "running"]
        plate_ID = self._harvester.get_plate_id()

        state_dict = {
            "running": running,
            "state": state,
            "plate_barecode":plate_ID or 'Null'
        }

        cmd_state = {
            "transfer":True,
            "trash": True,
            "park": True,
            "abort": True,
        }

        message = ""

        return state_dict, cmd_state, message

    def get_cmd_info(self):
        """ return information about existing commands for this object
        """
        """ [cmd_id, cmd_display_name, nb_args, cmd_category, description ] """

        cmd_list = [
            [
                "Actions",
                [
                    ["transfer", "Transfer sample", "Actions", None],
                    ["trash", "Trash sample", "Actions", None],
                    ["park", "Park", "Actions", None],
                    ["abort", "Abort", "Actions", None],
                ],
            ],
        ]

        return cmd_list

    def send_command(self, cmd_name, args=None):
        if cmd_name in ["park"]:
            self._do_park()
        if cmd_name == "trash":
            self._do_trash()
        if cmd_name == "transfer":
            self._transfer_sample()
        if cmd_name == "abort":
            self._do_abort()
        if cmd_name == "loadPlateWithBarcode":
            self._load_plate(args)
        if cmd_name == "set_room_temperature_mode":
            self._set_room_temperature_mode(args)
        return True
