"""ESRF SC3 Sample Changer Hardware Object
"""
from HardwareRepository.TaskUtils import task
import SC3
import ESRF.ESRFSC3 as ESRFSC3


class Command:
    def __init__(self, cmd):
        self.cmd = cmd

    def isSpecConnected(self):
        return True

    @task
    def __call__(self, *args, **kwargs):
        self.cmd(*args, **kwargs)


class ESRFMD2SC3(ESRFSC3.ESRFSC3):
    def __init__(self, *args, **kwargs):
        ESRFSC3.ESRFSC3.__init__(self, *args, **kwargs)

    def init(self):
        self.controller = self.get_object_by_role("controller")
        SC3.SC3.init(self)
        self.prepareCentringAfterLoad = True
        # self.prepareCentring = Command(controller.moveToPhase("Centring"))
        # self._moveToLoadingPosition = Command(controller.moveToPhase("Transfer"))
        # self._moveToUnloadingPosition = Command(controller.moveToPhase("Transfer"))

    @task
    def unlockMinidiffMotors(self):
        pass

    @task
    def prepare_centring(self, *args, **kwargs):
        # self.controller.moveToPhase("Centring", wait=True, timeout=1000)
        pass

    @task
    def _moveToLoadingPosition(self, *args, **kwargs):
        # self.controller.moveToPhase("Transfer", wait=True, timeout=10000)
        pass

    @task
    def _moveToUnloadingPosition(self, *args, **kwargs):
        # self.controller.moveToPhase("Transfer", wait=True, timeout=10000)
        pass

    def _getLoadingState(self):
        self.controller._wait_ready(10000)
