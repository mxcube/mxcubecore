from HardwareRepository.HardwareObjects.abstract.sample_changer.CatsMaint import (
    CatsMaint,
)


class ALBACatsMaint(CatsMaint):
    def __init__(self, *args):
        CatsMaint.__init__(self, *args)

    def init(self):
        CatsMaint.init(self)

        # load ALBA attributes and commands from XML
        self._chnAtHome = self.getChannelObject("_chnAtHome")
        self.super_abort_cmd = self.getCommandObject("super_abort")

        # channel to ask diffractometer for mounting position
        self.shifts_channel = self.getChannelObject("shifts")

    def _doAbort(self):
        if self.super_abort_cmd is not None:
            self.super_abort_cmd()
        self._cmdAbort()

    def _doResetMemory(self):
        """
        Reset CATS memory.
        """
        # Check do_PRO6_RAH first
        if self._chnAtHome.getValue() is True:
            CatsMaint._doResetMemory(self)

    def _doReset(self):
        """
        Reset CATS system.
        """
        self._cmdAbort()
        self._cmdReset()
        self._doResetMemory()

    def _doOperationCommand(self, cmd, pars):
        """
        Send a CATS command

        @cmd: command
        @pars: command arguments
        """
        CatsMaint._doOperationCommand(self)

    def _get_shifts(self):
        """
        Get the mounting position from the Diffractometer DS.

        @return: 3-tuple
        """
        if self.shifts_channel is not None:
            shifts = self.shifts_channel.getValue()
        else:
            shifts = None
        return shifts


def test_hwo(hwo):
    print(hwo._get_shifts())
