from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.QueueManager import QueueManager


class LNLSQueueManager(QueueManager):
    """
    This class implements a queue manager for LNLS.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSQueueManager.LNLSQueueManager
    configuration: {}
    """

    def init(self):
        super().init()
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")

    def pause(self, state):
        if state:
            self._bluesky_api.pause()
        else:
            self._bluesky_api.resume()
        self.set_pause(state)

    def stop(self):
        self._bluesky_api.abort()
        super().stop()
