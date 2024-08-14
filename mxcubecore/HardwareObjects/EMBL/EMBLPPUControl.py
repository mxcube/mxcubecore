import logging

from mxcubecore.BaseHardwareObjects import HardwareObject


__credits__ = ["EMBL Hamburg"]
__category__ = "General"


class EMBLPPUControl(HardwareObject):
    """
    Allows to restart processes on PPU
    """

    def __init__(self, name):
        super().__init__(name)

        self.all_status = None
        self.status_result = None
        self.restart_result = None

        self.error_state = None
        self.is_error = False
        self.file_transfer_in_error = False

        self.cmd_all_status = None
        self.cmd_furka_restart = None
        self.cmd_all_restart = None
        self.chan_all_status = None
        self.chan_file_info = None
        self.chan_all_restart = None

        self.msg = ""

        self.status_running = None
        self.restart_running = None
        self.execution_state = None

    def init(self):
        self.all_status = ""
        self.status_result = ""
        self.restart_result = ""
        self.execution_state = self.get_property("executionState")
        self.error_state = self.get_property("errorState")

        self.chan_all_status = self.get_channel_object("chanAllStatus")

        self.cmd_all_status = self.get_command_object("cmdAllStatus")
        self.cmd_all_restart = self.get_command_object("cmdAllRestart")
        self.cmd_furka_restart = self.get_command_object("cmdFurkaRestart")
        self.cmd_furka_restart("")

        self.get_status()

        self.chan_file_info = self.get_channel_object("chanFileInfo", optional=True)
        if self.chan_file_info is not None:
            self.chan_file_info.connect_signal("update", self.file_info_changed)

        self.connect(self.chan_all_status, "update", self.all_status_changed)

        self.chan_all_restart = self.get_channel_object("chanAllRestart")
        self.connect(self.chan_all_restart, "update", self.all_restart_changed)

    def all_status_changed(self, status):
        """
        Updates status
        :param status: str
        :return:
        """
        if self.status_running and not status:
            self.all_status = self.cmd_all_status.get()  # status
            self.update_status()
        self.status_running = status

    def all_restart_changed(self, status):
        """
        Updates status after all process restart
        :param status:
        :return:
        """
        if self.restart_running and not status:
            self.restart_result = self.cmd_all_restart.get()  # status
        self.restart_running = status

    def file_info_changed(self, values):
        """
        Updated information about transfered frames
        values is a list of 3 values, where the last one indicates the number
        of droped frames
        :param values:
        :return:
        """
        values = list(values)
        # if len(values) == 2:
        #    value = values[1]
        # else:
        #    value = values[0]

        self.file_transfer_in_error = values[2] > 0
        self.emit("fileTranferStatusChanged", (values))

        self.is_error = (
            self.all_status.startswith(self.error_state) or self.file_transfer_in_error
        )

        if self.file_transfer_in_error:
            self.emit("ppuStatusChanged", self.is_error, "File tansfer in error")

    def get_status(self):
        """
        Returns status
        :return: boolean, str
        """
        self.cmd_all_status("")
        return self.is_error, self.all_status

    def update_status(self):
        """
        Update status method
        :return:
        """
        self.is_error = (
            self.all_status.startswith(self.error_state) or self.file_transfer_in_error
        )

        if self.all_status.startswith(self.error_state):
            msg_list = self.all_status.split("\n")
            logging.getLogger("GUI").error("PPU control is in Error state!")
            if len(msg_list) > 1:
                for msg_line in msg_list:
                    if msg_line:
                        msg = "PPU control: %s" % msg_line
                        logging.getLogger("GUI").error(msg)
        else:
            msg = "PPUControl: %s" % self.all_status
            logging.getLogger("HWR").debug(msg)

        self.msg = (
            "Restart result:\n\n%s\n\n" % self.restart_result
            + "All status result:\n\n%s\n" % self.all_status
        )

        self.emit("ppuStatusChanged", self.is_error, self.msg)

        return self.is_error, self.all_status

    def restart_all(self):
        """
        Restarts all processes
        :return:
        """
        self.emit("ppuStatusChanged", False, "Restarting.... ")
        self.cmd_all_restart("")
        self.get_status()

    def re_emit_values(self):
        """
        Reemits signals
        :return:
        """
        self.emit("ppuStatusChanged", self.is_error, self.msg)
