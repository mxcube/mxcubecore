"""ESRF SC3 Sample Changer Hardware Object
"""

import ESRFSC3
import SC3

from mxcubecore.TaskUtils import task


class Command:
    def __init__(self, cmd):
        self.cmd = cmd

    def isSpecConnected(self):
        return True

    @task
    def __call__(self, *args, **kwargs):
        self.cmd(*args, **kwargs)


class ID30SC3(ESRFSC3.ESRFSC3):
    def __init__(self, *args, **kwargs):
        ESRFSC3.ESRFSC3.__init__(self, *args, **kwargs)

    def init(self):
        controller = self.get_object_by_role("controller")

        SC3.SC3.init(self)
        self.prepareCentringAfterLoad = True

        self.prepareCentring = Command(controller.prepare_centring)
        self._moveToLoadingPosition = Command(
            controller.move_to_sample_loading_position
        )
        self._moveToUnloadingPosition = Command(
            controller.move_to_sample_loading_position
        )

    @task
    def unlockMinidiffMotors(self):
        pass
