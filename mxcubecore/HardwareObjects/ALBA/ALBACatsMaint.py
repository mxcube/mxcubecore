from mxcubecore.HardwareObjects.abstract.sample_changer.CatsMaint import CatsMaint


class ALBACatsMaint(CatsMaint):
    def __init__(self, *args):
        CatsMaint.__init__(self, *args)

    def init(self):
        CatsMaint.init(self)

        # load ALBA attributes and commands from XML
        self._chnAtHome = self.get_channel_object("_chnAtHome")
        self.super_abort_cmd = self.get_command_object("super_abort")

        # channel to ask diffractometer for mounting position
        self.shifts_channel = self.get_channel_object("shifts")

    def _do_abort(self):
        if self.super_abort_cmd is not None:
            self.super_abort_cmd()
        self._cmdAbort()

    def _do_reset_memory(self):
        """
        Reset CATS memory.
        """
        # Check do_PRO6_RAH first
        if self._chnAtHome.get_value() is True:
            CatsMaint._do_reset_memory(self)

    def _do_reset(self):
        """
        Reset CATS system.
        """
        self._cmdAbort()
        self._cmdReset()
        self._do_reset_memory()

    def _do_operation_command(self, cmd, pars):
        """
        Send a CATS command

        @cmd: command
        @pars: command arguments
        """
        CatsMaint._do_operation_command(self)

    def _get_shifts(self):
        """
        Get the mounting position from the Diffractometer DS.

        @return: 3-tuple
        """
        if self.shifts_channel is not None:
            shifts = self.shifts_channel.get_value()
        else:
            shifts = None
        return shifts


def test_hwo(hwo):
    print(hwo._get_shifts())
