"""
FLEX HCD maintenance mockup.
"""
from HardwareRepository.BaseHardwareObjects import Equipment


TOOL_FLANGE, TOOL_UNIPUCK, TOOL_SPINE, TOOL_PLATE, TOOL_LASER, TOOL_DOUBLE_GRIPPER = (
    0,
    1,
    2,
    3,
    4,
    5,
)

TOOL_TO_STR = {
    "Flange": TOOL_FLANGE,
    "Unipuck": TOOL_UNIPUCK,
    "Rotat": TOOL_SPINE,
    "Plate": TOOL_PLATE,
    "Laser": TOOL_LASER,
    "Double": TOOL_DOUBLE_GRIPPER,
}


class FlexHCDMaintenance(Equipment):

    __TYPE__ = "FLEX_HCD"
    NO_OF_LIDS = 3

    """
    """

    def __init__(self, *args, **kwargs):
        Equipment.__init__(self, *args, **kwargs)

    def init(self):
        self._sc = self.get_object_by_role("sample_changer")

    def get_current_tool(self):
        return self._sc.get_gripper()

    def _do_abort(self):
        """
        Abort current command

        :returns: None
        :rtype: None
        """
        return self._sc._do_abort()

    def _do_home(self):
        """
        Abort current command

        :returns: None
        :rtype: None
        """
        self._sc._do_abort()
        return self._sc._do_reset()

    def _do_reset(self):
        """
        Reset sample changer

        :returns: None
        :rtype: None
        """
        self._sc._do_reset()

    def _do_defreeze_gripper(self):
        """
        :returns: None
        :rtype: None
        """
        self._sc.defreeze()

    def _do_change_gripper(self, args):
        """
        :returns: None
        :rtype: None
        """
        self._sc.change_gripper(gripper=args)

    def _do_reset_sample_number(self):
        """
        :returns: None
        :rtype: None
        """
        self._sc.reset_loaded_sample()

    def _update_global_state(self):
        state_dict, cmd_state, message = self.get_global_state()
        self.emit("globalStateChanged", (state_dict, cmd_state, message))

    def get_global_state(self):
        """
        """
        state = self._sc._read_state()
        ready = self._sc._is_device_busy()
        running = state in ("RUNNING",)

        state_dict = {"running": running, "state": state}

        cmd_state = {
            "home": True,
            "defreeze": True,
            "reset_sample_number": True,
            "change_gripper": True,
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
                    ["home", "Home", "Actions", None],
                    ["defreeze", "Defreeze gripper", "Actions", None],
                    ["reset_sample_number", "Reset sample number", "Actions", None],
                    ["abort", "Abort", "Actions", None],
                ],
            ],
        ]

        try:
            grippers = self._sc.get_available_grippers()
        except Exception:
            pass
        else:
            gripper_cmd_list = []

            for gripper in grippers:
                arg = list(self._sc.gripper_types.keys())[list(self._sc.gripper_types.values()).index(gripper)]
                gripper_cmd_list.append(["change_gripper", gripper.title().replace("_", " "), "Gripper", arg])

            grippers_cmd = ["Gripper: %s" % self._sc.get_gripper().title().replace("_", " "), gripper_cmd_list,]

            cmd_list.append(grippers_cmd)

        return cmd_list

    def send_command(self, cmd_name, args=None):
        tool = self.get_current_tool()

        if cmd_name in ["home"]:
            self._do_home()
        if cmd_name in ["defreeze"]:
            self._do_defreeze_gripper()
        if cmd_name in ["reset_sample_number"]:
            self._do_reset_sample_number()
        if cmdname == "change_gripper":
            self._do_change_gripper(int(args))
        if cmdname == "abort":
            self._do_abort()

        return True
